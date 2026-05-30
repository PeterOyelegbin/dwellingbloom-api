from rest_framework import serializers, validators
from django.core.validators import RegexValidator
from .models import UserModel, PasswordResetToken


class SignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[validators.UniqueValidator(queryset=UserModel.objects.all())])
    password = serializers.CharField(min_length=8, write_only=True, validators=[RegexValidator(regex='^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', message='Password must be 8+ chars with a mix of uppercase, lowercase, numbers, and symbols')], help_text="8+ chars with uppercase, lowercase, number, and special symbol")
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    class Meta:
        model = UserModel
        # fields = "__all__"
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'confirm_password', 'phone_number', 'role', 'bvn', 'account_number', 'account_name', 'bank_name')
        extra_kwargs = {
            'id': {'read_only': True},
            'bvn': {'write_only': True},
            'account_number': {'write_only': True},
            'account_name': {'write_only': True},
            'bank_name': {'write_only': True},
        }

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        user = UserModel.objects.create_user(**validated_data)
        return user


class ResendActivationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get('email')
        user = UserModel.objects.filter(email=email).first()
        if user is None:
            raise serializers.ValidationError("User with this email does not exist.")
        if user.is_verified:
            raise serializers.ValidationError("User is already verified.")
        if not user.is_active:
            raise serializers.ValidationError("User is not active.")
        attrs['user'] = user
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = UserModel.objects.filter(email=email).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_verified:
            raise serializers.ValidationError("Account not verified, please check your email.")
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive, contact support.")
        attrs['user'] = user
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get('email')
        user = UserModel.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError("Invalid email.")
        if not user.is_verified or not user.is_active:
            raise serializers.ValidationError("Account not eligible for password reset.")
        attrs['user'] = user
        return attrs


class UpdatePasswordSerializer(serializers.Serializer):
    otp = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True, validators=[RegexValidator(regex='^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', message='Password must be 8+ chars with a mix of uppercase, lowercase, numbers, and symbols')], help_text="8+ chars with uppercase, lowercase, number, and special symbol")
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        otp = attrs.get('otp')
        reset_token = PasswordResetToken.objects.filter(token=otp).first()
        if not reset_token:
            raise serializers.ValidationError("Invalid token.")
        if reset_token.is_expired():
            reset_token.delete()
            raise serializers.ValidationError("Token has expired.")
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        attrs['reset_token'] = reset_token  # Pass token to view if needed
        return attrs

    def save(self, **kwargs):
        reset_token = self.validated_data['reset_token']
        user = reset_token.user
        user.set_password(self.validated_data['new_password'])
        user.save()
        reset_token.delete()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('id', 'first_name', 'last_name', 'email', 'phone_number', 'role', 'bvn', 'account_number', 'account_name', 'bank_name')
        read_only_fields = ['id', 'first_name', 'last_name', 'email', 'role', 'bvn']


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number', 'role', 'bvn', 'account_number', 'account_name', 'bank_name', 'is_verified', 'is_active']
