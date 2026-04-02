/* ============================================
   TC Rot-Weiß Losheim — Main JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  initHeader();
  initScrollReveal();
  initSmoothScroll();
  initMobileNav();
  initCounters();
  initModals();
  initInterestTags();
});

/* === Sticky Header Shrink === */
function initHeader() {
  const header = document.querySelector('.site-header');
  if (!header) return;

  let lastScroll = 0;
  window.addEventListener('scroll', () => {
    const scroll = window.scrollY;
    if (scroll > 60) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
    lastScroll = scroll;
  }, { passive: true });
}

/* === Scroll Reveal Animations === */
function initScrollReveal() {
  const reveals = document.querySelectorAll('.reveal, .reveal-left, .reveal-right');
  if (!reveals.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -40px 0px'
  });

  reveals.forEach(el => observer.observe(el));
}

/* === Smooth Scroll for anchor links === */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#') return;
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const headerH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--header-h'));
        const top = target.getBoundingClientRect().top + window.scrollY - headerH;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });
}

/* === Mobile Navigation === */
function initMobileNav() {
  const toggle = document.querySelector('.mobile-toggle');
  const nav = document.querySelector('.mobile-nav');
  if (!toggle || !nav) return;

  toggle.addEventListener('click', () => {
    toggle.classList.toggle('open');
    nav.classList.toggle('open');
    document.body.style.overflow = nav.classList.contains('open') ? 'hidden' : '';
  });

  nav.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      toggle.classList.remove('open');
      nav.classList.remove('open');
      document.body.style.overflow = '';
    });
  });
}

/* === Animated Counters === */
function initCounters() {
  const counters = document.querySelectorAll('[data-count]');
  if (!counters.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(el => observer.observe(el));
}

function animateCounter(el) {
  const target = parseInt(el.dataset.count);
  const suffix = el.dataset.suffix || '';
  const duration = 2000;
  const start = performance.now();

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.floor(eased * target);
    el.textContent = current + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

/* === Modals === */
function initModals() {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
    }
  });
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('open');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('open');
}

/* === Interest Tags (Contact Form) === */
function initInterestTags() {
  document.querySelectorAll('.interest-tag').forEach(tag => {
    tag.addEventListener('click', () => tag.classList.toggle('active'));
  });
}

/* === Vorstand Modal Data === */
function openVorstandModal(id) {
  const data = {
    moritz: {
      name: 'Moritz Serwe',
      role: '1. Vorsitzender',
      text: 'Moritz leitet den Verein mit Herzblut und hat es sich zum Ziel gesetzt, den TC Losheim fit für die Zukunft zu machen. Wenn er nicht gerade Sitzungen leitet, steht er selbst auf dem Platz.',
      since: 'Im Vorstand seit 2022'
    },
    joerg: {
      name: 'Jörg Mohm',
      role: '2. Vorsitzender',
      text: 'Jörg ist die rechte Hand des Vorsitzenden und sorgt dafür, dass im Hintergrund alles rund läuft. Von Vereinsorganisation bis Platzbelegung — er hat den Überblick.',
      since: ''
    },
    sascha: {
      name: 'Sascha Kuhn',
      role: 'Sportwart',
      text: 'Als Sportwart koordiniert Sascha den gesamten Spielbetrieb — von der Mannschaftsmeldung über den Spielplan bis zur Zusammenarbeit mit dem Saarländischen Tennisbund.',
      since: ''
    },
    constantin: {
      name: 'Constantin Wieber',
      role: 'Jugendwart',
      text: 'Constantin kümmert sich um die Zukunft des Vereins: unsere Kinder und Jugendlichen. Fast 50% unserer Mitglieder sind unter 18 — und das liegt auch an seinem Engagement.',
      since: ''
    },
    kristin: {
      name: 'Kristin Serwe',
      role: 'Pressewartin',
      text: 'Kristin ist die Stimme des TC Losheim nach außen. Website, Instagram, Pressemitteilungen — sie sorgt dafür, dass unsere Geschichten erzählt werden.',
      since: ''
    },
    dobelmann: {
      name: 'Sascha Dobelmann',
      role: 'Schatzmeister',
      text: 'Sascha hält die Finanzen im Griff und sorgt dafür, dass der Verein auf soliden Füßen steht und wir in unsere Anlage und unsere Jugend investieren können.',
      since: ''
    }
  };

  const d = data[id];
  if (!d) return;

  document.getElementById('modal-name').textContent = d.name;
  document.getElementById('modal-role').textContent = d.role;
  document.getElementById('modal-text').textContent = d.text;
  document.getElementById('modal-since').textContent = d.since;
  document.getElementById('modal-since').style.display = d.since ? 'block' : 'none';
  openModal('vorstand-modal');
}
