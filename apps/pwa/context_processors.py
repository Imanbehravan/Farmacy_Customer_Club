from django.conf import settings


def pwa(request):
    return {
        'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY,
        'PWA_VERSION': settings.PWA_VERSION,
        'SITE_NAME': settings.SITE_NAME,
        'PHARMACY_NAME': settings.PHARMACY_NAME,
        'PHARMACY_ADDRESS': settings.PHARMACY_ADDRESS,
    }
