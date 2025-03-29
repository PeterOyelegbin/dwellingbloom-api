from django.urls import reverse
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from .models import UserModel, PasswordResetToken
from .serializers import SignupSerializer, LoginSerializer
import json

# Override settings to use a test database
@override_settings(
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
)
class UserViewsTestCase(TestCase):
    def setUp(self):
        """
        Set up test data and client.
        """
        self.client = APIClient()
        self.signup_url = reverse('signup-list')
        self.login_url = reverse('login-list')
        self.verify_email_url = reverse('verify-email', args=['uidb64', 'token'])
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'first_name': 'Test',
            'last_name': 'User',
        }
        self.login_data = {
            'email': 'test@example.com',
            'password': 'testpassword123',
        }


    def test_signup_success(self):
        """
        Test successful user signup.
        """
        response = self.client.post(self.signup_url, data=self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['message'], 'Verification email sent')

        # Check if the user was created in the database
        user = UserModel.objects.filter(email=self.user_data['email']).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, self.user_data['email'])


    def test_signup_invalid_data(self):
        """
        Test signup with invalid data.
        """
        invalid_data = {
            'email': 'invalid-email',
            'password': 'short',
        }
        response = self.client.post(self.signup_url, data=invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        

    def test_verify_email_success(self):
        """
        Test successful email verification.
        """
        # Create a user
        user = UserModel.objects.create_user(**self.user_data)
        user.verified = False
        user.save()

        # Generate a valid token (mocking the token generation logic)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.get(self.verify_email_url.replace('uidb64', uidb64).replace('token', token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['message'], 'Email verified successfully')

        # Check if the user is now verified
        user.refresh_from_db()
        self.assertTrue(user.verified)


    def test_verify_email_invalid_token(self):
        """
        Test email verification with an invalid token.
        """
        # Create a user
        user = UserModel.objects.create_user(**self.user_data)
        user.verified = False
        user.save()

        # Use an invalid token
        uidb64 = 'invalid_uidb64'
        token = 'invalid_token'

        response = self.client.get(self.verify_email_url.replace('uidb64', uidb64).replace('token', token))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertEqual(response.data['error'], 'Invalid token')

        # Ensure the user is still not verified
        user.refresh_from_db()
        self.assertFalse(user.verified)


    def test_login_success(self):
        """
        Test successful user login.
        """
        # Create a user first
        user = UserModel.objects.create_user(**self.user_data)
        user.verified = True  # Ensure the user is verified
        user.save()

        response = self.client.post(self.login_url, data=self.login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['message'], 'Login successful')
        self.assertIn('access_token', response.data)


    def test_login_invalid_credentials(self):
        """
        Test login with invalid credentials.
        """
        # Create a user first
        user = UserModel.objects.create_user(**self.user_data)
        user.verified = True
        user.save()

        invalid_login_data = {
            'email': 'test@example.com',
            'password': 'wrongpassword',
        }
        response = self.client.post(self.login_url, data=invalid_login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['success'], False)
        self.assertEqual(response.data['message'], 'Invalid credentials')
