from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.conf import settings
from django.db import transaction, models
from django.utils import timezone
from utils.logger_config import general_logger
from .models import Apartment, EscrowTransaction, LandlordPayoutAccount
from .serializers import (
    EscrowTransactionSerializer, InitiateEscrowSerializer, InitiateEscrowResponseSerializer,
    LandlordPayoutAccountSerializer, ReleaseEscrowSerializer, RefundEscrowSerializer,
)
from . import paystack_client as paystack


@extend_schema(tags=['Users'])
class PayoutAccountViewSet(viewsets.ViewSet):
    """
    Landlord manages their bank payout account.
    Custom actions only — no list/create/retrieve since it's per-user.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LandlordPayoutAccountSerializer, responses=LandlordPayoutAccountSerializer)
    @action(detail=False, methods=["get", "post"], url_path="me")
    def me(self, request):
        if request.user.role == 'TENANT':
            return Response(
                {'success': False, 'status': 403, 'message': 'Only landlords can manage payout accounts'},
                status=status.HTTP_403_FORBIDDEN
            )
        if request.method == "GET":
            try:
                account = request.user.payout_account
            except LandlordPayoutAccount.DoesNotExist:
                return Response(
                    {'success': False, 'status': 404, 'message': 'No payout account set.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(LandlordPayoutAccountSerializer(account).data)

        # POST — create or update
        serializer = LandlordPayoutAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = paystack.create_transfer_recipient(
            name=(request.user.first_name + " " + request.user.last_name).strip(),
            account_number=data["account_number"],
            bank_code=data["bank_code"],
        )
        if not result.get("status"):
            return Response(
                {'success': False, 'status': 400, 'message': result.get("message", "Could not create recipient")},
                status=status.HTTP_400_BAD_REQUEST
            )
        payout, _ = LandlordPayoutAccount.objects.update_or_create(
            user=request.user,
            defaults={
                "bank_name": result["data"]["details"]["bank_name"],
                "bank_code": data["bank_code"],
                "account_number": data["account_number"],
                "account_name": result["data"]["details"]["account_name"],
                "recipient_code": result["data"]["recipient_code"],
            },
        )
        return Response(LandlordPayoutAccountSerializer(payout).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Escrows'])
@extend_schema_view(
    retrieve=extend_schema(parameters=[OpenApiParameter(name="reference", type=OpenApiTypes.STR, location=OpenApiParameter.PATH, description="Escrow reference (e.g. escrow_abc123...)")]),
    release=extend_schema(parameters=[OpenApiParameter(name="reference", type=OpenApiTypes.STR, location=OpenApiParameter.PATH)]),
    refund=extend_schema(parameters=[OpenApiParameter(name="reference", type=OpenApiTypes.STR, location=OpenApiParameter.PATH)]),
    dispute=extend_schema(parameters=[OpenApiParameter(name="reference", type=OpenApiTypes.STR, location=OpenApiParameter.PATH)]),
    verify=extend_schema(parameters=[OpenApiParameter(name="reference", type=OpenApiTypes.STR, location=OpenApiParameter.PATH)]),
)
class EscrowViewSet(viewsets.ViewSet):
    """
    Escrow operations: list, retrieve, initiate, release, refund.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = "reference"

    # -------- Helper --------
    def _get_user_escrows(self, user):
        return EscrowTransaction.objects.filter(
            models.Q(tenant=user) | models.Q(landlord=user)
        ).select_related("apartment", "tenant", "landlord").order_by("-created_at")

    def _get_escrow(self, reference, user):
        """
        Returns (escrow, error_response).
        Ensures the requesting user is either the tenant, landlord, or staff.
        """
        try:
            escrow = EscrowTransaction.objects.select_related("apartment", "tenant", "landlord").get(reference=reference)
        except EscrowTransaction.DoesNotExist:
            return None, Response({'success': False, 'status': 404, 'message': "Escrow not found"}, status=status.HTTP_404_NOT_FOUND)
        if user not in (escrow.tenant, escrow.landlord) and not user.is_staff:
            return None, Response({'success': False, 'status': 403, 'message': "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        return escrow, None

    # -------- List --------
    @extend_schema(request=None, responses=EscrowTransactionSerializer(many=True))
    def list(self, request):
        qs = self._get_user_escrows(request.user)
        serializer = EscrowTransactionSerializer(qs, many=True)
        return Response(serializer.data)

    # -------- Retrieve --------
    @extend_schema(request=None, responses=EscrowTransactionSerializer)
    def retrieve(self, request, reference=None):
        escrow, error = self._get_escrow(reference, request.user)
        if error:
            return error
        return Response(EscrowTransactionSerializer(escrow).data, status=status.HTTP_200_OK)

    # -------- Get Bank List --------
    @extend_schema(request=None)
    @action(detail=False, methods=["get"], url_path="banks", permission_classes=[AllowAny])
    def banks(self, request):
        """
        Returns a list of banks supported by Paystack.
        """
        result = paystack.list_banks()
        if not result.get("status"):
            return Response({'success': False, 'status': 400, 'message': result.get("message", "Could not fetch bank list")}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)

    # -------- Initiate Payment --------
    @extend_schema(request=InitiateEscrowSerializer, responses=InitiateEscrowResponseSerializer)
    @action(detail=False, methods=["post"], url_path="initiate")
    def initiate(self, request):
        serializer = InitiateEscrowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        apartment = Apartment.objects.get(id=serializer.validated_data["apartment_id"])
        if apartment.landlord == request.user:
            return Response({'success': False, 'status': 400, 'message': "You cannot rent your own apartment"}, status=status.HTTP_400_BAD_REQUEST)
        if not LandlordPayoutAccount.objects.filter(user=apartment.landlord).exists():
            return Response({'success': False, 'status': 400, 'message': "Landlord has not set up payout account yet"}, status=status.HTTP_400_BAD_REQUEST)
        total_naira = apartment.monthly_rent + apartment.agreement_fee
        amount_kobo = int(total_naira * 100)
        escrow = EscrowTransaction.objects.create(
            apartment=apartment,
            tenant=request.user,
            landlord=apartment.landlord,
            amount=amount_kobo,
        )
        callback = f"{settings.FRONTEND_URL}/escrow/callback?reference={escrow.reference}"
        result = paystack.initialize_transaction(
            email=request.user.email,
            amount_kobo=amount_kobo,
            reference=escrow.reference,
            callback_url=callback,
        )
        if not result.get("status"):
            escrow.delete()
            return Response({'success': False, 'status': 400, 'message': result.get("message", "Could not initialize payment")}, status=status.HTTP_400_BAD_REQUEST)
        escrow.paystack_access_code = result["data"]["access_code"]
        escrow.save(update_fields=["paystack_access_code"])
        response_serializer = InitiateEscrowResponseSerializer({
            "reference": escrow.reference,
            "access_code": result["data"]["access_code"],
            "authorization_url": result["data"]["authorization_url"],
            "amount_naira": total_naira,
        })
        general_logger.info(f"Escrow {escrow.reference} initiated for apartment {apartment.id} by tenant {request.user}. Amount: {total_naira} Naira. Paystack access code: {escrow.paystack_access_code}")
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # -------- Verify (optional — for redirect callback) --------
    @extend_schema(request=None, responses=EscrowTransactionSerializer)
    @action(detail=True, methods=["get"], url_path="verify")
    def verify(self, request, reference=None):
        """
        Fallback for when webhook hasn't arrived yet.
        Idempotent: safe to call multiple times.
        """
        escrow, error = self._get_escrow(reference, request.user)
        if error:
            return error
        if escrow.status != EscrowTransaction.Status.PENDING:
            return Response(EscrowTransactionSerializer(escrow).data, status=status.HTTP_200_OK)
        result = paystack.verify_transaction(escrow.reference)
        if not result.get("status") or result["data"]["status"] != "success":
            return Response({'success': False, 'status': 400, 'message': "Payment not successful yet"}, status=status.HTTP_400_BAD_REQUEST)

        fee = int(escrow.amount * settings.PLATFORM_FEE_PERCENT)
        escrow.platform_fee = fee
        escrow.landlord_amount = escrow.amount - fee
        escrow.status = EscrowTransaction.Status.HELD
        escrow.paid_at = timezone.now()
        escrow.save()

        escrow.apartment.is_available = False
        escrow.apartment.save(update_fields=["is_available"])
        return Response(EscrowTransactionSerializer(escrow).data, status=status.HTTP_200_OK)

    # -------- Release to Landlord --------
    @extend_schema(request=None, responses=EscrowTransactionSerializer)
    @action(detail=True, methods=["post"], url_path="release")
    def release(self, request, reference=None):
        serializer = ReleaseEscrowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason") or "Rent payout"
        with transaction.atomic():
            try:
                escrow = EscrowTransaction.objects.select_for_update().select_related("landlord", "apartment").get(reference=reference)
            except EscrowTransaction.DoesNotExist:
                return Response({'success': False, 'status': 404, 'message': "Escrow not found"}, status=status.HTTP_404_NOT_FOUND)

            # Only tenant can release (or staff)
            if request.user != escrow.tenant and not request.user.is_staff:
                return Response({'success': False, 'status': 403, 'message': "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

            if escrow.status != EscrowTransaction.Status.HELD:
                return Response({'success': False, 'status': 400, 'message': f"Cannot release. Current status: {escrow.status}"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                payout = LandlordPayoutAccount.objects.get(user=escrow.landlord)
            except LandlordPayoutAccount.DoesNotExist:
                return Response({'success': False, 'status': 400, 'message': "Landlord has not set up a payout account"}, status=status.HTTP_400_BAD_REQUEST)
            result = paystack.initiate_transfer(
                amount_kobo=escrow.landlord_amount,
                recipient_code=payout.recipient_code,
                reason=reason,
                reference=f"payout_{escrow.reference}",
            )
            if not result.get("status"):
                return Response({'success': False, 'status': 400, 'message': result.get("message", "Transfer failed")}, status=status.HTTP_400_BAD_REQUEST)
            escrow.status = EscrowTransaction.Status.RELEASED
            escrow.paystack_transfer_code = result["data"]["transfer_code"]
            escrow.released_at = timezone.now()
            escrow.save()
            general_logger.info(f"Escrow {escrow.reference} released to landlord {escrow.landlord} via Paystack transfer {escrow.paystack_transfer_code} by user {request.user}")
        return Response(EscrowTransactionSerializer(escrow).data, status=status.HTTP_200_OK)

    # -------- Refund to Tenant --------
    @extend_schema(request=RefundEscrowSerializer, responses=EscrowTransactionSerializer)
    @action(detail=True, methods=["post"], url_path="refund")
    def refund(self, request, reference=None):
        serializer = RefundEscrowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            try:
                escrow = EscrowTransaction.objects.select_for_update().select_related("apartment").get(reference=reference)
            except EscrowTransaction.DoesNotExist:
                return Response({'success': False, 'status': 404, 'message': "Escrow not found"}, status=status.HTTP_404_NOT_FOUND)
            if request.user != escrow.tenant and not request.user.is_staff:
                return Response({'success': False, 'status': 403, 'message': "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
            if escrow.status != EscrowTransaction.Status.HELD:
                return Response({'success': False, 'status': 400, 'message': f"Cannot refund. Current status: {escrow.status}"}, status=status.HTTP_400_BAD_REQUEST)
            result = paystack.refund_transaction(escrow.reference)
            if not result.get("status"):
                return Response({'success': False, 'status': 400, 'message': result.get("message", "Refund failed")}, status=status.HTTP_400_BAD_REQUEST)
            escrow.status = EscrowTransaction.Status.REFUNDED
            escrow.save()

            escrow.apartment.is_available = True
            escrow.apartment.save(update_fields=["is_available"])
            general_logger.info(f"Escrow {escrow.reference} refunded to tenant {escrow.tenant} via Paystack refund by user {request.user}")
        return Response(EscrowTransactionSerializer(escrow).data, status=status.HTTP_200_OK)

    # -------- Dispute (tenant flags a problem) --------
    @extend_schema(request=None, responses=EscrowTransactionSerializer)
    @action(detail=True, methods=["post"], url_path="dispute")
    def dispute(self, request, reference=None):
        escrow, error = self._get_escrow(reference, request.user)
        if error:
            return error
        if request.user != escrow.tenant:
            return Response({'success': False, 'status': 403, 'message': "Only the tenant can raise a dispute"}, status=status.HTTP_403_FORBIDDEN)
        if escrow.status != EscrowTransaction.Status.HELD:
            return Response({'success': False, 'status': 400, 'message': "Only held funds can be disputed"}, status=status.HTTP_400_BAD_REQUEST)
        escrow.status = EscrowTransaction.Status.DISPUTED
        escrow.save(update_fields=["status"])
        general_logger.info(f"Escrow {escrow.reference} disputed by tenant {escrow.tenant} via Paystack dispute by user {request.user}")
        return Response(EscrowTransactionSerializer(escrow).data, status=status.HTTP_200_OK)
