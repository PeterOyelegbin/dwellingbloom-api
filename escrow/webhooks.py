from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from utils.logger_config import general_logger
from .models import EscrowTransaction
import hmac, hashlib, json


@csrf_exempt
def paystack_webhook(request):
    signature = request.headers.get("x-paystack-signature")
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), request.body, hashlib.sha512).hexdigest()
    if signature != expected:
        return HttpResponse(status=401)
    event = json.loads(request.body)
    event_type = event["event"]
    data = event["data"]

    # ---------- Payment received ----------
    if event_type == "charge.success":
        try:
            escrow = EscrowTransaction.objects.get(reference=data["reference"], status=EscrowTransaction.Status.PENDING)
        except EscrowTransaction.DoesNotExist:
            general_logger.warning(f"Escrow with reference {data['reference']} not found or not in PENDING status for charge.success webhook.")
            return HttpResponse(status=200)
        fee = int(escrow.amount * settings.PLATFORM_FEE_PERCENT)
        escrow.platform_fee = fee
        escrow.landlord_amount = escrow.amount - fee
        escrow.status = EscrowTransaction.Status.HELD
        escrow.paid_at = timezone.now()
        escrow.save()

        escrow.apartment.is_available = False
        escrow.apartment.save(update_fields=["is_available"])
        general_logger.info(f"Escrow {escrow.reference} payment received and funds held.")

    # ---------- Transfer to landlord completed ----------
    elif event_type == "transfer.success":
        ref = data["reference"]  # "payout_<escrow_reference>"
        if ref.startswith("payout_"):
            escrow_ref = ref.replace("payout_", "", 1)
            EscrowTransaction.objects.filter(reference=escrow_ref, status=EscrowTransaction.Status.RELEASED).update(status=EscrowTransaction.Status.RELEASED)  # already set, kept for clarity
            general_logger.info(f"Escrow {escrow_ref} transfer completed.")

    # ---------- Transfer failed ----------
    elif event_type == "transfer.failed":
        ref = data["reference"]
        if ref.startswith("payout_"):
            escrow_ref = ref.replace("payout_", "", 1)
            # Roll back — put funds back to HELD so release can be retried
            EscrowTransaction.objects.filter(reference=escrow_ref).update(status=EscrowTransaction.Status.HELD, paystack_transfer_code="", released_at=None)
            general_logger.info(f"Escrow {escrow_ref} transfer failed.")
    return HttpResponse(status=200)
