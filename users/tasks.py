from django.utils import timezone
from django.contrib.auth import get_user_model
from celery import shared_task

from .models import AccessToken

User = get_user_model()


@shared_task(bind=True)
def cleanup_expired_tokens(self):
    """
    Очистка истекших токенов доступа.
    """
    expired_tokens = AccessToken.objects.filter(
        expires_at__lt=timezone.now(), is_active=True
    )

    count = expired_tokens.update(is_active=False)

    # Логируем результат
    print(f"Cleaned up {count} expired tokens")

    # Отправляем уведомление администраторам
    from users.signals import send_realtime_notification

    admin_users = User.objects.filter(is_superuser=True)

    for admin in admin_users:
        send_realtime_notification(
            admin.id,
            "system_notification",
            {
                "level": "info",
                "title": "Очистка токенов",
                "message": f"Удалено {count} истекших токенов доступа.",
            },
        )

    return count


@shared_task(bind=True)
def send_user_notification(self, user_id, title, message, level="info"):
    """
    Отправка уведомления пользователю.
    """
    from users.signals import send_realtime_notification

    send_realtime_notification(
        user_id,
        "system_notification",
        {
            "level": level,
            "title": title,
            "message": message,
        },
    )

    return True


@shared_task(bind=True)
def bulk_user_operation(self, user_ids, operation, **kwargs):
    """
    Массовые операции над пользователями.
    """
    users = User.objects.filter(id__in=user_ids)

    if operation == "deactivate":
        count = users.update(is_active=False)
        message = f"Деактивировано {count} пользователей"

    elif operation == "activate":
        count = users.update(is_active=True)
        message = f"Активировано {count} пользователей"

    elif operation == "delete":
        count = users.delete()[0]
        message = f"Удалено {count} пользователей"

    else:
        return f"Неизвестная операция: {operation}"

    # Уведомляем администратора
    from users.signals import send_realtime_notification

    admin_users = User.objects.filter(is_superuser=True)

    for admin in admin_users:
        send_realtime_notification(
            admin.id,
            "system_notification",
            {
                "level": "info",
                "title": "Массовые операции",
                "message": message,
            },
        )

    return message
