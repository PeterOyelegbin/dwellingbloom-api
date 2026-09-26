from rest_framework.permissions import BasePermission


class IsLandlordRole(BasePermission):
    """Only users with role='LANDLORD' can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "LANDLORD"


class IsLandlordOfApartment(BasePermission):
    """Object-level: user must be the landlord of the apartment, or be admin."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.landlord_id == request.user.id
