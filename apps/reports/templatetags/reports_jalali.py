import jdatetime
from django import template
from django.utils import timezone

register = template.Library()


@register.filter(name="jalali")
def jalali(value, fmt="%Y/%m/%d"):
    if not value:
        return ""
    if hasattr(value, "tzinfo") and timezone.is_aware(value):
        value = timezone.localtime(value)
    if hasattr(value, "hour"):
        j = jdatetime.datetime.fromgregorian(datetime=value)
    else:
        j = jdatetime.date.fromgregorian(date=value)
    return j.strftime(fmt)