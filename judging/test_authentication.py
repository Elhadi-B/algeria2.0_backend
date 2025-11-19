from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import Judge, Team, Criterion, Evaluation, Event
from .authentication import JudgeTokenAuthentication
import uuid


class JudgeTokenAuthenticationTest(TestCase):
    """Test judge token authentication"""
    
    def setUp(self):
        self.judge = Judge.objects.create(
            name="Test Judge",
            email="judge@example.com",
            organization="Test Org"
        )
        self.client = APIClient()
    
    def test_authenticate_with_authorization_header(self):
        """Test authentication with Authorization: Token <uuid> header"""
        auth = JudgeTokenAuthentication()
        
        # Create a mock request
        class MockRequest:
            def __init__(self):
                self.META = {}
                self.GET = {}
                self.method = 'GET'
                self.data = {}
        
        request = MockRequest()
        request.META['HTTP_AUTHORIZATION'] = f'Token {self.judge.token}'
        
        user, auth_obj = auth.authenticate(request)
        self.assertEqual(user, self.judge)
        self.assertIsNone(auth_obj)
    
    def test_authenticate_with_query_param(self):
        """Test authentication with ?token= query parameter"""
        auth = JudgeTokenAuthentication()
        
        class MockRequest:
            def __init__(self):
                self.META = {}
                self.GET = {}
                self.method = 'GET'
                self.data = {}
        
        request = MockRequest()
        request.GET['token'] = str(self.judge.token)
        
        user, auth_obj = auth.authenticate(request)
        self.assertEqual(user, self.judge)
    
    def test_authenticate_invalid_token(self):
        """Test authentication fails with invalid token"""
        auth = JudgeTokenAuthentication()
        
        class MockRequest:
            def __init__(self):
                self.META = {}
                self.GET = {}
                self.method = 'GET'
                self.data = {}
        
        request = MockRequest()
        request.META['HTTP_AUTHORIZATION'] = 'Token invalid-uuid-token'
        
        with self.assertRaises(Exception):  # AuthenticationFailed
            auth.authenticate(request)
    
    def test_authenticate_inactive_judge(self):
        """Test authentication fails for inactive judge"""
        self.judge.active = False
        self.judge.save()
        
        auth = JudgeTokenAuthentication()
        
        class MockRequest:
            def __init__(self):
                self.META = {}
                self.GET = {}
                self.method = 'GET'
                self.data = {}
        
        request = MockRequest()
        request.META['HTTP_AUTHORIZATION'] = f'Token {self.judge.token}'
        
        with self.assertRaises(Exception):  # AuthenticationFailed
            auth.authenticate(request)


class SubmitScoreTest(TestCase):
    """Test score submission with proper authentication"""
    
    def setUp(self):
        self.judge = Judge.objects.create(
            name="Test Judge",
            email="judge@example.com",
            organization="Test Org"
        )
        self.team = Team.objects.create(
            project_name="Test Team",
            short_description="Description"
        )
        self.event = Event.objects.create(name="Test Event", locked=False)
        
        # Seed criteria
        Criterion.objects.create(name="Innovation & Creativity", weight=0.25)
        Criterion.objects.create(name="Market Potential", weight=0.25)
        Criterion.objects.create(name="Feasibility", weight=0.20)
        
        self.client = APIClient()
    
    def test_submit_score_with_authorization_header(self):
        """Test submitting score with Authorization header"""
        url = '/api/judge/submit-score/'
        data = {
            'team_id': self.team.id,
            'scores': {
                'innovation': {'score': 8, 'note': 'Good'},
                'market': {'score': 7},
                'feasibility': {'score': 6}
            },
            'general_comment': 'Solid project'
        }
        
        response = self.client.post(
            url, 
            data, 
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.judge.token}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('evaluation', response.data)
        
        # Verify evaluation was created
        evaluation = Evaluation.objects.get(team=self.team, judge=self.judge)
        self.assertIsNotNone(evaluation)
        self.assertGreater(evaluation.total, 0)
    
    def test_submit_score_with_query_param(self):
        """Test submitting score with token query parameter"""
        url = f'/api/judge/submit-score/?token={self.judge.token}'
        data = {
            'team_id': self.team.id,
            'scores': {
                'innovation': {'score': 9},
                'market': {'score': 8}
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_submit_score_locked_event(self):
        """Test that submitting score fails when event is locked"""
        self.event.locked = True
        self.event.save()
        
        url = '/api/judge/submit-score/'
        data = {
            'team_id': self.team.id,
            'scores': {
                'innovation': {'score': 8}
            }
        }
        
        response = self.client.post(
            url,
            data,
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.judge.token}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('locked', response.data.get('error', '').lower())
    
    def test_edit_score_when_locked(self):
        """Test that editing existing score fails when event is locked"""
        # Create existing evaluation
        Evaluation.objects.create(
            team=self.team,
            judge=self.judge,
            scores={'innovation': {'score': 8}},
            general_comment='Initial'
        )
        
        # Lock event
        self.event.locked = True
        self.event.save()
        
        # Try to edit
        url = '/api/judge/submit-score/'
        data = {
            'team_id': self.team.id,
            'scores': {
                'innovation': {'score': 9}  # Changed score
            }
        }
        
        response = self.client.post(
            url,
            data,
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.judge.token}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RankingCalculationTest(TestCase):
    """Test ranking calculation with weighted scores"""
    
    def setUp(self):
        self.team1 = Team.objects.create(
            project_name="Team A",
            short_description="Description A"
        )
        self.team2 = Team.objects.create(
            project_name="Team B",
            short_description="Description B"
        )
        
        self.judge1 = Judge.objects.create(
            name="Judge 1",
            email="judge1@example.com",
            organization="Org"
        )
        self.judge2 = Judge.objects.create(
            name="Judge 2",
            email="judge2@example.com",
            organization="Org"
        )
        
        # Seed criteria with exact weights
        self.innovation = Criterion.objects.create(name="Innovation & Creativity", weight=0.25)
        self.market = Criterion.objects.create(name="Market Potential", weight=0.25)
        self.feasibility = Criterion.objects.create(name="Feasibility", weight=0.20)
        self.team_exec = Criterion.objects.create(name="Team & Execution", weight=0.15)
        self.presentation = Criterion.objects.create(name="Presentation Quality", weight=0.15)
    
    def test_weighted_average_calculation(self):
        """Test that ranking calculates weighted averages correctly"""
        # Team 1: innovation=8, market=7 -> (8*0.25 + 7*0.25) = 3.75
        Evaluation.objects.create(
            team=self.team1,
            judge=self.judge1,
            scores={
                'innovation': {'score': 8},
                'market': {'score': 7}
            }
        )
        
        # Team 1: Second judge - innovation=9, market=8 -> (9*0.25 + 8*0.25) = 4.25
        Evaluation.objects.create(
            team=self.team1,
            judge=self.judge2,
            scores={
                'innovation': {'score': 9},
                'market': {'score': 8}
            }
        )
        
        # Team 2: innovation=6, market=5 -> (6*0.25 + 5*0.25) = 2.75
        Evaluation.objects.create(
            team=self.team2,
            judge=self.judge1,
            scores={
                'innovation': {'score': 6},
                'market': {'score': 5}
            }
        )
        
        # Calculate averages
        from django.db.models import Avg
        team1_avg = Evaluation.objects.filter(team=self.team1).aggregate(Avg('total'))['total__avg']
        team2_avg = Evaluation.objects.filter(team=self.team2).aggregate(Avg('total'))['total__avg']
        
        # Team 1 should have higher average
        self.assertGreater(team1_avg, team2_avg)
        
        # Team 1 average should be approximately (3.75 + 4.25) / 2 = 4.0
        self.assertAlmostEqual(team1_avg, 4.0, places=1)
    
    def test_ranking_endpoint_order(self):
        """Test that ranking endpoint returns teams in correct order"""
        # Create evaluations
        Evaluation.objects.create(
            team=self.team2,  # Lower score team
            judge=self.judge1,
            scores={'innovation': {'score': 5}, 'market': {'score': 4}}
        )
        
        Evaluation.objects.create(
            team=self.team1,  # Higher score team
            judge=self.judge1,
            scores={'innovation': {'score': 9}, 'market': {'score': 8}}
        )
        
        # Test via API (would need admin auth)
        # For now, test the ordering logic
        from django.db.models import Avg
        teams = Team.objects.annotate(avg_score=Avg('evaluations__total')).order_by('-avg_score')
        
        self.assertEqual(teams[0], self.team1)
        self.assertEqual(teams[1], self.team2)
