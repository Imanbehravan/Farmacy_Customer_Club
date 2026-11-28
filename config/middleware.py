
from django.utils import timezone
from zoneinfo import _zoneinfo


class TimezoneMiddleware:
    """ست کردن تایم‌زون تهران برای تمام درخواست‌ها"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.tehran_tz = _zoneinfo.ZoneInfo("Asia/Tehran")

    def __call__(self, request):
        with timezone.override(self.tehran_tz):
            return self.get_response(request)
