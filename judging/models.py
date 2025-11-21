from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class Event(models.Model):
    """Event model for the pitch judging event"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    date = models.DateTimeField(default=timezone.now)
    locked = models.BooleanField(default=False, help_text="When locked, judges cannot edit scores")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return self.name


class Criterion(models.Model):
    """Fixed criteria for judging with weights"""
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=100, unique=True, blank=True, help_text="Auto-generated unique identifier (e.g., innovation, feasibility)")
    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True, help_text="Description of what judges should evaluate")
    weight = models.DecimalField(max_digits=5, decimal_places=2, 
                                validators=[MinValueValidator(0), MaxValueValidator(1)],
                                help_text="Weight should be between 0 and 1")
    order = models.IntegerField(default=0, unique=True, help_text="Display order in evaluation form - must be unique")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['order'], name='unique_criterion_order')
        ]

    def __str__(self):
        return f"{self.name} (weight: {self.weight})"


class Team(models.Model):
    """Team model limited to team number and name (user managed IDs)"""
    num_equipe = models.CharField(max_length=50, primary_key=True)
    nom_equipe = models.CharField(max_length=255)

    class Meta:
        ordering = ['nom_equipe']

    def __str__(self):
        return f"{self.num_equipe} - {self.nom_equipe}"


class Judge(models.Model):
    """Judge model with token-based authentication"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    # Removed image and image_path fields
    organization = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.organization})"

    def regenerate_token(self):
        """Regenerate a new token for the judge"""
        self.token = uuid.uuid4()
        self.save(update_fields=['token'])
        return self.token


class Evaluation(models.Model):
    """Evaluation model - one per judge-team pair with per-criterion scores"""
    id = models.AutoField(primary_key=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='evaluations')
    judge = models.ForeignKey(Judge, on_delete=models.CASCADE, related_name='evaluations')
    scores = models.JSONField(default=dict, 
                             help_text="Structure: {'innovation': {'score': 8, 'note': 'x'}, ...}")
    total = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    general_comment = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['team', 'judge']]
        ordering = ['-total', '-updated_at']

    def __str__(self):
        return f"{self.judge.name} -> {self.team.nom_equipe}: {self.total}"

    def calculate_total(self):
        """Calculate weighted total from scores and criteria weights"""
        if not self.scores:
            return 0
        
        total = 0
        criteria = {c.name.lower().replace(' ', '_').replace('&', ''): c 
                   for c in Criterion.objects.all()}
        
        for criterion_key, score_data in self.scores.items():
            if isinstance(score_data, dict) and 'score' in score_data:
                score = float(score_data['score'])
                # Normalize criterion key
                criterion_key_normalized = criterion_key.lower().replace(' ', '_').replace('&', '')
                
                # Try to find matching criterion
                criterion = None
                for key, crit in criteria.items():
                    if key in criterion_key_normalized or criterion_key_normalized in key:
                        criterion = crit
                        break
                
                if criterion:
                    total += score * float(criterion.weight)
        
        return round(total, 2)

    def save(self, *args, **kwargs):
        """Override save to calculate total"""
        self.total = self.calculate_total()
        super().save(*args, **kwargs)