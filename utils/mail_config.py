from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from celery import shared_task
from .logger_config import email_logger, general_logger

def generate_email_activation_link(user):
    uid = urlsafe_base64_encode(force_bytes(user.id))
    token = default_token_generator.make_token(user)
    activation_link = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}"
    return activation_link


def verification_email_template(user, verification_link: str) -> str:
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
                                <p style="font-size: 16px; color: #333;">Thank you for registering. Please verify your email by clicking the button below:</p>
                                <table cellpadding="0" cellspacing="0" border="0" align="center">
                                    <tr>
                                        <td align="center">
                                            <a href="{verification_link}"
                                                style="background-color: #4CAF50; color: white; padding: 10px 30px;
                                                       text-decoration: none; border-radius: 5px; font-size: 16px;">
                                                Verify Email
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                <p style="font-size: 16px; color: #333; margin-top: 20px;">
                                    If the button doesn't work, copy and paste this link:<br>
                                    <a href="{verification_link}" style="color: #4CAF50;">{verification_link}</a>
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

                                <p style="font-size: 16px; color: #333333; margin: 0;">Regards,<br><a href="https://dwellingbloom.com.ng" style="font-style: bold; text-decoration: none;">DwellingBloom</a></p>
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
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


def verify_email_activation_link(user, token):
    try:
        if default_token_generator.check_token(user, token):
            user.is_verified = True
            user.last_login = timezone.now()
            user.save()
            return True
        else:
            general_logger.error("Invalid or expired token: user=%s, token=%s", user, token)
            return False
    except (ValueError, TypeError) as e:
        general_logger.error(f"Error verifying email activation link: {e}")
        return False
