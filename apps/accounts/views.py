import hmac
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from . import sms
from .models import User, OTPCode

logger = logging.getLogger(__name__)

# تبدیل ارقام فارسی/عربی به انگلیسی
_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def _normalize_digits(value):
    return (value or '').translate(_DIGITS).strip()


def _client_ip(request):
    # nginx آی‌پی واقعی کلاینت را به‌عنوان آخرین مقدار X-Forwarded-For اضافه می‌کند
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '')


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)

    def post(self, request):
        phone_number = _normalize_digits(request.POST.get('phone_number'))
        if len(phone_number) != 11 or not phone_number.isdigit() or not phone_number.startswith('09'):
            messages.error(request, 'شماره موبایل معتبر نیست. مثال: 09123456789')
            return render(request, self.template_name)

        now = timezone.now()
        cooldown = settings.OTP_COOLDOWN_SECONDS
        recent = OTPCode.objects.filter(phone_number=phone_number)

        # ۱) فاصله‌ی حداقلی بین دو درخواست: اگر هنوز کد قبلی معتبر است به صفحه‌ی تایید برو
        last = recent.first()
        if last and (now - last.created_at) < timedelta(seconds=cooldown) and last.is_valid():
            wait = cooldown - int((now - last.created_at).total_seconds())
            request.session['otp_phone'] = phone_number
            messages.info(request, f'کد تایید اخیراً ارسال شده است. تا {wait} ثانیه‌ی دیگر می‌توانید دوباره درخواست دهید.')
            return redirect('verify_otp')

        # ۲) سقف تعداد درخواست در ساعت برای هر شماره
        sent_last_hour = recent.filter(created_at__gte=now - timedelta(hours=1)).count()
        if sent_last_hour >= settings.OTP_MAX_PER_HOUR:
            messages.error(request, 'تعداد درخواست‌های شما زیاد بوده است. لطفاً بعداً دوباره تلاش کنید.')
            return render(request, self.template_name)

        # ۳) سقف تعداد درخواست در ساعت برای هر آی‌پی (جلوگیری از سوءاستفاده و هزینه‌ی پیامک)
        ip_key = f'otp_ip_{_client_ip(request)}'
        cache.add(ip_key, 0, timeout=3600)
        try:
            ip_count = cache.incr(ip_key)
        except ValueError:
            ip_count = 1
        if ip_count > settings.OTP_MAX_PER_IP_HOUR:
            messages.error(request, 'تعداد درخواست‌ها بیش از حد مجاز است. لطفاً بعداً دوباره تلاش کنید.')
            return render(request, self.template_name)

        # ساخت کد جدید و باطل‌کردن کدهای قبلی
        OTPCode.objects.filter(phone_number=phone_number, is_used=False).update(is_used=True)
        code = OTPCode.generate_code()
        otp = OTPCode.objects.create(phone_number=phone_number, code=code)

        request.session.pop('otp_display_code', None)

        if sms.is_configured():
            try:
                sms.send_otp(phone_number, code)
            except sms.SMSError:
                logger.exception('ارسال پیامک کد تایید ناموفق بود')
                otp.delete()
                messages.error(request, 'ارسال پیامک با مشکل مواجه شد. لطفاً چند دقیقه‌ی دیگر دوباره تلاش کنید.')
                return render(request, self.template_name)
            messages.success(request, f'کد تایید به شماره {phone_number} ارسال شد.')
        elif settings.OTP_SHOW_ON_SCREEN:
            # حالت موقت/توسعه: فقط وقتی کلید پیامک تنظیم نشده است
            request.session['otp_display_code'] = code
            messages.success(request, 'کد تایید ساخته شد و در صفحه‌ی بعد نمایش داده می‌شود.')
        else:
            otp.delete()
            logger.error('سرویس پیامک پیکربندی نشده است (KAVENEGAR_API_KEY)')
            messages.error(request, 'سرویس ارسال پیامک در دسترس نیست.')
            return render(request, self.template_name)

        request.session['otp_phone'] = phone_number
        return redirect('verify_otp')


class VerifyOTPView(View):
    template_name = 'accounts/verify_otp.html'

    def _context(self, request):
        show = settings.OTP_SHOW_ON_SCREEN and not sms.is_configured()
        return {
            'phone': request.session.get('otp_phone'),
            'otp_code': request.session.get('otp_display_code') if show else None,
        }

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        if not request.session.get('otp_phone'):
            return redirect('login')
        return render(request, self.template_name, self._context(request))

    def post(self, request):
        phone_number = request.session.get('otp_phone')
        code = _normalize_digits(request.POST.get('code'))

        if not phone_number:
            return redirect('login')

        otp = OTPCode.objects.filter(phone_number=phone_number, is_used=False).order_by('-created_at').first()
        if otp is None:
            messages.error(request, 'کد تایید معتبر نیست. دوباره درخواست دهید.')
            return redirect('login')

        if not otp.is_valid():
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            messages.error(request, 'کد تایید منقضی شده. دوباره تلاش کنید.')
            return redirect('login')

        if not hmac.compare_digest(otp.code, code):
            otp.attempts += 1
            if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
                otp.is_used = True
                otp.save(update_fields=['attempts', 'is_used'])
                messages.error(request, 'تعداد تلاش‌های ناموفق بیش از حد مجاز بود. دوباره کد بگیرید.')
                return redirect('login')
            otp.save(update_fields=['attempts'])
            messages.error(request, 'کد تایید اشتباه است.')
            return render(request, self.template_name, self._context(request))

        otp.is_used = True
        otp.save(update_fields=['is_used'])

        user, created = User.objects.get_or_create(phone_number=phone_number)
        if not user.is_active:
            messages.error(request, 'حساب کاربری شما غیرفعال است.')
            return redirect('login')
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        request.session.pop('otp_phone', None)
        request.session.pop('otp_display_code', None)

        if created:
            messages.success(request, 'ثبت نام شما با موفقیت انجام شد!')
        else:
            messages.success(request, 'ورود موفقیت آمیز بود!')

        return redirect('dashboard')


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