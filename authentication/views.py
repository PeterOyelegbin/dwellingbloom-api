from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.throttling import AnonRateThrottle
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import extend_schema, OpenApiParameter
from utils.logger_config import general_logger
from utils.jwt_config import CustomJWTAuthentication
from utils.kyc_config import verify_bvn
from utils.mail_config import *
from utils.page_config import ListPagination
from utils.validation_helper import extract_validation_error_message
from .models import PasswordResetToken
from .serializers import *


# Create your views here.
User = get_user_model()

@extend_schema(tags=['Auth'])
class AuthViewSet(viewsets.ViewSet):
    """
    Handles authentication: signup, email verification, login, logout, password reset.
    """
    serializer_class = None  # Set in each action

    def get_permissions(self):
        if self.action in ['logout']:
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.AllowAny()]

    # ---- Signup ---- #
    @extend_schema(request=SignupSerializer)
    def signup(self, request):
        """
        User signup endpoint

        Handles user registration and sends verification email.
        """
        serializer = SignupSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            # verification = verify_bvn(serializer.validated_data)
            # if not verification.get("success"):
            #     return Response(
            #         {"success": False, "status": 400, "error": "BVN verification failed"},
            #         status=status.HTTP_400_BAD_REQUEST
            #     )
            serializer.save()
            AuthViewSet.resend_activation(self, request, reg_email=serializer.validated_data['email'])  # Send activation email
            return Response(
                {"success": True, "status": 201, "message": "Signup successful, check email for verification."},
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            error_message = extract_validation_error_message(e)
            general_logger.error("Validation error: %s", e)
            return Response(
                {"success": False, "status": 400, "error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occured: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ---- Resend Activation Email ---- #
    @extend_schema(request=ResendActivationEmailSerializer)
    @action(detail=False, methods=['post'], throttle_classes=[AnonRateThrottle])
    def resend_activation(self, request, reg_email=None):
        """
        Resend email verification link endpoint

        Resends the email verification link to the user.
        """
        email = reg_email if reg_email is not None else request.data.get('email')
        serializer = ResendActivationEmailSerializer(data={'email': email})
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            verification_link = generate_email_activation_link(user)
            email_subject = 'DwellingBloom App Support: Verify Your Email'
            email_body = verification_email_template(user, verification_link)
            recipient = [user.email]
            # Asynchronously handle send mail
            send_email_task.delay(email_subject, email_body, recipient)
            return Response(
                {"success": True, "status": 200, "message": "Activation email resent."},
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            error_message = extract_validation_error_message(e)
            general_logger.error("Validation error: %s", e)
            return Response(
                {"success": False, "status": 400, "error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            general_logger.error("Exception error in resend_activation: %s", e, exc_info=True)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ---- Verify Email ---- #
    @extend_schema()
    def verify_email(self, request, uidb64=None, token=None):
        """
        Email verification endpoint

        Verifies the user's email using the token sent in the activation link.
        """
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=uid)
            if verify_email_activation_link(user, token):
                return Response(
                    {"success": True, "status": 200, "message": "Email verified successfully."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"success": False, "status": 400, "error": "Invalid verification link."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            general_logger.error("User not found: %s", uid)
            return Response(
                {"success": False, "status": 404, "error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except (TypeError, ValueError, Exception) as e:
            general_logger.error("Exception error: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ---- Login ---- #
    @extend_schema(request=LoginSerializer)
    @action(detail=False, methods=['post'], throttle_classes=[AnonRateThrottle])
    def login(self, request):
        """
        User login endpoint

        Authenticates user and returns JWT access and refresh tokens.
        """
        serializer = LoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            return Response(
                {
                    "success": True,
                    "status": 200,
                    "message": "Login successful",
                    "access_token": str(access),
                    "refresh_token": str(refresh),
                    "token_type": "Bearer",
                    "expires_in": access.lifetime.total_seconds()
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            error_message = extract_validation_error_message(e)
            general_logger.error("Validation error: %s", e)
            return Response(
                {"success": False, "status": 400, "error": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ---- Refresh Access Token ---- #
    @extend_schema(request=RefreshTokenSerializer)
    @action(detail=False, methods=['post'], throttle_classes=[AnonRateThrottle])
    def refresh(self, request):
        """
        Token refresh endpoint

        Accepts a valid refresh token and returns a new access token.
        """
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "status": 400, "error": "Invalid refresh token format"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            refresh = RefreshToken(serializer.validated_data['refresh'])
            access = refresh.access_token
            return Response(
                {
                    "success": True,
                    "status": 200,
                    "message": "Token refreshed successfully",
                    "access_token": str(access),
                    "token_type": "Bearer",
                    "expires_in": access.lifetime.total_seconds(),
                },
                status=status.HTTP_200_OK,
            )
        except TokenError as e:
            general_logger.warning("Token error during refresh: %s", e)
            return Response(
                {"success": False, "status": 401, "error": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception as e:
            general_logger.error("Exception error during refresh: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # # ---- Logout ---- #
    @extend_schema(request=RefreshTokenSerializer)
    def logout(self, request):
        """
        User logout endpoint

        Blacklists both the access token and the refresh token.
        """
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "status": 400, "error": "Invalid refresh token format"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            # --- Blacklist the refresh token ---
            try:
                refresh = RefreshToken(serializer.validated_data['refresh'])
                CustomJWTAuthentication.blacklist_token(jti=refresh.payload['jti'], exp=refresh.payload['exp'])
            except TokenError as e:
                general_logger.warning("Refresh token invalid during logout (ignoring): %s", e)
            # --- Blacklist the access token ---
            access_token = request.auth
            if access_token:
                CustomJWTAuthentication.blacklist_token(jti=access_token['jti'], exp=access_token.payload['exp'])
            return Response(
                {"success": True, "status": 200, "message": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            general_logger.error("Exception error during logout: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ---- Password Reset ---- #
    @extend_schema(request=ResetPasswordSerializer)
    @action(detail=False, methods=['post'], throttle_classes=[AnonRateThrottle])
    def reset_password(self, request):
        """
        User reset password endpoint

        Initiates the password reset process by sending a token to the user's email.
        """
        serializer = ResetPasswordSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            # Check for an existing unexpired token
            existing_token = PasswordResetToken.objects.filter(user=user).first()
            if existing_token:
                if existing_token.is_expired():
                    existing_token.delete()
                    token = PasswordResetToken.generate_token()
                    PasswordResetToken.objects.create(user=user, token=token)
                else:
                    token = existing_token.token
            else:
                token = PasswordResetToken.generate_token()
                PasswordResetToken.objects.create(user=user, token=token)
            email_subject = 'DwellingBloom App Support: Password Reset Request'
            email_body = reset_password_email_template(user, token)
            recipient = [user.email]
            # Asynchronously handle send mail
            send_email_task.delay(email_subject, email_body, recipient)
            return Response(
                {'success': True, 'status': 200, 'message': 'OTP sent to email.'},
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            error_message = extract_validation_error_message(e)
            general_logger.error("Validation error: %s", e)
            return Response(
                {"success": False, "status": 400, "error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            general_logger.error("Exception error in reset_password: %s", e, exc_info=True)
            return Response(
                {"success": False, "status": 500, "error": "An error occured: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    # ---- Update Password ---- #
    @extend_schema(request=UpdatePasswordSerializer)
    def confirm_reset_password(self, request):
        """
        User update password endpoint

        Updates the user's password using the token sent to their email.
        """
        serializer = UpdatePasswordSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"success": True, "status": 200, "message": "Password updated successfully."},
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            error_message = extract_validation_error_message(e)
            general_logger.error("Validation error: %s", e)
            return Response(
                {"success": False, "status": 400, "error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occured: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserViewSet(viewsets.ViewSet):
    """
    Handles user profiles (CRUD) and admin actions.
    """
    serializer_class = None  # Set in each action

    # ---- Permissions ---- #
    def get_permissions(self):
        if self.action in ['me', 'profile_update']:
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.IsAdminUser()]

    # ---- View Profile ---- #
    @extend_schema(tags=['Users'])
    def me(self, request):
        """
        Current user's profile endpoint

        Gets the profile of the authenticated user.
        """
        try:
            serializer = ProfileSerializer(request.user)
            return Response(
                {'success': True, 'status': 200, 'message': 'User profile retrieved successfully', 'data': serializer.data},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            return Response(
                {"success": False, "status": 401, "error": "Unauthorized access"},
                status=status.HTTP_401_UNAUTHORIZED
            )

    # ---- Update Profile ---- #
    @extend_schema(request=ProfileSerializer, tags=['Users'])
    def profile_update(self, request):
        """
        Update user profile endpoint

        Handles profile updates for the authenticated user.
        """
        try:
            user = self.request.user
            serializer = ProfileSerializer(user, data=self.request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {'success': True, 'status': 200, 'message': 'Profile updated successfully', 'data': serializer.data},
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            error_message = extract_validation_error_message(e)
            general_logger.error("Validation error: %s", e)
            return Response(
                {"success": False, "status": 400, "error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occured: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ---- Admin Actions ---- #
    @extend_schema(
        operation_id='admin_users_list',
        parameters=[
            OpenApiParameter(name='search', description='Search by email, first name, or last name', required=False, type=str),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Results per page (max 100)', required=False, type=int),
        ],
        tags=['Admin']
    )
    def list(self, request):
        """
        List users endpoint

        Admin lists all registered users.
        Supports search by email, first name, or last name via ?search=
        Supports pagination via ?page= and ?page_size=
        """
        try:
            search_query = request.query_params.get('search', '').strip()
            users = User.objects.all().order_by('id')
            if search_query:
                users = users.filter(
                    Q(email__icontains=search_query) | Q(first_name__icontains=search_query) | Q(last_name__icontains=search_query)
                )
            # --- Paginate ---
            paginator = ListPagination()
            paginated_users = paginator.paginate_queryset(users, request)
            serializer = AdminUserSerializer(paginated_users, many=True)
            return Response(
                {
                    "success": True,
                    "status": 200,
                    "message": "Users listed successfully",
                    "pagination": {
                        "total":    paginator.page.paginator.count,
                        "page":     paginator.page.number,
                        "pages":    paginator.page.paginator.num_pages,
                        "has_next": paginator.page.has_next(),
                        "has_prev": paginator.page.has_previous(),
                    },
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occurred: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(operation_id='admin_users_retrieve', tags=['Admin'])
    def retrieve(self, request, pk=None):
        """
        Retrieve user endpoint

        Admin retrieves user data using user ID.
        """
        try:
            user = get_object_or_404(User, id=pk)
            serializer = AdminUserSerializer(user)
            return Response(
                {"success": True, "status": 200, "message": "User retrieved successfully", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            general_logger.error("User not found: %s", pk)
            return Response(
                {"success": False, "status": 404, "error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occured: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(tags=['Admin'])
    def destroy(self, request, pk=None):
        """
        Deleter user endpoint

        Admin delete a user account using user ID.
        """
        try:
            user = get_object_or_404(User, id=pk)
            user.delete()
            return Response(
                {"success": True, "status": 200, "message": "User deleted successfully"},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            general_logger.error("User not found: %s", pk)
            return Response(
                {"success": False, "status": 404, "error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            return Response(
                {"success": False, "status": 500, "error": "An error occured: Contact support"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
