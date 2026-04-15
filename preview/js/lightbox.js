// Lightbox for project gallery pages
// Filter-aware: only navigates currently visible gallery items
(function() {
  const lb = document.getElementById('lightbox');
  if (!lb) return;

  const lbImg     = lb.querySelector('.lightbox__img');
  const lbClose   = lb.querySelector('.lightbox__close');
  const lbPrev    = lb.querySelector('.lightbox__prev');
  const lbNext    = lb.querySelector('.lightbox__next');
  const lbCounter = lb.querySelector('.lightbox__counter');

  let current = 0;

  /* Return visible gallery items sorted by visual grid position.
     gallery.js sets inline style.gridColumn (e.g. "2") and style.gridRow
     (e.g. "14 / span 6") — parseInt of each gives the real masonry position. */
  function visibleItems() {
    const els = Array.from(document.querySelectorAll('.gallery-item[data-src]'))
      .filter(el => el.style.display !== 'none' && !el._hidden);
    els.sort((a, b) => {
      const rowA = parseInt(a.style.gridRow)    || 0;
      const rowB = parseInt(b.style.gridRow)    || 0;
      const colA = parseInt(a.style.gridColumn) || 0;
      const colB = parseInt(b.style.gridColumn) || 0;
      return rowA !== rowB ? rowA - rowB : colA - colB;
    });
    return els;
  }

  function open(idx) {
    const items = visibleItems();
    if (!items.length) return;
    current = ((idx % items.length) + items.length) % items.length;
    lbImg.src = items[current].dataset.src;
    lbCounter.textContent = `${current + 1} / ${items.length}`;
    lb.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    lb.classList.remove('active');
    document.body.style.overflow = '';
    lbImg.src = '';
  }

  function prev() { open(current - 1); }
  function next() { open(current + 1); }

  /* Click handler: read data-src directly from the clicked element — correct image
     opens regardless of DOM vs visual order. Index into sorted list sets current
     so prev/next navigation continues from the right position. */
  document.addEventListener('click', e => {
    const item = e.target.closest('.gallery-item[data-src]');
    if (!item || item._hidden || item.style.display === 'none') return;
    if (e.target.classList.contains('gallery-resize-h') ||
        e.target.classList.contains('gallery-resize-v')) return;
    const items = visibleItems();
    const idx = items.indexOf(item);
    current = idx >= 0 ? idx : 0;
    lbImg.src = item.dataset.src;
    lbCounter.textContent = `${current + 1} / ${items.length}`;
    lb.classList.add('active');
    document.body.style.overflow = 'hidden';
  });

  lbClose.addEventListener('click', close);
  lbPrev.addEventListener('click', prev);
  lbNext.addEventListener('click', next);
  lb.addEventListener('click', e => { if (e.target === lb) close(); });

  document.addEventListener('keydown', e => {
    if (!lb.classList.contains('active')) return;
    if (e.key === 'Escape')     close();
    if (e.key === 'ArrowLeft')  prev();
    if (e.key === 'ArrowRight') next();
  });
})();
