from django.db.models.signals import post_save
from django.dispatch import receiver
from decouple import config
from .models import Message
from .tasks import notify_new_message


@receiver(post_save, sender=Message)
def notify_on_new_message(sender, instance, created, **kwargs):
    if not created:
        return
    # give the recipient a window to read it in-app before emailing
    notify_new_message.apply_async(args=[str(instance.id)], countdown=config('MESSAGE_NOTIFCATION_DELAY_SECONDS', default=600, cast=int)
)
