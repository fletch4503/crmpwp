from django import forms
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import SignupForm, LoginForm

from .models import User


class CustomSignupForm(SignupForm):
    """
    Кастомная форма регистрации пользователя allauth.
    """

    first_name = forms.CharField(
        label=_("First name"),
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Enter first name"),
            }
        ),
    )
    last_name = forms.CharField(
        label=_("Last name"),
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": _("Enter last name")}
        ),
    )
    phone = forms.CharField(
        label=_("Phone number"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("+7 (999) 999-99-99"),
            }
        ),
    )

    def signup(self, request, user):
        """Called after user is created, but before saved to handle additional fields."""
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone = self.cleaned_data.get("phone", "")
        user.save()
        return user

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.phone = self.cleaned_data.get("phone", "")
        user.save()
        return user


class CustomLoginForm(LoginForm):
    """
    Кастомная форма входа allauth.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget.attrs.update({"class": "input input-bordered"})
        self.fields["password"].widget.attrs.update({"class": "input input-bordered"})