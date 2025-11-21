import csv
import json
import logging
from decimal import Decimal
from django.http import HttpResponse
from django.db.models import Avg, Count, Q
from django.db import transaction
from rest_framework import viewsets, status, views
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.decorators import method_decorator
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

logger = logging.getLogger(__name__)

from .models import Team, Judge, Criterion, Evaluation, Event
from .serializers import (
    TeamSerializer, TeamBasicSerializer, JudgeSerializer, JudgeCreateSerializer,
    EvaluationSerializer, ScoreSubmitSerializer, RankingSerializer, CriterionSerializer
)
from .authentication import JudgeTokenAuthentication
from .permissions import IsAdminUser, IsJudgeAuthenticated


@extend_schema_view(
    list=extend_schema(tags=['Teams', 'Admin'], summary='List all teams'),
    retrieve=extend_schema(tags=['Teams', 'Admin'], summary='Get team details'),
    create=extend_schema(tags=['Teams', 'Admin'], summary='Create a new team'),
    update=extend_schema(tags=['Teams', 'Admin'], summary='Update team'),
    partial_update=extend_schema(tags=['Teams', 'Admin'], summary='Partially update team'),
    destroy=extend_schema(tags=['Teams', 'Admin'], summary='Delete team'),
)
class TeamViewSet(viewsets.ModelViewSet):
    """Admin viewset for managing teams"""
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAdminUser]
    authentication_classes = [SessionAuthentication]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    


@extend_schema_view(
    list=extend_schema(tags=['Criteria', 'Admin'], summary='List all criteria'),
    retrieve=extend_schema(tags=['Criteria', 'Admin'], summary='Get criterion details'),
    create=extend_schema(tags=['Criteria', 'Admin'], summary='Create a new criterion'),
    update=extend_schema(tags=['Criteria', 'Admin'], summary='Update criterion'),
    partial_update=extend_schema(tags=['Criteria', 'Admin'], summary='Partially update criterion'),
    destroy=extend_schema(tags=['Criteria', 'Admin'], summary='Delete criterion'),
)
class CriterionViewSet(viewsets.ModelViewSet):
    """Admin viewset for managing evaluation criteria and weights"""
    queryset = Criterion.objects.all()
    serializer_class = CriterionSerializer
    authentication_classes = [SessionAuthentication]
    
    def get_permissions(self):
        """Allow public read access, but require admin for write operations"""
        if self.action in ['list', 'retrieve']:
            return []
        return [IsAdminUser()]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def update(self, request, *args, **kwargs):
        """Update criterion and recalculate all evaluations if weight changed"""
        instance = self.get_object()
        old_weight = instance.weight
        
        response = super().update(request, *args, **kwargs)
        
        # If weight changed, recalculate all evaluations
        if response.status_code == 200:
            # Refresh instance from database to get updated weight
            instance.refresh_from_db()
            new_weight = instance.weight
            if old_weight != new_weight:
                # Recalculate totals for all evaluations
                evaluations = Evaluation.objects.all()
                eval_count = evaluations.count()
                for evaluation in evaluations:
                    evaluation.save()  # This triggers calculate_total() via the model's save method
                
                return Response({
                    **response.data,
                    'message': f'Criterion updated. Recalculated {eval_count} evaluation totals.'
                })
        
        return response
    
    def partial_update(self, request, *args, **kwargs):
        """Partial update criterion and recalculate evaluations if weight changed"""
        return self.update(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(tags=['Evaluations', 'Admin'], summary='List all evaluations'),
    retrieve=extend_schema(tags=['Evaluations', 'Admin'], summary='Get evaluation details'),
    update=extend_schema(tags=['Evaluations', 'Admin'], summary='Update evaluation'),
    partial_update=extend_schema(tags=['Evaluations', 'Admin'], summary='Partially update evaluation'),
    destroy=extend_schema(tags=['Evaluations', 'Admin'], summary='Delete evaluation'),
)
class EvaluationViewSet(viewsets.ModelViewSet):
    """Admin viewset for managing evaluations"""
    queryset = Evaluation.objects.select_related('team', 'judge').all()
    serializer_class = EvaluationSerializer
    permission_classes = [IsAdminUser]
    authentication_classes = [SessionAuthentication]
    
    def get_queryset(self):
        """Allow filtering by team_id or judge_id"""
        queryset = Evaluation.objects.select_related('team', 'judge').all()
        team_id = self.request.query_params.get('team_id', None)
        judge_id = self.request.query_params.get('judge_id', None)
        
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        if judge_id:
            queryset = queryset.filter(judge_id=judge_id)
        
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def update(self, request, *args, **kwargs):
        """Update evaluation - recalculates total automatically"""
        # Note: Admins can update even when event is locked (unlike judges)
        instance = self.get_object()
        
        # Only allow updating scores and general_comment (not team/judge)
        data = request.data.copy()
        # Remove team and judge from update data to prevent changing them
        data.pop('team', None)
        data.pop('judge', None)
        
        serializer = self.get_serializer(instance, data=data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Total is recalculated automatically via Evaluation.save() in the model
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """Partial update evaluation - recalculates total automatically"""
        return self.update(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Create evaluation - validates unique team/judge pair"""
        # Check if evaluation already exists for this team/judge pair
        team_id = request.data.get('team')
        judge_id = request.data.get('judge')
        
        if team_id and judge_id:
            if Evaluation.objects.filter(team_id=team_id, judge_id=judge_id).exists():
                return Response(
                    {'error': 'Evaluation already exists for this team/judge pair.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        response = super().create(request, *args, **kwargs)
        
        # Total is recalculated automatically via Evaluation.save() in the model
        return response


@extend_schema_view(
    list=extend_schema(tags=['Judges', 'Admin'], summary='List all judges'),
    retrieve=extend_schema(tags=['Judges', 'Admin'], summary='Get judge details'),
    create=extend_schema(tags=['Judges', 'Admin'], summary='Create a new judge'),
    update=extend_schema(tags=['Judges', 'Admin'], summary='Update judge'),
    partial_update=extend_schema(tags=['Judges', 'Admin'], summary='Partially update judge'),
    destroy=extend_schema(tags=['Judges', 'Admin'], summary='Delete judge'),
)
class JudgeViewSet(viewsets.ModelViewSet):
    """Admin viewset for managing judges"""
    queryset = Judge.objects.all()
    serializer_class = JudgeSerializer
    permission_classes = [IsAdminUser]
    authentication_classes = [SessionAuthentication]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return JudgeCreateSerializer
        return JudgeSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        # Show token in detail view
        if self.action == 'retrieve':
            context['show_token'] = True
        return context
    
    @extend_schema(
        tags=['Judges', 'Admin'],
        summary='Regenerate judge token',
        responses={200: {'description': 'Token regenerated successfully'}}
    )
    @action(detail=True, methods=['post'])
    def regenerate_token(self, request, pk=None):
        """Regenerate token for a judge"""
        judge = self.get_object()
        new_token = judge.regenerate_token()
        return Response({
            'judge_id': judge.id,
            'token': str(new_token),
            'message': 'Token regenerated successfully'
        })


@extend_schema(
    tags=['Judges', 'Admin'],
    summary='Create a new judge',
    description='Create a new judge and return their token login link',
    request=JudgeCreateSerializer,
    responses={201: JudgeSerializer}
)
@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAdminUser])
def create_judge(request):
    """Create judge endpoint - returns token link"""
    serializer = JudgeCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    judge = serializer.save()
    
    base_url = request.build_absolute_uri('/').rstrip('/')
    login_url = f"{base_url}/judge/login?token={judge.token}"
    
    return Response({
        'judge': JudgeSerializer(judge, context={'request': request, 'show_token': True}).data,
        'token': str(judge.token),
        'login_link': login_url,
        'message': 'Judge created successfully'
    }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Judges', 'Admin'],
    summary='Regenerate judge token',
    description='Generate a new token for an existing judge',
    responses={200: {'description': 'Token regenerated successfully'}}
)
@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAdminUser])
def regenerate_judge_token(request, judge_id):
    """Regenerate token for a judge"""
    try:
        judge = Judge.objects.get(id=judge_id)
    except Judge.DoesNotExist:
        return Response({'error': 'Judge not found'}, status=status.HTTP_404_NOT_FOUND)
    
    new_token = judge.regenerate_token()
    base_url = request.build_absolute_uri('/').rstrip('/')
    login_url = f"{base_url}/judge/login?token={new_token}"
    
    return Response({
        'judge_id': judge.id,
        'token': str(new_token),
        'login_link': login_url,
        'message': 'Token regenerated successfully'
    })


@extend_schema(
    tags=['Teams', 'Admin'],
    summary='Upload teams from CSV',
    description='Upload teams from CSV file with preview mode. Set commit=true to actually import.',
    request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}, 'commit': {'type': 'string', 'default': 'false'}}}},
    responses={200: {'description': 'Preview or import result'}}
)
@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAdminUser])
def upload_teams(request):
    """CSV/JSON import endpoint with preview - matches new CSV format"""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    file = request.FILES['file']
    commit = request.data.get('commit', 'false').lower() == 'true'
    
    preview_rows = []
    errors = []
    
    try:
        # Try CSV first
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        
        rows = []
        for idx, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            errors_row = []
            
            # Map CSV columns to model fields
            # Handle column name variations (with/without spaces, case insensitive)
            project_title = row.get('Project Title', '').strip()
            if not project_title:
                # Try alternative column names
                project_title = row.get('project_title', '').strip() or row.get('ProjectTitle', '').strip()
            
            team_leader_name = row.get('Team Leader: Full Name', '').strip()
            if not team_leader_name:
                team_leader_name = row.get('Team Leader: Full Name', '').strip() or row.get('team_leader_full_name', '').strip()
            
            team_leader_year = row.get('Team Leader: Year of Study', '').strip()
            if not team_leader_year:
                team_leader_year = row.get('team_leader_year_of_study', '').strip()
            
            team_leader_email = row.get('Team Leader: Email address', '').strip()
            if not team_leader_email:
                team_leader_email = row.get('team_leader_email_address', '').strip()
            
            team_leader_phone = row.get('Team Leader: Phone Number', '').strip()
            if not team_leader_phone:
                team_leader_phone = row.get('team_leader_phone_number', '').strip()
            
            # Team members - handle the long column name
            team_members_key = None
            for key in row.keys():
                if 'Team Members' in key or 'team_members' in key.lower():
                    team_members_key = key
                    break
            team_members = row.get(team_members_key, '').strip() if team_members_key else ''
            
            project_domain = row.get('Project Domain', '').strip()
            if not project_domain:
                project_domain = row.get('project_domain', '').strip()
            
            project_summary_key = None
            for key in row.keys():
                if 'Project Summary' in key or 'project_summary' in key.lower():
                    project_summary_key = key
                    break
            project_summary = row.get(project_summary_key, '').strip() if project_summary_key else ''
            
            # Validate required fields
            if not project_title:
                errors_row.append(f"Row {idx}: Missing Project Title")
            
            if not project_summary:
                errors_row.append(f"Row {idx}: Missing Project Summary")
            
            if errors_row:
                errors.extend(errors_row)
                continue
            
            # Build team data
            team_data = {
                'project_name': project_title,
                'team_leader_name': team_leader_name,
                'team_leader_year': team_leader_year,
                'team_leader_email': team_leader_email,
                'team_leader_phone': team_leader_phone,
                'project_domain': project_domain,
                'short_description': project_summary,
                'members': team_members,
                'extra_info': {}
            }
            
            preview_rows.append(team_data)
            if commit:
                rows.append(team_data)
        
        if commit and not errors:
            created = []
            for team_data in rows:
                project_name = team_data.get('project_name', '')
                # Check if team with this project_name already exists
                if Team.objects.filter(project_name=project_name).exists():
                    errors.append(f"Équipe avec le nom de projet '{project_name}' existe déjà. Ignoré.")
                    continue
                try:
                    team = Team.objects.create(**team_data)
                    created.append({'id': team.id, 'project_name': team.project_name})
                except Exception as e:
                    errors.append(f"Erreur lors de la création de l'équipe '{project_name}': {str(e)}")
            
            return Response({
                'message': f'Successfully imported {len(created)} teams',
                'created': created,
                'errors': errors
            })
        else:
            return Response({
                'preview_rows': preview_rows[:10],  # Show first 10
                'total_rows': len(preview_rows),
                'errors': errors,
                'commit': commit,
                'message': 'Preview mode. Set commit=true to import.'
            })
    
    except Exception as e:
        return Response({
            'error': f'Failed to process file: {str(e)}',
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Evaluations', 'Admin'],
    summary='Get ranking',
    description='Get aggregated ranking with weighted averages. Can filter by criterion or judge.',
    parameters=[
        OpenApiParameter(name='criterion', description='Filter by criterion name', required=False, type=str),
        OpenApiParameter(name='judge', description='Filter by judge ID', required=False, type=int),
    ],
    responses={200: RankingSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_ranking(request):
    """Get aggregated ranking with weighted averages"""
    criterion_filter = request.GET.get('criterion')
    judge_filter = request.GET.get('judge')
    
    # Get all teams with their evaluations
    teams = Team.objects.all()
    
    rankings = []
    for team in teams:
        evaluations = Evaluation.objects.filter(team=team)
        
        if judge_filter:
            evaluations = evaluations.filter(judge_id=judge_filter)
        
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
            'team_id': team.id,
            'project_name': team.project_name,
            'average_score': round(Decimal(avg_score), 2),
            'total_evaluations': evaluations.count(),
            'criterion_breakdown': criterion_breakdown,
            'image_url': None  # Images removed
        })
    
    # Sort by average score descending
    rankings.sort(key=lambda x: x['average_score'], reverse=True)
    
    serializer = RankingSerializer(rankings, many=True)
    return Response(serializer.data)


@extend_schema(
    tags=['Admin'],
    summary='Export results as CSV',
    description='Export all evaluations as CSV file with new format: one row per team with all judge evaluations',
    responses={200: {'description': 'CSV file download'}}
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def export_csv(request):
    """Export all evaluations as CSV - one row per team with all judge evaluations"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="judging_results.csv"'
    
    writer = csv.writer(response)
    
    # Get all criteria ordered by order field
    criteria = Criterion.objects.all().order_by('order', 'name')
    
    # Get all teams with their evaluations
    teams = Team.objects.all().prefetch_related('evaluations__judge')
    
    # Get all judges to determine max number of judges
    all_judges = Judge.objects.all()
    max_judges = max([team.evaluations.count() for team in teams] + [0])
    
    # Build dynamic header
    header = ['project_id', 'project_name', 'avg_score']
    
    # Add columns for each judge (up to max_judges)
    for judge_num in range(1, max_judges + 1):
        header.append(f'judge_{judge_num}_name')
        # Add criterion score columns for this judge (no notes)
        for criterion in criteria:
            header.append(f'judge_{judge_num}_{criterion.name}_score')
        header.append(f'judge_{judge_num}_general_comment')
    
    # Add team leader and members info
    header.extend(['team_leader_name', 'team_leader_email', 'team_leader_phone', 'team_members'])
    writer.writerow(header)
    
    # Calculate average scores per team
    from django.db.models import Avg
    team_averages = {}
    for team in teams:
        avg = Evaluation.objects.filter(team=team).aggregate(Avg('total'))['total__avg']
        team_averages[team.id] = round(float(avg), 2) if avg else 0
    
    # Write data rows - one per team
    for team in teams:
        evaluations = team.evaluations.select_related('judge').all().order_by('judge__name')
        
        # Build row data
        row = [
            team.id,
            team.project_name,
            team_averages.get(team.id, 0),
        ]
        
        # Add judge evaluations
        for eval in evaluations:
            row.append(eval.judge.name)
            
            # Add scores for each criterion (no notes)
            scores = eval.scores or {}
            for criterion in criteria:
                # Try to match criterion by name
                criterion_data = None
                criterion_key = criterion.name.lower().replace(' ', '_').replace('&', '')
                for key, value in scores.items():
                    key_normalized = key.lower().replace(' ', '_').replace('&', '')
                    if criterion_key in key_normalized or key_normalized in criterion_key:
                        criterion_data = value
                        break
                
                if criterion_data and isinstance(criterion_data, dict):
                    row.append(criterion_data.get('score', ''))
                else:
                    row.append('')
            
            # Add general comment
            row.append(eval.general_comment)
        
        # Fill remaining judge columns if team has fewer evaluations than max
        num_judges = evaluations.count()
        if num_judges < max_judges:
            # Add empty columns for missing judges
            for _ in range(max_judges - num_judges):
                row.append('')  # judge name
                for _ in criteria:
                    row.append('')  # each criterion score
                row.append('')  # general comment
        
        # Add team leader info and members
        row.extend([
            team.team_leader_name or '',
            team.team_leader_email or '',
            team.team_leader_phone or '',
            team.members or ''
        ])
        
        writer.writerow(row)
    
    return response


@extend_schema(
    tags=['Admin'],
    summary='Export results as PDF',
    description='PDF export (not yet implemented)',
    responses={200: {'description': 'Stub response'}}
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def export_pdf(request):
    """PDF export stub - returns message for now"""
    return Response({
        'message': 'PDF export not yet implemented. Use CSV export instead.',
        'csv_endpoint': '/admin/export/csv/'
    })


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(views.APIView):
    """Issue a CSRF cookie for API clients"""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        from django.middleware.csrf import get_token
        return Response({'csrfToken': get_token(request)})


@method_decorator(csrf_protect, name='dispatch')
class AdminLoginView(views.APIView):
    """Admin login endpoint - alternative to Django admin login"""
    permission_classes = []
    authentication_classes = []
    
    def post(self, request):
        from django.contrib.auth import authenticate, login
        
        try:
            # Handle both JSON and form data
            if hasattr(request, 'data'):
                username = request.data.get('username')
                password = request.data.get('password')
            else:
                username = request.POST.get('username')
                password = request.POST.get('password')
            
            if not username or not password:
                return Response({'error': 'Username and password required'}, status=status.HTTP_400_BAD_REQUEST)
            
            user = authenticate(request, username=username, password=password)
            if user and user.is_staff:
                login(request, user)
                return Response({
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'is_staff': user.is_staff
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid credentials or not a staff user'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Login failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Judge endpoints

@extend_schema(
    tags=['Judge'],
    summary='Judge login',
    description='Login with judge token. Sets session cookie for subsequent requests.',
    request={'application/json': {'type': 'object', 'properties': {'token': {'type': 'string', 'format': 'uuid'}}}},
    responses={200: {'description': 'Login successful'}, 401: {'description': 'Invalid token'}}
)
class JudgeLoginView(views.APIView):
    """Judge login with token - sets session cookie"""
    permission_classes = []
    authentication_classes = []
    
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            judge = Judge.objects.get(token=token, active=True)
            # Set session for judge
            request.session['judge_id'] = judge.id
            request.session['judge_token'] = str(judge.token)
            
            serializer = JudgeSerializer(judge, context={'request': request, 'show_token': True})
            return Response({
                'judge': serializer.data,
                'message': 'Login successful'
            })
        except Judge.DoesNotExist:
            return Response({'error': 'Invalid or inactive token'}, status=status.HTTP_401_UNAUTHORIZED)


@extend_schema(
    tags=['Judge'],
    summary='List teams',
    description='List all teams available for evaluation',
    parameters=[
        OpenApiParameter(name='token', description='Judge token (can also use Authorization header)', required=True, type=str, location=OpenApiParameter.QUERY),
    ],
    responses={200: TeamBasicSerializer(many=True)}
)
class JudgeTeamsView(views.APIView):
    """List teams for judges to evaluate"""
    authentication_classes = [JudgeTokenAuthentication]
    permission_classes = [IsJudgeAuthenticated]
    
    def get(self, request):
        teams = Team.objects.all()
        serializer = TeamBasicSerializer(teams, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema(
    tags=['Judge', 'Evaluations'],
    summary='Get evaluation',
    description='Get existing evaluation for a specific team',
    parameters=[
        OpenApiParameter(name='token', description='Judge token (can also use Authorization header)', required=True, type=str, location=OpenApiParameter.QUERY),
    ],
    responses={200: EvaluationSerializer, 404: {'description': 'No evaluation found'}}
)
class JudgeEvaluationView(views.APIView):
    """Get existing evaluation for a team"""
    authentication_classes = [JudgeTokenAuthentication]
    permission_classes = [IsJudgeAuthenticated]
    
    def get(self, request, team_id):
        judge = request.user
        
        try:
            evaluation = Evaluation.objects.get(team_id=team_id, judge=judge)
            serializer = EvaluationSerializer(evaluation, context={'request': request})
            return Response(serializer.data)
        except Evaluation.DoesNotExist:
            return Response({'message': 'No evaluation found for this team'})


@extend_schema(
    tags=['Judge', 'Evaluations'],
    summary='Submit score',
    description='Submit or update evaluation score. Locked events prevent submissions/edits.',
    request=ScoreSubmitSerializer,
    parameters=[
        OpenApiParameter(name='token', description='Judge token (can also use Authorization header)', required=True, type=str, location=OpenApiParameter.QUERY),
    ],
    responses={
        200: {'description': 'Score submitted successfully'},
        403: {'description': 'Event is locked'},
        400: {'description': 'Validation error'}
    }
)
class SubmitScoreView(views.APIView):
    """Submit or update evaluation score"""
    authentication_classes = [JudgeTokenAuthentication]
    permission_classes = [IsJudgeAuthenticated]
    
    def post(self, request):
        judge = request.user
        
        # Check if event is locked
        event = Event.objects.first()  # Assuming single active event
        if event and event.locked:
            return Response({'error': 'Results are locked. Cannot submit scores.'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        serializer = ScoreSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        team_id = serializer.validated_data['team_id']
        scores = serializer.validated_data['scores']
        general_comment = serializer.validated_data.get('general_comment', '')
        
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if evaluation already exists (to prevent edits when locked)
        try:
            evaluation = Evaluation.objects.get(team=team, judge=judge)
            # Check if event is locked before allowing edit
            if event and event.locked:
                return Response({'error': 'Results are locked. Cannot edit scores.'}, 
                               status=status.HTTP_403_FORBIDDEN)
            # Update existing evaluation
            evaluation.scores = scores
            evaluation.general_comment = general_comment
            evaluation.save()
        except Evaluation.DoesNotExist:
            # Create new evaluation
            evaluation = Evaluation.objects.create(
                team=team,
                judge=judge,
                scores=scores,
                general_comment=general_comment
            )
        
        # Broadcast WebSocket update
        channel_layer = get_channel_layer()
        logger.info(f"Channel layer: {channel_layer}")
        if channel_layer:
            logger.info(f"Broadcasting WebSocket update for team {team.id}, judge {judge.id}")
            try:
                async_to_sync(channel_layer.group_send)(
                    'ranking_updates',
                    {
                        'type': 'ranking_updated',
                        'judge_id': judge.id,
                        'team_id': team.id,
                        'total': float(evaluation.total)
                    }
                )
                logger.info("WebSocket broadcast sent successfully")
            except Exception as e:
                logger.error(f"Failed to send WebSocket broadcast: {e}")
        else:
            logger.warning("Channel layer is None, WebSocket broadcast skipped")
        
        return Response({
            'message': 'Score submitted successfully',
            'evaluation': {
                'team_id': team.id,
                'total': evaluation.total,
                'scores': evaluation.scores,
                'general_comment': evaluation.general_comment
            }
        })