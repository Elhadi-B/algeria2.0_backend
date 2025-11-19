from rest_framework import permissions


class IsStaffOrReadOnly(permissions.BasePermission):
    """Allow staff users full access, read-only for others"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsAdminUser(permissions.BasePermission):
    """Require staff/admin authentication (works with Django admin session)"""
    
    def has_permission(self, request, view):
        # Check if user is authenticated and is staff (Django admin)
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_staff
        )


class IsJudgeAuthenticated(permissions.BasePermission):
    """Require judge token authentication"""
    
    def has_permission(self, request, view):
        from .models import Judge
        return isinstance(request.user, Judge) and request.user is not None
