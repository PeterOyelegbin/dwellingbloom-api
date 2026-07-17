from django.db import models
from django.conf import settings
from uuid import uuid4
from properties.models import Apartment


# Create your models here.
class Conversation(models.Model):
    """
    A conversation is scoped to a single apartment listing between the
    tenant who initiated it and the apartment's owner.
    """
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name="conversations")
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="tenant_conversations", limit_choices_to={"role": "TENANT"},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        # one thread per tenant per apartment
        constraints = [
            models.UniqueConstraint(fields=["apartment", "tenant"], name="unique_apartment_tenant_thread")
        ]

    @property
    def owner(self):
        return self.apartment.owner

    def __str__(self):
        return f"{self.tenant} <-> {self.apartment.owner} ({self.apartment.name})"


class Message(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender} @ {self.created_at:%Y-%m-%d %H:%M}"
