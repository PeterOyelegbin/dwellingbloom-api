from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.throttling import AnonRateThrottle
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import AccessToken
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_yasg.utils import swagger_auto_schema
from threading import Thread
from utils import CustomJWTAuthentication, send_async_email, cache, general_logger, bvn_verification, generate_email_activation_link, verify_email_activation_link
from .models import PasswordResetToken
from .serializers import (SignupSerializer, ResendActivationEmailSerializer,
    LoginSerializer, ResetPasswordSerializer,
    UpdatePasswordSerializer, ProfileSerializer, AdminUserSerializer
)
import requests, time


# Create your views here.
User = get_user_model()

class AuthViewSet(viewsets.ViewSet):
    """
    Handles authentication: signup, email verification, login, logout, password reset.
    """
    def get_permissions(self):
        if self.action in ['logout']:
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.AllowAny()]
        
    # ---- Signup ---- #
    @swagger_auto_schema(request_body=SignupSerializer, responses={201: 'CREATED', 400: 'BAD REQUEST', 500: 'SERVER ERROR'})
    def signup(self, request):
        """
        User signup endpoint
        
        Handles user registration and sends verification email.
        """
        serializer = SignupSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            if serializer.validated_data['role'] == 'OWNER':
                print("is_owner")
                # # TODO: Implement BVN verification for sellers
                # verify_bvn = bvn_verification(serializer.validated_data['bvn'])
                # if verify_bvn.status_code == 200:
                #     serializer.save(role='OWNER')  # Set user as owner
                # else:
                #     general_logger.error("BVN verification failed: %s", verify_bvn.json())
                #     response_data = {
                #         'success': False,
                #         'status': 400,
                #         'error': 'BVN verification failed',
                #     }
                #     return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            else:
                # For tenants, save without BVN verification
                serializer.save(role='TENANT')  # Set user as tenant
            AuthViewSet.resend_activation(self, request, reg_email=serializer.validated_data['email'])  # Send activation email
            response_data = {
                'success': True,
                'status': 201,
                'message': 'Signup successful, check email for verification.',
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            general_logger.error("Validation error: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": f"Validation error: {e}",
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # ---- Resend Activation Email ---- #
    @action(detail=False, methods=['post'], throttle_classes=[AnonRateThrottle])
    @swagger_auto_schema(request_body= ResendActivationEmailSerializer, responses={200: 'OK', 400: 'BAD REQUEST', 500:'SERVER ERROR'})
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
            email_subject = 'App Name: Verify Your Email'
            email_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f4;">
                    <tr>
                        <td align="center" style="padding: 20px;">
                            <!-- Card Container -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                                <tr>
                                    <td style="padding: 20px;">
                                        <!-- Content -->
                                        <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">Hello {user},</p>
                                        <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">Thank you for registering. Please verify your email address by clicking the button below:</p>
                                        <table cellpadding="0" cellspacing="0" border="0" align="center">
                                            <tr>
                                                <td align="center">
                                                    <a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 10px 30px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px; font-size: 16px;">
                                                        Verify Email
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        <p style="font-size: 16px; color: #333333; margin: 20px 0 0 0;">If the button doesn't work, copy and paste this link into your browser:</p>
                                        <p style="font-size: 16px; color: #333333; margin: 10px 0 20px 0;"><a href="{verification_link}" style="color: #4CAF50; text-decoration: none;">{verification_link}</a></p>
                                        <p style="font-size: 16px; color: #333333; margin: 0;">Regards,<br><a href="https://appname.com.ng" style="font-style: bold; text-decoration: none;">App Name</a></p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
            recipient = [user.email]
            # Asynchronously handle send mail
            Thread(target=send_async_email, args=(email_subject, email_body, recipient)).start()
            response = {
                "success": True,
                "status": 200,
                "message": "Activation email resent.",
            }
            return Response(response, status=status.HTTP_200_OK)
        except ValidationError as e:
            general_logger.error("Validation error: %s", e)
            response = {
                "success": False,
                "status": 400,
                "error": f"Validation error: {e}",
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # ---- Verify Email ---- #
    @swagger_auto_schema(responses={200: 'OK', 400: 'BAD REQUEST', 404: 'NOT FOUND', 500: 'SERVER ERROR'})
    def verify_email(self, request, uidb64=None, token=None):
        """
        Email verification endpoint
        
        Verifies the user's email using the token sent in the activation link.
        """
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=uid)
            if verify_email_activation_link(user, token):
                response_data = {
                    'success': True,
                    'status': 200,
                    'message': 'Email verified successfully.',
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    'success': False,
                    'status': 400,
                    'error': 'Invalid token.',
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            general_logger.error("User not found: %s", uid)
            response_data = {
                "success": False,
                "status": 404,
                "error": "User not found.",
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except (TypeError, ValueError, Exception) as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # ---- Login ---- #
    @action(detail=False, methods=['post'], throttle_classes=[AnonRateThrottle])
    @swagger_auto_schema(request_body=LoginSerializer, responses={200: 'OK', 400: 'BAD_REQUEST', 500: 'SERVER ERROR'})
    def login(self, request):
        """
        User login endpoint
        
        Authenticates user and returns JWT tokens.
        """
        serializer = LoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            access_token = AccessToken.for_user(user)
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Login successful',
                'access_token': str(access_token),
                'token_type': 'Bearer',
                'expires_in': access_token.lifetime.total_seconds(),
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as e:
            general_logger.error("Validation error: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": f"Validation error: {e}",
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # ---- Google login ---- #
    @swagger_auto_schema(responses={200: 'OK', 500: 'SERVER ERROR'})
    def google_login(self, request):
        """
        Google login endpoint

        Redirects to Google OAuth2 login page.
        """
        try:
            google_login_url = (
                f"https://accounts.google.com/o/oauth2/auth"
                f"?client_id={settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']}"
                f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
                f"&response_type=code"
                f"&scope=email%20profile"
            )
            return redirect(google_login_url)
        except Exception as e:
            general_logger.error("An error occurred: %s", e, exc_info=True)
            response_data = {
                'success': False,
                'status': 500,
                'error': 'Server error: Please contact admin',
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # ---- Google Callback ---- #
    @swagger_auto_schema(responses={200: 'OK', 400: 'BAD REQUEST', 500: 'SERVER ERROR'})
    def google_callback(self, request):
        """
        Google callback endpoint
        
        Handles the callback from Google after user authentication.
        """
        try:
            code = request.GET.get('code')
            if not code:
                general_logger.error("An error occurred: Code parameter is missing")
                response_data = {
                    'success': False,
                    'status': 400,
                    'error': 'Google auth error: Please contact admin',
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            # Exchange authorization code for access token
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                'code': code,
                'client_id': settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id'],
                'client_secret': settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['secret'],
                'redirect_uri': settings.GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code'
            }
            token_response = requests.post(token_url, data=token_data)
            token_json = token_response.json()

            if 'access_token' not in token_json:
                general_logger.error("An error occurred: Failed to retrieve access token")
                response_data = {
                    'success': False,
                    'status': 400,
                    'error': 'OAuth2 token error: Please contact admin',
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            access_token = token_json['access_token']

            # Fetch user info from Google API
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            user_info_response = requests.get(user_info_url, headers={'Authorization': f'Bearer {access_token}'}).json()
            
            email = user_info_response.get('email')
            first_name = user_info_response.get('given_name', '')
            last_name = user_info_response.get('family_name', '')

            # Check if user exists in the database
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create(email=email, first_name=first_name, last_name=last_name)
                # Generate a secure random password (hashed)
                random_password = User.objects.make_random_password()
                user.set_password(random_password)  # Set hashed password
                user.is_tenant = True  # Set user as tenant
                user.is_verified = True # Set user as verified
                user.save()

            # Generate JWT access token
            access_token = AccessToken.for_user(user)
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Successfully logged in with Google',
                'access_token': str(access_token),
                'token_type': 'Bearer',
                'expires_in': access_token.lifetime.total_seconds(),
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            general_logger.error("An error occurred: %s", e, exc_info=True)
            response_data = {
                'success': False,
                'status': 500,
                'error': 'Server error: Please contact admin',
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # ---- Logout ---- #
    @swagger_auto_schema(responses={205: 'RESET CONTENT', 400: 'BAD REQUEST', 500: 'SERVER ERROR'})
    def logout(self, request):
        """
        User logout endpoint

        Blacklists the access token.
        """
        try:
            token = request.auth
            if token:
                jti = token['jti']
                
                # Get current timestamp and token expiration
                current_time = int(time.time())
                expiration_time = token.payload['exp']
                
                # Get remaining token lifetime (in seconds)
                remaining_time = expiration_time - current_time
                
                # Only blacklist token in Redis with expiration if token hasn't expired
                if remaining_time > 0:
                    cache_key = CustomJWTAuthentication.get_cache_key(self, jti)
                    cache.set(cache_key, 'blacklisted', timeout=int(remaining_time))
                response_data = {
                    'success': True,
                    'status': 205,
                    'message': 'Successfully logged out.',
                }
                return Response(response_data, status=status.HTTP_205_RESET_CONTENT)
            else:
                response_data = {
                    'success': False,
                    'status': 400,
                    'message': 'Token is invalid or expired',
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # ---- Password Reset ---- #
    @action(detail=False, methods=['post'], throttle_classes=[AnonRateThrottle])
    @swagger_auto_schema(request_body=ResetPasswordSerializer, responses={200: 'OK', 400: 'BAD REQUEST', 500:'SERVER ERROR'})
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
            email_subject = 'App Name: Password Reset Request'
            email_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f4;">
                    <tr>
                        <td align="center" style="padding: 20px;">
                            <!-- Card Container -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                                <tr>
                                    <td style="padding: 20px;">
                                        <!-- Content -->
                                        <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">Dear <strong>{user}</strong>,</p>
                                        <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">You have requested a password reset. Use the following token to reset your password within the next <strong>10 minutes</strong> before it expires:</p>
                                        <table cellpadding="0" cellspacing="0" border="0" align="center">
                                            <tr>
                                                <td align="center">
                                                    <label style="background-color: #4CAF50; color: white; padding: 10px 30px; text-align: center; display: inline-block; font-size: 24px; font-style: bold;">
                                                        {token}
                                                    </label>
                                                </td>
                                            </tr>
                                        </table>
                                        <p style="font-size: 16px; color: #FF0000; margin: 20px 0 20px 0;">If you didn't request this, please ignore this email or contact support.</p>

                                        <p style="font-size: 16px; color: #333333; margin: 0;">Regards,<br><a href="https://appname.com.ng" style="font-style: bold; text-decoration: none;">App Name</a></p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
            recipient = [user.email]
            # Asynchronously handle send mail
            Thread(target=send_async_email, args=(email_subject, email_body, recipient)).start()
            response_data = {
                'success': True,
                'status': 200,
                'message': 'OTP sent to email.',
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as e:
            general_logger.error("Validation error: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": f"Validation error: {e}",
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # ---- Update Password ---- #
    @swagger_auto_schema(request_body=UpdatePasswordSerializer, responses={200: 'OK', 400: 'BAD REQUEST', 500:'SERVER ERROR'})
    def confirm_reset_password(self, request):
        """
        User update password endpoint

        Updates the user's password using the token sent to their email.
        """
        serializer = UpdatePasswordSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            response = {
                "success": True,
                "status": 200,
                "message": "Password updated successfully.",
            }
            return Response(response, status=status.HTTP_200_OK)
        except ValidationError as e:
            general_logger.error("Validation error: %s", e)
            response = {
                "success": False,
                "status": 400,
                "error": f"Validation error: {e}",
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class UserViewSet(viewsets.ViewSet):
    """
    Handles user profiles (CRUD) and admin actions.
    """
    # ---- Permissions ---- #
    def get_permissions(self):
        if self.action in ['me', 'profile_update']:
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.IsAdminUser()]
        
    # ---- View Profile ---- #
    @swagger_auto_schema(responses={200: 'OK', 401: 'UNAUTHORIZED'})
    def me(self, request):
        """
        Current user's profile endpoint

        Gets the profile of the authenticated user.
        Returns user data if authenticated, otherwise returns an error.
        """
        try:
            serializer = ProfileSerializer(request.user)
            response_data = {
                    'success': True,
                    'status': 200,
                    'message': 'User profile retrieved successfully',
                    'data': serializer.data
                }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 401,
                "error": "Unauthorized access",
            }
            return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
        
    # ---- Update Profile ---- #
    @swagger_auto_schema(request_body=ProfileSerializer, responses={200: 'OK', 400: 'BAD REQUEST', 500:'SERVER ERROR'})
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
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Profile updated successfully',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as e:
            general_logger.error("Validation error: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": f"Validation error: {e}",
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # ---- Admin Actions ---- #
    @swagger_auto_schema(responses={200: 'OK', 400: 'BAD REQUEST', 500:'SERVER ERROR'})
    def list(self, request):
        """
        List users endpoint

        Admin lists all registered users.
        """
        try:
            users = User.objects.all()
            serializer = AdminUserSerializer(users, many=True)
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Users listed successfully',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @swagger_auto_schema(responses={200: 'OK', 404: 'NOT FOUND', 500:'SERVER ERROR'})
    def retrieve(self, request, pk=None):
        """
        Retrieve user endpoint

        Admin retrieves user data using user ID.
        """
        try:
            user = get_object_or_404(User, id=pk)
            serializer = AdminUserSerializer(user)
            response_data = {
                'success': True,
                'status': 200,
                'message': 'User retrieved successfully',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            general_logger.error("User not found: %s", pk)
            response_data = {
                "success": False,
                "status": 404,
                "error": "User not found.",
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @swagger_auto_schema(responses={204: 'NO CONTENT', 404: 'NOT FOUND', 500:'SERVER ERROR'})
    def destroy(self, request, pk=None):
        """
        Deleter user endpoint

        Admin delete a user account using user ID.
        """
        try:
            user = get_object_or_404(User, id=pk)
            user.delete()
            response_data = {
                'success': True,
                'status': 200,
                'message': 'User deleted successfully',
            }
            return Response(response_data, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            general_logger.error("User not found: %s", pk)
            response_data = {
                "success": False,
                "status": 404,
                "error": "User not found.",
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            general_logger.error("Exception error: %s", e)
            response_data = {
                "success": False,
                "status": 500,
                "error": "An error occured: Contact support",
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        