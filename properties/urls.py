from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApartmentViewSet

router = DefaultRouter(trailing_slash=False)

router.register(r'apartments', ApartmentViewSet, basename="apartment")

urlpatterns = [
    path('', include(router.urls)),
]