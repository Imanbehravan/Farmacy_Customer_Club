import django_filters as df
import jdatetime
from django import forms

from apps.prescriptions.models import Prescription


class JalaliDateField(forms.Field):
    """ورودی شمسی مثل 1405/07/25 را به تاریخ میلادی تبدیل می‌کند"""

    def to_python(self, value):
        if not value:
            return None
        try:
            y, m, d = [int(x) for x in str(value).strip().replace("-", "/").split("/")]
            return jdatetime.date(y, m, d).togregorian()
        except (ValueError, TypeError):
            raise forms.ValidationError("تاریخ شمسی نامعتبر است. مثال: 1405/07/25")


class JalaliDateFilter(df.Filter):
    field_class = JalaliDateField


class PurchaseFilter(df.FilterSet):
    date_from = JalaliDateFilter(
        field_name="created_at", lookup_expr="date__gte", label="از تاریخ",
        widget=forms.TextInput(attrs={"placeholder": "1405/07/01"}),
    )
    date_to = JalaliDateFilter(
        field_name="created_at", lookup_expr="date__lte", label="تا تاریخ",
        widget=forms.TextInput(attrs={"placeholder": "1405/07/30"}),
    )
    min_amount = df.NumberFilter(field_name="amount", lookup_expr="gte", label="حداقل مبلغ")
    max_amount = df.NumberFilter(field_name="amount", lookup_expr="lte", label="حداکثر مبلغ")
    phone = df.CharFilter(field_name="user__phone_number", lookup_expr="icontains",
                          label="شماره موبایل")

    class Meta:
        model = Prescription
        fields = []