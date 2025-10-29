from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Company, Order, Payment, CompanyNote


class CompanyForm(forms.ModelForm):
    """
    Форма для создания/редактирования компании.
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
        model = Company
        fields = [
            "name",
            "inn",
            "company_type",
            "status",
            "legal_address",
            "actual_address",
            "phone",
            "email",
            "website",
            "contact_person",
            "contact_position",
            "credit_limit",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "inn": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "required": True,
                    "pattern": r"\d{10,12}",
                    "title": _("ИНН должен содержать 10 или 12 цифр"),
                }
            ),
            "company_type": forms.Select(attrs={"class": "select select-bordered"}),
            "status": forms.Select(attrs={"class": "select select-bordered"}),
            "legal_address": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered",
                    "rows": 3,
                    "required": True,
                }
            ),
            "actual_address": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
            "phone": forms.TextInput(attrs={"class": "input input-bordered"}),
            "email": forms.EmailInput(attrs={"class": "input input-bordered"}),
            "website": forms.URLInput(attrs={"class": "input input-bordered"}),
            "contact_person": forms.TextInput(attrs={"class": "input input-bordered"}),
            "contact_position": forms.TextInput(
                attrs={"class": "input input-bordered"}
            ),
            "credit_limit": forms.NumberInput(
                attrs={"class": "input input-bordered", "min": "0", "step": "0.01"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Если редактируем существующую компанию, заполняем поле tags_input
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


class OrderForm(forms.ModelForm):
    """
    Форма для создания/редактирования заказа.
    """

    class Meta:
        model = Order
        fields = [
            "company",
            "order_number",
            "title",
            "description",
            "amount",
            "status",
            "due_date",
            "priority",
            "notes",
        ]
        widgets = {
            "company": forms.Select(attrs={"class": "select select-bordered"}),
            "order_number": forms.TextInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "title": forms.TextInput(
                attrs={"class": "input input-bordered", "required": True}
            ),
            "description": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 4}
            ),
            "amount": forms.NumberInput(
                attrs={
                    "class": "input input-bordered",
                    "required": True,
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "status": forms.Select(attrs={"class": "select select-bordered"}),
            "due_date": forms.DateInput(
                attrs={"class": "input input-bordered", "type": "date"}
            ),
            "priority": forms.Select(attrs={"class": "select select-bordered"}),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Фильтруем компании по пользователю
        if self.user:
            self.fields["company"].queryset = Company.objects.filter(user=self.user)

    def clean_order_number(self):
        """Валидация номера заказа."""
        order_number = self.cleaned_data.get("order_number")
        company = self.cleaned_data.get("company")

        if company and order_number:
            # Проверяем уникальность номера заказа для компании
            existing_order = Order.objects.filter(
                company=company, order_number=order_number
            ).exclude(pk=self.instance.pk if self.instance else None)

            if existing_order.exists():
                raise forms.ValidationError(
                    _("Заказ с таким номером уже существует для этой компании")
                )

        return order_number

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class PaymentForm(forms.ModelForm):
    """
    Форма для создания/редактирования платежа.
    """

    class Meta:
        model = Payment
        fields = [
            "company",
            "order",
            "amount",
            "payment_method",
            "payment_number",
            "invoice_number",
            "payment_date",
            "status",
            "notes",
        ]
        widgets = {
            "company": forms.Select(attrs={"class": "select select-bordered"}),
            "order": forms.Select(attrs={"class": "select select-bordered"}),
            "amount": forms.NumberInput(
                attrs={
                    "class": "input input-bordered",
                    "required": True,
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "payment_method": forms.Select(attrs={"class": "select select-bordered"}),
            "payment_number": forms.TextInput(attrs={"class": "input input-bordered"}),
            "invoice_number": forms.TextInput(attrs={"class": "input input-bordered"}),
            "payment_date": forms.DateInput(
                attrs={
                    "class": "input input-bordered",
                    "type": "date",
                    "required": True,
                }
            ),
            "status": forms.Select(attrs={"class": "select select-bordered"}),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Фильтруем компании и заказы по пользователю
        if self.user:
            self.fields["company"].queryset = Company.objects.filter(user=self.user)
            self.fields["order"].queryset = Order.objects.filter(user=self.user)

    def clean(self):
        cleaned_data = super().clean()
        company = cleaned_data.get("company")
        order = cleaned_data.get("order")
        amount = cleaned_data.get("amount")

        # Если указан заказ, проверяем что он принадлежит компании
        if order and company and order.company != company:
            raise forms.ValidationError(
                _("Выбранный заказ не принадлежит выбранной компании")
            )

        # Проверяем доступный кредитный лимит
        if company and amount:
            available_credit = company.available_credit
            if amount > available_credit:
                raise forms.ValidationError(
                    _(
                        "Сумма платежа превышает доступный кредитный лимит (%(limit)s руб.)"
                    )
                    % {"limit": available_credit}
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class CompanyNoteForm(forms.ModelForm):
    """
    Форма для создания заметки о компании.
    """

    class Meta:
        model = CompanyNote
        fields = ["title", "content", "note_type", "is_important"]
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
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.company:
            instance.company = self.company
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class CompanySearchForm(forms.Form):
    """
    Форма поиска компаний.
    """

    query = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by name, INN, email..."),
                "hx-get": "/companies/search/",
                "hx-trigger": "input changed delay:300ms",
                "hx-target": "#companies-list",
                "hx-swap": "innerHTML",
            }
        ),
    )
    company_type = forms.ChoiceField(
        label=_("Type"),
        required=False,
        choices=[("", _("All"))] + Company.COMPANY_TYPES,
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=[("", _("All"))] + Company.STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    has_debt = forms.BooleanField(
        label=_("Has debt"),
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


class OrderSearchForm(forms.Form):
    """
    Форма поиска заказов.
    """

    query = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by order number, title, company..."),
            }
        ),
    )
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=[("", _("All"))] + Order.ORDER_STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "select select-bordered"}),
    )
    company = forms.ModelChoiceField(
        label=_("Company"),
        queryset=Company.objects.none(),
        required=False,
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

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Фильтруем компании по пользователю
        if self.user:
            self.fields["company"].queryset = Company.objects.filter(user=self.user)
