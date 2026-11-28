/* ============================================
   PWA: سرویس‌ورکر، نصب اپ و اعلان‌های Push
   ============================================ */
(function () {
  'use strict';

  const body = document.body;
  const AUTH = body.dataset.auth === '1';
  const VAPID = body.dataset.vapid || '';

  const ua = navigator.userAgent || '';
  const isIOS = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const DISMISS_KEY = 'pwa-install-dismissed-at';

  let deferredPrompt = null;

  /* ---------------------------------------------------------- سرویس‌ورکر */
  const swReady = ('serviceWorker' in navigator)
    ? navigator.serviceWorker.register('/sw.js', { scope: '/' }).then(function () {
        return navigator.serviceWorker.ready;
      }).catch(function (err) { console.warn('SW register failed', err); return null; })
    : Promise.resolve(null);

  /* ---------------------------------------------------------------- نصب */
  function installAvailable() {
    return !isStandalone && (!!deferredPrompt || isIOS);
  }

  function updateInstallUI() {
    const dismissedAt = parseInt(localStorage.getItem(DISMISS_KEY) || '0', 10);
    const recentlyDismissed = Date.now() - dismissedAt < 7 * 24 * 3600 * 1000;
    document.querySelectorAll('[data-install-banner]').forEach(function (el) {
      el.classList.toggle('show', installAvailable() && !recentlyDismissed);
    });
    document.querySelectorAll('[data-install-card]').forEach(function (el) {
      el.hidden = isStandalone;
    });
    document.querySelectorAll('[data-pwa-install]').forEach(function (btn) {
      btn.hidden = !installAvailable();
    });
    document.querySelectorAll('[data-install-done]').forEach(function (el) {
      el.hidden = !isStandalone;
    });
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    updateInstallUI();
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    updateInstallUI();
    if (window.showToast) showToast('اپلیکیشن با موفقیت نصب شد ✅');
  });

  document.addEventListener('click', function (e) {
    const installBtn = e.target.closest('[data-pwa-install]');
    if (installBtn) {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.finally(function () { deferredPrompt = null; updateInstallUI(); });
      } else if (isIOS) {
        document.querySelectorAll('[data-ios-steps]').forEach(function (el) { el.classList.add('show'); });
      }
      return;
    }
    if (e.target.closest('[data-install-dismiss]')) {
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
      updateInstallUI();
    }
  });

  /* --------------------------------------------------------------- Push */
  const pushSupported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  // در iOS فقط وقتی اپ به صفحه‌ی اصلی اضافه شده Push کار می‌کند
  const needsInstallForPush = isIOS && !isStandalone;

  function b64ToUint8(base64) {
    const pad = '='.repeat((4 - base64.length % 4) % 4);
    const raw = atob((base64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
    return Uint8Array.from(raw, function (c) { return c.charCodeAt(0); });
  }

  function post(url, payload) {
    return fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify(payload || {}),
    }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j.status = r.status; return j; }); });
  }

  async function currentSubscription() {
    const reg = await swReady;
    return reg ? reg.pushManager.getSubscription() : null;
  }

  async function subscribeBrowser(reg) {
    const opts = { userVisibleOnly: true, applicationServerKey: b64ToUint8(VAPID) };
    try {
      return await reg.pushManager.subscribe(opts);
    } catch (err) {
      // کلید VAPID عوض شده: اشتراک قدیمی را پاک و دوباره بسازیم
      const old = await reg.pushManager.getSubscription();
      if (old) { await old.unsubscribe(); return reg.pushManager.subscribe(opts); }
      throw err;
    }
  }

  async function enablePush() {
    if (!AUTH) return { ok: false, reason: 'auth' };
    if (needsInstallForPush) return { ok: false, reason: 'ios-install' };
    if (!pushSupported) return { ok: false, reason: 'unsupported' };
    if (!VAPID) return { ok: false, reason: 'no-key' };

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return { ok: false, reason: permission };

    const reg = await swReady;
    if (!reg) return { ok: false, reason: 'no-sw' };
    const sub = (await reg.pushManager.getSubscription()) || (await subscribeBrowser(reg));
    const res = await post('/pwa/push/subscribe/', { subscription: sub.toJSON() });
    return { ok: !!res.ok, reason: res.ok ? 'enabled' : (res.error || 'server') };
  }

  async function disablePush() {
    const sub = await currentSubscription();
    if (sub) {
      await post('/pwa/push/unsubscribe/', { endpoint: sub.endpoint });
      await sub.unsubscribe();
    }
    return { ok: true };
  }

  // هر بار که کاربر وارد می‌شود، اشتراک این دستگاه با حساب فعلی هماهنگ می‌شود
  async function syncPush() {
    if (!AUTH || !pushSupported || !VAPID || Notification.permission !== 'granted') return;
    try {
      const reg = await swReady;
      if (!reg) return;
      const sub = (await reg.pushManager.getSubscription()) || (await subscribeBrowser(reg));
      await post('/pwa/push/subscribe/', { subscription: sub.toJSON() });
    } catch (err) { console.warn('push sync failed', err); }
  }

  async function pushState() {
    if (needsInstallForPush) return 'ios-install';
    if (!pushSupported) return 'unsupported';
    if (Notification.permission === 'denied') return 'denied';
    if (Notification.permission === 'granted' && await currentSubscription()) return 'enabled';
    return 'off';
  }

  const STATE_TEXT = {
    'enabled': 'اعلان‌ها روی این دستگاه فعال است',
    'off': 'اعلان‌ها روی این دستگاه غیرفعال است',
    'denied': 'اعلان‌ها در تنظیمات مرورگر مسدود شده‌اند',
    'unsupported': 'این مرورگر از اعلان پشتیبانی نمی‌کند',
    'ios-install': 'برای فعال‌سازی اعلان در آیفون ابتدا اپ را به صفحه‌ی اصلی اضافه کنید',
  };

  async function refreshPushUI() {
    const state = await pushState();
    document.querySelectorAll('[data-push-status]').forEach(function (el) { el.textContent = STATE_TEXT[state]; });
    document.querySelectorAll('[data-push-dot]').forEach(function (el) { el.classList.toggle('on', state === 'enabled'); });
    document.querySelectorAll('[data-push-enable]').forEach(function (el) { el.hidden = state !== 'off'; });
    document.querySelectorAll('[data-push-disable],[data-push-test]').forEach(function (el) { el.hidden = state !== 'enabled'; });
    document.querySelectorAll('[data-push-denied-help]').forEach(function (el) { el.hidden = state !== 'denied'; });
    document.querySelectorAll('[data-push-prompt]').forEach(function (el) { el.hidden = state !== 'off'; });
    document.querySelectorAll('[data-ios-steps-push]').forEach(function (el) { el.classList.toggle('show', state === 'ios-install'); });
  }

  const REASON_TEXT = {
    'denied': 'اجازه‌ی اعلان داده نشد. از تنظیمات مرورگر آن را فعال کنید.',
    'default': 'درخواست اعلان بسته شد.',
    'unsupported': 'این مرورگر از اعلان پشتیبانی نمی‌کند.',
    'ios-install': 'ابتدا اپ را به صفحه‌ی اصلی اضافه کنید.',
    'no-key': 'کلید اعلان روی سرور تنظیم نشده است.',
  };

  document.addEventListener('click', async function (e) {
    const enable = e.target.closest('[data-push-enable]');
    const disable = e.target.closest('[data-push-disable]');
    const test = e.target.closest('[data-push-test]');
    const logout = e.target.closest('.js-logout');

    if (enable) {
      enable.disabled = true;
      const res = await enablePush();
      enable.disabled = false;
      if (res.ok) showToast('اعلان‌ها فعال شد ✅');
      else showToast(REASON_TEXT[res.reason] || 'فعال‌سازی اعلان ناموفق بود.', 'warning');
      refreshPushUI();
    } else if (disable) {
      await disablePush();
      showToast('اعلان‌ها غیرفعال شد.', 'info');
      refreshPushUI();
    } else if (test) {
      test.disabled = true;
      const res = await post('/pwa/push/test/');
      test.disabled = false;
      if (res.ok) showToast('اعلان آزمایشی ارسال شد؛ چند ثانیه صبر کنید.');
      else showToast(res.error || 'ارسال ناموفق بود.', 'error');
    } else if (logout) {
      // دستگاهی که از حساب خارج می‌شود نباید اعلان‌های آن حساب را بگیرد
      e.preventDefault();
      const href = logout.href;
      try {
        const sub = await currentSubscription();
        if (sub) await post('/pwa/push/unsubscribe/', { endpoint: sub.endpoint });
      } catch (err) { /* ignore */ }
      window.location.href = href;
    }
  });

  /* ---------------------------------------------------------------- init */
  updateInstallUI();
  refreshPushUI();
  syncPush().then(refreshPushUI);

  window.Pwa = { enablePush: enablePush, disablePush: disablePush, pushState: pushState, isStandalone: isStandalone, isIOS: isIOS };
})();
