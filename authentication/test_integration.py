from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.test import override_settings
from unittest.mock import patch
from .models import UserModel, PasswordResetToken
from utils.mail_config import generate_email_activation_token


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class UserManagementTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'email': 'test@example.com',
            'password': 'tEstp@ssword3',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'TENANT'
        }
        self.user = UserModel.objects.create_user(**self.user_data)
        self.user.is_verified = True
        self.user.save()


    @patch('utils.mail_config.send_email_task.delay')
    def test_user_signup(self, mock_send_email):
        url = reverse('signup')
        data = {
            'email': 'newuser@example.com',
            'password': 'st@ng8Te',
            'confirm_password': 'st@ng8Te',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'TENANT'            
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserModel.objects.filter(email='newuser@example.com').exists())


    def test_verify_email(self):
        # Generate a token using the app's actual token generator
        self.user.is_verified = False
        self.user.save()
        token = generate_email_activation_token(self.user)

        # Now verify the email via POST with token in body
        url = reverse('verify-email')
        response = self.client.post(url, data={'token': token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)


    def test_user_login(self):
        url = reverse('login')
        data = {
            'email': 'test@example.com',
            'password': 'tEstp@ssword3'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)


    def test_user_logout(self):
        # First, login to get the tokens
        login_url = reverse('login')
        login_data = {
            'email': 'test@example.com',
            'password': 'tEstp@ssword3'
        }
        login_response = self.client.post(login_url, login_data, format='json')
        access_token = login_response.data['access_token']
        refresh_token = login_response.data['refresh_token']

        # Now, logout — must send refresh token in body
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_url = reverse('logout')
        logout_response = self.client.post(logout_url, data={'refresh': refresh_token}, format='json')
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)


    @patch('utils.mail_config.send_email_task.delay')
    def test_password_reset(self, mock_send_email):
        url = reverse('reset-password')
        data = {
            'email': 'test@example.com'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())


    def test_password_update(self):
        # First, create a reset token
        reset_token = PasswordResetToken.generate_token()
        PasswordResetToken.objects.create(user=self.user, token=reset_token)

        # Now, update the password
        url = reverse('update-password')
        data = {
            'otp': reset_token,
            'new_password': 'nEwp@ssword1',
            'confirm_password': 'nEwp@ssword1'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('nEwp@ssword1'))


    @patch('utils.mail_config.send_email_task.delay')
    def test_resend_activation_email(self, mock_send_email):
        # First, create a user that needs activation
        self.user.is_verified = False
        self.user.save()

        # Now, resend the activation email
        url = reverse('resend-activation')
        data = {
            'email': 'test@example.com'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
