from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

from .models import UserRole

User = get_user_model()


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """
    Обработчик создания нового пользователя.
    """
    if created:
        # Отправляем уведомление через WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{instance.id}",
            {
                "type": "system_notification",
                "level": "info",
                "title": "Добро пожаловать!",
                "message": f"Аккаунт {instance.email} успешно создан.",
                "timestamp": timezone.now().isoformat(),
            },
        )


@receiver(post_save, sender=UserRole)
def user_role_changed_handler(sender, instance, created, **kwargs):
    """
    Обработчик изменения ролей пользователя.
    """
    action = "назначена" if created else "изменена"

    # Отправляем уведомление пользователю
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{instance.user.id}",
        {
            "type": "system_notification",
            "level": "info",
            "title": "Роль изменена",
            "message": f"Вам {action} роль: {instance.role.name}",
            "timestamp": timezone.now().isoformat(),
        },
    )


# Сигналы для других приложений
def send_realtime_notification(user_id, event_type, data):
    """
    Вспомогательная функция для отправки уведомлений через WebSocket.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": event_type,
            **data,
            "timestamp": timezone.now().isoformat(),
        },
    )


# Импортируем сигналы из других приложений
from projects.signals import *  # noqa
from emails.signals import *  # noqa
from contacts.signals import *  # noqa
from companies.signals import *  # noqa
