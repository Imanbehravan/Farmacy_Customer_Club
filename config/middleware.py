from zoneinfo import ZoneInfo
from django.utils import timezone


class TimezoneMiddleware:
    """ست کردن تایم‌زون تهران برای تمام درخواست‌ها"""
    def __init__(self, get_response):
        self.get_response = get_response
        self.tehran_tz = ZoneInfo('Asia/Tehran')

    def __call__(self, request):
        timezone.activate(self.tehran_tz)
        response = self.get_response(request)
        timezone.deactivate()
        return response