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

  /* Return only gallery items that are currently visible */
  function visibleItems() {
    return Array.from(document.querySelectorAll('.gallery-item[data-src]'))
      .filter(el => el.style.display !== 'none' && !el._hidden);
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

  /* delegate click — works after JS repositioning */
  document.addEventListener('click', e => {
    const item = e.target.closest('.gallery-item[data-src]');
    if (!item || item._hidden || item.style.display === 'none') return;
    if (e.target.classList.contains('gallery-resize-h') ||
        e.target.classList.contains('gallery-resize-v')) return;
    const idx = visibleItems().indexOf(item);
    if (idx >= 0) open(idx);
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
