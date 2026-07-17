from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Conversation, Message
from .permissions import IsConversationParticipant
from .serializers import (
    ConversationListSerializer, ConversationCreateSerializer,
    MessageSerializer, MessageCreateSerializer,
)


# Create your views here.
@extend_schema(tags=['Conversations'])
class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()
        
        user = self.request.user
        return (
            Conversation.objects.filter(Q(tenant=user) | Q(apartment__owner=user))
            .select_related("apartment", "tenant", "apartment__owner")
            .prefetch_related("messages")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ConversationCreateSerializer
        return ConversationListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        out = ConversationListSerializer(conversation, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="List messages in a conversation, or send a new one (poll this endpoint).",
        request=MessageCreateSerializer, responses=MessageSerializer,
        parameters=[OpenApiParameter(name="id", type=OpenApiTypes.UUID, location=OpenApiParameter.PATH)],
    )
    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        conversation = self.get_object()  # runs has_object_permission

        if request.method == "POST":
            serializer = MessageCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=serializer.validated_data["content"],
            )
            conversation.save(update_fields=["updated_at"])
            return Response(
                MessageSerializer(message).data, status=status.HTTP_201_CREATED
            )

        qs = conversation.messages.select_related("sender")
        # simple polling optimisation: ?after=<message_id created_at ISO>
        after = request.query_params.get("after")
        if after:
            qs = qs.filter(created_at__gt=after)
        return Response(MessageSerializer(qs, many=True).data)

    @extend_schema(
        summary="Mark all messages from the other party as read.",
        parameters=[OpenApiParameter(name="id", type=OpenApiTypes.UUID, location=OpenApiParameter.PATH)],
    )
    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        conversation = self.get_object()
        updated = conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        return Response({"marked_read": updated})
