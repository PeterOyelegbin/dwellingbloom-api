from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from django.core.cache import cache
from utils.logger_config import general_logger
import hashlib, time

"""
Custom JWT Authentication where access token is checked for blackilisting
before authentication.
"""
class CustomJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        # Validate the token using the default mechanism
        validated_token = super().get_validated_token(raw_token)

        # Create a cache key using the token's jti (JWT ID)
        jti = validated_token['jti']
        cache_key = self.get_cache_key(jti)

        # Check if the token is blacklisted in the cache
        if cache.get(cache_key) == 'blacklisted':
            raise AuthenticationFailed("This token has been blacklisted.")

        return validated_token

    @staticmethod
    def get_cache_key(jti):
        """
        Generates a cache key based on the token string by hashing the token.
        You can also include additional logic to create a unique key.
        """
        return hashlib.sha256(jti.encode()).hexdigest()

    @staticmethod
    def blacklist_token(jti: str, exp: int) -> bool:
        """
        Blacklists a token in Redis using its JTI and expiry timestamp.
        Returns True if blacklisted, False if already expired or on failure.
        """
        try:
            remaining_time = exp - int(time.time())
            if remaining_time > 0:
                cache.set(CustomJWTAuthentication.get_cache_key(jti), 'blacklisted', timeout=remaining_time)
                return True
            return False
        except Exception as e:
            general_logger.error("Failed to blacklist token (jti=%s): %s", jti, e)
            return False


class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'utils.jwt_config.CustomJWTAuthentication'  # full import path
    name = 'Bearer'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
