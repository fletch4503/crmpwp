from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    """
    Кастомный адаптер для allauth account.
    """

    def save_user(self, request, user, form, commit=True):
        """
        Сохраняет пользователя с дополнительными полями.
        """
        user = super().save_user(request, user, form, commit=False)
        user.first_name = form.cleaned_data.get("first_name", "")
        user.last_name = form.cleaned_data.get("last_name", "")
        user.phone = form.cleaned_data.get("phone", "")

        # Сохраняем IP адрес при регистрации
        if request:
            user.ip_address = self._get_client_ip(request)

        if commit:
            user.save()
        return user

    def _get_client_ip(self, request):
        """
        Получает IP адрес клиента.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def send_mail(self, template_prefix, email, context):
        """
        Отправляет email с кастомными настройками.
        """
        context["current_site"] = context.get("current_site") or getattr(
            settings, "SITE_NAME", "CRM"
        )
        return super().send_mail(template_prefix, email, context)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Кастомный адаптер для allauth social account.
    """

    def save_user(self, request, sociallogin, form=None):
        """
        Сохраняет пользователя из социальной сети.
        """
        user = super().save_user(request, sociallogin, form)

        # Сохраняем IP адрес при регистрации через социальную сеть
        if request:
            user.ip_address = self._get_client_ip(request)
            user.save()

        return user

    def _get_client_ip(self, request):
        """
        Получает IP адрес клиента.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
