from django import template

from apps.reports.jalali_utils import to_jalali

register = template.Library()


@register.filter
def jalali(value, fmt="%Y/%m/%d"):
    return to_jalali(value, fmt)