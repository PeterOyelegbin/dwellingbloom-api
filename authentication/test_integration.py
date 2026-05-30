from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from .models import UserModel, PasswordResetToken


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


    def test_user_signup(self):
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
        # First generate a verification token
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        # Now verify the email
        url = reverse('verify-email', kwargs={'uidb64': uid, 'token': token})
        response = self.client.post(url)
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
        # First, login to get the token
        login_url = reverse('login')
        login_data = {
            'email': 'test@example.com',
            'password': 'tEstp@ssword3'
        }
        login_response = self.client.post(login_url, login_data, format='json')
        token = login_response.data['access_token']

        # Now, logout
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        logout_url = reverse('logout')
        logout_response = self.client.post(logout_url)
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)


    def test_password_reset(self):
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


    def test_resend_activation_email(self):
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


    def test_google_auth_redirect(self):
        url = reverse('google-login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn('accounts.google.com', response.url)
        