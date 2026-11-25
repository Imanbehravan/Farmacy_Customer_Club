"""
ارسال پیامک کد تایید.

از دو سرویس‌دهنده‌ی رایج با توکن (API Key) پشتیبانی می‌شود:
  - kavenegar  (پیش‌فرض)
  - smsir

تنظیمات از فایل .env خوانده می‌شود (نام متغیرها در .env.example هست).
هیچ کتابخانه‌ی اضافه‌ای لازم نیست؛ فقط urllib از کتابخانه‌ی استاندارد پایتون.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class SMSError(Exception):
    """خطا در ارسال پیامک (متن خطا فقط برای لاگ است، نه نمایش به کاربر)."""


def is_configured():
    return bool(settings.SMS_API_KEY)


def _request(url, *, data=None, headers=None, as_json=False):
    body = None
    hdrs = dict(headers or {})
    if data is not None:
        if as_json:
            body = json.dumps(data).encode('utf-8')
            hdrs['Content-Type'] = 'application/json'
        else:
            body = urllib.parse.urlencode(data).encode('utf-8')
            hdrs['Content-Type'] = 'application/x-www-form-urlencoded'
    req = urllib.request.Request(url, data=body, headers=hdrs, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=settings.SMS_TIMEOUT) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode('utf-8', errors='replace')
        raise SMSError(f'HTTP {exc.code}: {raw[:300]}') from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SMSError(f'خطای شبکه: {exc}') from exc
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise SMSError(f'پاسخ نامعتبر از سرویس پیامک: {raw[:300]}') from exc


# ---------------------------------------------------------------- Kavenegar
def _send_kavenegar(phone, code):
    base = f'https://api.kavenegar.com/v1/{settings.SMS_API_KEY}'
    if settings.SMS_TEMPLATE:
        # ارسال با قالب (verify/lookup) — روش پیشنهادی برای کد تایید
        payload = {'receptor': phone, 'token': code, 'template': settings.SMS_TEMPLATE}
        result = _request(f'{base}/verify/lookup.json', data=payload)
    else:
        if not settings.SMS_SENDER:
            raise SMSError('SMS_TEMPLATE یا SMS_SENDER باید در .env تنظیم شود.')
        payload = {
            'receptor': phone,
            'sender': settings.SMS_SENDER,
            'message': f'کد تایید باشگاه مشتریان: {code}',
        }
        result = _request(f'{base}/sms/send.json', data=payload)

    status = (result.get('return') or {}).get('status')
    if status != 200:
        raise SMSError(f'کاوه‌نگار: {result.get("return")}')


# ------------------------------------------------------------------- SMS.ir
def _send_smsir(phone, code):
    headers = {'X-API-KEY': settings.SMS_API_KEY, 'Accept': 'application/json'}
    if settings.SMS_TEMPLATE:
        payload = {
            'mobile': phone,
            'templateId': int(settings.SMS_TEMPLATE),
            'parameters': [{'name': settings.SMS_TEMPLATE_PARAM, 'value': code}],
        }
        result = _request('https://api.sms.ir/v1/send/verify', data=payload,
                          headers=headers, as_json=True)
    else:
        if not settings.SMS_SENDER:
            raise SMSError('SMS_TEMPLATE یا SMS_SENDER باید در .env تنظیم شود.')
        payload = {
            'lineNumber': int(settings.SMS_SENDER),
            'messageText': f'کد تایید باشگاه مشتریان: {code}',
            'mobiles': [phone],
        }
        result = _request('https://api.sms.ir/v1/send/bulk',
                          data=payload, headers=headers, as_json=True)

    if result.get('status') != 1:
        raise SMSError(f'sms.ir: {result}')


_PROVIDERS = {
    'kavenegar': _send_kavenegar,
    'smsir': _send_smsir,
}


def send_otp(phone, code):
    """
    کد تایید را به شماره‌ی موبایل پیامک می‌کند.
    در صورت خطا SMSError پرتاب می‌شود.
    """
    if not is_configured():
        if settings.DEBUG:
            # حالت توسعه: بدون پنل پیامکی، کد فقط در لاگ سرور چاپ می‌شود (نه روی صفحه)
            logger.warning('[DEV] SMS_API_KEY تنظیم نشده. کد تایید %s: %s', phone, code)
            return
        raise SMSError('SMS_API_KEY در .env تنظیم نشده است.')

    sender = _PROVIDERS.get(settings.SMS_PROVIDER)
    if sender is None:
        raise SMSError(f'SMS_PROVIDER نامعتبر: {settings.SMS_PROVIDER}')
    sender(phone, code)
