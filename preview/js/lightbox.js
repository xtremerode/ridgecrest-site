// Lightbox for project gallery pages
(function() {
  const lb = document.getElementById('lightbox');
  if (!lb) return;

  const lbImg = lb.querySelector('.lightbox__img');
  const lbClose = lb.querySelector('.lightbox__close');
  const lbPrev = lb.querySelector('.lightbox__prev');
  const lbNext = lb.querySelector('.lightbox__next');
  const lbCounter = lb.querySelector('.lightbox__counter');

  const items = Array.from(document.querySelectorAll('.gallery-item[data-src]'));
  let current = 0;

  function open(idx) {
    current = idx;
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

  function prev() { open((current - 1 + items.length) % items.length); }
  function next() { open((current + 1) % items.length); }

  items.forEach((el, i) => el.addEventListener('click', () => open(i)));
  lbClose.addEventListener('click', close);
  lbPrev.addEventListener('click', prev);
  lbNext.addEventListener('click', next);
  lb.addEventListener('click', (e) => { if (e.target === lb) close(); });

  document.addEventListener('keydown', (e) => {
    if (!lb.classList.contains('active')) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowLeft') prev();
    if (e.key === 'ArrowRight') next();
  });
})();
