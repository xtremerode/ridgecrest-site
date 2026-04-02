/* gallery.js — Ridgecrest Designs
 * True masonry grid layout for .gallery-masonry containers.
 *
 * Guarantees:
 *   - Consistent 4px gap between every image in all directions
 *   - Variable-height brick pattern (shortest-column placement, no 4-corner alignments)
 *   - Each sorted section starts and ends flush across all columns
 *   - Responsive: recalculates on window resize
 *
 * Requires CSS:
 *   .gallery-masonry { display:grid; grid-template-columns:repeat(3,1fr);
 *                      grid-auto-rows:4px; gap:4px }
 *   .gallery-masonry--js .gallery-item img { height:100%; object-fit:cover }
 */
(function () {
  'use strict';

  var GAP        = 4;   /* px — must match CSS gap */
  var ROW_UNIT   = 4;   /* px — must match CSS grid-auto-rows */
  var LABEL_SPAN = 8;   /* grid rows reserved for each .gallery-section-label (~60px) */

  /* Deterministic pseudo-random variation per item index: [0.80, 1.20]
   * Stable across reloads so layout never shuffles unexpectedly. */
  function variation(index) {
    var h = Math.imul(index + 1, 0x9E3779B9) >>> 0;
    h = Math.imul(h ^ (h >>> 16), 0x85EBCA6B) >>> 0;
    h = Math.imul(h ^ (h >>> 13), 0xC2B2AE35) >>> 0;
    h = (h ^ (h >>> 16)) >>> 0;
    return 0.80 + (h % 10000) / 10000 * 0.40;
  }

  /* Desired pixel height → number of grid row spans */
  function px2span(px) {
    return Math.max(2, Math.round((px + GAP) / (ROW_UNIT + GAP)));
  }

  /* Index of the column with the smallest current height */
  function shortestCol(heights) {
    var min = heights[0], idx = 0;
    for (var i = 1; i < heights.length; i++) {
      if (heights[i] < min) { min = heights[i]; idx = i; }
    }
    return idx;
  }

  /* Column count — mirrors CSS media queries exactly */
  function getCols() {
    var w = window.innerWidth;
    if (w <= 480) return 1;
    if (w <= 768) return 2;
    return 3;
  }

  function layoutGrid(grid) {
    var cols      = getCols();
    var gridWidth = grid.clientWidth;
    if (!gridWidth) return;
    var colWidth = (gridWidth - (cols - 1) * GAP) / cols;

    /* Per-column tracking (row numbers are 1-based; 0 = nothing placed yet) */
    var colH      = new Array(cols).fill(0);  /* last occupied row in each col */
    var lastEl    = new Array(cols).fill(null);
    var lastStart = new Array(cols).fill(1);
    var lastSpan  = new Array(cols).fill(0);

    /* Stretch the last item in each short column to reach maxRow */
    function equalize() {
      var maxH = 0, c;
      for (c = 0; c < cols; c++) if (colH[c] > maxH) maxH = colH[c];
      for (c = 0; c < cols; c++) {
        if (colH[c] < maxH && lastEl[c]) {
          var newSpan = lastSpan[c] + (maxH - colH[c]);
          lastEl[c].style.gridRow = lastStart[c] + ' / span ' + newSpan;
        }
        colH[c] = maxH;  /* advance all columns — including empty ones */
      }
      return maxH;
    }

    var itemIdx  = 0;
    var children = grid.children;

    for (var i = 0; i < children.length; i++) {
      var child = children[i];

      /* ── Section divider: equalize columns, place label, reset state ── */
      if (child.classList.contains('gallery-section-label')) {
        var maxH       = equalize();
        var labelStart = maxH > 0 ? maxH + 1 : 1;
        child.style.gridColumn = '1 / -1';
        child.style.gridRow    = labelStart + ' / span ' + LABEL_SPAN;
        var afterLabel = labelStart + LABEL_SPAN - 1;
        for (var c = 0; c < cols; c++) {
          colH[c]      = afterLabel;
          lastEl[c]    = null;
          lastSpan[c]  = 0;
        }
        continue;
      }

      /* ── Gallery image item ── */
      if (!child.classList.contains('gallery-item')) continue;

      var img    = child.querySelector('img');
      var iw     = img ? (parseInt(img.getAttribute('width'),  10) || 0) : 0;
      var ih     = img ? (parseInt(img.getAttribute('height'), 10) || 0) : 0;
      var aspect = (iw && ih) ? iw / ih : 1.333;  /* fallback: landscape 4:3 */

      var baseH   = colWidth / aspect;
      /* Clamp: never shorter than 35% of column width, never taller than 150%.
       * Prevents ultra-portrait images from dominating and panoramics from collapsing. */
      var targetH = Math.min(Math.max(baseH * variation(itemIdx),
                                      colWidth * 0.35),
                             colWidth * 1.50);
      var span    = px2span(targetH);

      var col      = shortestCol(colH);
      var startRow = colH[col] + 1;

      child.style.gridColumn = (col + 1).toString();
      child.style.gridRow    = startRow + ' / span ' + span;

      colH[col]      = startRow + span - 1;
      lastEl[col]    = child;
      lastStart[col] = startRow;
      lastSpan[col]  = span;
      itemIdx++;
    }

    /* Equalize the final section bottom */
    equalize();

    /* Switch images to cover-fill mode — fires after explicit spans are set */
    grid.classList.add('gallery-masonry--js');
  }

  function layoutAll() {
    var grids = document.querySelectorAll('.gallery-masonry');
    for (var g = 0; g < grids.length; g++) layoutGrid(grids[g]);
  }

  /* Debounced resize: recalculate when viewport changes */
  var _rt;
  window.addEventListener('resize', function () {
    clearTimeout(_rt);
    _rt = setTimeout(layoutAll, 150);
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', layoutAll);
  } else {
    layoutAll();
  }

  /* Expose for external callers (e.g. admin overlay after image delete) */
  window.GalleryEngine = window.GalleryEngine || {};
  window.GalleryEngine.layoutAll = layoutAll;
})();
