import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Avg
from .models import Team, Evaluation
import logging

logger = logging.getLogger(__name__)


class RankingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time ranking updates"""
    
    async def connect(self):
        """Join ranking_updates group"""
        logger.info("WebSocket connection attempt")
        self.group_name = 'ranking_updates'
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info("WebSocket connection accepted")
        
        # Send initial ranking on connect
        ranking = await self.get_current_ranking()
        logger.info(f"Sending initial ranking with {len(ranking)} teams")
        await self.send(text_data=json.dumps({
            'type': 'initial_ranking',
            'ranking': ranking
        }))
    
    async def disconnect(self, close_code):
        """Leave ranking_updates group"""
        logger.info(f"WebSocket disconnected with code {close_code}")
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket client"""
        logger.info(f"Received WebSocket message: {text_data}")
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'get_ranking':
            ranking = await self.get_current_ranking()
            await self.send(text_data=json.dumps({
                'type': 'ranking_update',
                'ranking': ranking
            }))
    
    async def ranking_updated(self, event):
        """Handle ranking_updated event from channel layer"""
        logger.info(f"Ranking update event received: {event}")
        # Get updated ranking
        ranking = await self.get_current_ranking()
        
        # Send to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'ranking_update',
            'ranking': ranking,
            'judge_id': event.get('judge_id'),
            'team_id': event.get('team_id'),
            'total': event.get('total')
        }))
        logger.info(f"Sent ranking update with {len(ranking)} teams")
        
        # Send to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'ranking_update',
            'ranking': ranking,
            'judge_id': event.get('judge_id'),
            'team_id': event.get('team_id'),
            'total': event.get('total')
        }))
    
    @database_sync_to_async
    def get_current_ranking(self):
        """Get current ranking with weighted averages"""
        from .models import Criterion
        
        teams = Team.objects.all()
        rankings = []
        
        for team in teams:
            evaluations = Evaluation.objects.filter(team=team)
            
            if not evaluations.exists():
                continue
            
            # Calculate average total score
            avg_score = evaluations.aggregate(avg=Avg('total'))['avg'] or 0
            
            # Calculate criterion breakdown
            criterion_breakdown = {}
            for criterion in Criterion.objects.all():
                criterion_scores = []
                for eval in evaluations:
                    # Try to find score for this criterion in the scores JSON
                    criterion_key = criterion.name.lower().replace(' ', '_').replace('&', '')
                    for key, score_data in eval.scores.items():
                        key_normalized = key.lower().replace(' ', '_').replace('&', '')
                        if criterion_key in key_normalized or key_normalized in criterion_key:
                            if isinstance(score_data, dict) and 'score' in score_data:
                                criterion_scores.append(float(score_data['score']))
                
                if criterion_scores:
                    criterion_breakdown[criterion.name] = {
                        'average': sum(criterion_scores) / len(criterion_scores),
                        'count': len(criterion_scores)
                    }
            
            rankings.append({
                'num_equipe': team.num_equipe,
                'nom_equipe': team.nom_equipe,
                'average_score': str(round(avg_score, 2)),
                'total_evaluations': evaluations.count(),
                'criterion_breakdown': criterion_breakdown
            })
        
        # Sort by average score descending
        rankings.sort(key=lambda x: float(x['average_score']), reverse=True)
        
        # Assign ranks with tie handling
        for i, team in enumerate(rankings):
            # Convert to float for proper comparison
            current_score = float(team['average_score'])
            prev_score = float(rankings[i-1]['average_score']) if i > 0 else None
            
            if i > 0 and current_score == prev_score:
                # Same score as previous team, use same rank
                team['rank'] = rankings[i-1]['rank']
            else:
                # Different score, assign rank based on position (i+1)
                team['rank'] = i + 1
        
        return rankings


class WinnersConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time winners announcements"""
    
    async def connect(self):
        """Join winners_announcements group (no auth required for public)"""
        logger.info("Winners WebSocket connection attempt")
        self.group_name = 'winners_announcements'
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info("Winners WebSocket connection accepted")
    
    async def disconnect(self, close_code):
        """Leave winners_announcements group"""
        logger.info(f"Winners WebSocket disconnected with code {close_code}")
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket client"""
        logger.info(f"Received Winners WebSocket message: {text_data}")
        # Public clients don't send messages, only receive
    
    async def winner_announcement(self, event):
        """Handle winner_announcement event from channel layer"""
        logger.info(f"Winner announcement event received: {event}")
        await self.send(text_data=json.dumps({
            'type': 'winner_announcement',
            'place': event.get('place'),
            'action': event.get('action'),  # 'start_animation', 'reveal'
        }))
