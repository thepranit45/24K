/* ═══════════════════════════════════════════════════════════════
   24 K BARBERSHOP — Main JS
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
  barberId:     '',
  barberName:   'Any Available Barber',
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
    document.querySelectorAll('#mobileNav a').forEach(link => {
      link.addEventListener('click', closeMobileNav);
    });
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
  wizard.barberId        = '';
  wizard.barberName      = 'Any Available Barber';

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

  // Pre-select first date chip if date is not selected yet
  const dateChip = document.querySelector('.date-chip.selected') || document.querySelector('.date-chip');
  if (dateChip) {
    selectDate(dateChip);
  }

  wizardGoTo(1);
  openBookingWizard();
}

function selectBarber(card, id, name) {
  document.querySelectorAll('.barber-select-card').forEach(c => c.classList.remove('selected'));
  card.classList.add('selected');
  wizard.barberId   = id || '';
  wizard.barberName = name || 'Any Available Barber';

  if (wizard.date) {
    loadTimeSlots();
  }
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

let currentStepIndex = 1;

/** Navigate between wizard panels */
function wizardGoTo(step) {
  const isForward = step >= currentStepIndex;
  currentStepIndex = step;

  document.querySelectorAll('.wizard-panel').forEach(p => {
    p.classList.remove('active', 'slide-from-right', 'slide-from-left');
  });

  document.querySelectorAll('.wizard-step').forEach((s, i) => {
    s.classList.remove('active', 'done');
    if (i + 1 < step)  s.classList.add('done');
    if (i + 1 === step) s.classList.add('active');
  });

  const panel = document.getElementById(`wizard-panel-${step}`);
  if (panel) {
    const animClass = isForward ? 'slide-from-right' : 'slide-from-left';
    panel.classList.add('active', animClass);
    panel.scrollTop = 0;

    // Trigger stagger animation for date chips on step 3
    if (step === 3) {
      document.querySelectorAll('#dateStrip .date-chip').forEach((chip, idx) => {
        chip.style.animation = 'none';
        chip.offsetHeight; // trigger reflow
        chip.style.animation = `chipStaggerIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) ${0.04 * idx}s forwards`;
      });
    }

    // Trigger stagger animation for barber cards on step 2
    if (step === 2) {
      document.querySelectorAll('.barber-select-card').forEach((card, idx) => {
        card.style.animation = 'none';
        card.offsetHeight;
        card.style.animation = `barberStaggerIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) ${0.05 * idx}s forwards`;
      });
    }
  }

  // Load time slots when going to step 4 (Time)
  if (step === 4) {
    loadTimeSlots();
  }
}

// ── Date picker ───────────────────────────────────────────────
function selectDate(chip) {
  document.querySelectorAll('.date-chip').forEach(c => c.classList.remove('selected', 'pulse-pop'));
  chip.classList.add('selected', 'pulse-pop');

  setTimeout(() => chip.classList.remove('pulse-pop'), 450);

  wizard.date = chip.dataset.date;
  const d = new Date(wizard.date + 'T00:00:00');
  const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
  wizard.dateDisplay = d.toLocaleDateString('en-IN', options);

  const labelEl = document.getElementById('selectedDateLabel');
  if (labelEl) labelEl.textContent = wizard.dateDisplay;

  const btn = document.getElementById('btnDateNext');
  if (btn) btn.disabled = false;

  // Reset time selection
  wizard.time = null;
  wizard.timeDisplay = null;
  const btnTime = document.getElementById('btnTimeNext');
  if (btnTime) btnTime.disabled = true;

  // Immediately load time slots for this date
  loadTimeSlots();
}

function scrollDates(dir) {
  const strip = document.getElementById('dateStrip');
  if (strip) strip.scrollBy({ left: dir * 220, behavior: 'smooth' });
}

// ── Time slots ────────────────────────────────────────────────
async function loadTimeSlots() {
  const grid = document.getElementById('timeGrid');
  if (!grid) return;

  if (!wizard.date) {
    const chip = document.querySelector('.date-chip.selected') || document.querySelector('.date-chip');
    if (chip) {
      wizard.date = chip.dataset.date;
      const d = new Date(wizard.date + 'T00:00:00');
      const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
      wizard.dateDisplay = d.toLocaleDateString('en-IN', options);
      const labelEl = document.getElementById('selectedDateLabel');
      if (labelEl) labelEl.textContent = wizard.dateDisplay;
    }
  }

  if (!wizard.date) {
    grid.innerHTML = '<div class="time-loading"><p style="color:#f59e0b">Please select a date first.</p></div>';
    return;
  }

  grid.innerHTML = '<div class="time-loading"><div class="spinner"></div><p>Loading available slots…</p></div>';
  wizard.time = null;
  wizard.timeDisplay = null;
  const btnNext = document.getElementById('btnTimeNext');
  if (btnNext) btnNext.disabled = true;

  try {
    const slotsBaseUrl = window.SLOTS_URL || '/api/slots/';
    const url = `${slotsBaseUrl}?date=${wizard.date}&service_id=${wizard.serviceId || ''}&barber_id=${wizard.barberId || ''}`;
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

    const availableSlots = data.slots.filter(s => !s.booked);
    let noticeBanner = '';
    if (availableSlots.length === 0) {
      noticeBanner = '<div class="time-loading" style="grid-column: 1 / -1;"><p style="color:#f59e0b; margin-bottom: 1rem;"><i class="fa-solid fa-clock"></i> All slots for this date are past business hours or booked. Please pick another date.</p></div>';
    }

    grid.innerHTML = noticeBanner + data.slots.map((slot, index) => {
      const delay = (0.03 * (index % 12)).toFixed(2);
      if (slot.booked) {
        return `<button class="time-slot booked" disabled title="Slot unavailable or past" style="animation: slotPopIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) ${delay}s forwards">
          ${slot.display}
        </button>`;
      }
      return `<button class="time-slot" data-time="${slot.time}" data-display="${slot.display}" onclick="selectTimeSlot(this)" style="animation: slotPopIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) ${delay}s forwards">
        ${slot.display}
      </button>`;
    }).join('');
  } catch (err) {
    console.error("loadTimeSlots error:", err);
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
  document.getElementById('sum-barber').textContent   = wizard.barberName;
  document.getElementById('sum-date').textContent     = wizard.dateDisplay;
  document.getElementById('sum-time').textContent     = wizard.timeDisplay;
  document.getElementById('sum-duration').textContent = wizard.serviceDuration + ' minutes';
  document.getElementById('sum-name').textContent     = name;
  document.getElementById('sum-phone').textContent    = phone;
  document.getElementById('sum-total').textContent    = '₹' + wizard.servicePrice;

  wizardGoTo(6);
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
    barber_id:     wizard.barberId,
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
