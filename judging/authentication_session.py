from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session authentication that doesn't enforce CSRF checks.
    Use this for API endpoints that need to work from different origins.
    """
    
    def enforce_csrf(self, request):
        # Disable CSRF enforcement for this authentication class
        return
