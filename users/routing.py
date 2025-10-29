from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Уведомления пользователя
    re_path(r"ws/notifications/$", consumers.NotificationConsumer.as_asgi()),
    # Работа с проектами в реальном времени
    re_path(
        r"ws/projects/(?P<project_id>[^/]+)/$", consumers.ProjectConsumer.as_asgi()
    ),
    # Работа с email в реальном времени
    re_path(r"ws/emails/$", consumers.EmailConsumer.as_asgi()),
]
