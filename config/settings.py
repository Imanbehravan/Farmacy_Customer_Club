from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'apps.accounts',
    'apps.prescriptions',
    'apps.customer_club',
    'apps.notifications',
    'apps.pwa',
    'apps.chat',
    'apps.blog',
    'django_filters',
    "apps.reports",
    "jalali_date",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.TimezoneMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.pwa.context_processors.pwa',
            ],
             "builtins": ["apps.reports.templatetags.reports_jalali"],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='pharmacy_club'),
        'USER': config('POSTGRES_USER', default='pharmacy_user'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='pharmacy_pass_2024'),
        'HOST': config('DB_HOST', default='db'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# کش (برای محدودیت تعداد درخواست کد تایید) — روی همان Redis پروژه
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
        'KEY_PREFIX': 'pharmacy',
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://redis:6379/0')],
        },
    },
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Customer Club Settings
MONTHLY_PURCHASE_THRESHOLD = 1_000_000  # 1 million Toman
DISCOUNT_PERCENTAGE = 10
DISCOUNT_CATEGORY = 'cosmetic'

# Jazzmin Admin Config
JAZZMIN_SETTINGS = {
    "site_title": "باشگاه مشتریان داروخانه",
    "site_header": "داروخانه",
    "site_brand": "باشگاه مشتریان",
    "welcome_sign": "خوش آمدید",
    "language_chooser": False,
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "accounts.User": "fas fa-user",
        "prescriptions.Prescription": "fas fa-file-prescription",
        "customer_club.Purchase": "fas fa-shopping-cart",
        "customer_club.Discount": "fas fa-percent",
        "notifications.Notification": "fas fa-bell",
        "chat.ChatRoom": "fas fa-comments",
    },
    "custom_css": "css/admin.css",
}

# ------------------------------------------------------------------
# پیامک و کد تایید (OTP)
# مقادیر از فایل .env خوانده می‌شود؛ توضیح هر کدام در .env.example
# ------------------------------------------------------------------
SMS_PROVIDER = config('SMS_PROVIDER', default='kavenegar').strip().lower()   # kavenegar | smsir
SMS_API_KEY = (
    config('SMS_API_KEY', default='')
    or config('SMS_TOKEN', default='')
    or config('KAVENEGAR_API_KEY', default='')
    or config('SMSIR_API_KEY', default='')
).strip()
SMS_TEMPLATE = config('SMS_TEMPLATE', default='').strip()            # نام/شناسه‌ی قالب تایید در پنل پیامک
SMS_TEMPLATE_PARAM = config('SMS_TEMPLATE_PARAM', default='Code')    # فقط برای sms.ir
SMS_SENDER = config('SMS_SENDER', default='').strip()                # شماره خط (فقط اگر قالب ندارید)
SMS_TIMEOUT = 10                                                     # ثانیه

OTP_RESEND_SECONDS = 120        # فاصله‌ی مجاز بین دو ارسال برای یک شماره
OTP_MAX_SENDS_PER_HOUR = 5      # حداکثر ارسال در ساعت برای هر شماره
OTP_MAX_SENDS_PER_IP_HOUR = 20  # حداکثر ارسال در ساعت برای هر IP
OTP_MAX_WRONG_ATTEMPTS = 5      # بعد از این تعداد کد اشتباه، کد باطل می‌شود

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'apps.accounts': {'handlers': ['console'], 'level': 'INFO'},
    },
}


# ------------------------------------------------------------------
# PWA و اعلان‌های Push
# ------------------------------------------------------------------
SITE_NAME = config('SITE_NAME', default='باشگاه مشتریان داروخانه')
SITE_URL = config('SITE_URL', default='http://localhost')
PHARMACY_NAME = config('PHARMACY_NAME', default='داروخانه دکتر شمشیرگران')
PHARMACY_ADDRESS = config(
    'PHARMACY_ADDRESS',
    default='بیرجند، بلوار شهید آیت‌الله مدرس، پلاک ۱۹۹',
)
PWA_SHORT_NAME = config('PWA_SHORT_NAME', default='باشگاه مشتریان')
PWA_THEME_COLOR = '#4e7034'        # سبز ماچا
PWA_BACKGROUND_COLOR = '#f4f8ec'
PWA_VERSION = config('PWA_VERSION', default='1')   # با عوض شدنش کش اپ روی گوشی‌ها نو می‌شود

# کلیدها را با  python manage.py generate_vapid_keys  بسازید و در .env بگذارید
VAPID_PUBLIC_KEY = config('VAPID_PUBLIC_KEY', default='').strip()
VAPID_PRIVATE_KEY = config('VAPID_PRIVATE_KEY', default='').strip()
VAPID_ADMIN_EMAIL = config('VAPID_ADMIN_EMAIL', default='admin@localhost.local').strip()
PUSH_TTL_SECONDS = 60 * 60 * 24      # اگر دستگاه آفلاین بود تا ۲۴ ساعت نگه داشته شود
PUSH_TIMEOUT_SECONDS = 10
PUSH_ASYNC = config('PUSH_ASYNC', default=True, cast=bool)
# اگر سرور داخل ایران به fcm.googleapis.com دسترسی ندارد، آدرس پروکسی را اینجا بدهید
# مثال:  PUSH_PROXY_URL=http://user:pass@host:port   یا  socks5h://host:1080
PUSH_PROXY_URL = config('PUSH_PROXY_URL', default='').strip()
