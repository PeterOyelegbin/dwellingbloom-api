from django.urls import reverse
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from .models import UserModel
from utils.mail_config import generate_email_activation_token


# Override settings to use a test database and in-memory cache
@override_settings(
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    },
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class UserViewsTestCase(TestCase):
    def setUp(self):
        """
        Set up test data and client.
        """
        self.client = APIClient()
        self.signup_url = reverse('signup')
        self.login_url = reverse('login')
        self.verify_email_url = reverse('verify-email')
        self.user_data = {
            'email': 'test@example.com',
            'password': 'tEstp@ssword1',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'TENANT'
        }
        self.signup_data = {
            'email': 'test@example.com',
            'password': 'tEstp@ssword1',
            'confirm_password': 'tEstp@ssword1',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'TENANT'
        }
        self.login_data = {
            'email': 'test@example.com',
            'password': 'tEstp@ssword1',
            'confirm_password': 'tEstp@ssword1'
        }


    @patch('utils.mail_config.send_email_task.delay')
    def test_signup_success(self, mock_send_email):
        """
        Test successful user signup.
        """
        response = self.client.post(self.signup_url, data=self.signup_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['message'], 'Signup successful, check email for verification.')

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
        user.is_verified = False
        user.save()

        # Generate a valid token using the app's actual token generator
        token = generate_email_activation_token(user)

        response = self.client.post(self.verify_email_url, data={'token': token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['message'], 'Email verified successfully.')

        # Check if the user is now verified
        user.refresh_from_db()
        self.assertTrue(user.is_verified)


    def test_login_success(self):
        """
        Test successful user login.
        """
        # Create a user first
        user = UserModel.objects.create_user(**self.user_data)
        user.is_verified = True  # Ensure the user is verified
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
        user.is_verified = True
        user.save()

        invalid_login_data = {
            'email': 'test@example.com',
            'password': 'wr0ngPa$$word',
        }
        response = self.client.post(self.login_url, data=invalid_login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertEqual(response.data['error'], 'Invalid email or password.')
