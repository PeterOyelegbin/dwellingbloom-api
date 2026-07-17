from rest_framework import serializers
# from django.db import models as db_models
from drf_spectacular.utils import extend_schema_field
from .models import Conversation, Message
# from properties.models import Apartment


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "content", "is_read", "created_at"]
        read_only_fields = ["id", "conversation", "sender", "is_read", "created_at"]


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["content"]

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message content can't be empty.")
        return value


class ConversationListSerializer(serializers.ModelSerializer):
    apartment_name = serializers.CharField(source="apartment.name", read_only=True)
    other_party = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "apartment", "apartment_name", "other_party", "last_message", "unread_count", "updated_at"]

    @extend_schema_field(serializers.DictField(child=serializers.CharField(), allow_null=True))
    def get_other_party(self, obj):
        request_user = self.context["request"].user
        other = obj.apartment.owner if request_user.id == obj.tenant_id else obj.tenant
        if other is None:
            return None
        return {"id": str(other.id), "name": f"{other.first_name} {other.last_name}"}

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if not last:
            return None
        return {"content": last.content, "sender": last.sender_id, "created_at": last.created_at}

    @extend_schema_field(serializers.IntegerField())
    def get_unread_count(self, obj):
        request_user = self.context["request"].user
        return obj.messages.filter(is_read=False).exclude(sender=request_user).count()


class ConversationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "apartment"]
        read_only_fields = ["id"]

    def validate_apartment(self, apartment):
        request_user = self.context["request"].user
        if request_user.role != "TENANT":
            raise serializers.ValidationError("Only tenants can start a conversation.")
        if apartment.owner_id == request_user.id:
            raise serializers.ValidationError("You can't message yourself about your own listing.")
        return apartment

    def create(self, validated_data):
        request_user = self.context["request"].user
        conversation, _ = Conversation.objects.get_or_create(
            apartment=validated_data["apartment"], tenant=request_user
        )
        return conversation
