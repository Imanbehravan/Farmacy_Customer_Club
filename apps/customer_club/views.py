from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db import models as dj_models

import jdatetime
from .models import Purchase, Discount, GlobalDiscount, CampaignUsage


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ─────────────────────────────────────────────
#  API: اطلاعات تخفیف کاربر  (AJAX)
# ─────────────────────────────────────────────
class UserDiscountInfoView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin))
    def get(self, request):
        phone = request.GET.get('phone', '').strip()
        try:
            from apps.accounts.models import User
            user = User.objects.get(phone_number=phone)
        except Exception:
            return JsonResponse({'found': False})

        # Personal loyalty discount
        loyalty = Discount.objects.filter(
            user=user, is_used=False, expires_at__gt=timezone.now()
        ).first()

        # Active global campaigns — فقط کمپین‌هایی که این کاربر استفاده نکرده
        used_ids = CampaignUsage.objects.filter(user=user).values_list('campaign_id', flat=True)
        campaigns = GlobalDiscount.objects.filter(
            is_active=True, expires_at__gt=timezone.now()
        ).exclude(id__in=used_ids).values('id', 'name', 'percentage', 'category')

        # Monthly total
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_total = Purchase.objects.filter(
            user=user, purchase_date__gte=month_start
        ).aggregate(t=dj_models.Sum('amount'))['t'] or 0

        # Recent purchases
        recent = list(Purchase.objects.filter(user=user).order_by('-purchase_date')[:5].values(
            'amount', 'original_amount', 'discount_percentage', 'is_cosmetic',
            'description', 'purchase_date'
        ))
        for r in recent:
            r['purchase_date'] = jdatetime.datetime.fromgregorian(datetime=r['purchase_date'].replace(tzinfo=None) if hasattr(r['purchase_date'], 'replace') else r['purchase_date']).strftime('%Y/%m/%d')

        return JsonResponse({
            'found': True,
            'phone': user.phone_number,
            'name': user.full_name,
            'loyalty_discount': {
                'id': loyalty.id,
                'percentage': loyalty.percentage,
                'expires_at': jdatetime.datetime.fromgregorian(datetime=loyalty.expires_at).strftime('%Y/%m/%d'),
            } if loyalty else None,
            'campaigns': list(campaigns),
            'monthly_total': monthly_total,
            'threshold': 1_000_000,
            'recent_purchases': recent,
        })


# ─────────────────────────────────────────────
#  ثبت خرید جدید
# ─────────────────────────────────────────────
class AdminPurchasesView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def get(self, request):
        purchases = Purchase.objects.select_related(
            'user', 'prescription'
        ).order_by('-purchase_date')[:100]
        active_campaigns = GlobalDiscount.objects.filter(
            is_active=True, expires_at__gt=timezone.now()
        )
        context = {
            'purchases': purchases,
            'active_campaigns': active_campaigns,
        }
        return render(request, 'admin_panel/purchases.html', context)

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def post(self, request):
        from apps.accounts.models import User
        from apps.prescriptions.models import Prescription
        from apps.notifications.models import Notification

        phone          = request.POST.get('phone_number', '').strip()
        original_amt   = request.POST.get('original_amount', '0').replace(',', '').strip()
        final_amt      = request.POST.get('final_amount', '0').replace(',', '').strip()
        discount_pct   = int(request.POST.get('discount_percentage', '0') or '0')
        discount_src   = request.POST.get('discount_source', '')
        loyalty_id     = request.POST.get('loyalty_discount_id', '').strip()
        campaign_id    = request.POST.get('campaign_id', '').strip()
        is_cosmetic    = request.POST.get('is_cosmetic') == '1'
        prescription_id= request.POST.get('prescription_id', '').strip()
        description    = request.POST.get('description', '').strip()

        # Validate user
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            messages.error(request, f'کاربری با شماره {phone} یافت نشد.')
            return redirect('admin_purchases')

        try:
            original_int = int(original_amt)
            final_int    = int(final_amt)
        except ValueError:
            messages.error(request, 'مبلغ وارد شده معتبر نیست.')
            return redirect('admin_purchases')

        # Prescription
        prescription = None
        if prescription_id:
            try:
                prescription = Prescription.objects.get(id=prescription_id, user=user)
                prescription.status = 'delivered'
                prescription.save(update_fields=['status'])
            except Prescription.DoesNotExist:
                pass

        # Create purchase
        purchase = Purchase.objects.create(
            user=user,
            original_amount=original_int,
            amount=final_int,
            discount_percentage=discount_pct,
            discount_source=discount_src,
            is_cosmetic=is_cosmetic,
            prescription=prescription,
            description=description,
        )

        # Invalidate personal loyalty discount if used
        if loyalty_id and discount_src == 'loyalty':
            try:
                disc = Discount.objects.get(id=loyalty_id, user=user)
                if disc.is_active():
                    disc.use()
                    Notification.objects.create(
                        user=user,
                        title='تخفیف باشگاه مشتریان استفاده شد ✅',
                        message=(
                            f'تخفیف {discount_pct}٪ شما برای خرید به مبلغ '
                            f'{original_int:,} تومان اعمال شد.\n'
                            f'مبلغ نهایی پرداختی: {final_int:,} تومان.\n'
                            f'برای دریافت تخفیف بعدی، خریدهای ماهانه‌تان را ادامه دهید.'
                        ),
                        notification_type='discount'
                    )
            except Discount.DoesNotExist:
                pass
        elif discount_pct > 0 and discount_src == 'campaign':
            # ثبت استفاده از کمپین برای این کاربر
            campaign_id = request.POST.get('campaign_id', '').strip()
            if campaign_id:
                try:
                    campaign_obj = GlobalDiscount.objects.get(id=campaign_id)
                    CampaignUsage.objects.get_or_create(user=user, campaign=campaign_obj)
                except GlobalDiscount.DoesNotExist:
                    pass
            Notification.objects.create(
                user=user,
                title=f'تخفیف ویژه {discount_pct}٪ اعمال شد 🎁',
                message=(
                    f'تخفیف کمپین ویژه {discount_pct}٪ برای خرید شما اعمال شد.\n'
                    f'مبلغ اصلی: {original_int:,} تومان\n'
                    f'مبلغ با تخفیف: {final_int:,} تومان'
                ),
                notification_type='discount'
            )

        savings = original_int - final_int
        msg = f'خرید {final_int:,} تومان برای {phone} ثبت شد.'
        if savings > 0:
            msg += f' (صرفه‌جویی: {savings:,} تومان)'
        messages.success(request, msg)
        return redirect('admin_purchases')


# ─────────────────────────────────────────────
#  کمپین‌های تخفیف همگانی
# ─────────────────────────────────────────────
class AdminCampaignsView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def get(self, request):
        campaigns = GlobalDiscount.objects.order_by('-created_at')
        return render(request, 'admin_panel/campaigns.html', {'campaigns': campaigns})

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def post(self, request):
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        percentage  = request.POST.get('percentage', '').strip()
        category    = request.POST.get('category', 'cosmetic')
        expires_at  = request.POST.get('expires_at', '').strip()

        if not name or not percentage or not expires_at:
            messages.error(request, 'نام، درصد و تاریخ انقضا الزامی هستند.')
            return redirect('admin_campaigns')

        from datetime import datetime
        try:
            expire_dt = datetime.strptime(expires_at, '%Y-%m-%d')
            expire_dt = timezone.make_aware(expire_dt)
        except ValueError:
            messages.error(request, 'فرمت تاریخ اشتباه است.')
            return redirect('admin_campaigns')

        campaign = GlobalDiscount.objects.create(
            name=name,
            description=description,
            percentage=int(percentage),
            category=category,
            expires_at=expire_dt,
            created_by=request.user,
        )
        messages.success(request, f'کمپین «{name}» با تخفیف {percentage}٪ ایجاد شد.')
        return redirect('admin_campaigns')


class ToggleCampaignView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def post(self, request, pk):
        campaign = get_object_or_404(GlobalDiscount, pk=pk)
        campaign.is_active = not campaign.is_active
        campaign.save(update_fields=['is_active'])
        status = 'فعال' if campaign.is_active else 'غیرفعال'
        messages.success(request, f'کمپین «{campaign.name}» {status} شد.')
        return redirect('admin_campaigns')