// ── Nav logo injection ────────────────────────────────────────────────────────
// If the server injected a logo URL, prepend the logo image to the left of
// the "Ridgecrest Designs" text in every .nav__logo link.
(function() {
  var logoUrl = window.__RD_LOGO_URL;
  if (!logoUrl) return;
  var logoLinks = document.querySelectorAll('a.nav__logo');
  if (!logoLinks.length) return;
  logoLinks.forEach(function(link) {
    var img = document.createElement('img');
    img.src = logoUrl;
    img.alt = 'Ridgecrest Designs logo';
    img.className = 'nav__logo-img';
    link.insertBefore(img, link.firstChild);
  });
})();

// Nav scroll
const nav = document.getElementById('nav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('nav--scrolled', window.scrollY > 60);
  });
}

// Mobile menu toggle
const toggle = document.getElementById('navToggle');
const links = document.getElementById('navLinks');
if (toggle && links) {
  toggle.addEventListener('click', () => {
    links.classList.toggle('nav__links--open');
    toggle.classList.toggle('nav__toggle--open');
  });
  // Close on link click
  links.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      links.classList.remove('nav__links--open');
      toggle.classList.remove('nav__toggle--open');
    });
  });
}

// ── Random hero images ────────────────────────────────────────────────────────
// Curated pool of full-room / architectural shots that look great at hero scale.
// Service pages already have specific inline background-image styles — those are
// left untouched. Only heroes without an existing image get a random one.
const HERO_POOL = [
  'ff5b18_c520c9ca384d4c3ebe02707d0c8f45ab_mv2',  // Danville Hilltop — exterior
  'ff5b18_c1e5fd8a13c34fa985b5b84f87a8f7d1_mv2',  // Lafayette Luxury
  'ff5b18_39536b28ce0447b9a87797bb4c70ee51_mv2',  // Alamo Luxury
  'ff5b18_94919d08fc9245fc849ac03c4ea2caaf_mv2',  // Orinda Kitchen
  'ff5b18_9820c1603a9c414d8cc8009784d1ca7c_mv2',  // Pleasanton Custom
  'ff5b18_296b1e9ff5d14e128006c21217e3f3e9_mv2',  // Sunol Homestead
  'ff5b18_598ba1466dbb45249778e2ea0e0b95e3_mv2',  // Danville navy kitchen
  'ff5b18_d7eb886d364544c1993777e2db5e8bb6_mv2',  // Lafayette white oak kitchen
  'ff5b18_086efaaaac9f44f9bfebafc043e1a7a2_mv2',  // Farmhouse kitchen
  'ff5b18_3c0cef18e48849089c5ed48614041900_mv2',  // Danville Dream whole-home
  'ff5b18_17513c9b8f434b90b64b2762c46f3a45_mv2',  // Sierra Mountain
  'ff5b18_82e5d2a1febd4d1abc6eecd7aadb0101_mv2',  // Sunol Homestead gallery 2
  'ff5b18_53f46b46f9094468addb44305dff0a55_mv2',  // Pleasanton Custom gallery 2
  'ff5b18_75a9ba9c5a87418daf6d2b69c70f60ff_mv2',  // Living room / stone fireplace
  'ff5b18_29ec897c45d74caabd831b08f46ec1bc_mv2',  // Mountain retreat kitchen
  'ff5b18_9192e5d316c84e40b65fff6dbd4d0e36_mv2',  // Custom home office
  'ff5b18_0b10882438704be9af57966897e72b37_mv2',  // Custom library built-ins
  'ff5b18_b246a630ba864e2a8fe67d964745b9b5_mv2',  // Danville Hilltop gallery 2
  'ff5b18_7e0f0e5602694ed280e46ec708e7b068_mv2',  // Danville Hilltop gallery 3
  'ff5b18_63757c728db94733b4f60a7102c0f722_mv2',  // Danville Hilltop gallery 4
  'ff5b18_096e22af570b4c509e3a8b7d085076ee_mv2',  // Alamo gallery
  'ff5b18_b3b82b5920dd48509b6b78c1a91dcaec_mv2',  // Project gallery
  'ff5b18_c0e8f9e9008c498eac5efafae3c46b04_mv2',  // Project gallery
  'ff5b18_d741bf6a821b40e8b4730181bcf0fc48_mv2',  // Project gallery
  'ff5b18_fa8d30d31488413ca93cf28ed74c8e05_mv2',  // Project gallery
];

function randomHeroImage() {
  return HERO_POOL[Math.floor(Math.random() * HERO_POOL.length)];
}

// Helper: apply stored position/zoom to a hero element
function applyHeroTransform(el) {
  if (window.__RD_HERO_POSITION) el.style.backgroundPosition = window.__RD_HERO_POSITION;
  if (window.__RD_HERO_ZOOM && window.__RD_HERO_ZOOM > 1.001)
    el.style.backgroundSize = Math.round(window.__RD_HERO_ZOOM * 100) + '%';
}

// Fixed fallback hero used when DB has no stored image for a page.
// Must be deterministic — never random — so the page looks the same on every load.
const HERO_FALLBACK = `/assets/images-opt/${HERO_POOL[0]}.webp`;

// Inner page heroes (.page-hero--service)
// Use DB-stored hero (window.__RD_HERO) if server injected it; otherwise fixed fallback.
document.querySelectorAll('.page-hero--service').forEach(el => {
  if (!el.style.backgroundImage) {
    const src = window.__RD_HERO || HERO_FALLBACK;
    el.style.backgroundImage = `url('${src}')`;
  }
  applyHeroTransform(el);
});

// Homepage hero (.hero__bg)
// Use DB-stored hero if server injected window.__RD_HERO; otherwise fixed fallback.
const heroBg = document.querySelector('.hero__bg');
if (heroBg) {
  const heroSrc = window.__RD_HERO || HERO_FALLBACK;
  heroBg.style.backgroundImage = `url('${heroSrc}')`;
  applyHeroTransform(heroBg);
}

// Project page heroes (.project-hero__img)
// Image is already set inline by the server; just apply stored position/zoom.
document.querySelectorAll('.project-hero__img').forEach(el => {
  applyHeroTransform(el);
});

// Hero text position — apply stored offset to .hero__content if server injected it
if (window.__RD_HERO_TEXT_X || window.__RD_HERO_TEXT_Y) {
  const tx = window.__RD_HERO_TEXT_X || 0;
  const ty = window.__RD_HERO_TEXT_Y || 0;
  document.querySelectorAll('.hero__content, .page-hero__inner').forEach(el => {
    el.style.transform = `translate(${tx}px, ${ty}px)`;
  });
}

// ── Fade-in on scroll ─────────────────────────────────────────────────────────
// Elements already in the viewport get 'visible' immediately (no flash).
// Elements below the fold start hidden and animate in when scrolled to.
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('visible');
      observer.unobserve(e.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.service-card, .step, .portfolio-card, .portfolio-item, .team-card, .process-step, .value-card').forEach(el => {
  const r = el.getBoundingClientRect();
  if (r.top < window.innerHeight && r.bottom > 0) {
    // Already on screen — mark visible immediately, skip animation
    el.classList.add('fade-in', 'visible');
  } else {
    el.classList.add('fade-in');
    observer.observe(el);
  }
});

// ── [PX] Responsive background-image swap ────────────────────────────────────
// Picks _480w / _960w / _1920w variant based on element width × device pixel ratio.
// Runs on DOMContentLoaded and on resize. Only targets elements with background-image
// pointing to /assets/images-opt/ that have responsive variants on disk.
(function() {
  'use strict';
  var SUFFIXES = ['_1920w', '_960w', '_480w'];
  var BASE_RE = /\/assets\/images-opt\/([^'")\s?]+)\.webp/;

  function _pickVariant(el) {
    var bg = el.style.backgroundImage || '';
    var match = bg.match(BASE_RE);
    if (!match) return;
    var fullName = match[1];

    // Strip any existing width suffix to get the base name
    var baseName = fullName.replace(/_(480|960|1920|201)w$/, '');
    // Don't process if already has the right suffix for this size
    var elWidth = el.offsetWidth * (window.devicePixelRatio || 1);

    var suffix = '_1920w'; // default
    if (elWidth <= 500) suffix = '_480w';
    else if (elWidth <= 1000) suffix = '_960w';

    var newName = baseName + suffix;
    if (newName === fullName) return; // already correct

    var newUrl = '/assets/images-opt/' + newName + '.webp';
    el.style.backgroundImage = bg.replace(
      /\/assets\/images-opt\/[^'")\s?]+\.webp/,
      newUrl
    );
  }

  function _swapAll() {
    document.querySelectorAll('[style]').forEach(function(el) {
      if (el.style.backgroundImage && el.style.backgroundImage.indexOf('/assets/images-opt/') >= 0) {
        _pickVariant(el);
      }
    });
  }

  // Run on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _swapAll);
  } else {
    _swapAll();
  }

  // Run on resize (debounced)
  var _resizeTimer;
  window.addEventListener('resize', function() {
    clearTimeout(_resizeTimer);
    _resizeTimer = setTimeout(_swapAll, 300);
  });
})();

// ── Diff visual split mode ─────────────────────────────────────────────────
// Apply the correct panel-count class from the server-injected mode variable.
(function() {
  var mode = window.__RD_DIFF_MODE || 'one';
  var vis = document.querySelector('.diff__visual');
  if (!vis) return;
  vis.classList.remove('diff__visual--one', 'diff__visual--two');
  vis.classList.add('diff__visual--' + mode);
})();
