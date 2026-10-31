from django.db import models
from django.core.exceptions import ValidationError
from uuid import uuid4
from authentication.models import UserModel
from properties.models import Apartment


# Create your models here.
class LandlordPayoutAccount(models.Model):
    """
    Stores the Landlord's bank details for Paystack transfers with the resulting recipient_code once created.
    """
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    user = models.OneToOneField(UserModel, on_delete=models.CASCADE, related_name="payout_account")
    bank_name = models.CharField(max_length=255)        # returned/verified by Paystack
    bank_code = models.CharField(max_length=10)         # e.g. "058" for GTBank
    account_number = models.CharField(max_length=10)
    account_name = models.CharField(max_length=100) # returned/verified by Paystack
    recipient_code = models.CharField(max_length=100, blank=True)   # from Paystack
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payout profile for {self.user}"


class EscrowTransaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Payment"
        HELD = "HELD", "Held in Escrow"
        RELEASED = "RELEASED", "Released to Landlord"
        REFUNDED = "REFUNDED", "Refunded to Tenant"
        DISPUTED = "DISPUTED", "Disputed"
        FAILED = "failed", "Payment failed"

    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    apartment = models.ForeignKey(Apartment, on_delete=models.PROTECT, related_name="escrow_transactions")
    tenant = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="escrow_payments")
    landlord = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name="escrow_payouts")
    amount = models.PositiveBigIntegerField()          # total in kobo (Paystack uses kobo)
    platform_fee = models.PositiveBigIntegerField(default=0)
    landlord_amount = models.PositiveBigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paystack_access_code = models.CharField(max_length=100, blank=True)
    paystack_transfer_code = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"escrow_{uuid4().hex[:16]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"EscrowTransaction({self.id}) {self.status} ₦{self.amount} — {self.apartment.name}"
