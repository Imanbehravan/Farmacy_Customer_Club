/* ============================================
   اعلان‌های داخل برنامه (badge، فهرست، خوانده‌شدن)
   ============================================ */
(function () {
  if (document.body.dataset.auth !== '1') return;

  const ICONS = {
    prescription: 'fa-file-medical',
    discount: 'fa-tag',
    broadcast: 'fa-bullhorn',
    general: 'fa-bell',
  };

  function setBadge(count) {
    document.querySelectorAll('.js-notif-count').forEach(function (el) {
      el.hidden = !(count > 0);
      el.textContent = count > 99 ? '99+' : count.toLocaleString('fa-IR');
    });
    // نشان عددی روی آیکن اپ نصب‌شده (در مرورگرهای پشتیبان)
    try {
      if (count > 0 && navigator.setAppBadge) navigator.setAppBadge(count);
      else if (navigator.clearAppBadge) navigator.clearAppBadge();
    } catch (e) { /* ignore */ }
  }

  function render(list, items) {
    if (!list) return;
    if (!items.length) {
      list.innerHTML = '<div class="notif-empty">اعلانی وجود ندارد</div>';
      return;
    }
    list.innerHTML = items.map(function (n) {
      return '<div class="notif-card ' + (n.is_read ? '' : 'unread') + '" data-id="' + esc(n.id) + '">' +
        '<div class="notif-icon-wrap"><i class="fas ' + (ICONS[n.type] || ICONS.general) + '"></i></div>' +
        '<div class="notif-body"><strong>' + esc(n.title) + '</strong><p>' + esc(n.message) + '</p>' +
        '<small>' + esc(n.created_at) + '</small></div>' +
        (n.is_read ? '' : '<span class="notif-dot"></span>') + '</div>';
    }).join('');
  }

  window.loadNotifications = function () {
    return fetch('/api/notifications/', { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        setBadge(data.unread_count);
        render(document.getElementById('notifList'), data.notifications);
      })
      .catch(function () { /* آفلاین */ });
  };

  window.markRead = function (id) {
    return fetch('/api/notifications/' + id + '/read/', {
      method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken() },
    }).then(window.loadNotifications);
  };

  window.markAllRead = function () {
    return fetch('/api/notifications/', {
      method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken() },
    }).then(window.loadNotifications);
  };

  document.addEventListener('click', function (e) {
    const card = e.target.closest('#notifList .notif-card.unread');
    if (card) window.markRead(card.dataset.id);
  });

  // وقتی Push رسید و برنامه باز است، شمارنده تازه می‌شود
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', function (e) {
      if (e.data && e.data.type === 'push-received') window.loadNotifications();
    });
  }
  window.addEventListener('focus', window.loadNotifications);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) window.loadNotifications();
  });

  window.loadNotifications();
  setInterval(window.loadNotifications, 60000);
})();
