from celery import shared_task
from django.utils.html import escape
from .models import Message
from utils.mail_config import send_email_task


@shared_task
def notify_new_message(message_id):
    try:
        message = Message.objects.select_related("conversation__apartment", "conversation__tenant", "sender").get(id=message_id)
    except Message.DoesNotExist:
        return
    # re-check at execution time — recipient may have read it during the countdown
    if message.is_read:
        return
    conversation = message.conversation
    recipient = (
        conversation.apartment.owner
        if message.sender_id == conversation.tenant_id
        else conversation.tenant
    )
    if recipient is None or not recipient.email:
        return
    safe_sender_name = escape(f"{message.sender.first_name} {message.sender.last_name}")
    safe_recipient_name = escape(recipient.first_name)
    safe_apartment_name = escape(conversation.apartment.name)
    safe_content = escape(message.content[:200])
    subject = f"New message about {conversation.apartment.name}"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 24px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden;">
          <tr>
            <td style="padding: 24px;">
              <h2 style="margin: 0 0 16px; color: #1a1a1a;">New message on DwellingBloom</h2>
              <p style="margin: 0 0 12px; color: #333333;">
                Hi {safe_recipient_name},
              </p>
              <p style="margin: 0 0 12px; color: #333333;">
                <strong>{safe_sender_name}</strong> sent you a message about <strong>{safe_apartment_name}</strong>:
              </p>
              <blockquote style="margin: 0 0 20px; padding: 12px 16px; background: #f9f9f9;
                    border-left: 3px solid #cccccc; color: #555555; font-style: italic;">
                {safe_content}
              </blockquote>
              <a href="https://dwellingbloom.com/conversations/{conversation.id}"
                 style="display: inline-block; padding: 10px 20px; background-color: #2b6cb0;
                    color: #ffffff; text-decoration: none; border-radius: 4px;">
                Reply now
              </a>
              <p style="margin: 24px 0 0; font-size: 12px; color: #999999;">
                You're receiving this because you have an active conversation on DwellingBloom.
              </p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    send_email_task.delay(email_subject=subject, email_body=body, email_recipient=[recipient.email])
