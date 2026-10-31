from rest_framework import serializers 
from drf_spectacular.utils import extend_schema_field
from .models import LandlordPayoutAccount, EscrowTransaction
from properties.models import Apartment
from properties.serializers import ApartmentSerializer


class LandlordPayoutAccountSerializer(serializers.ModelSerializer):
    """Input: landlord submits bank details. Output: recipient_code."""
    class Meta:
        model = LandlordPayoutAccount
        fields = ["id", "bank_name", "bank_code", "account_number", "account_name", "recipient_code", "created_at"]
        read_only_fields = ["id", "bank_name", "account_name", "recipient_code", "created_at"]

    def validate_account_number(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Account number must be exactly 10 digits.")
        return value

    def validate_bank_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Bank code must be numeric.")
        return value


class EscrowTransactionSerializer(serializers.ModelSerializer):
    """Read-only view of an escrow record (for tenant/landlord dashboards)."""
    apartment = ApartmentSerializer(read_only=True)
    tenant = serializers.StringRelatedField(read_only=True)
    landlord = serializers.StringRelatedField(read_only=True)
    amount_naira = serializers.SerializerMethodField()
    landlord_amount_naira = serializers.SerializerMethodField()
    platform_fee_naira = serializers.SerializerMethodField()

    class Meta:
        model = EscrowTransaction
        fields = [
            "id", "reference", "apartment", "tenant", "landlord", "amount", "amount_naira", "platform_fee", 
            "platform_fee_naira", "landlord_amount", "landlord_amount_naira", "status", "paystack_access_code",
            "paystack_transfer_code", "paid_at", "released_at", "created_at",
        ]

    @extend_schema_field(serializers.FloatField)
    def get_amount_naira(self, obj):
        return obj.amount / 100

    @extend_schema_field(serializers.FloatField)
    def get_landlord_amount_naira(self, obj):
        return obj.landlord_amount / 100

    @extend_schema_field(serializers.FloatField)
    def get_platform_fee_naira(self, obj):
        return obj.platform_fee / 100


class InitiateEscrowSerializer(serializers.Serializer):
    """
    Input for starting an escrow payment.
    We only need the apartment_id from the URL, but we accept an optional
    amount override to guard against tampering with apartment price.
    """
    apartment_id = serializers.UUIDField()

    def validate_apartment_id(self, value):
        try:
            apartment = Apartment.objects.select_related("landlord").get(id=value)
        except Apartment.DoesNotExist:
            raise serializers.ValidationError("Apartment not found.")
        if apartment.landlord is None:
            raise serializers.ValidationError("This apartment has no active landlord and can't receive payments.")
        if not apartment.is_available:
            raise serializers.ValidationError("Apartment is no longer available.")
        if not apartment.is_verified:
            raise serializers.ValidationError("Apartment has not been verified yet.")
        return value


class InitiateEscrowResponseSerializer(serializers.Serializer):
    """Response returned to frontend after initializing payment."""
    reference = serializers.CharField()
    access_code = serializers.CharField()
    authorization_url = serializers.URLField()
    amount_naira = serializers.DecimalField(max_digits=12, decimal_places=2)


class ReleaseEscrowSerializer(serializers.Serializer):
    """Optional confirmation payload when releasing escrow."""
    reason = serializers.CharField(required=False, allow_blank=True, default="Rent payout")


class RefundEscrowSerializer(serializers.Serializer):
    """Optional refund reason."""
    reason = serializers.CharField(required=False, allow_blank=True)
