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

  /* Return visible gallery items sorted by visual grid position (row then column).
     Masonry reorders items via CSS grid-row/grid-column so DOM order != visual order.
     Sorting by computed style ensures prev/next navigation matches what the user sees. */
  function visibleItems() {
    const els = Array.from(document.querySelectorAll('.gallery-item[data-src]'))
      .filter(el => el.style.display !== 'none' && !el._hidden);
    els.sort((a, b) => {
      const sa = getComputedStyle(a), sb = getComputedStyle(b);
      const rowA = parseInt(sa.gridRowStart)    || 0;
      const rowB = parseInt(sb.gridRowStart)    || 0;
      const colA = parseInt(sa.gridColumnStart) || 0;
      const colB = parseInt(sb.gridColumnStart) || 0;
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

  /* Click handler: read data-src directly from the clicked element so the correct
     full-res image opens regardless of DOM vs visual order mismatch. Then find that
     element's position in the visually-sorted list to set current for prev/next. */
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
