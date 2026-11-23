import jdatetime
from django.shortcuts import render

from apps.reports.views import staff_only  # همان محدودیت is_staff گزارش‌ها
from .services import get_monthly_ranking

JALALI_MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']

PERCENTAGES = [5, 10, 15, 20]
VALID_DAYS = [3, 7, 14, 30]


def _parse_month(params):
    """سال و ماه را از GET یا POST می‌خواند؛ اگر نامعتبر بود ماه جاری."""
    today = jdatetime.date.today()
    try:
        year = int(params.get('year', today.year))
        month = int(params.get('month', today.month))
        if not 1 <= month <= 12:
            raise ValueError
        jdatetime.date(year, month, 1)  # سال نامعتبر همین‌جا خطا می‌دهد
    except ValueError:
        year, month = today.year, today.month
    return year, month


@staff_only
def ranking_page(request):
    is_post = request.method == 'POST'
    year, month = _parse_month(request.POST if is_post else request.GET)
    ranking = get_monthly_ranking(year, month)

    context = {
        'ranking': ranking,
        'year': year,
        'month': month,
        'month_name': JALALI_MONTHS[month - 1],
        'months': list(enumerate(JALALI_MONTHS, start=1)),
        'customer_count': len(ranking),
        'percentages': PERCENTAGES,
        'valid_days': VALID_DAYS,
        'percentage': 10,
        'days': 7,
        'selected_ids': set(),
    }

    if is_post:
        selected_ids = {int(v) for v in request.POST.getlist('user_ids') if v.isdigit()}
        # فقط کسانی که واقعاً در رتبه‌بندی همین ماه هستند قبول می‌شوند
        selected = [r for r in ranking if r['user_id'] in selected_ids]

        try:
            percentage = int(request.POST.get('percentage', ''))
            days = int(request.POST.get('days', ''))
        except ValueError:
            percentage = days = None

        errors = []
        if not selected:
            errors.append('هیچ مشتری‌ای انتخاب نشده است.')
        if percentage not in PERCENTAGES:
            errors.append('درصد تخفیف معتبر نیست.')
        if days not in VALID_DAYS:
            errors.append('مدت اعتبار معتبر نیست.')

        context['selected_ids'] = {r['user_id'] for r in selected}
        if errors:
            context['errors'] = errors
        else:
            context['percentage'] = percentage
            context['days'] = days
            context['confirm'] = {
                'count': len(selected),
                'percentage': percentage,
                'days': days,
                'customers': selected,
            }

    return render(request, 'customer_ranking/ranking.html', context)