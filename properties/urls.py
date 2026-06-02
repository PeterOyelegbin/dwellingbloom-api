from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ApartmentViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'apartments', ApartmentViewSet, basename="apartments")

urlpatterns = [
    path('apartments', ApartmentViewSet.as_view({'get': 'list', 'post': 'create'}), name='apartment-listing'),
    path('apartments/<uuid:pk>', ApartmentViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name='apartment-detail'),
]
