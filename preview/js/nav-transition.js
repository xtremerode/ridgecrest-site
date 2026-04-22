// ── Hero pre-warm on navigation ───────────────────────────────────────────────
// When the user hovers over a nav link, immediately start downloading that
// page's hero image so it's in cache (or partially loaded) before they click.
//
// The primary flash fix is CSS injection in <head> by the server — this script
// is a bonus layer that pre-warms the cache for the NEXT page before navigation.
//
// window.__RD_HERO_MAP is injected by the server: { "/view/page.html": "/assets/..." }
(function () {
  'use strict';

  // Don't activate on admin dashboard pages (they have no hero map)
  if (window.location.pathname.indexOf('/admin') !== -1) return;

  var heroMap = window.__RD_HERO_MAP || {};
  var preloaded = {};  // url → Image object (keeps reference in memory = stays cached)

  function heroUrlFor(href) {
    try {
      var path = new URL(href, window.location.href).pathname;
      // Normalize: /view/ prefix, .html optional
      if (heroMap[path]) return heroMap[path];
      if (path.slice(-5) !== '.html' && heroMap[path + '.html']) return heroMap[path + '.html'];
      if (path.slice(-5) === '.html' && heroMap[path.slice(0, -5)]) return heroMap[path.slice(0, -5)];
    } catch (e) {}
    return null;
  }

  function isInternalLink(a) {
    if (!a || !a.href) return false;
    if (a.target === '_blank') return false;
    if (a.getAttribute('href') && a.getAttribute('href').charAt(0) === '#') return false;
    try {
      return new URL(a.href).host === window.location.host;
    } catch (e) { return false; }
  }

  function preloadHero(heroSrc) {
    if (!heroSrc || preloaded[heroSrc]) return;
    var img = new Image();
    img.src = heroSrc;
    preloaded[heroSrc] = img;  // hold reference → stays in browser cache
  }

  // On hover: start downloading the hero image for the link destination
  document.addEventListener('mouseover', function (e) {
    var a = e.target.closest ? e.target.closest('a[href]') : null;
    if (!a || !isInternalLink(a)) return;
    var heroSrc = heroUrlFor(a.href);
    if (heroSrc) preloadHero(heroSrc);
  }, { passive: true });

  // On touchstart (mobile): same as hover intent
  document.addEventListener('touchstart', function (e) {
    var a = e.target.closest ? e.target.closest('a[href]') : null;
    if (!a || !isInternalLink(a)) return;
    var heroSrc = heroUrlFor(a.href);
    if (heroSrc) preloadHero(heroSrc);
  }, { passive: true });

})();
