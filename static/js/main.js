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

  // Keep page actions reachable on phones by moving the fixed bottom nav
  // out of the way while the user is scrolling down. It returns as soon as
  // the user scrolls up again.
  const mobileBottomNav = document.querySelector('.mobile-bottom-nav');
  const mobileViewport = window.matchMedia('(max-width: 768px)');
  let previousScrollY = window.scrollY;
  let bottomNavFramePending = false;

  const updateMobileBottomNav = () => {
    if (!mobileBottomNav) return;

    const currentScrollY = window.scrollY;
    const scrollDelta = currentScrollY - previousScrollY;
    const isMobile = mobileViewport.matches;

    if (!isMobile || currentScrollY < 80 || scrollDelta < -8) {
      mobileBottomNav.classList.remove('is-hidden');
    } else if (scrollDelta > 8) {
      mobileBottomNav.classList.add('is-hidden');
    }

    previousScrollY = currentScrollY;
    bottomNavFramePending = false;
  };

  window.addEventListener('scroll', () => {
    if (!bottomNavFramePending) {
      bottomNavFramePending = true;
      window.requestAnimationFrame(updateMobileBottomNav);
    }
  }, { passive: true });
  mobileViewport.addEventListener('change', updateMobileBottomNav);

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

function handleBookAppointmentHero(e) {
  if (e) e.preventDefault();
  const firstService = document.querySelector('.mockup-service-card');
  if (firstService) {
    selectService(firstService);
  } else {
    const servicesSec = document.getElementById('services');
    if (servicesSec) {
      servicesSec.scrollIntoView({ behavior: 'smooth' });
    }
  }
}

/** Open wizard with a selected service */
function selectService(btn) {
  if (!btn) return;
  wizard.serviceId       = btn.dataset.serviceId;
  wizard.serviceName     = btn.dataset.serviceName;
  wizard.servicePrice    = btn.dataset.servicePrice;
  wizard.serviceDuration = btn.dataset.serviceDuration;
  wizard.barberId        = '';
  wizard.barberName      = 'Any Available Barber';

  const preferredBarber = document.querySelector('[data-preferred-barber]');
  const anyAvailableBarber = document.querySelector('.barber-select-card--any');
  if (preferredBarber) {
    selectBarber(preferredBarber, preferredBarber.dataset.barberId, preferredBarber.dataset.barberName);
  } else if (anyAvailableBarber) {
    selectBarber(anyAvailableBarber, '', 'Any Available Barber');
  }

  // Populate step 1 if elements exist
  const nameEl  = document.getElementById('wiz-service-name');
  const durEl   = document.getElementById('wiz-service-duration');
  const priceEl = document.getElementById('wiz-service-price');
  if (nameEl)  nameEl.textContent = wizard.serviceName;
  if (durEl)   durEl.textContent = wizard.serviceDuration + ' min';
  if (priceEl) priceEl.textContent = '₹' + wizard.servicePrice;

  // Prefill user details if available
  if (window._userData) {
    const u = window._userData;
    const inpName  = document.getElementById('inp-name');
    const inpEmail = document.getElementById('inp-email');
    const inpPhone = document.getElementById('inp-phone');
    if (inpName  && !inpName.value  && u.name)  inpName.value  = u.name;
    if (inpEmail && !inpEmail.value && u.email) inpEmail.value = u.email;
    if (inpPhone && !inpPhone.value && u.phone) inpPhone.value = u.phone;
  }

  // Pre-select first date chip if date is not selected yet
  const dateChip = document.querySelector('.date-chip.selected') || document.querySelector('.date-chip');
  if (dateChip) {
    selectDate(dateChip);
  }

  // Update selection highlight in options list
  highlightSelectedWizardService();

  wizardGoTo(1);
  openBookingWizard();
}

let currentWizardCategory = 'all';

/** Toggle full service list in wizard Step 1 */
function toggleWizardServices() {
  const container = document.getElementById('wizardAllServicesList');
  const arrow = document.getElementById('viewAllServicesArrow');
  const btnText = document.getElementById('viewAllBtnText');
  if (!container) return;

  const isOpen = container.style.display !== 'none';
  if (isOpen) {
    container.style.display = 'none';
    if (arrow) arrow.style.transform = 'rotate(0deg)';
    if (btnText) btnText.textContent = 'Browse All Services';
  } else {
    container.style.display = 'block';
    if (arrow) arrow.style.transform = 'rotate(180deg)';
    if (btnText) btnText.textContent = 'Close Service Menu';
    highlightSelectedWizardService();
    // Focus search or scroll list smoothly into view
    const searchInp = document.getElementById('wizardServiceSearchInput');
    if (searchInp) {
      setTimeout(() => searchInp.focus(), 150);
    }
  }
}

/** Highlight selected service option in wizard Step 1 */
function highlightSelectedWizardService() {
  document.querySelectorAll('.wizard-service-option').forEach(opt => {
    if (String(opt.dataset.serviceId) === String(wizard.serviceId)) {
      opt.classList.add('selected');
    } else {
      opt.classList.remove('selected');
    }
  });
}

/** Select a service from the wizard Step 1 options list */
function pickWizardService(card) {
  if (!card) return;
  wizard.serviceId       = card.dataset.serviceId;
  wizard.serviceName     = card.dataset.serviceName;
  wizard.servicePrice    = card.dataset.servicePrice;
  wizard.serviceDuration = card.dataset.serviceDuration;

  // Update selected service preview card
  const nameEl = document.getElementById('wiz-service-name');
  const durEl  = document.getElementById('wiz-service-duration');
  const priceEl = document.getElementById('wiz-service-price');
  if (nameEl) nameEl.textContent = wizard.serviceName;
  if (durEl) durEl.innerHTML = `<i class="fa-regular fa-clock"></i> ${wizard.serviceDuration} min`;
  if (priceEl) priceEl.textContent = '₹' + wizard.servicePrice;

  // Pulse animation on the selected service card
  const ssc = document.querySelector('.selected-service-card');
  if (ssc) {
    ssc.style.transform = 'scale(1.02)';
    setTimeout(() => { ssc.style.transform = ''; }, 200);
  }

  // Update highlight in list
  highlightSelectedWizardService();

  // Update summary fields if needed
  const sumService = document.getElementById('sum-service');
  const sumDuration = document.getElementById('sum-duration');
  const sumTotal = document.getElementById('sum-total');
  if (sumService) sumService.textContent = wizard.serviceName;
  if (sumDuration) sumDuration.textContent = wizard.serviceDuration + ' min';
  if (sumTotal) sumTotal.textContent = '₹' + wizard.servicePrice;
}

/** Filter wizard services by category (All, MALE, FEMALE) */
function filterWizardServices(cat, tabBtn) {
  currentWizardCategory = cat;
  document.querySelectorAll('.wiz-cat-tab').forEach(t => t.classList.remove('active'));
  if (tabBtn) tabBtn.classList.add('active');

  const query = (document.getElementById('wizardServiceSearchInput')?.value || '').toLowerCase().trim();
  applyWizardServiceFilters(query, cat);
}

/** Live search in wizard services */
function searchWizardServices(val) {
  const clearBtn = document.getElementById('searchClearBtn');
  if (clearBtn) {
    clearBtn.style.display = val.length > 0 ? 'flex' : 'none';
  }
  applyWizardServiceFilters(val.toLowerCase().trim(), currentWizardCategory);
}

function clearServiceSearch() {
  const searchInp = document.getElementById('wizardServiceSearchInput');
  const clearBtn = document.getElementById('searchClearBtn');
  if (searchInp) {
    searchInp.value = '';
    searchInp.focus();
  }
  if (clearBtn) clearBtn.style.display = 'none';
  applyWizardServiceFilters('', currentWizardCategory);
}

function applyWizardServiceFilters(query, cat) {
  let matchCount = 0;
  document.querySelectorAll('.wizard-service-option').forEach(opt => {
    const sName = (opt.dataset.serviceName || '').toLowerCase();
    const sCat  = opt.dataset.category || '';
    const matchesCat = (cat === 'all' || sCat === cat);
    const matchesQuery = !query || sName.includes(query);

    if (matchesCat && matchesQuery) {
      opt.style.display = 'flex';
      matchCount++;
    } else {
      opt.style.display = 'none';
    }
  });

  const noMsg = document.getElementById('wizardNoServices');
  if (noMsg) {
    noMsg.style.display = matchCount === 0 ? 'block' : 'none';
  }
}

function selectBarber(card, id, name) {
  document.querySelectorAll('.barber-select-card, .barber-wheel__card').forEach(c => {
    c.classList.remove('selected');
    c.setAttribute('aria-checked', 'false');
  });
  card.classList.add('selected');
  card.setAttribute('aria-checked', 'true');
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

    // Stagger the barber wheel entrance and settle wheel positions on step 2
    if (step === 2) {
      if (window.__barberWheel) {
        requestAnimationFrame(() => window.__barberWheel.render(true));
      }
      document.querySelectorAll('.barber-wheel__dots .wheel-dot, .barber-wheel__nav, .barber-wheel__counter, .barber-wheel__controls').forEach((el) => {
        el.style.animation = 'none';
        el.offsetHeight;
        el.style.animation = '';
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

function getCsrfToken() {
  if (window.CSRF_TOKEN && window.CSRF_TOKEN.length > 5) return window.CSRF_TOKEN;
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue || '';
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
    const csrfToken = getCsrfToken();
    const res = await fetch(window.BOOK_URL || '/book/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
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
    console.error("Booking error:", err);
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

// ──────────────────────────────────────────────────────────────
// BARBER WHEEL — swipeable circular selector for "Choose Your Barber"
// ──────────────────────────────────────────────────────────────
let __barberWheel = null;
let __barberWheelInit = false;
window.__barberWheel = null;

function initBarberWheel() {
  const stage = document.getElementById('barberWheelStage');
  if (!stage || __barberWheelInit && __barberWheel?.stage === stage) return;
  __barberWheelInit = true;

  const cards = Array.from(stage.querySelectorAll('.barber-wheel__card'));
  if (!cards.length) return;

  const dotsWrap = document.getElementById('wheelDots');
  const counter = document.getElementById('wheelCounter');
  const prevBtn = document.getElementById('wheelPrev');
  const nextBtn = document.getElementById('wheelNext');

  const initial = Math.max(0, cards.findIndex(c => c.classList.contains('selected') || c.getAttribute('aria-checked') === 'true'));

  const w = {
    stage, cards, dotsWrap, counter, prevBtn, nextBtn,
    count: cards.length,
    active: initial >= 0 ? initial : 0,
    raw: 0,                 // accumulated drag offset (cards)
    velocity: 0,
    dragging: false,
    animating: false,
    pointerActive: false,
    pointerId: null,
    lastX: 0, lastY: 0, lastT: 0,
    startX: 0, startY: 0, startT: 0,
    consumedTouch: false,
    reduced: window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    raf: 0,

    spacing() {
      const w = this.cards[0].getBoundingClientRect().width || 280;
      return w + 14;
    },

    norm(i) {
      const n = ((i % this.count) + this.count) % this.count;
      return n;
    },

    /** Fractional distance of card i from the visual center (wrapped). */
    dist(i) {
      let d = i - (this.active + this.raw);
      d = ((d + this.count) % this.count + this.count / 2) % this.count - this.count / 2;
      return d;
    },

    positionCards(animate) {
      const away = this.count > 1 ? this.spacing() : 0;
      this.cards.forEach((card, i) => {
        const d = this.dist(i);
        const ad = Math.abs(d);
        const y = 18 * Math.sin(Math.min(ad, 4) * Math.PI / 4) * Math.min(1, ad * 2);
        const scale = ad < 1 ? 1 - 0.16 * ad : (ad < 2 ? 0.84 - 0.14 * (ad - 1) : 0.7);
        const opacity = ad < 1 ? 1 - 0.35 * ad : (ad < 2 ? 0.65 - 0.3 * (ad - 1) : 0.32);
        const blur = ad < 1 ? 0 : (ad < 2 ? (ad - 1) * 6 : 7);
        const ry = -Math.min(ad, 1.5) * 18;
        card.style.transform =
          `translateX(calc(-50% + ${(away * d).toFixed(1)}px)) translateY(${y.toFixed(1)}px) ` +
          `scale(${scale.toFixed(3)}) rotateY(${ry.toFixed(1)}deg)`;
        card.style.zIndex = String(20 - Math.min(ad, 9));
        card.style.opacity = opacity.toFixed(3);
        card.style.filter = blur > 0 ? `blur(${blur.toFixed(1)}px)` : 'none';
        card.classList.toggle('wheel-active', Math.abs(d) < 0.5);
        card.classList.toggle('wheel-side', Math.abs(d) >= 0.5 && Math.abs(d) < 1.5);
        card.setAttribute('aria-hidden', Math.abs(d) >= 1.5 ? 'true' : 'false');
      });
      if (this.counter) {
        const shown = this.norm(this.active + Math.round(this.raw));
        this.counter.textContent = `${shown + 1} of ${this.count}`;
      }
      this.updateDots(animate);
    },

    updateDots(animate) {
      if (!this.dotsWrap) return;
      const shown = this.norm(this.active + Math.round(this.raw));
      this.dotsWrap.querySelectorAll('.wheel-dot').forEach((dot, i) => {
        const on = i === shown;
        dot.classList.toggle('active', on);
        dot.setAttribute('aria-current', on ? 'true' : 'false');
        if (animate && on) {
          dot.style.animation = 'none';
          dot.offsetHeight;
          dot.style.animation = 'wheelDotPulse 0.45s cubic-bezier(0.34, 1.56, 0.64, 1)';
        }
      });
    },

    snap(target, withSpring) {
      if (this.animating) return;
      this.animating = true;
      this.raw = 0;
      this.active = this.norm(target);
      const changed = this.changed !== this.active;
      this.changed = this.active;

      this.stage.classList.toggle('wheel-snapping', withSpring && !this.reduced);
      this.positionCards(withSpring && !this.reduced);

      const finish = () => {
        this.stage.classList.remove('wheel-snapping');
        this.animating = false;
        this.applySelection();
        if (changed && !this.reduced) {
          try { navigator.vibrate && navigator.vibrate(10); } catch (e) { /* not supported */ }
        }
      };
      if (withSpring && !this.reduced) {
        setTimeout(finish, 600);
      } else {
        finish();
      }
    },

    applySelection() {
      const card = this.cards[this.active];
      const id = card.dataset.barberId || '';
      const name = card.dataset.barberName || 'Any Available Barber';
      const wasSelected = wizard.barberId === id;
      this.cards.forEach(c => {
        c.classList.remove('selected');
        c.setAttribute('aria-checked', 'false');
        c.querySelectorAll('.barber-wheel__select-btn').forEach(b => { b.textContent = 'Select Barber'; });
      });
      card.classList.add('selected');
      card.setAttribute('aria-checked', 'true');
      card.querySelectorAll('.barber-wheel__select-btn').forEach(b => { b.textContent = 'Selected ✓'; });
      if (!wasSelected) {
        card.classList.remove('wheel-just-selected');
        card.offsetHeight;
        card.classList.add('wheel-just-selected');
      }
      if (stage) stage.focus({ preventScroll: true });
      if (wizard.barberId !== id || wizard.barberName !== name) {
        selectBarber(card, id, name);
      }
    },

    render(entering) {
      this.positionCards(false);
    },

    destroy() {
      this.stage.removeEventListener('pointerdown', this._onDown);
      this.stage.removeEventListener('pointermove', this._onMove);
      this.stage.removeEventListener('pointerup', this._onUp);
      this.stage.removeEventListener('pointercancel', this._onUp);
      this.stage.removeEventListener('keydown', this._onKey);
      this.stage.removeEventListener('touchmove', this._onTouch);
      this.stage.removeEventListener('click', this._onClick);
      window.removeEventListener('resize', this._onResize);
    },
  };

  // Dots
  if (dotsWrap) {
    dotsWrap.innerHTML = cards.map((c, i) =>
      `<button type="button" class="wheel-dot" data-i="${i}" aria-label="Show ${c.dataset.barberName || 'barber'} ${i + 1} of ${cards.length}"></button>`
    ).join('');
  }

  // Single card: centered without carousel controls
  if (w.count <= 1) {
    if (dotsWrap) dotsWrap.style.display = 'none';
    if (counter) counter.style.display = 'none';
    if (prevBtn) prevBtn.style.display = 'none';
    if (nextBtn) nextBtn.style.display = 'none';
    w.stage.classList.add('wheel-single');
  }

  // Pointer gestures (mouse + touch unified)
  w._onDown = (e) => {
    if (w.animating) return;
    if (w.dragging || w.pointerActive) return;
    w.pointerActive = true;
    w.pointerId = e.pointerId;
    w.dragging = true;
    w.startX = w.lastX = e.clientX;
    w.startY = w.lastY = e.clientY;
    w.startT = w.lastT = performance.now();
    w.velocity = 0;
    w.raw = 0;
    w.consumedTouch = false;
    w.stage.classList.add('wheel-dragging');
    w.stage.setPointerCapture && w.stage.setPointerCapture(e.pointerId);
  };

  w._onMove = (e) => {
    if (!w.dragging || e.pointerId !== w.pointerId) return;
    const dx = e.clientX - w.lastX;
    const dy = e.clientY - w.lastY;
    const now = performance.now();
    const dt = Math.max(1, now - w.lastT);
    if (Math.abs(e.clientX - w.startX) > 10 && Math.abs(e.clientX - w.startX) > Math.abs(e.clientY - w.startY)) {
      w.consumedTouch = true;
      if (e.cancelable) e.preventDefault();
    }
    // Track follows the pointer: dragging left (dx<0) moves the next card
    // toward the center, so the raw offset grows positive.
    const dCards = -dx / w.spacing();
    w.raw += dCards;
    if (dt > 0) w.velocity = 0.75 * w.velocity + 0.25 * (dCards / dt); // cards per ms
    w.lastX = e.clientX; w.lastY = e.clientY; w.lastT = now;
    if (!w.raf) {
      w.raf = requestAnimationFrame(() => { w.raf = 0; w.positionCards(false); });
    }
  };

  w._onUp = (e) => {
    if (!w.dragging || e.pointerId !== w.pointerId) return;
    w.dragging = false;
    w.pointerActive = false;
    w.stage.classList.remove('wheel-dragging');
    w.stage.releasePointerCapture && w.stage.releasePointerCapture(e.pointerId);

    const moved = Math.abs(e.clientX - w.startX);
    let targetRaw = w.raw;
    if (!w.reduced) {
      targetRaw += w.velocity * 240; // momentum: cards per ms * 240ms
    }

    if (!w.consumedTouch && moved < 8 && Math.abs(w.raw) < 0.25) {
      // Tap: rotate the tapped side card into the center
      const card = document.elementFromPoint(e.clientX, e.clientY);
      const hit = card && card.closest ? card.closest('.barber-wheel__card') : null;
      if (hit) {
        const idx = w.cards.indexOf(hit);
        if (idx !== -1 && idx !== w.active) {
          w.snap(idx, true);
          return;
        }
      }
    }

    const drift = Math.round(targetRaw);
    const maxDrift = Math.max(1, Math.floor(w.count / 2));
    w.snap(w.active + Math.max(-maxDrift, Math.min(maxDrift, drift)), true);
    w.velocity = 0;
  };

  // Block vertical page scroll only while a horizontal swipe is happening
  w._onTouch = (e) => {
    if (!w.dragging) return;
    const dx = e.touches[0].clientX - w.startX;
    const dy = e.touches[0].clientY - w.startY;
    if (Math.abs(dx) > 12 && Math.abs(dx) > Math.abs(dy)) {
      if (e.cancelable) e.preventDefault();
    }
  };

  w._onKey = (e) => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      if (w.animating) return;
      w.snap(w.active + (e.key === 'ArrowRight' ? 1 : -1), true);
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      w.applySelection();
    }
  };

  w._onClick = (e) => {
    const btn = e.target.closest('.barber-wheel__select-btn');
    if (btn) {
      const card = btn.closest('.barber-wheel__card');
      if (card && w.cards.indexOf(card) === w.active) {
        e.preventDefault();
        w.applySelection();
      }
    }
  };

  w._onResize = () => { w.positionCards(false); };

  w._onTouch = w._onTouch.bind(w);
  w._onDown = w._onDown.bind(w);
  w._onMove = w._onMove.bind(w);
  w._onUp = w._onUp.bind(w);
  w._onKey = w._onKey.bind(w);
  w._onClick = w._onClick.bind(w);
  w._onResize = w._onResize.bind(w);

  stage.addEventListener('pointerdown', w._onDown);
  stage.addEventListener('pointermove', w._onMove);
  stage.addEventListener('pointerup', w._onUp);
  stage.addEventListener('pointercancel', w._onUp);
  stage.addEventListener('keydown', w._onKey);
  if (w.prevBtn) w.prevBtn.addEventListener('click', () => { if (!w.animating) w.snap(w.active - 1, true); });
  if (w.nextBtn) w.nextBtn.addEventListener('click', () => { if (!w.animating) w.snap(w.active + 1, true); });
  if (dotsWrap) dotsWrap.addEventListener('click', (e) => {
    const dot = e.target.closest('.wheel-dot');
    if (dot && !w.animating) w.snap(parseInt(dot.dataset.i, 10), true);
  });

  // Native touchmove must stay non-passive for scroll prevention
  stage.addEventListener('touchmove', (e) => w._onTouch(e), { passive: false });
  window.addEventListener('resize', w._onResize);

  w.positionCards(false);
  w.applySelection(true);

  window.__barberWheel = w;

  return w;
}

document.addEventListener('DOMContentLoaded', () => {
  initBarberWheel();

  const isIOS = /iPad|iPhone|iPod/.test(window.navigator.userAgent)
    || (window.navigator.platform === 'MacIntel' && window.navigator.maxTouchPoints > 1);
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  const installPrompt = document.getElementById('iosInstallPrompt');
  const closeInstallPrompt = document.getElementById('iosInstallPromptClose');
  const installLink = document.getElementById('iosInstallLink');
  const installPromptText = document.getElementById('iosInstallPromptText');

  if (isIOS && !isStandalone && installPrompt && localStorage.getItem('24k-ios-install-dismissed') !== 'true') {
    installPrompt.hidden = false;
  }

  closeInstallPrompt?.addEventListener('click', () => {
    installPrompt.hidden = true;
    localStorage.setItem('24k-ios-install-dismissed', 'true');
  });

  installLink?.addEventListener('click', () => {
    if (!installPrompt) return;
    if (!isIOS && installPromptText) {
      installPromptText.innerHTML = 'Open this website in <b>Safari on your iPhone or iPad</b>, then tap Share <i class="fa-solid fa-arrow-up-from-bracket" aria-hidden="true"></i> and <b>Add to Home Screen</b>.';
    }
    installPrompt.hidden = false;
    localStorage.removeItem('24k-ios-install-dismissed');
  });

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => navigator.serviceWorker.register('/service-worker.js').catch(() => {}));
  }
});
