import uuid
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Кастомный менеджер для модели User.
    """

    def _create_user(self, email, username, password, **extra_fields):
        """
        Создает и сохраняет пользователя с email и паролем.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username=None, password=None, **extra_fields):
        """
        Создает обычного пользователя.
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email, username=None, password=None, **extra_fields):
        """
        Создает суперпользователя.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self._create_user(email, username, password, **extra_fields)


class AccessTokenManager:
    """
    Менеджер для работы с токенами доступа.
    """

    @staticmethod
    def generate_token(user, expires_in_hours=24):
        """
        Генерирует новый токен доступа для пользователя.
        """
        from django.utils import timezone
        from .models import AccessToken

        expires_at = timezone.now() + timezone.timedelta(hours=expires_in_hours)
        token_value = str(uuid.uuid4())

        token = AccessToken.objects.create(
            user=user, token=token_value, expires_at=expires_at
        )

        return token

    @staticmethod
    def validate_token(token_value):
        """
        Проверяет валидность токена.
        """
        from django.utils import timezone
        from .models import AccessToken

        try:
            token = AccessToken.objects.get(token=token_value, is_active=True)
            if token.is_expired:
                token.is_active = False
                token.save()
                return None
            return token
        except AccessToken.DoesNotExist:
            return None

    @staticmethod
    def revoke_token(token_value):
        """
        Отзывает токен.
        """
        from .models import AccessToken

        try:
            token = AccessToken.objects.get(token=token_value)
            token.is_active = False
            token.save()
            return True
        except AccessToken.DoesNotExist:
            return False

    @staticmethod
    def cleanup_expired_tokens():
        """
        Удаляет истекшие токены.
        """
        from django.utils import timezone
        from .models import AccessToken

        expired_tokens = AccessToken.objects.filter(
            expires_at__lt=timezone.now(), is_active=True
        )
        count = expired_tokens.update(is_active=False)
        return count
