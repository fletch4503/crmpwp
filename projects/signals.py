from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Project, ProjectEmail


@receiver(post_save, sender=Project)
def project_created_handler(sender, instance, created, **kwargs):
    """
    Обработчик создания/обновления проекта.
    """
    if created:
        # Отправляем уведомление создателю проекта
        from users.signals import send_realtime_notification

        send_realtime_notification(
            instance.user.id,
            "project_created",
            {
                "project_id": str(instance.id),
                "title": instance.title,
            },
        )


@receiver(post_save, sender=ProjectEmail)
def project_email_linked_handler(sender, instance, created, **kwargs):
    """
    Обработчик привязки email к проекту.
    """
    if created:
        # Отправляем уведомление в группу проекта
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"project_{instance.project.id}",
            {
                "type": "email_linked",
                "email_id": str(instance.id),
                "subject": instance.subject,
                "timestamp": timezone.now().isoformat(),
            },
        )

        # Отправляем уведомление пользователю
        from users.signals import send_realtime_notification

        send_realtime_notification(
            instance.project.user.id,
            "system_notification",
            {
                "level": "info",
                "title": "Email привязан к проекту",
                "message": f'Email "{instance.subject}" привязан к проекту "{instance.project.title}"',
            },
        )
