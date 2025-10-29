from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Contact, ContactGroup, ContactInteraction


class ContactForm(forms.ModelForm):
    """
    Форма для создания/редактирования контакта.
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
        model = Contact
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "company",
            "position",
            "address",
            "notes",
            "telegram",
            "whatsapp",
            "linkedin",
            "website",
            "is_favorite",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "last_name": forms.TextInput(attrs={"class": "input input-bordered"}),
            "email": forms.EmailInput(attrs={"class": "input input-bordered"}),
            "phone": forms.TextInput(attrs={"class": "input input-bordered"}),
            "company": forms.TextInput(attrs={"class": "input input-bordered"}),
            "position": forms.TextInput(attrs={"class": "input input-bordered"}),
            "address": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 4}
            ),
            "telegram": forms.TextInput(attrs={"class": "input input-bordered"}),
            "whatsapp": forms.TextInput(attrs={"class": "input input-bordered"}),
            "linkedin": forms.URLInput(attrs={"class": "input input-bordered"}),
            "website": forms.URLInput(attrs={"class": "input input-bordered"}),
            "is_favorite": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Если редактируем существующий контакт, заполняем поле tags_input
        if self.instance and self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(self.instance.tags)

    def clean_tags_input(self):
        """Очистка и валидация тегов."""
        tags_input = self.cleaned_data.get("tags_input", "")
        if tags_input:
            # Разделяем по запятым, убираем пробелы, фильтруем пустые
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            return tags
        return []

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user

        # Сохраняем теги
        instance.tags = self.cleaned_data.get("tags_input", [])

        if commit:
            instance.save()
        return instance


class ContactGroupForm(forms.ModelForm):
    """
    Форма для создания/редактирования группы контактов.
    """

    class Meta:
        model = ContactGroup
        fields = ["name", "description", "color", "contacts"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "description": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
            "color": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "type": "color",
                    "value": "#3B82F6",
                }
            ),
            "contacts": forms.SelectMultiple(attrs={"class": "select select-bordered"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Фильтруем контакты по пользователю
        if self.user:
            self.fields["contacts"].queryset = Contact.objects.filter(user=self.user)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class ContactInteractionForm(forms.ModelForm):
    """
    Форма для добавления взаимодействия с контактом.
    """

    class Meta:
        model = ContactInteraction
        fields = ["interaction_type", "title", "description", "duration", "outcome"]
        widgets = {
            "interaction_type": forms.Select(attrs={"class": "select select-bordered"}),
            "title": forms.TextInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "description": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 4}
            ),
            "duration": forms.NumberInput(
                attrs={
                    "class": "input input-bordered",
                    "min": "1",
                    "placeholder": _("Duration in minutes"),
                }
            ),
            "outcome": forms.TextInput(attrs={"class": "input input-bordered"}),
        }

    def __init__(self, *args, **kwargs):
        self.contact = kwargs.pop("contact", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.contact:
            instance.contact = self.contact
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class ContactImportForm(forms.Form):
    """
    Форма для импорта контактов.
    """

    file = forms.FileField(
        label=_("File"),
        help_text=_("Supported formats: CSV, vCard"),
        widget=forms.FileInput(
            attrs={
                "class": "file-input file-input-bordered",
                "accept": ".csv,.vcf,.vcard",
            }
        ),
    )
    file_format = forms.ChoiceField(
        label=_("Format"),
        choices=[
            ("csv", "CSV"),
            ("vcard", "vCard"),
        ],
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    group = forms.ModelChoiceField(
        label=_("Add to group"),
        queryset=ContactGroup.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Фильтруем группы по пользователю
        if self.user:
            self.fields["group"].queryset = ContactGroup.objects.filter(user=self.user)


class ContactSearchForm(forms.Form):
    """
    Форма поиска контактов.
    """

    query = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by name, email, phone, company..."),
                "hx-get": "/contacts/search/",
                "hx-trigger": "input changed delay:300ms",
                "hx-target": "#contacts-list",
                "hx-swap": "innerHTML",
            }
        ),
    )
    group = forms.ModelChoiceField(
        label=_("Group"),
        queryset=ContactGroup.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    is_favorite = forms.BooleanField(
        label=_("Favorites only"),
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

        # Фильтруем группы по пользователю
        if self.user:
            self.fields["group"].queryset = ContactGroup.objects.filter(user=self.user)
