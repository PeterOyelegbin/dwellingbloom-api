from django.utils import timezone
from django.core.signing import Signer
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import get_user_model
from django.conf import settings
from celery import shared_task
from time import time
from .logger_config import email_logger, general_logger

def generate_email_activation_token(user):
    """
    Generate a token with expiration embedded in it.
    """
    signer = Signer(salt='email-verification')
    expiry_timestamp = int(time()) + (settings.EMAIL_VERIFICATION_EXPIRY_HOURS * 60 * 60)
    data = f"{user.id}:{expiry_timestamp}"
    return signer.sign(data)


def verification_email_template(user, verification_token: str) -> str:
    """
    Returns html body for the email verification email.
    """
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f4;">
            <tr>
                <td align="center" style="padding: 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0" border="0"
                        style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                        <tr>
                            <td style="padding: 20px;">
                                <p style="font-size: 16px; color: #333;">Hello {user},</p>
                                <p style="font-size: 16px; color: #333;">Thank you for registering. Use the verification token below to verify your email within the next 12 hours before it expires:</p>
                                <table cellpadding="0" cellspacing="0" border="0" align="center" style="margin: 20px 0;">
                                    <tr>
                                        <td align="center" style="background-color: #4CAF50; color: white; padding: 12px 24px; border-radius: 5px; font-size: 18px; font-weight: bold;">
                                            {verification_token}
                                        </td>
                                    </tr>
                                </table>
                                <p style="font-size: 16px; color: #333; margin-top: 20px;">
                                    Enter this token in the verification form to activate your account.
                                </p>
                                <p style="font-size: 16px; color: #333;">
                                    Regards,<br>
                                    <a href="https://dwellingbloom.com.ng" style="font-weight: bold; text-decoration: none;">DwellingBloom</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return body


def reset_password_email_template(user, token: str) -> str:
    """
    Returns html body for the reset password email.
    """
    body = f"""
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

                                <p style="font-size: 16px; color: #333333; margin: 0;">Regards,<br><a href="https://dwellingbloom.com.ng" style="font-weight: bold; text-decoration: none;">DwellingBloom</a></p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return body


@shared_task(bind=True, max_retries=3, default_retry_delay=60, autoretry_for=(Exception,), retry_backoff=True,
    retry_backoff_max=600, retry_jitter=True, time_limit=300, soft_time_limit=240)
def send_email_task(self, email_subject, email_body, email_recipient, email_headers=None):
    """
    Sends an HTML email asynchronously via Celery.
    Retries up to 3 times on failure with a 60s delay.
    """
    try:
        email_sender = settings.DEFAULT_FROM_EMAIL
        email = EmailMultiAlternatives(email_subject, email_body, email_sender, email_recipient, headers=email_headers)
        email.content_subtype = 'html'
        email.send()
    except Exception as e:
        email_logger.error("Error sending email (attempt %s): %s", self.request.retries + 1, e)
        raise self.retry(exc=e)


def verify_email_activation_token(token):
    """
    Verify the token by checking embedded expiration only.
    """
    signer = Signer(salt='email-verification')
    try:
        User = get_user_model()
        data = signer.unsign(token)
        # Parse user_id and expiry
        user_id, expiry_timestamp = data.split(':')
        expiry_timestamp = int(expiry_timestamp)
        # Check if token has expired
        if time() > expiry_timestamp:
            general_logger.error("Token has expired")
            return None
        # Get and verify user
        user = User.objects.get(id=user_id)
        user.is_verified = True
        user.last_login = timezone.now()
        user.save()
        return user
    except (ValueError, TypeError, User.DoesNotExist) as e:
        general_logger.error("Invalid token: %s", e)
        return None
    except Exception as e:
        general_logger.error("Invalid or expired token: %s", e)
        return None
