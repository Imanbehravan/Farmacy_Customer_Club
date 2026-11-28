"""ارسال Web Push (استاندارد VAPID) به دستگاه‌های کاربران."""
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import close_old_connections, transaction
from django.urls import reverse
from django.utils import timezone

from .models import PushSubscription

logger = logging.getLogger(__name__)

MAX_FAILURES = 5          # بعد از این تعداد خطای پیاپی، اشتراک حذف می‌شود
BODY_LIMIT = 140


def is_configured():
    return bool(settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY)


def _clip(text, limit=BODY_LIMIT):
    text = ' '.join((text or '').split())
    return text if len(text) <= limit else text[:limit - 1] + '…'


def _session():
    """در صورت نیاز (سرور داخل ایران) ارسال از طریق پروکسی انجام می‌شود."""
    proxy = getattr(settings, 'PUSH_PROXY_URL', '')
    if not proxy:
        return None
    import requests
    s = requests.Session()
    s.proxies = {'http': proxy, 'https': proxy}
    return s


def _send_one(sub_id, payload, session=None):
    """یک اعلان را برای یک اشتراک می‌فرستد. True یعنی موفق."""
    from pywebpush import webpush, WebPushException

    close_old_connections()
    try:
        sub = PushSubscription.objects.get(pk=sub_id)
    except PushSubscription.DoesNotExist:
        return False

    try:
        webpush(
            subscription_info=sub.as_webpush(),
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'},
            ttl=settings.PUSH_TTL_SECONDS,
            timeout=settings.PUSH_TIMEOUT_SECONDS,
            requests_session=session,
        )
    except WebPushException as exc:
        status = getattr(exc.response, 'status_code', None)
        if status in (404, 410):
            sub.delete()          # اشتراک منقضی/لغو شده
            logger.info('push subscription %s removed (HTTP %s)', sub_id, status)
        else:
            _register_failure(sub, f'HTTP {status}: {exc}')
        return False
    except Exception as exc:  # خطای شبکه، پروکسی، کلید اشتباه و ...
        _register_failure(sub, repr(exc))
        return False

    PushSubscription.objects.filter(pk=sub_id).update(
        failure_count=0, last_success_at=timezone.now())
    return True


def _register_failure(sub, reason):
    logger.warning('push to subscription %s failed: %s', sub.pk, reason)
    sub.failure_count += 1
    if sub.failure_count >= MAX_FAILURES:
        sub.delete()
    else:
        sub.save(update_fields=['failure_count'])


def _deliver(jobs):
    """jobs: لیستی از (sub_id, payload)"""
    if not jobs:
        return 0
    session = _session()
    sent = 0
    try:
        if len(jobs) == 1 or not settings.PUSH_ASYNC:
            return sum(int(_send_one(sid, payload, session)) for sid, payload in jobs)
        with ThreadPoolExecutor(max_workers=8) as pool:
            for ok in pool.map(lambda j: _send_one(j[0], j[1], session), jobs):
                sent += int(ok)
    finally:
        close_old_connections()
    return sent


def _run(jobs):
    if settings.PUSH_ASYNC:
        threading.Thread(target=_deliver, args=(jobs,), daemon=True).start()
        return None
    return _deliver(jobs)


def build_payload(title, body, url=None, tag=None, kind='general', unread=None):
    return {
        'title': title,
        'body': _clip(body),
        'url': url or reverse('dashboard'),
        'tag': tag or kind,
        'kind': kind,
        'unread': unread,
        'icon': settings.STATIC_URL + 'icons/icon-192.png',
        'badge': settings.STATIC_URL + 'icons/badge-96.png',
    }


def _jobs_for_users(user_ids, payload_for_user):
    jobs = []
    subs = PushSubscription.objects.filter(user_id__in=list(user_ids)).values_list('id', 'user_id')
    for sub_id, user_id in subs:
        jobs.append((sub_id, payload_for_user(user_id)))
    return jobs


def send_push_to_users(user_ids, title, body, url=None, tag=None, kind='general'):
    """اعلان یکسان برای چند کاربر (مثلاً همه‌ی کارمندان)."""
    if not is_configured():
        return None
    user_ids = list(user_ids)
    jobs = _jobs_for_users(user_ids, lambda uid: build_payload(title, body, url, tag, kind))
    return _run(jobs)


def send_push_to_user(user, title, body, url=None, tag=None, kind='general', sync=None):
    if not is_configured():
        return None
    unread = _unread_count(user.id)
    jobs = _jobs_for_users([user.id], lambda uid: build_payload(title, body, url, tag, kind, unread))
    if sync:
        return _deliver(jobs)
    return _run(jobs)


def _unread_count(user_id):
    from apps.notifications.models import Notification
    return Notification.objects.filter(user_id=user_id, is_read=False).count()


NOTIFICATION_URLS = {
    'prescription': 'my_prescriptions',
    'discount': 'notifications_page',
    'broadcast': 'notifications_page',
    'general': 'notifications_page',
}


def notification_url(notification):
    return reverse(NOTIFICATION_URLS.get(notification.notification_type, 'notifications_page'))


def push_notifications(notifications):
    """
    برای فهرستی از Notification (ساخته‌شده با create یا bulk_create) پوش می‌فرستد.
    تعداد خوانده‌نشده‌ی هر کاربر هم برای نشان (badge) روی آیکون اپ ارسال می‌شود.
    """
    if not is_configured():
        return None
    notifications = [n for n in notifications if n.pk]
    if not notifications:
        return None

    from django.db.models import Count
    from apps.notifications.models import Notification

    user_ids = {n.user_id for n in notifications}
    subscribed = set(PushSubscription.objects.filter(user_id__in=user_ids)
                     .values_list('user_id', flat=True))
    if not subscribed:
        return None
    unread = dict(Notification.objects.filter(user_id__in=subscribed, is_read=False)
                  .values('user_id').annotate(c=Count('id')).values_list('user_id', 'c'))

    subs_by_user = {}
    for sub_id, user_id in PushSubscription.objects.filter(user_id__in=subscribed).values_list('id', 'user_id'):
        subs_by_user.setdefault(user_id, []).append(sub_id)

    jobs = []
    for n in notifications:
        for sub_id in subs_by_user.get(n.user_id, []):
            jobs.append((sub_id, build_payload(
                n.title, n.message, notification_url(n),
                tag=f'n-{n.pk}', kind=n.notification_type,
                unread=unread.get(n.user_id, 0))))
    return _run(jobs)


def push_after_commit(notifications):
    transaction.on_commit(lambda: push_notifications(notifications))


def notify_staff(title, body, url=None, tag=None, kind='staff'):
    """اعلان برای همه‌ی کارمندان/ادمین‌هایی که اپ را نصب کرده‌اند."""
    from apps.accounts.models import User
    ids = User.objects.filter(is_staff=True, is_active=True).values_list('id', flat=True)
    return send_push_to_users(ids, title, body, url or reverse('admin_dashboard'), tag, kind)
