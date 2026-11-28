from django.conf import settings
from django.db import models


class PushSubscription(models.Model):
    """اشتراک Web Push یک دستگاه/مرورگر برای یک کاربر."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='push_subscriptions', verbose_name='کاربر',
    )
    endpoint = models.TextField(unique=True, verbose_name='Endpoint')
    p256dh = models.CharField(max_length=255, verbose_name='کلید p256dh')
    auth = models.CharField(max_length=255, verbose_name='کلید auth')
    user_agent = models.CharField(max_length=300, blank=True, verbose_name='مرورگر/دستگاه')
    failure_count = models.PositiveSmallIntegerField(default=0, verbose_name='تعداد خطای پیاپی')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')
    last_success_at = models.DateTimeField(null=True, blank=True, verbose_name='آخرین ارسال موفق')

    class Meta:
        verbose_name = 'اشتراک اعلان'
        verbose_name_plural = 'اشتراک‌های اعلان'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.endpoint[:40]}…'

    def as_webpush(self):
        return {
            'endpoint': self.endpoint,
            'keys': {'p256dh': self.p256dh, 'auth': self.auth},
        }
