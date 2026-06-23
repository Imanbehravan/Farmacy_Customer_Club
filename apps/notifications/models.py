from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('prescription', 'نسخه'),
        ('discount', 'تخفیف'),
        ('broadcast', 'پیام همگانی'),
        ('general', 'عمومی'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications', verbose_name='کاربر'
    )
    title = models.CharField(max_length=200, verbose_name='عنوان')
    message = models.TextField(verbose_name='متن')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES,
                                         default='general', verbose_name='نوع')
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ')

    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلان‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.phone_number} — {self.title}"


class BroadcastMessage(models.Model):
    """پیام همگانی که ادمین برای همه کاربران ارسال می‌کند"""
    title = models.CharField(max_length=200, verbose_name='عنوان')
    message = models.TextField(verbose_name='متن پیام')
    discount_percentage = models.IntegerField(
        null=True, blank=True, verbose_name='درصد تخفیف همگانی (اختیاری)'
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ارسال')
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='sent_broadcasts', verbose_name='فرستنده'
    )
    recipient_count = models.IntegerField(default=0, verbose_name='تعداد دریافت‌کنندگان')

    class Meta:
        verbose_name = 'پیام همگانی'
        verbose_name_plural = 'پیام‌های همگانی'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.title} — {self.sent_at.strftime('%Y/%m/%d')}"
