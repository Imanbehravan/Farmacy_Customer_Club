from datetime import datetime, time

import jdatetime
from django.db.models import Sum, Count
from django.utils import timezone

from apps.reports.services import  base_queryset


def month_range(j_year, j_month):
    """بازه [شروع، پایان) ماه شمسی را به datetime میلادی aware برمی‌گرداند."""
    start_j = jdatetime.date(j_year, j_month, 1)
    if j_month == 12:
        end_j = jdatetime.date(j_year + 1, 1, 1)
    else:
        end_j = jdatetime.date(j_year, j_month + 1, 1)

    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(start_j.togregorian(), time.min), tz)
    end = timezone.make_aware(datetime.combine(end_j.togregorian(), time.min), tz)
    return start, end


def get_monthly_ranking(j_year, j_month):
    """لیست مشتریان مرتب‌شده بر اساس مجموع خرید ماه."""
    start, end = month_range(j_year, j_month)

    rows = (
        base_queryset()
        .filter(status='delivered', delivered_at__gte=start, delivered_at__lt=end)
        .values('user_id', 'user__phone_number', 'user__first_name', 'user__last_name')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )

    ranking = []
    for rank, row in enumerate(rows, start=1):
        name = f"{row['user__first_name']} {row['user__last_name']}".strip()
        ranking.append({
            'rank': rank,
            'user_id': row['user_id'],
            'name': name or row['user__phone_number'],
            'phone_number': row['user__phone_number'],
            'total': row['total'],
            'count': row['count'],
        })
    return ranking