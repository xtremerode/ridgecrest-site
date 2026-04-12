/* ============================================================
   Gallery Admin — Drag-to-resize
   Active when URL contains ?admin=1
   Extends gallery.js engine positions.
   ============================================================ */
(function () {
  'use strict';

  if (!/[?&]admin=1/.test(location.search)) return;

  const GAP = (window.GalleryEngine || {}).GAP || 6;

  /* ── Wait for gallery to be ready, then activate ── */
  function activate(container) {
    const slug = container.dataset.project || '';
    let   dirty = false;

    /* floating Save button */
    const saveBtn = document.createElement('button');
    saveBtn.className = 'gallery-admin-save';
    saveBtn.textContent = 'Save Layout';
    document.body.appendChild(saveBtn);

    /* add resize handles to every gallery-item */
    function addHandles(item) {
      if (item.querySelector('.gallery-resize-h')) return; // already added
      item.classList.add('gallery-item--resizable');

      const hHandle = document.createElement('div');
      hHandle.className = 'gallery-resize-h';
      hHandle.title = 'Drag to resize width';

      const vHandle = document.createElement('div');
      vHandle.className = 'gallery-resize-v';
      vHandle.title = 'Drag to resize height';

      item.appendChild(hHandle);
      item.appendChild(vHandle);

      /* ── horizontal resize (right edge) ── */
      hHandle.addEventListener('mousedown', e => {
        e.preventDefault();
        e.stopPropagation();

        const startX  = e.clientX;
        const startW  = parseInt(item.style.width) || item.offsetWidth;
        const startL  = parseInt(item.style.left)  || 0;

        /* find the item to the right (closest left edge > this item's right edge) */
        const myRight = startL + startW;
        let neighbor  = null;
        let neighborStartW = 0;
        let neighborStartL = 0;

        for (const el of container.querySelectorAll('.gallery-item')) {
          if (el === item) continue;
          const nLeft = parseInt(el.style.left) || 0;
          if (Math.abs(nLeft - (myRight + GAP)) < 20) {
            neighbor = el;
            neighborStartW = parseInt(el.style.width) || el.offsetWidth;
            neighborStartL = nLeft;
            break;
          }
        }

        function onMove(me) {
          const dx = me.clientX - startX;
          let newW = Math.max(80, startW + dx);

          if (neighbor) {
            /* adjust neighbor: shrink or grow to compensate */
            const neighborW = Math.max(80, neighborStartW - dx);
            /* reposition neighbor left edge */
            const newRight = startL + newW + GAP;
            neighbor.style.width = neighborW + 'px';
            neighbor.style.left  = newRight + 'px';
          }
          item.style.width = newW + 'px';
          dirty = true;
        }

        function onUp() {
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup',   onUp);
        }

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup',   onUp);
      });

      /* ── vertical resize (bottom edge) ── */
      vHandle.addEventListener('mousedown', e => {
        e.preventDefault();
        e.stopPropagation();

        const startY = e.clientY;
        const startH = parseInt(item.style.height) || item.offsetHeight;
        const myTop  = parseInt(item.style.top) || 0;
        const myBot  = myTop + startH;

        /* find items whose top edge aligns with this item's bottom + GAP */
        const below = [];
        for (const el of container.querySelectorAll('.gallery-item')) {
          if (el === item) continue;
          const eTop = parseInt(el.style.top) || 0;
          if (Math.abs(eTop - (myBot + GAP)) < 20) below.push(el);
        }
        const belowStartTops = below.map(el => parseInt(el.style.top) || 0);

        function onMove(me) {
          const dy   = me.clientY - startY;
          const newH = Math.max(60, startH + dy);
          item.style.height = newH + 'px';
          /* shift everything below down/up accordingly */
          const delta = newH - startH;
          below.forEach((el, i) => {
            el.style.top = (belowStartTops[i] + delta) + 'px';
          });
          /* update container height */
          let maxBottom = 0;
          for (const el of container.querySelectorAll('.gallery-item, .gallery-divider')) {
            const t = parseInt(el.style.top)    || 0;
            const h = parseInt(el.style.height) || 0;
            if (t + h > maxBottom) maxBottom = t + h;
          }
          container.style.height = maxBottom + 'px';
          dirty = true;
        }

        function onUp() {
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup',   onUp);
        }

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup',   onUp);
      });
    }

    /* attach handles to existing items and watch for new ones */
    container.querySelectorAll('.gallery-item').forEach(addHandles);
    new MutationObserver(mutations => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node.classList && node.classList.contains('gallery-item')) addHandles(node);
        }
      }
    }).observe(container, { childList: true });

    /* ── Save layout — proxied through parent admin frame (no client-side token) ── */
    saveBtn.addEventListener('click', () => {
      const layout = {};
      for (const el of container.querySelectorAll('.gallery-item')) {
        const hash = el.dataset.hash;
        if (!hash) continue;
        layout[hash] = {
          left:   parseInt(el.style.left)   || 0,
          top:    parseInt(el.style.top)    || 0,
          width:  parseInt(el.style.width)  || 0,
          height: parseInt(el.style.height) || 0,
        };
      }
      saveBtn.textContent = 'Saving…';
      window.parent.postMessage({ type: 'rd_gallery_save', slug, layout }, window.location.origin);
    });

    /* Listen for save result from parent admin frame */
    window.addEventListener('message', (e) => {
      if (e.origin !== window.location.origin) return;
      if (!e.data || e.data.type !== 'rd_gallery_save_result') return;
      if (e.data.ok) {
        saveBtn.textContent = 'Saved ✓';
        dirty = false;
        setTimeout(() => { saveBtn.textContent = 'Save Layout'; }, 2500);
      } else {
        saveBtn.textContent = 'Error — retry';
      }
    });

    /* warn on unsaved changes */
    window.addEventListener('beforeunload', e => {
      if (dirty) { e.preventDefault(); e.returnValue = ''; }
    });
  }

  /* wait until gallery-brick--ready */
  function waitAndActivate() {
    const container = document.querySelector('.gallery-brick');
    if (!container) return;
    if (container.classList.contains('gallery-brick--ready')) {
      activate(container);
    } else {
      const ob = new MutationObserver(() => {
        if (container.classList.contains('gallery-brick--ready')) {
          ob.disconnect();
          activate(container);
        }
      });
      ob.observe(container, { attributes: true, attributeFilter: ['class'] });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitAndActivate);
  } else {
    waitAndActivate();
  }

})();
