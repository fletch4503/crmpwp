from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Project, ProjectNote


class ProjectForm(forms.ModelForm):
    """
    Форма для создания/редактирования проекта.
    """

    tags_input = forms.CharField(
        label=_("Tags"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Enter tags separated by commas"),
                "data-tags": "true",
            }
        ),
        help_text=_("Enter tags separated by commas"),
    )

    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "company",
            "contact",
            "inn",
            "project_number",
            "status",
            "priority",
            "deadline",
            "notes",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "description": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 4}
            ),
            "company": forms.Select(attrs={"class": "select select-bordered"}),
            "contact": forms.Select(attrs={"class": "select select-bordered"}),
            "inn": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "pattern": r"\d{10,12}",
                    "title": _("ИНН должен содержать 10 или 12 цифр"),
                }
            ),
            "project_number": forms.TextInput(attrs={"class": "input input-bordered"}),
            "status": forms.Select(attrs={"class": "select select-bordered"}),
            "priority": forms.Select(attrs={"class": "select select-bordered"}),
            "deadline": forms.DateInput(
                attrs={"class": "input input-bordered", "type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Фильтруем компании и контакты по пользователю
        if self.user:
            from companies.models import Company
            from contacts.models import Contact

            self.fields["company"].queryset = Company.objects.filter(
                user=self.user, is_active=True
            )
            self.fields["contact"].queryset = Contact.objects.filter(
                user=self.user, is_active=True
            )

        # Если редактируем существующий проект, заполняем поле tags_input
        if self.instance and self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(self.instance.tags)

    def clean_inn(self):
        """Валидация ИНН."""
        inn = self.cleaned_data.get("inn")
        if inn:
            if not inn.isdigit():
                raise forms.ValidationError(_("ИНН должен содержать только цифры"))
            if len(inn) not in [10, 12]:
                raise forms.ValidationError(_("ИНН должен содержать 10 или 12 цифр"))
        return inn

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user

        # Сохраняем теги
        instance.tags = self.cleaned_data.get("tags_input", [])

        if commit:
            instance.save()
        return instance


class ProjectStatusUpdateForm(forms.ModelForm):
    """
    Форма для обновления статуса проекта.
    """

    reason = forms.CharField(
        label=_("Reason for status change"),
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "textarea textarea-bordered",
                "rows": 3,
                "placeholder": _("Optional reason for status change"),
            }
        ),
    )

    class Meta:
        model = Project
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "select select-bordered"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.old_status = None
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.old_status = self.instance.status

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Создаем запись в истории статусов
        if self.old_status and self.old_status != instance.status:
            from .models import ProjectStatusHistory

            ProjectStatusHistory.objects.create(
                project=instance,
                user=self.user,
                old_status=self.old_status,
                new_status=instance.status,
                reason=self.cleaned_data.get("reason", ""),
            )

        if commit:
            instance.save()
        return instance


class ProjectNoteForm(forms.ModelForm):
    """
    Форма для создания заметки к проекту.
    """

    class Meta:
        model = ProjectNote
        fields = ["title", "content", "note_type", "is_important", "is_private"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered",
                    "rows": 6,
                    "required": True,
                }
            ),
            "note_type": forms.Select(attrs={"class": "select select-bordered"}),
            "is_important": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "is_private": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop("project", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class ProjectSearchForm(forms.Form):
    """
    Форма поиска проектов.
    """

    query = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _(
                    "Search by title, description, INN, project number..."
                ),
                "hx-get": "/projects/search/",
                "hx-trigger": "input changed delay:300ms",
                "hx-target": "#projects-list",
                "hx-swap": "innerHTML",
            }
        ),
    )
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=[("", _("All"))] + Project.STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    priority = forms.ChoiceField(
        label=_("Priority"),
        required=False,
        choices=[("", _("All"))] + Project.PRIORITY_CHOICES,
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    company = forms.ModelChoiceField(
        label=_("Company"),
        queryset=None,
        required=False,
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    contact = forms.ModelChoiceField(
        label=_("Contact"),
        queryset=None,
        required=False,
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    inn = forms.CharField(
        label=_("ИНН"),
        required=False,
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": _("ИНН компании")}
        ),
    )
    project_number = forms.CharField(
        label=_("Project number"),
        required=False,
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": _("Номер проекта")}
        ),
    )
    has_deadline = forms.BooleanField(
        label=_("Has deadline"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
    )
    is_overdue = forms.BooleanField(
        label=_("Overdue only"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
    )
    tags = forms.CharField(
        label=_("Tags"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Filter by tags"),
                "data-tags-filter": "true",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Фильтруем компании и контакты по пользователю
        if self.user:
            from companies.models import Company
            from contacts.models import Contact

            self.fields["company"].queryset = Company.objects.filter(
                user=self.user, is_active=True
            )
            self.fields["contact"].queryset = Contact.objects.filter(
                user=self.user, is_active=True
            )


class ProjectEmailFilterForm(forms.Form):
    """
    Форма фильтрации email проекта.
    """

    sender = forms.EmailField(
        label=_("Sender"),
        required=False,
        widget=forms.EmailInput(attrs={"class": "input input-bordered"}),
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
    has_attachments = forms.BooleanField(
        label=_("Has attachments"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
    )
    search_body = forms.CharField(
        label=_("Search in body"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search text in email body"),
            }
        ),
    )
