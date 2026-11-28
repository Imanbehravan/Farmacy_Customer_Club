"""
ارسال پیامک کد تایید با «Verify Lookup» کاوه‌نگار.

تنظیمات (از .env):
    KAVENEGAR_API_KEY   کلید API پنل کاوه‌نگار
    KAVENEGAR_TEMPLATE  نام قالب تایید (مثلاً verify) — متن قالب باید %token داشته باشد
    KAVENEGAR_SENDER    (اختیاری) فقط اگر قالب ندارید و پیامک ساده می‌فرستید
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

API_BASE = 'https://api.kavenegar.com/v1'


class SMSError(Exception):
    """خطا در ارسال پیامک (متن خطا فقط برای لاگ است، نه نمایش به کاربر)."""


def _api_key():
    return (getattr(settings, 'KAVENEGAR_API_KEY', '') or '').strip()


def is_configured():
    return bool(_api_key())


def send_otp(phone, code):
    """
    کد تایید را به شماره‌ی موبایل پیامک می‌کند.
    در صورت هر خطا SMSError پرتاب می‌شود.
    """
    api_key = _api_key()
    if not api_key:
        raise SMSError('KAVENEGAR_API_KEY در .env تنظیم نشده است.')

    template = (getattr(settings, 'KAVENEGAR_TEMPLATE', '') or '').strip()
    if template:
        url = f'{API_BASE}/{api_key}/verify/lookup.json'
        data = {'receptor': phone, 'token': code, 'template': template}
    else:
        sender = (getattr(settings, 'KAVENEGAR_SENDER', '') or '').strip()
        if not sender:
            raise SMSError('KAVENEGAR_TEMPLATE یا KAVENEGAR_SENDER باید در .env تنظیم شود.')
        url = f'{API_BASE}/{api_key}/sms/send.json'
        data = {'receptor': phone, 'sender': sender,
                'message': f'کد تایید باشگاه مشتریان: {code}'}

    try:
        resp = requests.post(url, data=data, timeout=getattr(settings, 'SMS_TIMEOUT', 10))
    except requests.RequestException as exc:
        # کلید API داخل آدرس است؛ نباید وارد لاگ شود
        raise SMSError(f'خطای شبکه: {str(exc).replace(api_key, "***")}') from exc

    try:
        body = resp.json()
    except ValueError as exc:
        raise SMSError(f'پاسخ نامعتبر از کاوه‌نگار (HTTP {resp.status_code})') from exc

    result = body.get('return') or {}
    if resp.status_code != 200 or result.get('status') != 200:
        raise SMSError(f'کاوه‌نگار (HTTP {resp.status_code}): {result}')
