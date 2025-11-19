import uuid
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Judge


class JudgeTokenAuthentication(authentication.BaseAuthentication):
    """Token-based authentication for judges - supports query param or Authorization header"""
    
    def authenticate(self, request):
        token = None
        
        # Priority 1: Check Authorization header (Token <uuid>)
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            token = auth_header.split(' ', 1)[1].strip()
        elif auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1].strip()
        
        # Priority 2: Check query parameter (?token=...)
        if not token:
            token = request.GET.get('token') or request.query_params.get('token')
        
        # Priority 3: Check POST data (for login endpoint)
        if not token and request.method == 'POST':
            if hasattr(request, 'data') and isinstance(request.data, dict):
                token = request.data.get('token')
        
        if not token:
            return None
        
        # Validate UUID format
        try:
            token_uuid = uuid.UUID(str(token))
        except (ValueError, AttributeError):
            raise AuthenticationFailed('Invalid token format')
        
        try:
            judge = Judge.objects.get(token=token_uuid, active=True)
            return (judge, None)  # (user, auth) tuple
        except Judge.DoesNotExist:
            raise AuthenticationFailed('Invalid or inactive token')
