from django.db import models
from django.conf import settings


class Prescription(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در حال بررسی'),
        ('items_entered', 'اقلام وارد شده'),
        ('ready', 'آماده تحویل'),
        ('partial', 'موجودی ناقص'),
        ('delivered', 'تحویل داده شده'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        verbose_name='کاربر'
    )
    tracking_code = models.CharField(max_length=50, verbose_name='کد رهگیری')
    national_id = models.CharField(max_length=10, verbose_name='کد ملی')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='وضعیت'
    )
    admin_notes = models.TextField(blank=True, verbose_name='توضیحات ادمین')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        verbose_name = 'نسخه'
        verbose_name_plural = 'نسخه‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tracking_code} - {self.user.phone_number}"

    def get_status_display_class(self):
        mapping = {
            'pending': 'warning',
            'items_entered': 'info',
            'ready': 'success',
            'partial': 'danger',
            'delivered': 'info',
        }
        return mapping.get(self.status, 'secondary')

    def all_items_available(self):
        items = self.items.all()
        if not items.exists():
            return None
        return all(item.is_available for item in items)

    def unavailable_items(self):
        return self.items.filter(is_available=False)


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='نسخه'
    )
    drug_name = models.CharField(max_length=200, verbose_name='نام دارو')
    quantity = models.CharField(max_length=100, verbose_name='مقدار / تعداد')
    dosage = models.CharField(max_length=100, blank=True, verbose_name='دوز / نحوه مصرف')
    is_available = models.BooleanField(default=True, verbose_name='موجود است')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'قلم نسخه'
        verbose_name_plural = 'اقلام نسخه'
        ordering = ['id']

    def __str__(self):
        return f"{self.drug_name} ({self.quantity})"