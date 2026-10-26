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
    phone = df.CharFilter(method="filter_phone", label="شماره موبایل")
    year = df.NumberFilter(method = "noop", label="سال")
    month = df.NumberFilter(method = "noop", label="ماه")
    day = df.NumberFilter(method = "noop", label="روز")

    class Meta:
        model = Prescription
        fields = []
        
    def noop(self, queryset, name, value):

        return queryset
    def filter_phone(self, queryset, name, value):
        # ارقام فارسی/عربی -> انگلیسی
        v = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        v = "".join(ch for ch in v if ch.isdigit())   # حذف فاصله، +، خط تیره
        if v.startswith("98"):
            v = v[2:]
        v = v.lstrip("0")
        if not v:
            return queryset
        return queryset.filter(user__phone_number__contains=v)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        data = self.form.cleaned_data
        y, m, d = data.get("year"), data.get("month"), data.get("day")
        if not y:
            return queryset

        y = int(y)
        try:
            if m and d:
                start = jdatetime.date(y, int(m), int(d))
                end = start + jdatetime.timedelta(days=1)
            elif m:
                start = jdatetime.date(y, int(m), 1)
                end = (jdatetime.date(y + 1, 1, 1) if int(m) == 12
                       else jdatetime.date(y, int(m) + 1, 1))
            else:
                start = jdatetime.date(y, 1, 1)
                end = jdatetime.date(y + 1, 1, 1)
        except ValueError:
            return queryset.none()

        return queryset.filter(
            created_at__date__gte=start.togregorian(),
            created_at__date__lt=end.togregorian(),
        )