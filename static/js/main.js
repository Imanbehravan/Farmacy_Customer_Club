/* ============================================
   باشگاه مشتریان — توابع عمومی
   ============================================ */

function getCookie(name) {
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? decodeURIComponent(v[2]) : null;
}

function csrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return getCookie('csrftoken') || (meta && meta.content) || '';
}

// جلوگیری از XSS هنگام ساخت HTML از داده‌ی سرور/کاربر
function esc(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function formatNumber(n) {
  return parseInt(n, 10).toLocaleString('fa-IR');
}

function showToast(message, type) {
  type = type || 'success';
  const toast = document.createElement('div');
  toast.className = 'alert alert-' + type + ' toast';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(function () {
    toast.style.transition = 'opacity .3s ease';
    toast.style.opacity = '0';
    setTimeout(function () { toast.remove(); }, 300);
  }, 3800);
}

document.addEventListener('DOMContentLoaded', function () {
  // بستن خودکار پیام‌ها بعد از ۵ ثانیه
  document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = 'all .3s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(function () { alert.remove(); }, 300);
    }, 5000);
  });

  // فیلد موبایل: فقط رقم
  document.querySelectorAll('input[type="tel"]').forEach(function (input) {
    input.addEventListener('input', function () {
      this.value = this.value.replace(/[^0-9+\s]/g, '');
    });
  });

  // کد ملی: ۱۰ رقم
  document.querySelectorAll('#nationalId, input[name="national_id"]').forEach(function (input) {
    input.addEventListener('input', function () {
      this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10);
    });
  });

  // نمایش مبلغ به تومان (فرم ثبت خرید ادمین)
  const amountInput = document.querySelector('input[name="amount"]');
  if (amountInput) {
    amountInput.addEventListener('blur', function () {
      const val = parseInt(this.value.replace(/,/g, ''), 10);
      if (!isNaN(val)) this.setAttribute('title', val.toLocaleString('fa-IR') + ' تومان');
    });
  }
});

// بستن مودال با کلیک روی پس‌زمینه یا Escape
document.addEventListener('click', function (e) {
  const overlay = document.getElementById('prescriptionModal');
  if (overlay && e.target === overlay && typeof closePrescriptionModal === 'function') {
    closePrescriptionModal();
  }
});
document.addEventListener('keydown', function (e) {
  if (e.key !== 'Escape') return;
  const overlay = document.getElementById('prescriptionModal');
  if (overlay && overlay.style.display !== 'none' && typeof closePrescriptionModal === 'function') {
    closePrescriptionModal();
  }
});
