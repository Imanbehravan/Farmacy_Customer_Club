from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views import View
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from .models import User, OTPCode


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)

    def post(self, request):
        phone_number = request.POST.get('phone_number', '').strip()
        if not phone_number or len(phone_number) != 11 or not phone_number.startswith('09'):
            messages.error(request, 'شماره موبایل معتبر نیست. مثال: 09123456789')
            return render(request, self.template_name)

        # Generate and save OTP
        OTPCode.objects.filter(phone_number=phone_number, is_used=False).update(is_used=True)
        code = OTPCode.generate_code()
        OTPCode.objects.create(phone_number=phone_number, code=code)

        # TODO: وقتی درگاه پیامکی گرفتی، اینجا کد رو با SMS بفرست و
        # OTP_SHOW_ON_SCREEN رو در settings.py روی False بذار.
        if getattr(settings, 'OTP_SHOW_ON_SCREEN', True):
            # نمایش کد روی صفحه‌ی تأیید (حالت موقت تا زمان راه‌اندازی پیامک)
            request.session['otp_display_code'] = code
            messages.success(request, 'کد تایید ساخته شد و در صفحه‌ی بعد نمایش داده می‌شود.')
        else:
            request.session.pop('otp_display_code', None)
            messages.success(request, f'کد تایید به شماره {phone_number} ارسال شد.')

        request.session['otp_phone'] = phone_number
        return redirect('verify_otp')


class VerifyOTPView(View):
    template_name = 'accounts/verify_otp.html'

    def _context(self, request):
        show = getattr(settings, 'OTP_SHOW_ON_SCREEN', True)
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
        code = request.POST.get('code', '').strip()

        if not phone_number:
            return redirect('login')

        try:
            otp = OTPCode.objects.filter(
                phone_number=phone_number,
                code=code,
                is_used=False
            ).latest('created_at')

            if not otp.is_valid():
                messages.error(request, 'کد تایید منقضی شده. دوباره تلاش کنید.')
                return redirect('login')

            otp.is_used = True
            otp.save()

            user, created = User.objects.get_or_create(phone_number=phone_number)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            del request.session['otp_phone']
            request.session.pop('otp_display_code', None)

            if created:
                messages.success(request, 'ثبت نام شما با موفقیت انجام شد!')
            else:
                messages.success(request, 'ورود موفقیت آمیز بود!')

            return redirect('dashboard')

        except OTPCode.DoesNotExist:
            messages.error(request, 'کد تایید اشتباه است.')
            return render(request, self.template_name, self._context(request))


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