import jdatetime
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def jalali(value, fmt='%Y/%m/%d'):
    """تبدیل تاریخ میلادی به شمسی — مثال: {{ some_date|jalali:"%Y/%m/%d %H:%M" }}"""
    if not value:
        return ''
    try:
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        jdt = jdatetime.datetime.fromgregorian(datetime=value)
        return jdt.strftime(fmt)
    except Exception:
        return str(value)


@register.filter
def jalali_date(value):
    """فقط تاریخ شمسی — بدون ساعت"""
    return jalali(value, '%Y/%m/%d')


@register.filter
def jalali_datetime(value):
    """تاریخ و ساعت شمسی"""
    return jalali(value, '%Y/%m/%d %H:%M')