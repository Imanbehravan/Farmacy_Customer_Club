from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth

from apps.prescriptions.models import Prescription


def base_queryset():
    """داده‌های گزارش: نسخه‌ها"""
    return Prescription.objects.all()


def summary(qs):
    """جمع‌های کلی"""
    return qs.aggregate(
        total=Sum("amount"),
        before_discount=Sum("original_amount"),
        discount=Sum(F("original_amount") - F("amount"), filter=Q(original_amount__gt=0)),
        count=Count("id"),
    )


def monthly_totals(qs):
    """جمع فروش و تعداد هر ماه"""
    return (
        qs.annotate(m=TruncMonth("created_at"))
          .values("m")
          .annotate(total=Sum("amount"), count=Count("id"))
          .order_by("m")
    )