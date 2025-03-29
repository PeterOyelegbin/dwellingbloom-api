from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SignupView, ResendActivationEmailView, VerifyEmailView, GoogleAuthRedirect, GoogleAuthCallback, LoginView, LogoutView, ResetPasswordView, UpdatePasswordView, ProfileView, UsersView

router = DefaultRouter(trailing_slash=False)

# Auth Endpoints
router.register(r'auth/signup', SignupView, basename="signup")
router.register(r'auth/resend-activation', ResendActivationEmailView, basename="resend-activation")
router.register(r'auth/login', LoginView, basename="login")
router.register(r'auth/logout', LogoutView, basename="logout")
router.register(r'auth/password/reset', ResetPasswordView, basename="reset-password")
router.register(r'auth/password/update', UpdatePasswordView, basename="update-password")

# Google OAuth
router.register(r'auth/google/login', GoogleAuthRedirect, basename="google-login")
router.register(r'auth/google/callback', GoogleAuthCallback, basename="google-callback")

# User Management
router.register(r'users', UsersView, basename="user")

urlpatterns = [
    path('', include(router.urls)),

    # Email Verification
    path('auth/verify-email/<str:uidb64>/<str:token>', VerifyEmailView.as_view({'post': 'verify'}), name='verify-email'),

    # Current User Profile
    path('users/me/profile', ProfileView.as_view({'get': 'retrieve', 'patch': 'update'}), name='user-profile'),
]
