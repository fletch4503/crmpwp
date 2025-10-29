from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Contact


@receiver(post_save, sender=Contact)
def contact_created_handler(sender, instance, created, **kwargs):
    """
    Обработчик создания контакта.
    """
    if created:
        # Отправляем уведомление пользователю
        from users.signals import send_realtime_notification

        send_realtime_notification(
            instance.user.id,
            "contact_created",
            {
                "contact_id": str(instance.id),
                "name": instance.full_name,
                "email": instance.email,
            },
        )
