/* ============================================
   PHARMACY CUSTOMER CLUB - MAIN JS
   ============================================ */

// CSRF Cookie helper
function getCookie(name) {
  let v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
  return v ? v[2] : null;
}

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      alert.style.transition = 'all .3s ease';
      setTimeout(() => alert.remove(), 300);
    }, 5000);
  });

  // Phone number formatter — only allow digits
  const phoneInputs = document.querySelectorAll('input[type="tel"]');
  phoneInputs.forEach(input => {
    input.addEventListener('input', function () {
      this.value = this.value.replace(/[^0-9]/g, '');
    });
  });

  // National ID formatter
  const nationalInputs = document.querySelectorAll('#nationalId, input[name="national_id"]');
  nationalInputs.forEach(input => {
    input.addEventListener('input', function () {
      this.value = this.value.replace(/[^0-9]/g, '');
      if (this.value.length > 10) this.value = this.value.slice(0, 10);
    });
  });

  // OTP input auto-focus next field on 6 digits
  const otpInput = document.querySelector('.otp-input');
  if (otpInput) {
    otpInput.addEventListener('input', function () {
      this.value = this.value.replace(/[^0-9]/g, '');
      if (this.value.length === 6) {
        this.closest('form').submit();
      }
    });
  }

  // Add number formatting for amounts (admin purchase form)
  const amountInput = document.querySelector('input[name="amount"]');
  if (amountInput) {
    amountInput.addEventListener('blur', function () {
      const val = parseInt(this.value.replace(/,/g, ''));
      if (!isNaN(val)) this.setAttribute('title', val.toLocaleString('fa-IR') + ' تومان');
    });
  }
});

// Modal close on overlay click
document.addEventListener('click', function (e) {
  const overlay = document.getElementById('prescriptionModal');
  if (overlay && e.target === overlay) {
    closePrescriptionModal && closePrescriptionModal();
  }
});

// Keyboard: Escape to close modal
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    const overlay = document.getElementById('prescriptionModal');
    if (overlay && overlay.style.display !== 'none') {
      closePrescriptionModal && closePrescriptionModal();
    }
  }
});

// Number formatting helper
function formatNumber(n) {
  return parseInt(n).toLocaleString('fa-IR');
}

// Toast notification helper (lightweight)
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `alert alert-${type}`;
  toast.style.cssText = `
    position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%);
    z-index: 9999; min-width: 260px; text-align: center;
    animation: slideUp .3s ease;
    box-shadow: 0 4px 20px rgba(0,0,0,.15);
  `;
  toast.innerHTML = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = '.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
