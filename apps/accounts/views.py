import logging
import re
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views import View
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .models import User, OTPCode
from .sms import send_otp, SMSError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- کمکی‌ها
_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def normalize_digits(value):
    """ارقام فارسی/عربی را به انگلیسی تبدیل می‌کند."""
    return (value or '').translate(_DIGITS).strip()


def normalize_phone(raw):
    """09123456789 را از فرمت‌هایی مثل +98912…، 0098912… و 912… می‌سازد."""
    v = re.sub(r'[\s\-()]', '', normalize_digits(raw))
    if v.startswith('+98'):
        v = '0' + v[3:]
    elif v.startswith('0098'):
        v = '0' + v[4:]
    elif v.startswith('98') and len(v) == 12:
        v = '0' + v[2:]
    elif v.startswith('9') and len(v) == 10:
        v = '0' + v
    return v


def is_valid_phone(value):
    return re.fullmatch(r'09\d{9}', value) is not None


def mask_phone(phone):
    return f'{phone[:4]}***{phone[-4:]}' if phone and len(phone) == 11 else phone


def client_ip(request):
    # پشت nginx: آخرین مقدار X-Forwarded-For همانی است که nginx اضافه کرده
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _count_hit(key, ttl):
    cache.add(key, 0, ttl)
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, ttl)
        return 1


def resend_wait_seconds(phone):
    """چند ثانیه تا مجاز شدن ارسال مجدد کد باقی مانده است."""
    last = OTPCode.objects.filter(phone_number=phone).order_by('-created_at').first()
    if not last:
        return 0
    passed = int((timezone.now() - last.created_at).total_seconds())
    return max(0, settings.OTP_RESEND_SECONDS - passed)


SENT, COOLDOWN, LIMITED, FAILED = 'sent', 'cooldown', 'limited', 'failed'


def issue_otp(request, phone):
    """
    یک کد جدید می‌سازد و پیامک می‌کند.
    خروجی: (وضعیت، پیام برای کاربر)
    """
    wait = resend_wait_seconds(phone)
    if wait > 0:
        return COOLDOWN, f'کد قبلاً برایتان ارسال شده است. {wait} ثانیه‌ی دیگر می‌توانید کد جدید بگیرید.'

    too_many = 'تعداد درخواست‌ها بیش از حد مجاز است. لطفاً کمی بعد دوباره تلاش کنید.'
    hour_ago = timezone.now() - timedelta(hours=1)
    if OTPCode.objects.filter(phone_number=phone, created_at__gte=hour_ago).count() >= settings.OTP_MAX_SENDS_PER_HOUR:
        return LIMITED, too_many
    if _count_hit(f'otp:ip:{client_ip(request)}', 3600) > settings.OTP_MAX_SENDS_PER_IP_HOUR:
        return LIMITED, too_many

    OTPCode.objects.filter(phone_number=phone, is_used=False).update(is_used=True)
    code = OTPCode.generate_code()
    otp = OTPCode.objects.create(phone_number=phone, code=code)
    cache.delete(f'otp:fail:{phone}')

    try:
        send_otp(phone, code)
    except SMSError as exc:
        logger.error('ارسال پیامک به %s ناموفق بود: %s', phone, exc)
        otp.delete()  # ارسال ناموفق نباید در محدودیت‌ها حساب شود
        return FAILED, 'ارسال پیامک با مشکل مواجه شد. چند لحظه بعد دوباره تلاش کنید.'

    return SENT, f'کد تایید به شماره {mask_phone(phone)} پیامک شد.'


# -------------------------------------------------------------------- ویوها
class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)

    def post(self, request):
        phone_number = normalize_phone(request.POST.get('phone_number', ''))
        if not is_valid_phone(phone_number):
            messages.error(request, 'شماره موبایل معتبر نیست. مثال: 09123456789')
            return render(request, self.template_name)

        status, message = issue_otp(request, phone_number)

        if status in (SENT, COOLDOWN):
            request.session['otp_phone'] = phone_number
            (messages.success if status == SENT else messages.info)(request, message)
            return redirect('verify_otp')

        messages.error(request, message)
        return render(request, self.template_name, {'phone_value': phone_number})


class VerifyOTPView(View):
    template_name = 'accounts/verify_otp.html'

    def _context(self, request):
        phone = request.session.get('otp_phone')
        return {
            'phone': phone,
            'phone_masked': mask_phone(phone),
            'resend_in': resend_wait_seconds(phone) if phone else 0,
            'resend_total': settings.OTP_RESEND_SECONDS,
        }

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        if not request.session.get('otp_phone'):
            return redirect('login')
        return render(request, self.template_name, self._context(request))

    def post(self, request):
        phone_number = request.session.get('otp_phone')
        code = normalize_digits(request.POST.get('code', ''))

        if not phone_number:
            return redirect('login')

        fail_key = f'otp:fail:{phone_number}'

        try:
            otp = OTPCode.objects.filter(
                phone_number=phone_number,
                code=code,
                is_used=False
            ).latest('created_at')

            if not otp.is_valid():
                messages.error(request, 'کد تایید منقضی شده است. کد جدید دریافت کنید.')
                return render(request, self.template_name, self._context(request))

            otp.is_used = True
            otp.save()
            cache.delete(fail_key)

            user, created = User.objects.get_or_create(phone_number=phone_number)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            request.session.pop('otp_phone', None)

            if created:
                messages.success(request, 'ثبت نام شما با موفقیت انجام شد!')
            else:
                messages.success(request, 'ورود موفقیت آمیز بود!')

            return redirect('dashboard')

        except OTPCode.DoesNotExist:
            fails = _count_hit(fail_key, 600)
            if fails >= settings.OTP_MAX_WRONG_ATTEMPTS:
                # جلوگیری از حدس زدن کد: کد فعلی باطل می‌شود
                OTPCode.objects.filter(phone_number=phone_number, is_used=False).update(is_used=True)
                cache.delete(fail_key)
                messages.error(request, 'چند بار کد اشتباه وارد شد. برای امنیت شما کد باطل شد؛ کد جدید دریافت کنید.')
            else:
                messages.error(request, 'کد تایید اشتباه است.')
            return render(request, self.template_name, self._context(request))


class ResendOTPView(View):
    """ارسال مجدد کد برای شماره‌ای که در session است."""

    def post(self, request):
        phone_number = request.session.get('otp_phone')
        if not phone_number:
            return redirect('login')
        status, message = issue_otp(request, phone_number)
        if status == SENT:
            messages.success(request, message)
        elif status == COOLDOWN:
            messages.info(request, message)
        else:
            messages.error(request, message)
        return redirect('verify_otp')

    def get(self, request):
        return redirect('verify_otp')


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')


class DashboardView(View):
    template_name = 'dashboard/index.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        from apps.notifications.models import Notification
        from apps.customer_club.models import Discount, Purchase
        from django.utils import timezone
        from datetime import timedelta

        notifications = Notification.objects.filter(
            user=request.user, is_read=False
        ).order_by('-created_at')[:5]

        # Check active discount
        active_discount = Discount.objects.filter(
            user=request.user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()

        # Monthly purchase total — ریست بعد از استفاده از تخفیف
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        from apps.customer_club.models import Discount as LoyaltyDiscount
        last_used = LoyaltyDiscount.objects.filter(
            user=request.user,
            is_used=True,
            used_at__gte=month_start
        ).order_by('-used_at').first()

        count_from = last_used.used_at if last_used else month_start

        monthly_total = Purchase.objects.filter(
            user=request.user,
            purchase_date__gt=count_from
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        context = {
            'notifications': notifications,
            'active_discount': active_discount,
            'monthly_total': monthly_total,
            'threshold': 1_000_000,
        }
        return render(request, self.template_name, context)


# Import needed for aggregate
from django.db import models