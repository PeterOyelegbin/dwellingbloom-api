from rest_framework.permissions import BasePermission


class IsOwnerRole(BasePermission):
    """Only users with role='OWNER' can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "OWNER"


class IsOwnerOfApartment(BasePermission):
    """Object-level: user must own the apartment, or be admin."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.owner_id == request.user.id
