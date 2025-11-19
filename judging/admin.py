from django.contrib import admin
from .models import Team, Judge, Criterion, Evaluation, Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'locked', 'created_at']
    list_filter = ['locked', 'date']
    search_fields = ['name']


@admin.register(Criterion)
class CriterionAdmin(admin.ModelAdmin):
    list_display = ['name', 'weight', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['-weight']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['project_name', 'short_description', 'created_at']
    search_fields = ['project_name', 'short_description']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Judge)
class JudgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'email', 'active', 'created_at']
    search_fields = ['name', 'email', 'organization']
    list_filter = ['active', 'created_at']
    readonly_fields = ['token', 'created_at']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields
        return []


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ['team', 'judge', 'total', 'updated_at']
    list_filter = ['updated_at', 'judge']
    search_fields = ['team__project_name', 'judge__name']
    readonly_fields = ['total', 'updated_at']