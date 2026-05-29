from django.urls import path
from .views import AuthViewSet, UserViewSet

urlpatterns = [
    # Auth Endpoints
    path('auth/signup', AuthViewSet.as_view({'post': 'signup'}), name='signup'),
    path('auth/resend-activation', AuthViewSet.as_view({'post': 'resend_activation'}), name='resend-activation'),
    path('auth/verify-email/<str:uidb64>/<str:token>', AuthViewSet.as_view({'post': 'verify_email'}), name='verify-email'),
    path('auth/login', AuthViewSet.as_view({'post': 'login'}), name='login'),
    path('auth/token/refresh', AuthViewSet.as_view({'post': 'refresh'}), name='token-refresh'),
    path('auth/logout', AuthViewSet.as_view({'post': 'logout'}), name='logout'),
    path('auth/password-reset/request', AuthViewSet.as_view({'post': 'reset_password'}), name='reset-password'),
    path('auth/password-reset/confirm', AuthViewSet.as_view({'post': 'confirm_reset_password'}), name='update-password'),

    # Current User Profile
    path('users/me', UserViewSet.as_view({'get': 'me', 'patch': 'profile_update'}), name='user-profile'),

    # Admin User Management
    path('admin/users', UserViewSet.as_view({'get': 'list'}), name='user-list'),
    path('admin/users/<uuid:pk>', UserViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='user-detail'),
]
