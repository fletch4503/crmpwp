from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from .models import User


class CustomUserCreationForm(UserCreationForm):
    """
    Форма создания пользователя с дополнительными полями.
    """

    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "input input-bordered", "placeholder": _("Enter email")}
        ),
    )
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
    date_of_birth = forms.DateField(
        label=_("Date of birth"),
        required=False,
        widget=forms.DateInput(attrs={"class": "input input-bordered", "type": "date"}),
    )

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "phone",
            "date_of_birth",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "input input-bordered"})
        self.fields["password2"].widget.attrs.update({"class": "input input-bordered"})


class CustomUserChangeForm(UserChangeForm):
    """
    Форма изменения пользователя.
    """

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "phone",
            "date_of_birth",
            "avatar",
            # "ip_address",
            # "is_email_verified",
            # "is_phone_verified",
            # "is_email_verified",
            # "is_email_verified",
            # "is_active",
            # "is_staff",
        )


class ProfileUpdateForm(forms.ModelForm):
    """
    Форма обновления профиля пользователя.
    """

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "date_of_birth", "avatar")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input input-bordered"}),
            "last_name": forms.TextInput(attrs={"class": "input input-bordered"}),
            "phone": forms.TextInput(attrs={"class": "input input-bordered"}),
            "date_of_birth": forms.DateInput(
                attrs={"class": "input input-bordered", "type": "date"}
            ),
            "avatar": forms.FileInput(
                attrs={"class": "file-input file-input-bordered"}
            ),
        }


class TokenGenerationForm(forms.Form):
    """
    Форма генерации токена доступа.
    """

    expires_in_hours = forms.IntegerField(
        label=_("Expires in (hours)"),
        min_value=1,
        max_value=8760,  # 1 year
        initial=24,
        widget=forms.NumberInput(attrs={"class": "input input-bordered"}),
    )
    description = forms.CharField(
        label=_("Description"),
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Optional description"),
            }
        ),
    )
