from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EscrowViewSet, PayoutAccountViewSet
from .webhooks import paystack_webhook

router = DefaultRouter()
router.register("escrows", EscrowViewSet, basename="escrow")
router.register("users/payout-account", PayoutAccountViewSet, basename="payout-account")

urlpatterns = [
    path("", include(router.urls)),
    path("webhooks/paystack/", paystack_webhook, name="paystack-webhook"),
]
