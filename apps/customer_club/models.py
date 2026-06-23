from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class GlobalDiscount(models.Model):
    """کمپین تخفیف همگانی — ادمین ایجاد می‌کند"""
    CATEGORY_CHOICES = [
        ('cosmetic', 'اقلام آرایشی-بهداشتی'),
        ('all', 'همه اقلام'),
    ]
    name = models.CharField(max_length=200, verbose_name='نام کمپین')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    percentage = models.IntegerField(verbose_name='درصد تخفیف')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES,
                                default='cosmetic', verbose_name='دسته‌بندی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    expires_at = models.DateTimeField(verbose_name='تاریخ انقضا')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_campaigns', verbose_name='ایجادکننده'
    )

    class Meta:
        verbose_name = 'کمپین تخفیف'
        verbose_name_plural = 'کمپین‌های تخفیف'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} — {self.percentage}٪"

    def is_valid(self):
        return self.is_active and self.expires_at > timezone.now()


class Purchase(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='purchases', verbose_name='کاربر'
    )
    original_amount = models.BigIntegerField(default=0, verbose_name='مبلغ قبل از تخفیف')
    amount = models.BigIntegerField(verbose_name='مبلغ نهایی پرداختی (تومان)')
    discount_percentage = models.IntegerField(default=0, verbose_name='درصد تخفیف اعمال‌شده')
    discount_source = models.CharField(
        max_length=50, blank=True, verbose_name='منبع تخفیف',
        help_text='loyalty=باشگاه مشتریان / campaign=کمپین همگانی'
    )
    is_cosmetic = models.BooleanField(default=False, verbose_name='اقلام آرایشی-بهداشتی')
    prescription = models.ForeignKey(
        'prescriptions.Prescription', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='purchases', verbose_name='نسخه'
    )
    description = models.CharField(max_length=255, blank=True, verbose_name='توضیحات')
    purchase_date = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ خرید')

    class Meta:
        verbose_name = 'خرید'
        verbose_name_plural = 'خریدها'
        ordering = ['-purchase_date']

    def __str__(self):
        return f"{self.user.phone_number} — {self.amount:,} تومان"

    def save(self, *args, **kwargs):
        if not self.original_amount:
            self.original_amount = self.amount
        super().save(*args, **kwargs)
        self._check_and_create_loyalty_discount()

    def _check_and_create_loyalty_discount(self):
        from apps.notifications.models import Notification
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        threshold = getattr(settings, 'MONTHLY_PURCHASE_THRESHOLD', 1_000_000)
        discount_pct = getattr(settings, 'DISCOUNT_PERCENTAGE', 10)

        # اگر تخفیف قبلی این ماه استفاده شده، از لحظه استفاده حساب می‌کنیم (ریست)
        last_used = Discount.objects.filter(
            user=self.user,
            is_used=True,
            used_at__gte=month_start
        ).order_by('-used_at').first()

        count_from = last_used.used_at if last_used else month_start

        monthly_total = Purchase.objects.filter(
            user=self.user,
            purchase_date__gt=count_from
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        # فقط اگر تخفیف فعال (استفاده‌نشده) برای این دوره وجود نداشته باشه
        already_rewarded = Discount.objects.filter(
            user=self.user,
            is_used=False,
            created_at__gt=count_from
        ).exists()

        if monthly_total >= threshold and not already_rewarded:
            expire_date = (
                timezone.now().replace(day=1) + timedelta(days=32)
            ).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            Discount.objects.create(
                user=self.user,
                discount_type='cosmetic',
                percentage=discount_pct,
                expires_at=expire_date
            )
            Notification.objects.create(
                user=self.user,
                title=f'🎉 تخفیف {discount_pct}٪ ویژه باشگاه مشتریان!',
                message=(
                    f'تبریک! مجموع خرید شما این ماه به {monthly_total:,} تومان رسید.\n'
                    f'یک کد تخفیف {discount_pct}٪ برای اقلام آرایشی-بهداشتی برای شما فعال شد.'
                ),
                notification_type='discount'
            )


class Discount(models.Model):
    """تخفیف شخصی باشگاه مشتریان"""
    DISCOUNT_TYPES = [
        ('cosmetic', 'اقلام آرایشی-بهداشتی'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='discounts', verbose_name='کاربر'
    )
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES,
                                     verbose_name='نوع تخفیف')
    percentage = models.IntegerField(default=10, verbose_name='درصد تخفیف')
    is_used = models.BooleanField(default=False, verbose_name='استفاده شده')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ استفاده')
    expires_at = models.DateTimeField(verbose_name='تاریخ انقضا')

    class Meta:
        verbose_name = 'تخفیف وفاداری'
        verbose_name_plural = 'تخفیف‌های وفاداری'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.phone_number} — {self.percentage}٪ — {'استفاده شده' if self.is_used else 'فعال'}"

    def is_active(self):
        return not self.is_used and self.expires_at > timezone.now()

    def use(self):
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class CampaignUsage(models.Model):
    """ردیابی استفاده هر کاربر از هر کمپین — فقط یک‌بار"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='campaign_usages', verbose_name='کاربر'
    )
    campaign = models.ForeignKey(
        GlobalDiscount, on_delete=models.CASCADE,
        related_name='usages', verbose_name='کمپین'
    )
    used_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ استفاده')

    class Meta:
        verbose_name = 'استفاده از کمپین'
        verbose_name_plural = 'استفاده‌های کمپین'
        unique_together = ('user', 'campaign')  # هر کاربر فقط یک‌بار

    def __str__(self):
        return f"{self.user.phone_number} — {self.campaign.name}"