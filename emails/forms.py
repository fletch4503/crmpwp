from django import forms
from django.utils.translation import gettext_lazy as _

from .models import EmailCredentials, EmailProcessingRule


class EmailCredentialsForm(forms.ModelForm):
    """
    Форма для настройки учетных данных Exchange.
    """

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": "input input-bordered"}),
        help_text=_("Your Exchange account password"),
    )

    class Meta:
        model = EmailCredentials
        fields = [
            "server",
            "email",
            "username",
            "password",
            "use_ssl",
            "port",
            "timeout",
            "sync_interval",
            "is_active",
        ]
        widgets = {
            "server": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "placeholder": "outlook.office365.com",
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "username": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "placeholder": "Usually same as email",
                    "required": True,
                }
            ),
            "use_ssl": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "port": forms.NumberInput(
                attrs={
                    "class": "input input-bordered",
                    "min": 1,
                    "max": 65535,
                    "value": 993,
                }
            ),
            "timeout": forms.NumberInput(
                attrs={
                    "class": "input input-bordered",
                    "min": 5,
                    "max": 300,
                    "value": 30,
                }
            ),
            "sync_interval": forms.NumberInput(
                attrs={
                    "class": "input input-bordered",
                    "min": 5,
                    "max": 1440,
                    "value": 15,
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class EmailProcessingRuleForm(forms.ModelForm):
    """
    Форма для создания/редактирования правил обработки email.
    """

    class Meta:
        model = EmailProcessingRule
        fields = [
            "name",
            "description",
            "sender_contains",
            "subject_contains",
            "body_contains",
            "auto_create_project",
            "auto_create_contact",
            "mark_as_important",
            "priority",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "description": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
            "sender_contains": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "placeholder": "e.g., @company.com",
                }
            ),
            "subject_contains": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "placeholder": "e.g., project, order",
                }
            ),
            "body_contains": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "placeholder": "e.g., ИНН, contract",
                }
            ),
            "auto_create_project": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "auto_create_contact": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "mark_as_important": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "priority": forms.NumberInput(
                attrs={
                    "class": "input input-bordered",
                    "min": 1,
                    "max": 1000,
                    "value": 100,
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class EmailSearchForm(forms.Form):
    """
    Форма поиска email сообщений.
    """

    query = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by subject, sender, body..."),
                "hx-get": "/emails/search/",
                "hx-trigger": "input changed delay:300ms",
                "hx-target": "#emails-list",
                "hx-swap": "innerHTML",
            }
        ),
    )
    sender = forms.EmailField(
        label=_("Sender"),
        required=False,
        widget=forms.EmailInput(attrs={"class": "input input-bordered"}),
    )
    has_attachments = forms.BooleanField(
        label=_("Has attachments"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
    )
    is_important = forms.BooleanField(
        label=_("Important only"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
    )
    is_read = forms.ChoiceField(
        label=_("Read status"),
        required=False,
        choices=[
            ("", _("All")),
            ("read", _("Read")),
            ("unread", _("Unread")),
        ],
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    date_from = forms.DateField(
        label=_("From date"),
        required=False,
        widget=forms.DateInput(attrs={"class": "input input-bordered", "type": "date"}),
    )
    date_to = forms.DateField(
        label=_("To date"),
        required=False,
        widget=forms.DateInput(attrs={"class": "input input-bordered", "type": "date"}),
    )
    parsed_inn = forms.CharField(
        label=_("Parsed ИНН"),
        required=False,
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": _("ИНН from email")}
        ),
    )
    related_to_project = forms.BooleanField(
        label=_("Related to projects"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
    )


class EmailTestConnectionForm(forms.Form):
    """
    Форма для тестирования подключения к Exchange.
    """

    server = forms.CharField(
        label=_("Exchange Server"),
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": "outlook.office365.com",
                "required": True,
            }
        ),
    )
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={"class": "input input-bordered", "required": True}
        ),
    )
    username = forms.CharField(
        label=_("Username"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "required": True}
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={"class": "input input-bordered", "required": True}
        ),
    )
    use_ssl = forms.BooleanField(
        label=_("Use SSL"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
    )
    port = forms.IntegerField(
        label=_("Port"),
        initial=993,
        min_value=1,
        max_value=65535,
        widget=forms.NumberInput(attrs={"class": "input input-bordered"}),
    )


class EmailImportForm(forms.Form):
    """
    Форма для ручного импорта email.
    """

    email_ids = forms.CharField(
        label=_("Email IDs"),
        widget=forms.Textarea(
            attrs={
                "class": "textarea textarea-bordered",
                "rows": 5,
                "placeholder": "Enter email message IDs, one per line",
            }
        ),
        help_text=_("Enter message IDs to import, one per line"),
    )
    force_reimport = forms.BooleanField(
        label=_("Force re-import"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
        help_text=_("Re-import emails that were already processed"),
    )
