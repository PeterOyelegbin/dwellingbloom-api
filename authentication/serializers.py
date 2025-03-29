from rest_framework import serializers
from .models import UserModel


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = UserModel
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'phone_number', 'is_seller', 'is_buyer', 'bvn', 'account_number', 'account_name', 'bank_name')

    def create(self, validated_data):
        user = UserModel.objects.create_user(**validated_data)
        return user
    

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('id', 'first_name', 'last_name', 'email', 'phone_number', 'is_seller', 'is_buyer', 'bvn', 'account_number', 'account_name', 'bank_name')
        read_only_fields = ['first_name', 'last_name', 'email', 'is_seller', 'is_buyer', 'bvn']


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number', 'is_seller', 'is_buyer', 'bvn', 'account_number', 'account_name', 'bank_name', 'verified', 'is_active']
    

class ResendActivationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    class Meta:
        fields = ('email', 'password')
        

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    

class UpdatePasswordSerializer(serializers.Serializer):
    otp = serializers.CharField()
    new_password = serializers.CharField(min_length=6)
    