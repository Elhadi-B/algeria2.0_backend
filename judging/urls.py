from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'admin/teams', views.TeamViewSet, basename='team')
router.register(r'admin/judges', views.JudgeViewSet, basename='judge')
router.register(r'admin/criteria', views.CriterionViewSet, basename='criterion')
router.register(r'admin/evaluations', views.EvaluationViewSet, basename='evaluation')

urlpatterns = [
    # CSRF token endpoint
    path('security/csrf/', views.CSRFTokenView.as_view(), name='get-csrf-token'),
    
    # Admin endpoints
    path('admin/login/', views.AdminLoginView.as_view(), name='admin-login'),
    path('admin/logout/', views.AdminLogoutView.as_view(), name='admin-logout'),
    path('admin/create-judge/', views.create_judge, name='create-judge'),
    path('admin/regenerate-token/<int:judge_id>/', views.regenerate_judge_token, name='regenerate-token'),
    path('admin/upload-teams/', views.upload_teams, name='upload-teams'),
    path('admin/ranking/', views.admin_ranking, name='admin-ranking'),
    path('admin/announce-winner/', views.announce_winner, name='announce-winner'),
    path('admin/export/csv/', views.export_csv, name='export-csv'),
    path('admin/export/pdf/', views.export_pdf, name='export-pdf'),
    
    # Public endpoints
    path('public/ranking/', views.public_ranking, name='public-ranking'),
    
    # Judge endpoints
    path('judge/login/', views.JudgeLoginView.as_view(), name='judge-login'),
    path('judge/teams/', views.JudgeTeamsView.as_view(), name='judge-teams'),
    path('judge/evaluation/<int:team_id>/', views.JudgeEvaluationView.as_view(), name='judge-evaluation'),
    path('judge/submit-score/', views.SubmitScoreView.as_view(), name='submit-score'),
    
    # Include router URLs
    path('', include(router.urls)),
]
