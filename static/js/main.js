/* ═══════════════════════════════════════════════════════════════
   THE GENTLEMAN'S CUT — Main JS
═══════════════════════════════════════════════════════════════ */

'use strict';

// ──────────────────────────────────────────────────────────────
// GLOBAL STATE
// ──────────────────────────────────────────────────────────────
const wizard = {
  serviceId:    null,
  serviceName:  null,
  servicePrice: null,
  serviceDuration: null,
  date:         null,       // 'YYYY-MM-DD'
  dateDisplay:  null,       // 'Mon 10 Aug'
  time:         null,       // '10:00'
  timeDisplay:  null,       // '10:00 AM'
};

// ──────────────────────────────────────────────────────────────
// NAVBAR — scroll effect
// ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const navbar = document.getElementById('navbar');
  if (navbar) {
    const onScroll = () => navbar.classList.toggle('scrolled', window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Hamburger
  const hamburger = document.getElementById('hamburger');
  const mobileNav = document.getElementById('mobileNav');
  const overlay   = document.getElementById('mobileNavOverlay');

  if (hamburger) {
    hamburger.addEventListener('click', () => {
      const open = mobileNav.classList.toggle('open');
      overlay.classList.toggle('open', open);
      hamburger.setAttribute('aria-expanded', String(open));
      document.body.classList.toggle('no-scroll', open);
    });
    overlay.addEventListener('click', closeMobileNav);
  }

  // Auto-dismiss toasts
  document.querySelectorAll('.toast[data-autohide]').forEach(toast => {
    setTimeout(() => toast.remove(), 5000);
  });

  // Animate on scroll
  initScrollAnimations();
});

function closeMobileNav() {
  const mobileNav = document.getElementById('mobileNav');
  const overlay   = document.getElementById('mobileNavOverlay');
  if (mobileNav) {
    mobileNav.classList.remove('open');
    overlay.classList.remove('open');
    document.body.classList.remove('no-scroll');
    document.getElementById('hamburger')?.setAttribute('aria-expanded', 'false');
  }
}

// ──────────────────────────────────────────────────────────────
// SCROLL ANIMATIONS
// ──────────────────────────────────────────────────────────────
function initScrollAnimations() {
  const els = document.querySelectorAll('[data-animate="fade-up"]');
  if (!els.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const delay = entry.target.dataset.delay || '0';
        entry.target.style.transitionDelay = delay + 'ms';
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  els.forEach(el => observer.observe(el));
}

// ──────────────────────────────────────────────────────────────
// BOOKING WIZARD
// ──────────────────────────────────────────────────────────────

/** Open wizard with a selected service */
function selectService(btn) {
  wizard.serviceId       = btn.dataset.serviceId;
  wizard.serviceName     = btn.dataset.serviceName;
  wizard.servicePrice    = btn.dataset.servicePrice;
  wizard.serviceDuration = btn.dataset.serviceDuration;

  // Populate step 1
  document.getElementById('wiz-service-name').textContent     = wizard.serviceName;
  document.getElementById('wiz-service-duration').textContent = wizard.serviceDuration + ' min';
  document.getElementById('wiz-service-price').textContent    = '₹' + wizard.servicePrice;

  // Prefill user details if available
  if (window._userData) {
    const u = window._userData;
    const nameEl    = document.getElementById('inp-name');
    const emailEl   = document.getElementById('inp-email');
    const phoneEl   = document.getElementById('inp-phone');
    if (nameEl  && !nameEl.value  && u.name)  nameEl.value  = u.name;
    if (emailEl && !emailEl.value && u.email) emailEl.value = u.email;
    if (phoneEl && !phoneEl.value && u.phone) phoneEl.value = u.phone;
  }

  wizardGoTo(1);
  openBookingWizard();
}

function openBookingWizard() {
  document.getElementById('bookingWizard').classList.add('open');
  document.getElementById('bookingBackdrop').classList.add('open');
  document.body.classList.add('no-scroll');
}

function closeBookingWizard() {
  document.getElementById('bookingWizard').classList.remove('open');
  document.getElementById('bookingBackdrop').classList.remove('open');
  document.body.classList.remove('no-scroll');
}

/** Navigate between wizard panels */
function wizardGoTo(step) {
  document.querySelectorAll('.wizard-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.wizard-step').forEach((s, i) => {
    s.classList.remove('active', 'done');
    if (i + 1 < step)  s.classList.add('done');
    if (i + 1 === step) s.classList.add('active');
  });
  const panel = document.getElementById(`wizard-panel-${step}`);
  if (panel) {
    panel.classList.add('active');
    panel.scrollTop = 0;
  }

  // Load time slots when going to step 3
  if (step === 3 && wizard.date) loadTimeSlots();
}

// ── Date picker ───────────────────────────────────────────────
function selectDate(chip) {
  document.querySelectorAll('.date-chip').forEach(c => c.classList.remove('selected'));
  chip.classList.add('selected');

  wizard.date = chip.dataset.date;
  const d = new Date(wizard.date + 'T00:00:00');
  const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
  wizard.dateDisplay = d.toLocaleDateString('en-IN', options);

  document.getElementById('selectedDateLabel').textContent = wizard.dateDisplay;

  const btn = document.getElementById('btnDateNext');
  if (btn) btn.disabled = false;

  // Reset time selection
  wizard.time = null;
  wizard.timeDisplay = null;
  const btnTime = document.getElementById('btnTimeNext');
  if (btnTime) btnTime.disabled = true;
}

function scrollDates(dir) {
  const strip = document.getElementById('dateStrip');
  if (strip) strip.scrollBy({ left: dir * 200, behavior: 'smooth' });
}

// ── Time slots ────────────────────────────────────────────────
async function loadTimeSlots() {
  const grid = document.getElementById('timeGrid');
  if (!grid || !wizard.date) return;

  grid.innerHTML = '<div class="time-loading"><div class="spinner"></div><p>Loading slots…</p></div>';
  wizard.time = null;
  wizard.timeDisplay = null;
  const btnNext = document.getElementById('btnTimeNext');
  if (btnNext) btnNext.disabled = true;

  try {
    const url = `${window.SLOTS_URL}?date=${wizard.date}&service_id=${wizard.serviceId}`;
    const res = await fetch(url);
    const data = await res.json();

    if (!res.ok || data.error) {
      grid.innerHTML = `<div class="time-loading"><p style="color:#fca5a5">${data.error || data.message || 'Error loading slots.'}</p></div>`;
      return;
    }

    if (!data.slots || data.slots.length === 0) {
      grid.innerHTML = '<div class="time-loading"><p>No slots available for this date.</p></div>';
      return;
    }

    grid.innerHTML = data.slots.map(slot => {
      if (slot.booked) {
        return `<button class="time-slot booked" disabled>
          ${slot.display}
          <span class="time-slot-booked-label">Booked</span>
        </button>`;
      }
      return `<button class="time-slot" data-time="${slot.time}" data-display="${slot.display}" onclick="selectTimeSlot(this)">
        ${slot.display}
      </button>`;
    }).join('');
  } catch (err) {
    grid.innerHTML = '<div class="time-loading"><p style="color:#fca5a5">Network error. Please try again.</p></div>';
  }
}

function selectTimeSlot(btn) {
  document.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
  btn.classList.add('selected');

  wizard.time        = btn.dataset.time;
  wizard.timeDisplay = btn.dataset.display;

  const btnNext = document.getElementById('btnTimeNext');
  if (btnNext) btnNext.disabled = false;
}

// ── Details validation ────────────────────────────────────────
function goToReview() {
  const name  = document.getElementById('inp-name')?.value.trim();
  const phone = document.getElementById('inp-phone')?.value.trim();
  let valid = true;

  clearErrors();

  if (!name) { showError('err-name', 'Full name is required.'); valid = false; }

  const digits = phone.replace(/\D/g, '');
  if (!phone || digits.length < 10) { showError('err-phone', 'Enter a valid mobile number (10 digits).'); valid = false; }

  if (!valid) return;

  // Build summary
  document.getElementById('sum-service').textContent  = wizard.serviceName;
  document.getElementById('sum-date').textContent     = wizard.dateDisplay;
  document.getElementById('sum-time').textContent     = wizard.timeDisplay;
  document.getElementById('sum-duration').textContent = wizard.serviceDuration + ' minutes';
  document.getElementById('sum-name').textContent     = name;
  document.getElementById('sum-phone').textContent    = phone;
  document.getElementById('sum-total').textContent    = '₹' + wizard.servicePrice;

  wizardGoTo(5);
}

function clearErrors() {
  ['err-name', 'err-phone', 'err-email'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '';
  });
}

function showError(id, msg) {
  const el = document.getElementById(id);
  if (el) el.textContent = msg;
}

// ── Submit booking ────────────────────────────────────────────
async function submitBooking() {
  const btn = document.getElementById('btnConfirm');
  const errEl = document.getElementById('bookingError');

  if (errEl) errEl.style.display = 'none';
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-inline"></span> Processing…'; }

  const payload = {
    service_id:    wizard.serviceId,
    booking_date:  wizard.date,
    booking_time:  wizard.time,
    full_name:     document.getElementById('inp-name')?.value.trim(),
    phone:         document.getElementById('inp-phone')?.value.trim(),
    email:         '',
    special_request: document.getElementById('inp-request')?.value.trim() || '',
  };

  try {
    const res = await fetch(window.BOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.CSRF_TOKEN,
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (res.ok && data.success) {
      closeBookingWizard();
      window.location.href = data.redirect;
    } else {
      const msg = data.error || 'Something went wrong. Please try again.';
      if (errEl) { errEl.textContent = msg; errEl.style.display = 'block'; }
      if (btn)   { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-lock"></i> Proceed to Payment'; }
    }
  } catch (err) {
    if (errEl) { errEl.textContent = 'Network error. Please check your connection and try again.'; errEl.style.display = 'block'; }
    if (btn)   { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-lock"></i> Proceed to Payment'; }
  }
}

// ──────────────────────────────────────────────────────────────
// TOAST (programmatic)
// ──────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = { success: 'fa-circle-check', error: 'fa-circle-xmark', warning: 'fa-triangle-exclamation', info: 'fa-circle-info' };
  const icon = icons[type] || icons.info;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div class="toast-icon"><i class="fa-solid ${icon}"></i></div>
    <span class="toast-message">${message}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
  `;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}
