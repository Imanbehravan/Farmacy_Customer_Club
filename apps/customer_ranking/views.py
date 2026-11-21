import jdatetime
from django.shortcuts import render

from apps.reports.views import staff_only  # همان محدودیت is_staff گزارش‌ها
from .services import get_monthly_ranking

JALALI_MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']


@staff_only
def ranking_page(request):
    today = jdatetime.date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if not 1 <= month <= 12:
            raise ValueError
        jdatetime.date(year, month, 1)  # سال نامعتبر همین‌جا خطا می‌دهد
    except ValueError:
        year, month = today.year, today.month

    ranking = get_monthly_ranking(year, month)
    return render(request, 'customer_ranking/ranking.html', {
        'ranking': ranking,
        'year': year,
        'month': month,
        'month_name': JALALI_MONTHS[month - 1],
        'months': list(enumerate(JALALI_MONTHS, start=1)),
        'customer_count': len(ranking),
    })