from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer
from .models import Team, Judge, Criterion, Evaluation, Event


class CriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criterion
        fields = ['id', 'key', 'name', 'description', 'weight', 'order', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'key']  # key is now auto-generated
    
    def validate_weight(self, value):
        """Validate that weight is between 0 and 1"""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Weight must be between 0 and 1")
        return value
    
    def validate_order(self, value):
        """Validate that order is unique"""
        # Check if another criterion has the same order
        queryset = Criterion.objects.filter(order=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(f"Un critère avec l'ordre {value} existe déjà.")
        return value
    
    def validate(self, data):
        """Validate that sum of weights doesn't exceed 1"""
        instance = getattr(self, 'instance', None)
        new_weight = float(data.get('weight', instance.weight if instance else 0))
        
        # Get all other criteria weights
        if instance:
            # Update: exclude current instance
            other_criteria = Criterion.objects.exclude(pk=instance.pk)
            total_weight = sum(float(c.weight) for c in other_criteria)
            # For update, subtract the old weight and add new
            old_weight = float(instance.weight)
            new_total = total_weight - old_weight + new_weight
        else:
            # Create: include all existing criteria
            other_criteria = Criterion.objects.all()
            total_weight = sum(float(c.weight) for c in other_criteria)
            new_total = total_weight + new_weight
        
        if new_total > 1:
            raise serializers.ValidationError({
                'weight': f"La somme des poids ne peut pas dépasser 1.0. Poids total avec ce critère: {new_total:.2f}"
            })
        
        return data
    
    def create(self, validated_data):
        """Create criterion with auto-generated key"""
        # Auto-generate key from name (lowercase, replace spaces with underscores)
        name = validated_data.get('name', '')
        key = name.lower().replace(' ', '_').replace('&', '').replace('-', '_')
        # Remove special characters
        key = ''.join(c for c in key if c.isalnum() or c == '_')
        validated_data['key'] = key
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update criterion - regenerate key if name changes"""
        if 'name' in validated_data and validated_data['name'] != instance.name:
            name = validated_data['name']
            key = name.lower().replace(' ', '_').replace('&', '').replace('-', '_')
            key = ''.join(c for c in key if c.isalnum() or c == '_')
            validated_data['key'] = key
        return super().update(instance, validated_data)


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['num_equipe', 'nom_equipe']
        extra_kwargs = {
            'num_equipe': {'required': True},
            'nom_equipe': {'required': True},
        }


class TeamBasicSerializer(serializers.ModelSerializer):
    """Lightweight serializer for judge endpoints"""

    class Meta:
        model = Team
        fields = ['num_equipe', 'nom_equipe']


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
    team_id = serializers.CharField()
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
    num_equipe = serializers.CharField()
    nom_equipe = serializers.CharField()
    average_score = serializers.DecimalField(max_digits=6, decimal_places=2)
    total_evaluations = serializers.IntegerField()
    criterion_breakdown = serializers.DictField()
    rank = serializers.IntegerField(required=False)


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
