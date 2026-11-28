import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.http import require_GET, require_POST

from . import push
from .models import PushSubscription


# ------------------------------------------------------------ مانیفست و سرویس‌ورکر
@require_GET
def manifest(request):
    data = {
        'id': '/',
        'name': settings.SITE_NAME,
        'short_name': settings.PWA_SHORT_NAME,
        'description': 'باشگاه مشتریان داروخانه؛ ثبت نسخه، مشاوره با داروساز و مزایای ویژه اعضا.',
        'lang': 'fa',
        'dir': 'rtl',
        'start_url': '/?source=pwa',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'portrait',
        'background_color': settings.PWA_BACKGROUND_COLOR,
        'theme_color': settings.PWA_THEME_COLOR,
        'categories': ['health', 'medical', 'shopping'],
        'icons': [
            {'src': static('icons/icon-192.png'), 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('icons/icon-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('icons/maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
        'shortcuts': [
            {'name': 'ثبت نسخه', 'url': '/dashboard/?action=prescription',
             'icons': [{'src': static('icons/icon-192.png'), 'sizes': '192x192'}]},
            {'name': 'مشاوره با داروساز', 'url': '/chat/',
             'icons': [{'src': static('icons/icon-192.png'), 'sizes': '192x192'}]},
            {'name': 'اعلان‌ها', 'url': '/notifications/',
             'icons': [{'src': static('icons/icon-192.png'), 'sizes': '192x192'}]},
        ],
    }
    resp = HttpResponse(json.dumps(data, ensure_ascii=False), content_type='application/manifest+json')
    resp['Cache-Control'] = 'no-cache'
    return resp


@require_GET
def service_worker(request):
    config = {
        'version': settings.PWA_VERSION,
        'offlineUrl': '/offline/',
        'precache': [
            '/offline/',
            static('fonts/Vazirmatn-Variable.woff2'),
            static('img/logo.png'),
            static('icons/favicon.png'),
            static('icons/icon-192.png'),
            static('icons/badge-96.png'),
        ],
        'icon': static('icons/icon-192.png'),
        'badge': static('icons/badge-96.png'),
    }
    resp = render(request, 'pwa/sw.js', {'config_json': json.dumps(config)},
                  content_type='application/javascript; charset=utf-8')
    resp['Service-Worker-Allowed'] = '/'
    resp['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp


@require_GET
def offline(request):
    return render(request, 'pwa/offline.html')


# ------------------------------------------------------------------ Web Push API
def _json_body(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return None


@login_required
@require_POST
def push_subscribe(request):
    data = _json_body(request)
    sub = (data or {}).get('subscription') or {}
    keys = sub.get('keys') or {}
    endpoint, p256dh, auth = sub.get('endpoint'), keys.get('p256dh'), keys.get('auth')
    if not (endpoint and p256dh and auth) or not str(endpoint).startswith('https://'):
        return JsonResponse({'ok': False, 'error': 'اطلاعات اشتراک ناقص است.'}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            'user': request.user,                       # اگر کاربر دیگری با همین دستگاه وارد شد، مالکیت منتقل می‌شود
            'p256dh': p256dh,
            'auth': auth,
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:300],
            'failure_count': 0,
        },
    )
    return JsonResponse({'ok': True, 'devices': request.user.push_subscriptions.count()})


@login_required
@require_POST
def push_unsubscribe(request):
    data = _json_body(request) or {}
    endpoint = data.get('endpoint')
    if endpoint:
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return JsonResponse({'ok': True, 'devices': request.user.push_subscriptions.count()})


@login_required
@require_POST
def push_test(request):
    if not push.is_configured():
        return JsonResponse({'ok': False, 'error': 'کلیدهای VAPID روی سرور تنظیم نشده است.'}, status=503)
    if not request.user.push_subscriptions.exists():
        return JsonResponse({'ok': False, 'error': 'هیچ دستگاهی برای این حساب فعال نیست.'}, status=400)
    sent = push.send_push_to_user(
        request.user, 'اعلان آزمایشی', 'اعلان‌ها روی این دستگاه با موفقیت فعال است ✅',
        url='/notifications/', tag='test', kind='test', sync=True)
    return JsonResponse({'ok': bool(sent), 'sent': sent or 0,
                         'error': None if sent else 'ارسال ناموفق بود؛ لاگ سرور را بررسی کنید.'})
