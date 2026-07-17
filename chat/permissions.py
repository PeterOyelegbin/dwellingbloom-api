from rest_framework.permissions import BasePermission


class IsConversationParticipant(BasePermission):
    """
    Only the tenant on the conversation or the apartment's owner may
    read/write it.
    """
    def has_object_permission(self, request, view, obj):
        # obj is a Conversation
        user = request.user
        return obj.tenant_id == user.id or obj.apartment.owner_id == user.id
