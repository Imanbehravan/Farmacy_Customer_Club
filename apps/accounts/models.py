import random
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('شماره تلفن الزامی است')
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=11, unique=True, verbose_name='شماره موبایل')
    first_name = models.CharField(max_length=50, blank=True, verbose_name='نام')
    last_name = models.CharField(max_length=50, blank=True, verbose_name='نام خانوادگی')
    national_id = models.CharField(max_length=10, blank=True, verbose_name='کد ملی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_staff = models.BooleanField(default=False, verbose_name='کارمند')
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='تاریخ عضویت')

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.phone_number

    @property
    def full_name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.phone_number


class OTPCode(models.Model):
    phone_number = models.CharField(max_length=11, verbose_name='شماره موبایل')
    code = models.CharField(max_length=6, verbose_name='کد تایید')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_used = models.BooleanField(default=False, verbose_name='استفاده شده')

    class Meta:
        verbose_name = 'کد تایید'
        verbose_name_plural = 'کدهای تایید'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone_number} - {self.code}"

    @classmethod
    def generate_code(cls):
        return ''.join(random.choices(string.digits, k=6))

    def is_valid(self):
        import datetime
        return not self.is_used and (timezone.now() - self.created_at) < datetime.timedelta(minutes=5)
