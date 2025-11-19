from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer
from .models import Team, Judge, Criterion, Evaluation, Event


class CriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criterion
        fields = ['id', 'key', 'name', 'description', 'weight', 'order', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_weight(self, value):
        """Validate that weight is between 0 and 1"""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Weight must be between 0 and 1")
        return value


class TeamSerializer(serializers.ModelSerializer):
    members_list = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = [
            'id', 'project_name',
            'team_leader_name', 'team_leader_year', 'team_leader_email', 'team_leader_phone', 'project_domain',
            'short_description', 'members', 'members_list', 'extra_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_members_list(self, obj):
        return obj.members_list


class TeamBasicSerializer(serializers.ModelSerializer):
    """Lightweight serializer for judge endpoints"""
    
    class Meta:
        model = Team
        fields = [
            'id', 'project_name',
            'team_leader_name', 'team_leader_year', 'team_leader_email', 'team_leader_phone', 'project_domain',
            'short_description'
        ]


class JudgeSerializer(serializers.ModelSerializer):
    token_display = serializers.SerializerMethodField()

    class Meta:
        model = Judge
        fields = ['id', 'name', 'organization',
                 'email', 'phone', 'token', 'token_display', 'active', 'created_at']
        read_only_fields = ['token', 'created_at']

    def get_token_display(self, obj):
        """Show token only on creation, not in list views"""
        return str(obj.token) if self.context.get('show_token') else '***'


class JudgeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating judges with auto-generated token"""
    
    class Meta:
        model = Judge
        fields = ['id', 'name', 'organization',
                 'email', 'phone']

    def create(self, validated_data):
        judge = Judge.objects.create(**validated_data)
        return judge


class EvaluationSerializer(serializers.ModelSerializer):
    team = TeamBasicSerializer(read_only=True)
    judge_name = serializers.CharField(source='judge.name', read_only=True)
    
    class Meta:
        model = Evaluation
        fields = ['id', 'team', 'judge', 'judge_name', 'scores', 'total',
                 'general_comment', 'updated_at']
        read_only_fields = ['total', 'updated_at']


class ScoreSubmitSerializer(serializers.Serializer):
    """Serializer for submitting scores"""
    team_id = serializers.IntegerField()
    scores = serializers.DictField(
        child=serializers.DictField(
            child=serializers.CharField(allow_blank=True)
        )
    )
    general_comment = serializers.CharField(required=False, allow_blank=True)
    
    def validate_scores(self, value):
        """Validate scores structure"""
        if not value:
            raise serializers.ValidationError("Scores cannot be empty")
        
        # Validate each score entry
        for criterion_key, score_data in value.items():
            if not isinstance(score_data, dict):
                raise serializers.ValidationError(
                    f"Score for {criterion_key} must be a dict with 'score' key"
                )
            if 'score' not in score_data:
                raise serializers.ValidationError(
                    f"Score for {criterion_key} must include 'score' field"
                )
            try:
                score_val = float(score_data['score'])
                if score_val < 0 or score_val > 5:
                    raise serializers.ValidationError(
                        f"Score for {criterion_key} must be between 0 and 5"
                    )
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    f"Score for {criterion_key} must be a valid number"
                )
        
        return value


class RankingSerializer(serializers.Serializer):
    """Serializer for ranking results"""
    team_id = serializers.IntegerField()
    project_name = serializers.CharField()
    average_score = serializers.DecimalField(max_digits=6, decimal_places=2)
    total_evaluations = serializers.IntegerField()
    criterion_breakdown = serializers.DictField()


class JudgeLoginSerializer(serializers.Serializer):
    """Serializer for judge login"""
    token = serializers.UUIDField()

    def validate(self, data):
        from .models import Judge
        token = data.get('token')
        try:
            judge = Judge.objects.get(token=token, active=True)
        except Judge.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive token")
        return data
