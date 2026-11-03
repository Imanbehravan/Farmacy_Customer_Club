import datetime

import jdatetime
from django.utils import timezone


def to_jalali(value, fmt="%Y/%m/%d"):
    if not value:
        return ""
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        value = value.date()
    return jdatetime.date.fromgregorian(date=value).strftime(fmt)