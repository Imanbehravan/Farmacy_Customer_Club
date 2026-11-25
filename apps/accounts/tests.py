from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import sms
from .models import OTPCode, User

PHONE = '09123456789'


class FakeResponse:
    def __init__(self, status=200, message='تایید شد', http=200):
        self.status_code = http
        self._body = {'return': {'status': status, 'message': message}}

    def json(self):
        return self._body


@override_settings(KAVENEGAR_API_KEY='test-key', KAVENEGAR_TEMPLATE='verify', OTP_SHOW_ON_SCREEN=False)
class KavenegarClientTests(TestCase):
    def test_sends_verify_lookup_request(self):
        with mock.patch('apps.accounts.sms.requests.post', return_value=FakeResponse()) as post:
            sms.send_otp(PHONE, '123456')
        url = post.call_args.args[0]
        data = post.call_args.kwargs['data']
        self.assertIn('/v1/test-key/verify/lookup.json', url)
        self.assertEqual(data, {'receptor': PHONE, 'token': '123456', 'template': 'verify'})

    def test_api_error_raises(self):
        with mock.patch('apps.accounts.sms.requests.post', return_value=FakeResponse(status=424, message='قالب یافت نشد')):
            with self.assertRaises(sms.SMSError):
                sms.send_otp(PHONE, '123456')

    def test_network_error_raises(self):
        import requests
        with mock.patch('apps.accounts.sms.requests.post', side_effect=requests.ConnectTimeout()):
            with self.assertRaises(sms.SMSError):
                sms.send_otp(PHONE, '123456')

    @override_settings(KAVENEGAR_API_KEY='')
    def test_missing_key_raises(self):
        with self.assertRaises(sms.SMSError):
            sms.send_otp(PHONE, '123456')


@override_settings(KAVENEGAR_API_KEY='test-key', OTP_SHOW_ON_SCREEN=False)
class LoginFlowTests(TestCase):
    def setUp(self):
        cache.clear()

    def _login(self, phone=PHONE):
        return self.client.post(reverse('login'), {'phone_number': phone})

    @mock.patch('apps.accounts.views.sms.send_otp')
    def test_login_sends_sms_and_redirects(self, send):
        resp = self._login()
        self.assertRedirects(resp, reverse('verify_otp'), fetch_redirect_response=False)
        otp = OTPCode.objects.get(phone_number=PHONE)
        send.assert_called_once_with(PHONE, otp.code)
        # کد نباید روی صفحه نمایش داده شود
        page = self.client.get(reverse('verify_otp'))
        self.assertNotContains(page, otp.code)

    @mock.patch('apps.accounts.views.sms.send_otp', side_effect=sms.SMSError('boom'))
    def test_sms_failure_shows_error_and_keeps_no_code(self, send):
        resp = self._login()
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(OTPCode.objects.exists())

    @mock.patch('apps.accounts.views.sms.send_otp')
    def test_persian_digits_are_normalized(self, send):
        self._login('۰۹۱۲۳۴۵۶۷۸۹')
        self.assertTrue(OTPCode.objects.filter(phone_number=PHONE).exists())

    def test_invalid_phone_rejected(self):
        resp = self._login('12345')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(OTPCode.objects.exists())

    @mock.patch('apps.accounts.views.sms.send_otp')
    def test_cooldown_prevents_second_sms(self, send):
        self._login()
        resp = self._login()
        self.assertRedirects(resp, reverse('verify_otp'), fetch_redirect_response=False)
        self.assertEqual(send.call_count, 1)

    @mock.patch('apps.accounts.views.sms.send_otp')
    def test_hourly_cap_per_phone(self, send):
        for _ in range(5):
            OTPCode.objects.create(phone_number=PHONE, code='111111', is_used=True)
        OTPCode.objects.update(created_at=timezone.now() - timedelta(minutes=10))
        resp = self._login()
        self.assertEqual(resp.status_code, 200)
        send.assert_not_called()

    @mock.patch('apps.accounts.views.sms.send_otp')
    def test_full_login_creates_user(self, send):
        self._login()
        otp = OTPCode.objects.get(phone_number=PHONE)
        resp = self.client.post(reverse('verify_otp'), {'code': otp.code})
        self.assertRedirects(resp, reverse('dashboard'), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(phone_number=PHONE).exists())
        self.assertIn('_auth_user_id', self.client.session)

    @mock.patch('apps.accounts.views.sms.send_otp')
    def test_wrong_code_locks_after_max_attempts(self, send):
        self._login()
        otp = OTPCode.objects.get(phone_number=PHONE)
        for _ in range(5):
            self.client.post(reverse('verify_otp'), {'code': '000000' if otp.code != '000000' else '111111'})
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)
        # حتی کد درست هم دیگر کار نمی‌کند
        self.client.post(reverse('verify_otp'), {'code': otp.code})
        self.assertNotIn('_auth_user_id', self.client.session)

    @mock.patch('apps.accounts.views.sms.send_otp')
    def test_expired_code_rejected(self, send):
        self._login()
        otp = OTPCode.objects.get(phone_number=PHONE)
        OTPCode.objects.filter(pk=otp.pk).update(created_at=timezone.now() - timedelta(minutes=6))
        self.client.post(reverse('verify_otp'), {'code': otp.code})
        self.assertNotIn('_auth_user_id', self.client.session)


@override_settings(KAVENEGAR_API_KEY='', OTP_SHOW_ON_SCREEN=True)
class ScreenFallbackTests(TestCase):
    """تا وقتی کلید کاوه‌نگار تنظیم نشده، رفتار قبلی (نمایش کد روی صفحه) حفظ می‌شود."""

    def setUp(self):
        cache.clear()

    def test_code_shown_on_screen_without_api_key(self):
        self.client.post(reverse('login'), {'phone_number': PHONE})
        otp = OTPCode.objects.get(phone_number=PHONE)
        page = self.client.get(reverse('verify_otp'))
        self.assertContains(page, otp.code)

    @override_settings(OTP_SHOW_ON_SCREEN=False)
    def test_no_key_and_no_screen_means_error(self):
        resp = self.client.post(reverse('login'), {'phone_number': PHONE})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(OTPCode.objects.exists())
