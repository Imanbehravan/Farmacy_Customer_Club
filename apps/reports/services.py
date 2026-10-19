from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth

from apps.customer_club.models import Purchase


def base_queryset():
    """داده‌های گزارش: خریدهایی که به یک نسخه وصل‌اند"""
    return Purchase.objects.all()


def summary(qs):
    """جمع‌های کلی"""
    return qs.aggregate(
        total=Sum("amount"),
        before_discount=Sum("original_amount"),
        discount=Sum(F("original_amount") - F("amount"), filter=Q(original_amount__gt=0)),
        count=Count("id"),
        prescriptions=Count("prescription", distinct=True),
    )


def monthly_totals(qs):
    """جمع فروش و تعداد خرید هر ماه"""
    return (
        qs.annotate(m=TruncMonth("purchase_date"))   # تاریخ را به اول ماهش تبدیل می‌کند
          .values("m")                               # بر اساس ماه گروه‌بندی کن
          .annotate(total=Sum("amount"), count=Count("id"))
          .order_by("m")
    )