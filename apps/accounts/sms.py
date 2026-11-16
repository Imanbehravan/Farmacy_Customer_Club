"""ارسال پیامک کد تایید با کاوه‌نگار (سرویس Verify Lookup).

مستندات: https://kavenegar.com/rest.html  (متد verify/lookup)

برای کار کردن لازم است:
  * KAVENEGAR_API_KEY   -> کلید API از پنل کاوه‌نگار
  * KAVENEGAR_TEMPLATE  -> نام «قالب تایید» که در پنل ساخته و تایید شده است
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

API_URL = 'https://api.kavenegar.com/v1/{api_key}/verify/lookup.json'


class SMSError(Exception):
    """خطا در ارسال پیامک (پیام برای لاگ است، نه برای نمایش به کاربر)."""


def is_configured():
    return bool(getattr(settings, 'KAVENEGAR_API_KEY', ''))


def send_otp(phone_number, code):
    """کد تایید را با قالب Verify Lookup کاوه‌نگار می‌فرستد.

    در صورت هر مشکلی SMSError پرتاب می‌شود.
    """
    api_key = getattr(settings, 'KAVENEGAR_API_KEY', '')
    if not api_key:
        raise SMSError('KAVENEGAR_API_KEY تنظیم نشده است')

    payload = {
        'receptor': phone_number,
        'token': code,
        'template': getattr(settings, 'KAVENEGAR_TEMPLATE', 'verify'),
    }
    try:
        resp = requests.post(
            API_URL.format(api_key=api_key),
            data=payload,
            timeout=getattr(settings, 'KAVENEGAR_TIMEOUT', 10),
        )
    except requests.RequestException as exc:
        raise SMSError(f'خطای شبکه در ارتباط با کاوه‌نگار: {exc.__class__.__name__}') from exc

    try:
        body = resp.json()
        status = body['return']['status']
        message = body['return'].get('message', '')
    except (ValueError, KeyError, TypeError):
        raise SMSError(f'پاسخ نامعتبر از کاوه‌نگار (HTTP {resp.status_code})')

    if status != 200:
        # مثلا 401: کلید اشتباه، 424: قالب پیدا نشد/تایید نشده، 418: اعتبار کافی نیست
        raise SMSError(f'کاوه‌نگار status={status}: {message}')

    logger.info('OTP SMS sent to %s***', phone_number[:6])
