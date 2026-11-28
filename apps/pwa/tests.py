import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.notifications.models import Notification

from .models import PushSubscription

User = get_user_model()

SUB = {
    'endpoint': 'https://fcm.googleapis.com/fcm/send/abc123',
    'keys': {'p256dh': 'BPk' + 'A' * 80, 'auth': 'authsecret123'},
}


@override_settings(VAPID_PUBLIC_KEY='pub', VAPID_PRIVATE_KEY='priv', PUSH_ASYNC=False)
class PwaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09120000001')
        self.staff = User.objects.create_user('09120000002', is_staff=True)

    def _post(self, name, data):
        return self.client.post(reverse(name), json.dumps(data), content_type='application/json')

    def test_manifest_and_sw_and_offline(self):
        m = self.client.get('/manifest.webmanifest')
        self.assertEqual(m.status_code, 200)
        data = json.loads(m.content)
        self.assertEqual(data['display'], 'standalone')
        self.assertEqual(data['dir'], 'rtl')
        self.assertTrue(any(i['purpose'] == 'maskable' for i in data['icons']))
        sw = self.client.get('/sw.js')
        self.assertEqual(sw.status_code, 200)
        self.assertEqual(sw['Service-Worker-Allowed'], '/')
        self.assertIn('javascript', sw['Content-Type'])
        self.assertIn(b'addEventListener(\'push\'', sw.content)
        self.assertEqual(self.client.get('/offline/').status_code, 200)

    def test_subscribe_requires_login_and_valid_data(self):
        self.assertEqual(self._post('push_subscribe', {'subscription': SUB}).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self._post('push_subscribe', {'subscription': {'endpoint': 'x'}}).status_code, 400)
        r = self._post('push_subscribe', {'subscription': SUB})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 1)
        # همان دستگاه با کاربر دیگر → مالکیت منتقل می‌شود (نه تکراری)
        self.client.force_login(self.staff)
        self._post('push_subscribe', {'subscription': SUB})
        self.assertEqual(PushSubscription.objects.get().user, self.staff)

    def test_unsubscribe(self):
        self.client.force_login(self.user)
        self._post('push_subscribe', {'subscription': SUB})
        self._post('push_unsubscribe', {'endpoint': SUB['endpoint']})
        self.assertEqual(PushSubscription.objects.count(), 0)

    @mock.patch('pywebpush.webpush')
    def test_new_notification_sends_push(self, wp):
        PushSubscription.objects.create(user=self.user, endpoint=SUB['endpoint'], p256dh='k', auth='a')
        with self.captureOnCommitCallbacks(execute=True):
            Notification.objects.create(user=self.user, title='نسخه آماده شد', message='سلام', notification_type='prescription')
        self.assertEqual(wp.call_count, 1)
        kwargs = wp.call_args.kwargs
        payload = json.loads(kwargs['data'])
        self.assertEqual(payload['title'], 'نسخه آماده شد')
        self.assertEqual(payload['url'], '/prescriptions/')
        self.assertEqual(payload['unread'], 1)

    @mock.patch('pywebpush.webpush')
    def test_bulk_broadcast_sends_push_to_each_user(self, wp):
        other = User.objects.create_user('09120000003')
        for u in (self.user, other):
            PushSubscription.objects.create(user=u, endpoint=f'https://x.example/{u.pk}', p256dh='k', auth='a')
        self.client.force_login(self.staff)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(reverse('admin_broadcast'), {'title': 'تخفیف', 'message': 'سلام به همه', 'target': 'all'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(wp.call_count, 2)

    @mock.patch('pywebpush.webpush')
    def test_expired_subscription_is_removed(self, wp):
        from pywebpush import WebPushException
        resp = mock.Mock(status_code=410)
        wp.side_effect = WebPushException('gone', response=resp)
        PushSubscription.objects.create(user=self.user, endpoint=SUB['endpoint'], p256dh='k', auth='a')
        with self.captureOnCommitCallbacks(execute=True):
            Notification.objects.create(user=self.user, title='t', message='m')
        self.assertEqual(PushSubscription.objects.count(), 0)

    @mock.patch('pywebpush.webpush')
    def test_staff_gets_push_for_new_prescription(self, wp):
        PushSubscription.objects.create(user=self.staff, endpoint=SUB['endpoint'], p256dh='k', auth='a')
        self.client.force_login(self.user)
        r = self.client.post(reverse('submit_prescription'),
                             {'tracking_code': '123456', 'national_id': '0012345678', 'insurance_type': 'tamin'})
        self.assertTrue(r.json().get('success'), r.content)
        self.assertGreaterEqual(wp.call_count, 1)
        self.assertIn('نسخه', json.loads(wp.call_args.kwargs['data'])['title'])

    def test_pages_render(self):
        for name in ('landing', 'login', 'pwa_offline'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.client.force_login(self.user)
        for name in ('dashboard', 'profile', 'notifications_page', 'my_prescriptions', 'user_chat', 'blog'):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)
            self.assertContains(r, 'manifest.webmanifest')
        self.client.force_login(self.staff)
        for name in ('admin_dashboard', 'admin_prescriptions', 'admin_chat_list', 'admin_purchases',
                     'admin_campaigns', 'admin_broadcast'):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)
