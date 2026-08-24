/* ═══════════════════════════════════════════════════════════════
   24 K — Premium Animation Engine
   Scroll reveal, particles, ripple, counters, page curtain
 ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ─── Page Curtain ──────────────────────────────────────────── */
  const curtain = document.getElementById('pageCurtain');
  if (curtain) {
    window.addEventListener('load', () => {
      setTimeout(() => curtain.classList.add('hidden'), 600);
    });
  }

  /* ─── Scroll Progress Bar ───────────────────────────────────── */
  const progressBar = document.getElementById('scrollProgressBar');
  if (progressBar) {
    window.addEventListener('scroll', () => {
      const scrollTop  = window.scrollY;
      const docHeight  = document.documentElement.scrollHeight - window.innerHeight;
      const percent    = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      progressBar.style.width = Math.min(percent, 100) + '%';
    }, { passive: true });
  }

  /* ─── Scroll Reveal (Intersection Observer) ─────────────────── */
  const revealOpts = { threshold: 0.12, rootMargin: '0px 0px -60px 0px' };
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        revealObserver.unobserve(entry.target);
      }
    });
  }, revealOpts);

  // Observe .reveal, [data-animate], stagger grids, section headings
  document.querySelectorAll(
    '.reveal, [data-animate="fade-up"], .stagger-grid, .section-heading-anim, .shimmer-underline'
  ).forEach(el => revealObserver.observe(el));

  /* ─── Navbar Scroll Effect ──────────────────────────────────── */
  const navbar = document.getElementById('navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 50);
    }, { passive: true });
  }

  /* ─── Animated Counter Numbers ──────────────────────────────── */
  function animateCounter(el, target, duration = 1500) {
    const start = performance.now();
    const isPlus = el.textContent.includes('+');
    const suffix = isPlus ? '+' : '';
    const prefix = el.textContent.includes('₹') ? '₹' : '';

    function update(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased    = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
      const value    = Math.round(eased * target);
      el.textContent = prefix + (value >= 1000 ? (value / 1000).toFixed(1) + 'k' : value) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  const counterObs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const raw = el.textContent.trim();
      // Parse: "5,000+", "10+", "4.9/5"
      const match = raw.match(/[\d,.]+/);
      if (match) {
        const num = parseFloat(match[0].replace(/,/g, ''));
        if (!isNaN(num) && num > 0) animateCounter(el, num);
      }
      counterObs.unobserve(el);
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('.trust-number, .trust-stars').forEach(el => {
    if (/\d/.test(el.textContent)) counterObs.observe(el);
  });

  /* ─── Ripple Effect on Buttons ──────────────────────────────── */
  function addRipple(e) {
    const btn = e.currentTarget;
    if (window.getComputedStyle(btn).position === 'static') {
      btn.style.position = 'relative';
    }
    btn.style.overflow = 'hidden';
    const rect   = btn.getBoundingClientRect();
    const size   = Math.max(rect.width, rect.height) * 1.4;
    const x      = e.clientX - rect.left - size / 2;
    const y      = e.clientY - rect.top  - size / 2;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    Object.assign(ripple.style, {
      width:  size + 'px',
      height: size + 'px',
      left:   x + 'px',
      top:    y + 'px',
    });
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 700);
  }

  document.querySelectorAll(
    '.btn-hero, .btn-wizard-next, .btn-wizard-back, .barber-wheel__select-btn, .ghc-select-btn, .date-chip, .btn-magnetic'
  ).forEach(btn => btn.addEventListener('click', addRipple));

  // Re-apply to dynamically added buttons
  const rippleObserver = new MutationObserver((mutations) => {
    mutations.forEach(m => {
      m.addedNodes.forEach(node => {
        if (node.nodeType !== 1) return;
        node.querySelectorAll('.btn-wizard-next, .btn-wizard-back, .barber-wheel__select-btn, .ghc-select-btn, .date-chip')
          .forEach(btn => btn.addEventListener('click', addRipple));
      });
    });
  });
  rippleObserver.observe(document.body, { childList: true, subtree: true });

  /* ─── Gold Particle Canvas ──────────────────────────────────── */
  const canvas = document.getElementById('particleCanvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    const particles = [];
    const MAX = 30;
    const GOLD_COLORS = ['rgba(212,175,55,', 'rgba(255,215,0,', 'rgba(243,229,171,'];

    function resizeCanvas() {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas, { passive: true });

    function createParticle() {
      const color = GOLD_COLORS[Math.floor(Math.random() * GOLD_COLORS.length)];
      return {
        x: Math.random() * canvas.width,
        y: canvas.height + 10,
        size: Math.random() * 2.5 + 0.5,
        speedY: Math.random() * 0.6 + 0.2,
        speedX: (Math.random() - 0.5) * 0.4,
        opacity: Math.random() * 0.5 + 0.1,
        color,
      };
    }

    for (let i = 0; i < MAX; i++) {
      const p = createParticle();
      p.y = Math.random() * canvas.height;
      particles.push(p);
    }

    function animParticles() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p, idx) => {
        p.y -= p.speedY;
        p.x += p.speedX;
        p.opacity -= 0.0008;
        if (p.y < -10 || p.opacity <= 0) {
          particles[idx] = createParticle();
          return;
        }
        ctx.save();
        ctx.globalAlpha = Math.max(0, p.opacity);
        ctx.fillStyle = p.color + p.opacity + ')';
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });
      requestAnimationFrame(animParticles);
    }
    requestAnimationFrame(animParticles);
  }

  /* ─── Section Reveal for headings ───────────────────────────── */
  document.querySelectorAll('h2.wizard-heading, h2.section-title, .mockup-intro').forEach(el => {
    el.classList.add('reveal');
    revealObserver.observe(el);
  });

  /* ─── Wizard Step Slide Animation ──────────────────────────── */
  // Patch wizardGoTo to add slide transitions
  if (typeof window.wizardGoTo === 'function') {
    const _origWizardGoTo = window.wizardGoTo;
    window.wizardGoTo = function (step) {
      const currentPanel = document.querySelector('.wizard-panel.active');
      if (currentPanel) {
        currentPanel.classList.add('slide-out-left');
      }
      setTimeout(() => {
        _origWizardGoTo(step);
        const newPanel = document.getElementById('wizard-panel-' + step);
        if (newPanel) {
          newPanel.classList.add('slide-in-right');
          setTimeout(() => newPanel.classList.remove('slide-in-right'), 450);
        }
        if (currentPanel) currentPanel.classList.remove('slide-out-left');
      }, 150);
    };
  } else {
    // Try again after scripts load
    window.addEventListener('load', () => {
      if (typeof window.wizardGoTo === 'function') {
        const _orig = window.wizardGoTo;
        window.wizardGoTo = function (step) {
          const currentPanel = document.querySelector('.wizard-panel.active');
          if (currentPanel) currentPanel.classList.add('slide-out-left');
          setTimeout(() => {
            _orig(step);
            const newPanel = document.getElementById('wizard-panel-' + step);
            if (newPanel) {
              newPanel.classList.add('slide-in-right');
              setTimeout(() => newPanel.classList.remove('slide-in-right'), 450);
            }
            if (currentPanel) currentPanel.classList.remove('slide-out-left');
          }, 150);
        };
      }
    });
  }

  /* ─── Magnetic Button Effect ────────────────────────────────── */
  document.querySelectorAll('.btn-magnetic').forEach(btn => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width  / 2;
      const y = e.clientY - rect.top  - rect.height / 2;
      const strength = 0.25;
      btn.style.transform = `translate(${x * strength}px, ${y * strength}px) scale(1.04)`;
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.transform = '';
    });
  });

  /* ─── Barber Card Tilt on Hover ─────────────────────────────── */
  function addTiltEffect(selector) {
    document.querySelectorAll(selector).forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width  - 0.5;
        const y = (e.clientY - rect.top)  / rect.height - 0.5;
        card.style.transform = `perspective(600px) rotateY(${x * 8}deg) rotateX(${-y * 6}deg) scale(1.02)`;
      });
      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
      });
    });
  }
  addTiltEffect('.mockup-service-card');
  addTiltEffect('.gender-hero-card');

  /* ─── Typing Cursor on Hero Eyebrow ─────────────────────────── */
  const eyebrow = document.querySelector('.hero-eyebrow');
  if (eyebrow) {
    const orig = eyebrow.textContent;
    eyebrow.textContent = '';
    let i = 0;
    function typeNext() {
      if (i <= orig.length) {
        eyebrow.textContent = orig.slice(0, i);
        i++;
        setTimeout(typeNext, 60);
      }
    }
    setTimeout(typeNext, 800);
  }

  /* ─── Stagger Grid observer ─────────────────────────────────── */
  const staggerObs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        staggerObs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.stagger-grid').forEach(g => staggerObs.observe(g));

})();
