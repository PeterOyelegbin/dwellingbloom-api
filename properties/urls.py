from django.urls import path
from .views import ApartmentViewSet

urlpatterns = [
    path('apartments', ApartmentViewSet.as_view({'get': 'list', 'post': 'create'}), name='apartment-listing'),
    path('apartments/<uuid:pk>', ApartmentViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name='apartment-detail'),
    path('apartments/<uuid:pk>/verify', ApartmentViewSet.as_view({'patch': 'verify_apartment'}), name='apartment-verify'),
]
