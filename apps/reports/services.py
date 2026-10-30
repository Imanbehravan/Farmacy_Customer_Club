from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth

from apps.prescriptions.models import Prescription
from collections import OrderedDict
import jdatetime
from django.utils import timezone


def jalali_monthly(qs):
    """جمع فروش و تعداد هر ماه شمسی"""
    buckets = OrderedDict()
    for p in qs.order_by("created_at").only("created_at", "amount"):
        t = timezone.localtime(p.created_at)
        j = jdatetime.datetime.fromgregorian(datetime=t)
        key = (j.year, j.month)
        b = buckets.setdefault(
            key, {"label": f"{j.year}/{j.month:02d}", "total": 0, "count": 0}
        )
        b["total"] += p.amount
        b["count"] += 1
    return list(buckets.values())

def base_queryset():
    """داده‌های گزارش: نسخه‌ها"""
    return Prescription.objects.filter(original_amount__gt=0)

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