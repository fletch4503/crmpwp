from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Company


@receiver(post_save, sender=Company)
def company_created_handler(sender, instance, created, **kwargs):
    """
    Обработчик создания компании.
    """
    if created:
        # Отправляем уведомление пользователю
        from users.signals import send_realtime_notification

        send_realtime_notification(
            instance.user.id,
            "system_notification",
            {
                "level": "info",
                "title": "Компания создана",
                "message": f'Компания "{instance.name}" успешно создана.',
            },
        )
