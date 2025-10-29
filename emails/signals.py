from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import EmailMessage
from .tasks import process_email_message


@receiver(post_save, sender=EmailMessage)
def email_received_handler(sender, instance, created, **kwargs):
    """
    Обработчик получения нового email.
    """
    if created:
        # Запускаем обработку email в фоне
        process_email_message.delay(instance.id)

        # Отправляем уведомление пользователю
        from users.signals import send_realtime_notification

        send_realtime_notification(
            instance.user.id,
            "email_received",
            {
                "email_id": str(instance.id),
                "subject": instance.subject,
                "sender": instance.sender,
            },
        )

        # Отправляем уведомление в группу email
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"email_user_{instance.user.id}",
            {
                "type": "email_received",
                "email_id": str(instance.id),
                "subject": instance.subject,
                "sender": instance.sender,
                "timestamp": timezone.now().isoformat(),
            },
        )
