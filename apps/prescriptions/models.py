from django.db import models
from django.conf import settings


INSURANCE_CHOICES = [
    # پایه
    ("tamin",      "بیمه تأمین اجتماعی"),
    ("salamat",    "بیمه سلامت ایرانیان"),
    ("artesh",     "بیمه نیروهای مسلح"),
    # تکمیلی
    ("iran",       "بیمه تکمیلی — ایران"),
    ("asia",       "بیمه تکمیلی — آسیا"),
    ("alborz",     "بیمه تکمیلی — البرز"),
    ("dana",       "بیمه تکمیلی — دانا"),
    ("day",        "بیمه تکمیلی — دی"),
    ("pasargad",   "بیمه تکمیلی — پاسارگاد"),
    ("saman",      "بیمه تکمیلی — سامان"),
    ("parsian",    "بیمه تکمیلی — پارسیان"),
    ("moalem",     "بیمه تکمیلی — معلم"),
    ("razi",       "بیمه تکمیلی — رازی"),
    ("sina",       "بیمه تکمیلی — سینا"),
    ("kowsar",     "بیمه تکمیلی — کوثر"),
    ("mellat",     "بیمه تکمیلی — ملت"),
    ("novin",      "بیمه تکمیلی — نوین"),
    ("hekmat",     "بیمه تکمیلی — حکمت صبا"),
    ("omid",       "بیمه تکمیلی — امید"),
    ("karafarinb", "بیمه تکمیلی — کارآفرین"),
    ("tosee",      "بیمه تکمیلی — توسعه"),
    ("atiye",      "بیمه تکمیلی — آتیه‌سازان حافظ"),
    ("sos",        "بیمه تکمیلی — کمک‌رسان (SOS)"),
    ("free",       "آزاد (بدون بیمه)"),
]

INSURANCE_BASE_KEYS = ["tamin", "salamat", "artesh"]
INSURANCE_SUPP_KEYS = [
    "iran", "asia", "alborz", "dana", "day", "pasargad", "saman",
    "parsian", "moalem", "razi", "sina", "kowsar", "mellat", "novin",
    "hekmat", "omid", "karafarinb", "tosee", "atiye", "sos",
]

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
    tracking_code  = models.CharField(max_length=50, verbose_name="کد رهگیری")
    national_id    = models.CharField(max_length=10, verbose_name="کد ملی")
    insurance_type = models.CharField(
        max_length=20,
        choices=INSURANCE_CHOICES,
        default="free",
        verbose_name="نوع بیمه"
    )
    contract_status = models.CharField(
        max_length=20,
        choices=[
            ("unknown",     "بررسی نشده"),
            ("contracted",  "داروخانه قرارداد دارد"),
            ("no_contract", "داروخانه قرارداد ندارد"),
        ],
        default="unknown",
        verbose_name="وضعیت قرارداد"
    )
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

    def get_insurance_label(self):
        return dict(INSURANCE_CHOICES).get(self.insurance_type, self.insurance_type)

    def get_insurance_short(self):
        full = self.get_insurance_label()
        return full.replace("بیمه تکمیلی — ", "").replace("بیمه ", "")

    def is_free(self):
        return self.insurance_type == "free"

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