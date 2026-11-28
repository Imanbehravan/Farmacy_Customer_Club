/* سرویس‌ورکر باشگاه مشتریان — کش، حالت آفلاین و Web Push */
const CONFIG = {{ config_json|safe }};
const STATIC_CACHE = 'club-static-' + CONFIG.version;
const RUNTIME_CACHE = 'club-runtime-' + CONFIG.version;

/* ------------------------------------------------------------- نصب */
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(STATIC_CACHE);
    // اگر یکی از فایل‌ها نبود، نصب کامل خراب نشود
    await Promise.all(CONFIG.precache.map((url) =>
      cache.add(new Request(url, { cache: 'reload' })).catch(() => null)));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keep = [STATIC_CACHE, RUNTIME_CACHE];
    const names = await caches.keys();
    await Promise.all(names.filter((n) => n.startsWith('club-') && !keep.includes(n)).map((n) => caches.delete(n)));
    await self.clients.claim();
  })());
});

/* ------------------------------------------------------------ درخواست‌ها */
const NEVER_CACHE = ['/api/', '/ws/', '/pwa/', '/admin-panel/', '/django-admin/', '/login/', '/verify/', '/logout/', '/sw.js'];

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (NEVER_CACHE.some((p) => url.pathname.startsWith(p))) {
    if (req.mode === 'navigate') event.respondWith(networkOrOffline(req));
    return;
  }

  // صفحات: همیشه از شبکه (اطلاعات کاربر نباید در کش بماند)؛ آفلاین → صفحه‌ی آفلاین
  if (req.mode === 'navigate') {
    event.respondWith(networkOrOffline(req));
    return;
  }

  // فایل‌های استاتیک و مدیا: اول کش، همزمان تازه‌سازی
  if (url.pathname.startsWith('/static/') || url.pathname.startsWith('/media/')) {
    event.respondWith(staleWhileRevalidate(req));
  }
});

async function networkOrOffline(req) {
  try {
    return await fetch(req);
  } catch (err) {
    const cached = await caches.match(CONFIG.offlineUrl);
    return cached || new Response('آفلاین هستید', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }
}

async function staleWhileRevalidate(req) {
  const cache = await caches.open(RUNTIME_CACHE);
  const cached = (await caches.match(req)) || (await cache.match(req));
  const network = fetch(req).then((res) => {
    if (res && res.ok) cache.put(req, res.clone());
    return res;
  }).catch(() => null);
  return cached || (await network) || Response.error();
}

/* ---------------------------------------------------------------- Push */
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = { body: event.data ? event.data.text() : '' }; }

  const title = data.title || 'باشگاه مشتریان داروخانه';
  const options = {
    body: data.body || '',
    icon: data.icon || CONFIG.icon,
    badge: data.badge || CONFIG.badge,
    tag: data.tag || 'club',
    renotify: true,
    dir: 'rtl',
    lang: 'fa',
    vibrate: [120, 60, 120],
    data: { url: data.url || '/dashboard/' },
  };

  event.waitUntil((async () => {
    // مرورگرها (به‌خصوص Safari/Chrome) نمایش اعلان برای هر Push را الزامی می‌کنند
    await self.registration.showNotification(title, options);

    if (typeof data.unread === 'number' && self.navigator.setAppBadge) {
      try { data.unread > 0 ? await self.navigator.setAppBadge(data.unread) : await self.navigator.clearAppBadge(); } catch (e) {}
    }
    // اگر برنامه باز است، شمارنده‌ی داخل صفحه هم تازه شود
    const clientsList = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    clientsList.forEach((c) => c.postMessage({ type: 'push-received', payload: data }));
  })());
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL((event.notification.data && event.notification.data.url) || '/dashboard/', self.location.origin).href;

  event.waitUntil((async () => {
    const list = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of list) {
      if (new URL(client.url).origin === self.location.origin && 'focus' in client) {
        await client.focus();
        if ('navigate' in client && client.url !== target) { try { await client.navigate(target); } catch (e) {} }
        return;
      }
    }
    await self.clients.openWindow(target);
  })());
});
