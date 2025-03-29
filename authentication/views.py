from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import AccessToken
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import authenticate
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from drf_yasg.utils import swagger_auto_schema
from datetime import timedelta
from threading import Thread
from utils import CustomJWTAuthentication, send_async_email, cache, general_logger, bvn_verification, generate_email_activation_link, verify_email_activation_link
from .serializers import SignupSerializer, ProfileSerializer, AdminUserSerializer, ResendActivationEmailSerializer, LoginSerializer, ResetPasswordSerializer, UpdatePasswordSerializer
from .models import UserModel, PasswordResetToken
import requests

# Create your views here.
class SignupView(viewsets.ViewSet):
    """
    User Signup Endpoint

    Register as a new user. 
    """
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=SignupSerializer, responses={201: 'CREATED', 400: 'BAD REQUEST'})
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            if serializer.validated_data['is_seller'] == True:
                print("Seller")
                # # TODO: Implement BVN verification for sellers
                # verify_bvn = bvn_verification(serializer.validated_data['bvn'])
                # if verify_bvn.status_code == 200:
                #     serializer.save()
                #     ResendActivationEmailView().create(request, reg_email=serializer.validated_data['email'])  # Send activation email
                #     response_data = {
                #         'success': True,
                #         'status': 201,
                #         'message': 'Seller registration successful',
                #     }
                #     return Response(response_data, status=status.HTTP_201_CREATED)
                # else:
                #     general_logger.error("BVN verification failed: %s", verify_bvn.json())
                #     response_data = {
                #         'success': False,
                #         'status': 400,
                #         'error': 'BVN verification failed',
                #     }
                #     return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            serializer.save(is_buyer=True)  # Set user as buyer
            ResendActivationEmailView().create(request, reg_email=serializer.validated_data['email'])  # Send activation email
            response_data = {
                'success': True,
                'status': 201,
                'message': 'Verification email sent',
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                "success": False,
                "status": 400,
                "error": "Validation error: Invalid input from user or empty fields",
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


class ResendActivationEmailView(viewsets.ViewSet):
    """
    Resend Email Verification Link Endpoint

    User request an email verification link if not recieved upon signup.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(request_body= ResendActivationEmailSerializer, responses={200: 'OK', 400: 'BAD REQUEST', 404: 'NOT FOUND'})
    def create(self, request, reg_email=None):
        email = reg_email if reg_email is not None else request.data.get('email')
        try:
            user = UserModel.objects.get(email=email)
            if user.verified:
                response_data = {
                    'success': False,
                    'status': 400,
                    'error': 'User already verified',
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
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
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Verification email resent',
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except UserModel.DoesNotExist:
            response_data = {
                'success': False,
                'status': 404,
                'error': 'User not found',
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        

class VerifyEmailView(viewsets.ViewSet):
    """
    User Email Verification Endpoint

    Verify newly registered user email.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(responses={200: 'OK', 400: 'BAD REQUEST'})
    def verify(self, request, uidb64=None, token=None, *args, **kwargs):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = UserModel.objects.get(id=uid)
            if verify_email_activation_link(user, token):
                response_data = {
                    'success': True,
                    'status': 200,
                    'message': 'Email verified successfully',
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    'success': False,
                    'status': 400,
                    'error': 'Invalid or expired token',
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist) as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                'success': False,
                'status': 400,
                'error': 'Invalid token',
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        

class LoginView(viewsets.ViewSet):
    """
    User Login Endpoint

    User log in with their email and password.
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=LoginSerializer, responses={200: 'OK', 401: 'UNAUTHORIZED', 400: 'BAD_REQUEST'})
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data.get('email')
            password = serializer.validated_data.get('password')
            user = authenticate(username=email, password=password)
            if user is not None:
                if user.verified:
                    access_token = AccessToken.for_user(user)
                    response_data = {
                        'success': True,
                        'status': 200,
                        'message': 'Login successful',
                        'user': str(user),
                        'access_token': str(access_token),
                        'token_type': 'Bearer',
                        'expires_in': 10800, # 3 hours
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {
                        'success': False,
                        'status': 401,
                        'message': 'Email not verified',
                    }
                    return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
            else:
                response_data = {
                    'success': False,
                    'status': 401,
                    'message': 'Invalid credentials',
                }
                return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                'success': False,
                'status': 400,
                'message': 'Validation error: Email or password field is invalid or empty',
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(viewsets.ViewSet):
    """
    User Logout Endpoint

    Logs out user by blacklisting their access token.
    """
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(responses={205: 'RESET CONTENT', 400: 'BAD REQUEST'})
    def create(self, request):
        try:
            token = request.auth
            if token:
                cache_key = CustomJWTAuthentication.get_cache_key(self, str(token))
                # Set timeout as per token expiry
                timeout = timedelta(hours=3).total_seconds()
                cache.set(cache_key, 'blacklisted', timeout=timeout)
                response_data = {
                    'success': True,
                    'status': 205,
                    'message': 'Logout successful',
                }
                return Response(response_data, status=status.HTTP_205_RESET_CONTENT)
            else:
                response_data = {
                    'success': False,
                    'status': 400,
                    'message': 'Invalid token',
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                'success': False,
                'status': 400,
                'message': "Validation error occured",
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        

class ResetPasswordView(viewsets.ViewSet):
    """
        Password Reset Endpoint

        Initiate a password reset as a register user. 
    """
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=ResetPasswordSerializer, responses={200: 'OK', 404: 'NOT FOUND', 500:'SERVER ERROR'})
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data.get('email')
            user = UserModel.objects.get(email=email)
            # Check for an existing unexpired token
            existing_token = PasswordResetToken.objects.filter(user=user).first()
            if existing_token:
                if not existing_token.is_expired():
                    token = existing_token.token
                else:
                    existing_token.delete()
                    token = PasswordResetToken.generate_token()
                    PasswordResetToken.objects.create(user=user, token=token)
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
                'message': 'Password reset token sent to email',
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except UserModel.DoesNotExist:
            response_data = {
                'success': False,
                'status': 404,
                'message': 'User does not exist!',
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            general_logger.error("Exception error occurred: %s", e)
            response_data = {
                'success': False,
                'status': 500,
                'message': 'An error occurred, kindly contact support!',
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class UpdatePasswordView(viewsets.ViewSet):
    """
        Update Password Endpoint

        Update the password as a register user. 
    """
    serializer_class = UpdatePasswordSerializer
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(request_body=UpdatePasswordSerializer, responses={200: 'OK', 400: 'BAD REQUEST', 500:'SERVER ERROR'})
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            token = serializer.validated_data.get('otp')
            new_password = serializer.validated_data.get('new_password')
            # Find the token in the database
            reset_token = PasswordResetToken.objects.get(token=token)
            if reset_token.is_expired():
                response_data = {
                    'success': False,
                    'status': 400,
                    'message': 'Token expired!',
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            reset_token.delete()
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Password reset successful',
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except PasswordResetToken.DoesNotExist:
            response_data = {
                'success': False,
                'status': 400,
                'message': 'Invalid token!',
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            general_logger.error("Exception error occurred: %s", e)
            response_data = {
                'success': False,
                'status': 500,
                'message': 'An error occurred, kindly contact support!'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class GoogleAuthRedirect(viewsets.ViewSet):
    """
    Google Signin Redirect Endpoint

    Redirects the user to Google's OAuth2 login page.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(responses={200: 'OK', 500: 'SERVER_ERROR'})
    def list(self, request, *args, **kwargs):
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
        

class GoogleAuthCallback(viewsets.ViewSet):
    """
    Google Sign-in Callback Endpoint

    Handles Google's OAuth2 callback, retrieves user data, and signs in or creates a user.
    Returns a JWT token upon successful authentication.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(responses={200: 'OK', 400: 'BAD_REQUEST', 500: 'SERVER_ERROR'})
    def list(self, request, *args, **kwargs):
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

            # Generate a secure random password (hashed)
            random_password = UserModel.objects.make_random_password()

            # Get or create user
            user, created = UserModel.objects.get_or_create(email=email, first_name=first_name, last_name=last_name)

            if created:
                user.set_password(random_password)  # Set hashed password
                user.is_buyer = True  # Set user as buyer
                user.verified = True # Set user as verified
                user.save()

            # Generate JWT access token
            access_token = AccessToken.for_user(user)
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Signin successful',
                'user': str(user),
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
        

class UsersView(viewsets.ViewSet):
    """
    User Management Endpoint

    Admin manages all registered users.
    """
    serializer_class = AdminUserSerializer
    permission_classes = (IsAdminUser,)
    
    @swagger_auto_schema(responses={200: 'OK', 404: 'NOT FOUND', 500: 'SERVER ERROR'})
    def list(self, request):
        try:
            queryset = UserModel.objects.all()
            serializer = self.serializer_class(queryset, many=True)
            response_data = {
                'success': True,
                'status': 200,
                'message': 'Users retrieved successfully',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except UserModel.DoesNotExist:
            response_data = {
                'success': False,
                'status': 404,
                'message': 'No user found',
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                'success': False,
                'status': 500,
                'error': 'An error occurred while fetching users',
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @swagger_auto_schema(responses={200: 'OK', 404: 'NOT FOUND', 500: 'SERVER_ERROR'})
    def destroy(self, request, pk=None):
        try:
            user = UserModel.objects.get(pk=pk)
            user.delete()
            response_data = {
                'success': True,
                'status': 200,
                'message': 'User deleted successfully',
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except UserModel.DoesNotExist:
            response_data = {
                'success': False,
                'status': 404,
                'error': 'User does not exist',
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                'success': False,
                'status': 500,
                'error': 'An error occurred while deleting user',
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ProfileView(viewsets.ViewSet):
    """
    Profile Management Endpoint

    Manage authenticated user profile.
    """
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)
    
    @swagger_auto_schema(responses={200: 'OK', 404: 'NOT FOUND', 500: 'SERVER ERROR'})
    def retrieve(self, request):
        try:
            user = request.user
            queryset = UserModel.objects.filter(id=user.id)
            serializer = self.serializer_class(queryset, many=True)
            response_data = {
                'success': True,
                'status': 200,
                'message': 'User profile retrieved successfully',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except UserModel.DoesNotExist:
            response_data = {
                'success': False,
                'status': 404,
                'message': 'No user found',
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                'success': False,
                'status': 500,
                'error': 'An error occurred while fetching user profile',
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @swagger_auto_schema(request_body=ProfileSerializer, responses={200: 'OK', 404: 'NOT FOUND', 500: 'SERVER_ERROR'})
    def update(self, request):
        try:
            auth_user = request.user
            user = UserModel.objects.get(pk=auth_user.id)
            serializer = self.serializer_class(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            response_data = {
                'success': True,
                'status': 200,
                'message': 'User profile updated successfully',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except UserModel.DoesNotExist:
            response_data = {
                'success': False,
                'status': 404,
                'error': 'User does not exist',
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            general_logger.error("An error occurred: %s", e)
            response_data = {
                'success': False,
                'status': 500,
                'error': 'An error occurred while updating user profile',
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        