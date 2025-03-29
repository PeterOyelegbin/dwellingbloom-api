from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractUser
from uuid import uuid4
from datetime import timedelta
from utils import UserModelManager
import random


# Create your models here.
class UserModel(AbstractUser):
    """
    This model will serve as the default authentication model via AUTH_USER_MODEL in settings.py
    """
    username = None
    id = models.UUIDField(default=uuid4, unique=True, primary_key=True, editable=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_buyer = models.BooleanField(default=False)
    is_seller = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    bvn = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=255, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    verified = models.BooleanField(default=False)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['first_name', 'last_name',]

    objects = UserModelManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['-date_joined']


class PasswordResetToken(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.token

    @staticmethod
    def generate_token():
        """
        generate_token method to generate a 6-digit OTP.
        """
        return ''.join(random.choices('0123456789', k=6))

    def is_expired(self):
        """
        Check if the OTP has expired.
        """
        expiration_time = timedelta(minutes=10) #Set expiration duration to 10 minutes
        return now() > self.created_at + expiration_time
    