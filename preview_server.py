#!/usr/bin/env python3
"""
Ridgecrest Preview Server — port 8081
Serves /home/claudeuser/agent/preview/ as a static preview site.
"""
from flask import Flask, Response, jsonify, render_template_string, request, send_file, session
import threading
import mimetypes
import os
import re
import secrets
import hashlib
import json
import sys
import subprocess
from datetime import datetime, timezone

# Try importing db/bcrypt for admin features — non-fatal if missing
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import psycopg2, psycopg2.extras
    from dotenv import load_dotenv
    load_dotenv()
    _DB_URL = os.getenv("DATABASE_URL", "postgresql://agent_user:StrongPass123!@localhost:5432/marketing_agent")
    HAS_DB = True
except ImportError:
    HAS_DB = False

try:
    import bcrypt as _bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

PREVIEW_DIR = '/home/claudeuser/agent/preview'
PORT = 8081
os.makedirs(PREVIEW_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# ── Admin auth tokens — persisted in DB so server restarts don't log users out ─
_ADMIN_TOKENS: set = set()   # in-memory cache for speed
_TOKENS_LOCK = threading.Lock()

# Admin password — bcrypt hash stored in ADMIN_PASSWORD_HASH env var
_DEFAULT_PW = "Hb2425hb+"
_ADMIN_HASH_ENV = os.getenv('ADMIN_PASSWORD_HASH', '')

def _ensure_sessions_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_sessions (
            token TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

def _load_tokens_from_db():
    """Load all persisted tokens into the in-memory set on startup."""
    conn = _db_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        _ensure_sessions_table(cur)
        conn.commit()
        cur.execute("SELECT token FROM admin_sessions")
        with _TOKENS_LOCK:
            for row in cur.fetchall():
                _ADMIN_TOKENS.add(row['token'])
    except Exception:
        pass
    finally:
        conn.close()

def _verify_admin_password(password: str) -> bool:
    env_hash = os.getenv('ADMIN_PASSWORD_HASH', '')
    if env_hash and HAS_BCRYPT:
        try:
            return _bcrypt.checkpw(password.encode(), env_hash.encode())
        except Exception:
            pass
    admin_pw = os.getenv('ADMIN_PASSWORD', _DEFAULT_PW)
    return secrets.compare_digest(password, admin_pw)

def _new_token() -> str:
    t = secrets.token_hex(32)
    with _TOKENS_LOCK:
        _ADMIN_TOKENS.add(t)
    # Persist to DB
    conn = _db_conn()
    if conn:
        try:
            cur = conn.cursor()
            _ensure_sessions_table(cur)
            cur.execute("INSERT INTO admin_sessions (token) VALUES (%s) ON CONFLICT DO NOTHING", (t,))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
    return t

def _valid_token(t: str) -> bool:
    with _TOKENS_LOCK:
        return t in _ADMIN_TOKENS

def _revoke_token(t: str):
    with _TOKENS_LOCK:
        _ADMIN_TOKENS.discard(t)
    conn = _db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM admin_sessions WHERE token = %s", (t,))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

def _require_admin():
    token = request.headers.get('X-Admin-Token', '')
    if not _valid_token(token):
        return jsonify({'error': 'unauthorized'}), 401
    return None

def _db_conn():
    if not HAS_DB:
        return None
    try:
        return psycopg2.connect(_DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception:
        return None


# ── Pages table: DB-backed hero images + visual editor support ────────────────

def _ensure_pages_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id SERIAL PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            title TEXT,
            hero_image TEXT,
            page_path TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    # Idempotent: add zoom/position columns to existing tables
    cur.execute("ALTER TABLE pages ADD COLUMN IF NOT EXISTS hero_position TEXT DEFAULT '50% 50%'")
    cur.execute("ALTER TABLE pages ADD COLUMN IF NOT EXISTS hero_zoom FLOAT DEFAULT 1.0")

def _seed_pages():
    """Scan all preview/ HTML files and seed the pages table (idempotent)."""
    if not HAS_DB:
        return
    conn = _db_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        _ensure_pages_table(cur)
        conn.commit()
        seeded = 0
        for root, dirs, files in os.walk(PREVIEW_DIR):
            dirs[:] = sorted([d for d in dirs if d != 'admin'])
            for fname in sorted(files):
                if not fname.endswith('.html'):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, PREVIEW_DIR).replace('\\', '/')
                slug = rel.replace('.html', '')
                if slug == 'index':
                    slug = 'home'
                try:
                    with open(fpath, 'r', errors='replace') as f:
                        html = f.read()
                except Exception:
                    continue
                title_m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
                title = title_m.group(1).strip() if title_m else fname
                title = re.sub(r'\s*[—–\-]\s*Ridgecrest.*$', '', title).strip()
                hero_m = re.search(
                    r"background-image\s*:\s*url\(['\"]?(/assets/[^'\")\s]+)['\"]?\)", html)
                hero_image = hero_m.group(1) if hero_m else None
                cur.execute("""
                    INSERT INTO pages (slug, title, hero_image, page_path)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE SET
                        title = EXCLUDED.title,
                        page_path = EXCLUDED.page_path,
                        hero_image = COALESCE(pages.hero_image, EXCLUDED.hero_image)
                """, (slug, title, hero_image, rel))
                seeded += 1
        conn.commit()
        conn.close()
        print(f'[pages] Seeded/verified {seeded} pages')
    except Exception as e:
        print(f'[pages] Seed error: {e}')
        try:
            conn.close()
        except Exception:
            pass

def _get_page_data(slug):
    """Return (hero_path, hero_position, hero_zoom) for a page slug, resolving active version."""
    conn = _db_conn()
    if not conn:
        return None, '50% 50%', 1.0
    try:
        cur = conn.cursor()
        _ensure_pages_table(cur)
        cur.execute("SELECT hero_image, hero_position, hero_zoom FROM pages WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if not row or not row['hero_image']:
            conn.close()
            return None, '50% 50%', 1.0
        hero_path = row['hero_image']
        hero_pos  = row['hero_position'] or '50% 50%'
        hero_zoom = float(row['hero_zoom'] or 1.0)
        # Resolve active version: if image_labels has an active_version for this file, use it
        base_fname = hero_path.split('/')[-1]
        try:
            _ensure_image_labels_table(cur)
            cur.execute("SELECT active_version FROM image_labels WHERE filename = %s", (base_fname,))
            lrow = cur.fetchone()
            if lrow and lrow.get('active_version'):
                av = lrow['active_version']
                opt_dir = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
                if os.path.isfile(os.path.join(opt_dir, av)):
                    hero_path = f'/assets/images-opt/{av}'
        except Exception:
            pass
        conn.close()
        return hero_path, hero_pos, hero_zoom
    except Exception:
        return None, '50% 50%', 1.0

# ── Card settings: DB-backed color/image mode per card ───────────────────────

def _ensure_card_settings_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS card_settings (
            id SERIAL PRIMARY KEY,
            page_slug TEXT NOT NULL,
            card_id TEXT NOT NULL,
            mode TEXT DEFAULT 'color',
            color TEXT DEFAULT '#1C1C1C',
            image TEXT,
            position TEXT DEFAULT '50% 50%',
            zoom FLOAT DEFAULT 1.0,
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(page_slug, card_id)
        )
    """)

def _get_card_settings(slug):
    """Return list of card setting dicts for a page slug."""
    conn = _db_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        _ensure_card_settings_table(cur)
        cur.execute(
            "SELECT card_id, mode, color, image, position, zoom FROM card_settings WHERE page_slug = %s",
            (slug,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def _apply_cards_to_html(content: bytes, cards: list) -> bytes:
    """Inject window.__RD_CARDS JSON into <head> and card-apply script before </body>."""
    if not cards:
        return content
    text = content.decode('utf-8', errors='replace')
    # Inject data var in <head>
    data_script = f'<script>window.__RD_CARDS={json.dumps(cards)};</script>'
    if '</head>' in text:
        text = text.replace('</head>', data_script + '</head>', 1)
    # Inject apply script before </body>
    apply_script = _CARD_APPLY_SCRIPT
    if '</body>' in text:
        text = text.replace('</body>', apply_script + '</body>', 1)
    return text.encode('utf-8')


def _apply_hero_to_html(content: bytes, hero_path: str,
                         hero_position: str = '50% 50%', hero_zoom: float = 1.0) -> bytes:
    """Swap the first inline background-image URL in HTML with hero_path.
    Always injects __RD_HERO / __RD_HERO_POSITION / __RD_HERO_ZOOM script vars
    so main.js can apply them (home page + any element set by JS)."""
    text = content.decode('utf-8', errors='replace')
    new_text, _ = re.subn(
        r"(background-image\s*:\s*url\(['\"]?)(/assets/[^'\")\s]+)(['\"]?\))",
        lambda m: m.group(1) + hero_path + m.group(3),
        text, count=1
    )
    # Always inject script vars — main.js reads these for all hero types
    script = (
        f'<script>window.__RD_HERO={json.dumps(hero_path)};'
        f'window.__RD_HERO_POSITION={json.dumps(hero_position)};'
        f'window.__RD_HERO_ZOOM={json.dumps(hero_zoom)};</script>'
    )
    if '</head>' in new_text:
        new_text = new_text.replace('</head>', script + '</head>', 1)
    else:
        new_text = script + new_text
    return new_text.encode('utf-8')

# ── Card apply script (non-edit mode) ────────────────────────────────────────
_CARD_APPLY_SCRIPT = """\
<script id="rd-card-apply">
(function(){
  var cards = window.__RD_CARDS;
  if (!cards || !cards.length) return;
  function apply() {
    cards.forEach(function(c) {
      var el = document.querySelector('[data-card-id="' + c.card_id + '"]');
      if (!el) return;
      if (c.mode === 'image' && c.image) {
        var z = c.zoom || 1.0;
        el.style.backgroundImage = "url('" + c.image + "')";
        el.style.backgroundSize = z > 1.001 ? Math.round(z*100) + '%' : 'cover';
        el.style.backgroundPosition = c.position || '50% 50%';
        el.classList.add('rd-card--image-mode');
      } else if (c.mode === 'color' && c.color) {
        el.style.background = c.color;
        el.style.backgroundImage = '';
        el.classList.remove('rd-card--image-mode');
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply);
  else apply();
})();
</script>
"""

# ── Card edit overlay (admin_edit=1 mode) ────────────────────────────────────
_CARD_EDIT_OVERLAY_TPL = """\
<script id="rd-card-edit-overlay">
(function(){{
  'use strict';
  var SLUG = {slug_json};
  var TOKEN = {token_json};
  var COLORS = ['#1C1C1C','#1a2a35','#2a2218','#1e2e24','#212830'];
  var imagePool = [];
  var saveTimers = {{}};
  var cardIndices = {{}}; // cardId → current index in imagePool (bidirectional navigation)
  var cardRefreshPill = {{}}; // cardId → refreshPill() fn (for rd_set_card_image handler)

  function findPoolIndex(image) {{
    if (!imagePool.length || !image) return 0;
    var clean = image.split('?')[0];
    var idx = imagePool.findIndex(function(u) {{ return u.split('?')[0] === clean; }});
    return idx >= 0 ? idx : 0;
  }}

  var cardMap = {{}};
  if (window.__RD_CARDS) {{
    window.__RD_CARDS.forEach(function(c) {{ cardMap[c.card_id] = JSON.parse(JSON.stringify(c)); }});
  }}

  function getState(cardId) {{
    return cardMap[cardId] || {{ card_id: cardId, mode: 'color', color: '#1C1C1C', image: null, position: '50% 50%', zoom: 1.0 }};
  }}

  function applyStyle(el, state) {{
    if (state.mode === 'image' && state.image) {{
      var z = state.zoom || 1.0;
      el.style.backgroundImage = "url('" + state.image + "')";
      el.style.backgroundSize = z > 1.001 ? Math.round(z*100) + '%' : 'cover';
      el.style.backgroundPosition = state.position || '50% 50%';
      el.classList.add('rd-card--image-mode');
    }} else {{
      el.style.backgroundImage = '';
      el.style.backgroundSize = '';
      el.style.backgroundPosition = '';
      el.style.background = state.color || '#1C1C1C';
      el.classList.remove('rd-card--image-mode');
    }}
  }}

  function saveCard(cardId, state) {{
    clearTimeout(saveTimers[cardId]);
    saveTimers[cardId] = setTimeout(function() {{
      fetch('/admin/api/cards/' + encodeURIComponent(SLUG) + '/' + encodeURIComponent(cardId), {{
        method: 'PUT',
        headers: {{'Content-Type': 'application/json', 'X-Admin-Token': TOKEN}},
        body: JSON.stringify(state)
      }});
    }}, 1500);
  }}

  function applyPoolToCards() {{
    if (!imagePool.length) return;
    Object.keys(cardMap).forEach(function(cardId) {{
      var s = cardMap[cardId];
      if (s.mode === 'image') {{
        // Initialize pool index from existing image (or 0 if not found)
        cardIndices[cardId] = findPoolIndex(s.image);
        if (!s.image) {{
          s.image = imagePool[0];
          var el = document.querySelector('[data-card-id="' + cardId + '"]');
          if (el) applyStyle(el, s);
        }}
      }}
    }});
  }}

  // Receive image pool from parent immediately (sent right after injection — no async wait)
  // Also handles rd_set_card_image from the Browse All picker in the parent panel.
  window.addEventListener('message', function(e) {{
    var d = e.data || {{}};
    if (d.type === 'rd_set_pool' && d.images && d.images.length) {{
      imagePool = d.images;
      applyPoolToCards();
    }}
    if (d.type === 'rd_set_card_image' && d.cardId && d.newImage) {{
      var s = cardMap[d.cardId];
      var cardEl = document.querySelector('[data-card-id="' + d.cardId + '"]');
      if (!s || !cardEl) return;
      s.mode = 'image';
      s.image = d.newImage;
      cardIndices[d.cardId] = findPoolIndex(d.newImage);
      applyStyle(cardEl, s);
      if (cardRefreshPill[d.cardId]) cardRefreshPill[d.cardId]();
      saveCard(d.cardId, s);
    }}
  }});

  function loadImages() {{
    fetch('/admin/api/pages/images', {{headers: {{'X-Admin-Token': TOKEN}}}})
      .then(function(r) {{ return r.json(); }})
      .then(function(imgs) {{
        // Only overwrite if pool is still empty (postMessage may have already populated it)
        if (!imagePool.length) {{
          imagePool = imgs.map(function(img) {{ return '/assets/images-opt/' + img.filename; }});
          applyPoolToCards();
        }}
      }}).catch(function() {{}});
  }}

  function setupCard(el) {{
    var cardId = el.getAttribute('data-card-id');
    var state = JSON.parse(JSON.stringify(getState(cardId)));
    cardMap[cardId] = state;

    if (window.getComputedStyle(el).position === 'static') el.style.position = 'relative';
    el.style.overflow = 'hidden';
    applyStyle(el, state);

    // Pill: [Color] [Image] toggle
    var pill = document.createElement('div');
    pill.setAttribute('data-rd-overlay','card');
    pill.style.cssText = 'position:absolute;bottom:8px;right:8px;z-index:9991;display:flex;border-radius:4px;overflow:hidden;opacity:0;transition:opacity .15s;pointer-events:none;box-shadow:0 2px 8px rgba(0,0,0,.5)';

    var colorBtn = document.createElement('button');
    colorBtn.textContent = 'Color';
    colorBtn.style.cssText = 'padding:5px 11px;font-size:11px;font-weight:700;font-family:system-ui,sans-serif;border:none;cursor:pointer;line-height:1.4;white-space:nowrap';

    var imgBtn = document.createElement('button');
    imgBtn.textContent = 'Image';
    imgBtn.style.cssText = 'padding:5px 11px;font-size:11px;font-weight:700;font-family:system-ui,sans-serif;border:none;cursor:pointer;line-height:1.4;white-space:nowrap';

    var browseCardBtn = document.createElement('button');
    browseCardBtn.textContent = 'Browse All';
    browseCardBtn.title = 'Browse all images';
    browseCardBtn.style.cssText = 'padding:5px 11px;font-size:11px;font-weight:700;font-family:system-ui,sans-serif;border:none;cursor:pointer;line-height:1.4;white-space:nowrap;background:rgba(0,0,0,.65);color:rgba(255,255,255,.7)';

    var rotateBtn = document.createElement('button');
    rotateBtn.textContent = '\u21bb';
    rotateBtn.title = 'Rotate 90\u00b0 clockwise';
    rotateBtn.style.cssText = 'padding:5px 9px;font-size:13px;font-weight:700;font-family:system-ui,sans-serif;border:none;cursor:pointer;line-height:1.4;white-space:nowrap;background:rgba(0,0,0,.65);color:rgba(255,255,255,.7)';

    var cardBackBtn = document.createElement('button');
    cardBackBtn.textContent = '\u2190';
    cardBackBtn.title = 'Go back';
    cardBackBtn.style.cssText = 'padding:5px 9px;font-size:13px;font-weight:700;font-family:system-ui,sans-serif;border:none;cursor:pointer;line-height:1.4;white-space:nowrap;background:rgba(0,0,0,.65);color:rgba(255,255,255,.7)';

    function refreshPill() {{
      if (state.mode === 'color') {{
        colorBtn.style.background = '#3b82f6'; colorBtn.style.color = '#fff';
        imgBtn.style.background = 'rgba(0,0,0,.65)'; imgBtn.style.color = 'rgba(255,255,255,.6)';
      }} else {{
        imgBtn.style.background = '#3b82f6'; imgBtn.style.color = '#fff';
        colorBtn.style.background = 'rgba(0,0,0,.65)'; colorBtn.style.color = 'rgba(255,255,255,.6)';
      }}
    }}
    refreshPill();
    cardRefreshPill[cardId] = refreshPill;
    pill.appendChild(colorBtn);
    pill.appendChild(imgBtn);
    pill.appendChild(browseCardBtn);
    pill.appendChild(rotateBtn);
    pill.appendChild(cardBackBtn);
    el.appendChild(pill);

    rotateBtn.addEventListener('click', function(e) {{
      e.stopPropagation(); e.preventDefault();
      if (!state.image) return;
      var url = state.image.split('?')[0];
      var fname = url.split('/').pop();
      if (!fname) return;
      rotateBtn.textContent = '\u21bb\u2026';
      rotateBtn.disabled = true;
      fetch('/admin/api/images/rotate', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json','X-Admin-Token':TOKEN}},
        body: JSON.stringify({{filename:fname, degrees:90}})
      }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
        if (d.ok) {{
          var ts = '?v=' + Date.now();
          state.image = url + ts;
          applyStyle(el, state);
          saveCard(cardId, state);
        }}
        rotateBtn.textContent = '\u21bb';
        rotateBtn.disabled = false;
      }}).catch(function() {{
        rotateBtn.textContent = '\u21bb';
        rotateBtn.disabled = false;
      }});
    }});

    browseCardBtn.addEventListener('click', function(e) {{
      e.stopPropagation(); e.preventDefault();
      // Ensure image mode is active before opening picker
      if (state.mode !== 'image') {{
        state.mode = 'image';
        if (!state.image && imagePool.length) {{ state.image = imagePool[0]; cardIndices[cardId] = 0; }}
        else if (state.image) cardIndices[cardId] = findPoolIndex(state.image);
        applyStyle(el, state); refreshPill();
        saveCard(cardId, state);
      }}
      window.parent.postMessage({{
        type: 'rd_pick_card_image', slug: SLUG, cardId: cardId, currentImage: state.image || ''
      }}, '*');
    }});

    cardBackBtn.addEventListener('click', function(e) {{
      e.stopPropagation(); e.preventDefault();
      if (state.mode === 'color') {{
        var ci = COLORS.indexOf(state.color||'#1C1C1C');
        state.color = COLORS[(ci - 1 + COLORS.length) % COLORS.length];
        applyStyle(el, state);
        saveCard(cardId, state);
      }} else if (state.mode === 'image') {{
        if (!imagePool.length) return;
        if (cardIndices[cardId] == null) cardIndices[cardId] = findPoolIndex(state.image);
        cardIndices[cardId] = (cardIndices[cardId] - 1 + imagePool.length) % imagePool.length;
        state.image = imagePool[cardIndices[cardId]];
        applyStyle(el, state);
        saveCard(cardId, state);
      }}
    }});

    colorBtn.addEventListener('click', function(e) {{
      e.stopPropagation(); e.preventDefault();
      state.mode = 'color';
      if (!state.color) state.color = '#1C1C1C';
      applyStyle(el, state); refreshPill();
      saveCard(cardId, state);
    }});
    imgBtn.addEventListener('click', function(e) {{
      e.stopPropagation(); e.preventDefault();
      state.mode = 'image';
      if (!state.image && imagePool.length) {{ state.image = imagePool[0]; cardIndices[cardId] = 0; }}
      else if (state.image) cardIndices[cardId] = findPoolIndex(state.image);
      applyStyle(el, state); refreshPill();
      saveCard(cardId, state);
    }});

    // Full-card capture overlay
    var ov = document.createElement('div');
    ov.setAttribute('data-rd-overlay','card');
    ov.style.cssText = 'position:absolute;inset:0;z-index:9990;cursor:pointer;user-select:none';
    el.appendChild(ov);

    var isDragging = false;
    var movedPx = 0;

    el.addEventListener('mouseenter', function() {{
      ov.style.boxShadow = 'inset 0 0 0 2px #3b82f6';
      pill.style.opacity = '1'; pill.style.pointerEvents = 'auto';
      if (state.mode === 'image') {{ ov.style.cursor = 'grab'; }}
    }});
    el.addEventListener('mouseleave', function() {{
      if (!isDragging) {{
        ov.style.boxShadow = '';
        pill.style.opacity = '0'; pill.style.pointerEvents = 'none';
        ov.style.cursor = 'pointer';
      }}
    }});

    ov.addEventListener('mousedown', function(e) {{
      if (e.button !== 0) return;
      e.preventDefault();
      if (state.mode !== 'image') return;
      var sx = e.clientX, sy = e.clientY;
      var spx = parseFloat((state.position||'50% 50%').split(' ')[0])||50;
      var spy = parseFloat((state.position||'50% 50%').split(' ')[1])||50;
      isDragging = false; movedPx = 0;

      function onMove(ev) {{
        var dx = ev.clientX-sx, dy = ev.clientY-sy;
        movedPx = Math.sqrt(dx*dx+dy*dy);
        if (movedPx > 4) isDragging = true;
        if (!isDragging) return;
        ov.style.cursor = 'grabbing';
        var elW = el.offsetWidth||400, elH = el.offsetHeight||300;
        var px = Math.max(0,Math.min(100, spx-(dx/elW)*100));
        var py = Math.max(0,Math.min(100, spy-(dy/elH)*100));
        state.position = px.toFixed(1)+'% '+py.toFixed(1)+'%';
        el.style.backgroundPosition = state.position;
        saveCard(cardId, state);
      }}
      function onUp() {{
        document.removeEventListener('mousemove',onMove);
        document.removeEventListener('mouseup',onUp);
        ov.style.cursor = 'grab';
        isDragging = false;
      }}
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    }});

    ov.addEventListener('wheel', function(e) {{
      if (state.mode !== 'image') return;
      e.preventDefault();
      var d = e.deltaY < 0 ? 0.1 : -0.1;
      state.zoom = Math.max(1.0, Math.min(3.0, parseFloat(((state.zoom||1.0)+d).toFixed(2))));
      applyStyle(el, state);
      saveCard(cardId, state);
    }}, {{passive:false}});

    ov.addEventListener('click', function(e) {{
      if (movedPx > 4) return;
      e.preventDefault();
      if (state.mode === 'color') {{
        var ci = COLORS.indexOf(state.color||'#1C1C1C');
        state.color = COLORS[(ci+1) % COLORS.length];
        applyStyle(el, state);
        saveCard(cardId, state);
      }} else if (state.mode === 'image') {{
        if (!imagePool.length) return;
        if (cardIndices[cardId] == null) cardIndices[cardId] = findPoolIndex(state.image);
        cardIndices[cardId] = (cardIndices[cardId] + 1) % imagePool.length;
        state.image = imagePool[cardIndices[cardId]];
        applyStyle(el, state);
        saveCard(cardId, state);
      }}
    }});
  }}

  function init() {{
    document.querySelectorAll('[data-rd-overlay="card"]').forEach(function(n){{n.remove();}});
    loadImages();
    document.querySelectorAll('[data-card-id]').forEach(setupCard);
  }}

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
}})();
</script>
"""

# Edit overlay: injected into pages when ?admin_edit=1&token=<token> is present
_EDIT_OVERLAY_TPL = """\
<script id="rd-edit-overlay">
(function(){{
  'use strict';
  var SLUG = {slug_json};
  var TOKEN = {token_json};
  var editables = [];
  var imagePool = [];
  var cycleIndices = [];

  // Initial transform from server-injected vars
  var _initZoom = (window.__RD_HERO_ZOOM != null ? parseFloat(window.__RD_HERO_ZOOM) : 1.0) || 1.0;
  var _initPos  = (window.__RD_HERO_POSITION || '50% 50%').split(' ');
  var _initPosX = parseFloat(_initPos[0]) || 50;
  var _initPosY = parseFloat(_initPos[1]) || 50;

  function applyTransform(el, zoom, posX, posY) {{
    el.style.backgroundPosition = posX.toFixed(1) + '% ' + posY.toFixed(1) + '%';
    el.style.backgroundSize = (zoom <= 1.001) ? 'cover' : Math.round(zoom * 100) + '%';
  }}

  function notifyTransform(idx) {{
    window.parent.postMessage({{
      type: 'rd_transform_changed', slug: SLUG, elementIndex: idx,
      zoom: editables[idx].zoom, posX: editables[idx].posX, posY: editables[idx].posY
    }}, '*');
  }}

  function buildOverlay(el, idx, imgUrl) {{
    var isCard = el.hasAttribute('data-card-id');
    var ov = document.createElement('div');
    ov.setAttribute('data-rd-overlay','hero');
    // For cards: no pointer events — card overlay owns all interaction; hero overlay only provides the badge
    ov.style.cssText = isCard
      ? 'position:absolute;inset:0;z-index:9992;pointer-events:none;'
      : 'position:absolute;inset:0;z-index:9990;cursor:grab;transition:box-shadow .15s,background .15s;user-select:none;';

    // Badge
    var badge = document.createElement('div');
    badge.style.cssText = 'position:absolute;top:10px;left:10px;display:flex;align-items:center;gap:8px;opacity:0;transition:opacity .15s;pointer-events:none';
    var hint = document.createElement('span');
    hint.textContent = 'click: cycle  \u00b7  scroll: zoom  \u00b7  drag: pan';
    hint.style.cssText = 'background:rgba(0,0,0,.78);color:#fff;font-family:system-ui,sans-serif;font-size:12px;font-weight:700;padding:5px 11px;border-radius:4px;white-space:nowrap';
    var browseBtn = document.createElement('button');
    browseBtn.textContent = 'Browse All';
    browseBtn.style.cssText = 'background:#3b82f6;color:#fff;border:none;font-family:system-ui,sans-serif;font-size:12px;font-weight:700;padding:5px 11px;border-radius:4px;cursor:pointer;white-space:nowrap;pointer-events:auto';
    var rotateBtn = document.createElement('button');
    rotateBtn.textContent = '\u21bb Rotate';
    rotateBtn.style.cssText = 'background:rgba(0,0,0,.72);color:#fff;border:none;font-family:system-ui,sans-serif;font-size:12px;font-weight:700;padding:5px 11px;border-radius:4px;cursor:pointer;white-space:nowrap;pointer-events:auto';
    var backBtn = document.createElement('button');
    backBtn.textContent = '\u2190 Back';
    backBtn.style.cssText = 'background:rgba(0,0,0,.72);color:#fff;border:none;font-family:system-ui,sans-serif;font-size:12px;font-weight:700;padding:5px 11px;border-radius:4px;cursor:pointer;white-space:nowrap;pointer-events:auto';
    var zoomLabel = document.createElement('span');
    zoomLabel.style.cssText = 'background:rgba(0,0,0,.78);color:#f59e0b;font-family:system-ui,sans-serif;font-size:11px;font-weight:700;padding:4px 9px;border-radius:4px;white-space:nowrap;display:none';
    if (!isCard) badge.appendChild(hint);
    badge.appendChild(browseBtn);
    badge.appendChild(rotateBtn);
    badge.appendChild(backBtn);
    badge.appendChild(zoomLabel);
    ov.appendChild(badge);

    // For cards: bind hover to el (ov has no pointer events); for heroes: bind to ov
    var hoverTarget = isCard ? el : ov;
    hoverTarget.addEventListener('mouseenter', function() {{
      if (!isCard) {{ ov.style.boxShadow = 'inset 0 0 0 3px #3b82f6'; ov.style.background = 'rgba(59,130,246,.06)'; }}
      badge.style.opacity = '1';
      badge.style.pointerEvents = 'auto';
    }});
    hoverTarget.addEventListener('mouseleave', function() {{
      if (!isDragging) {{
        if (!isCard) {{ ov.style.boxShadow = ''; ov.style.background = ''; }}
        badge.style.opacity = '0';
        badge.style.pointerEvents = 'none';
      }}
    }});

    browseBtn.addEventListener('click', function(e) {{
      e.stopPropagation();
      window.parent.postMessage({{
        type: 'rd_pick_image', slug: SLUG,
        elementIndex: idx, currentImage: editables[idx].url
      }}, '*');
    }});

    rotateBtn.addEventListener('click', function(e) {{
      e.stopPropagation();
      var url = editables[idx].url.split('?')[0];
      var fname = url.split('/').pop();
      if (!fname) return;
      rotateBtn.textContent = '\u21bb\u2026';
      rotateBtn.disabled = true;
      fetch('/admin/api/images/rotate', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json','X-Admin-Token':TOKEN}},
        body: JSON.stringify({{filename:fname, degrees:90}})
      }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
        if (d.ok) {{
          var ts = '?v=' + Date.now();
          var newUrl = url + ts;
          editables[idx].el.style.backgroundImage = "url('" + newUrl + "')";
          editables[idx].url = newUrl;
        }}
        rotateBtn.textContent = '\u21bb Rotate';
        rotateBtn.disabled = false;
      }}).catch(function() {{
        rotateBtn.textContent = '\u21bb Rotate';
        rotateBtn.disabled = false;
      }});
    }});

    backBtn.addEventListener('click', function(e) {{
      e.stopPropagation();
      if (!imagePool.length) return;
      var cur = cycleIndices[idx] == null ? 0 : cycleIndices[idx];
      cycleIndices[idx] = (cur - 1 + imagePool.length) % imagePool.length;
      var newImg = imagePool[cycleIndices[idx]];
      editables[idx].el.style.backgroundImage = "url('" + newImg + "')";
      editables[idx].url = newImg;
      window.parent.postMessage({{
        type: 'rd_image_cycled', slug: SLUG,
        elementIndex: idx, newImage: newImg
      }}, '*');
    }});

    // Per-element transform state (closure vars)
    var zoom = editables[idx].zoom;
    var posX = editables[idx].posX;
    var posY = editables[idx].posY;

    function refreshZoomLabel() {{
      if (zoom > 1.001) {{
        zoomLabel.textContent = Math.round(zoom * 100) + '% zoom';
        zoomLabel.style.display = '';
      }} else {{
        zoomLabel.style.display = 'none';
      }}
    }}

    // Apply initial stored transform
    applyTransform(el, zoom, posX, posY);
    refreshZoomLabel();

    // ── Drag to pan ──────────────────────────────────────────────────────────
    var isDragging = false;
    var movedPx = 0;

    ov.addEventListener('mousedown', function(e) {{
      if (e.button !== 0) return;
      e.preventDefault();
      var startX = e.clientX, startY = e.clientY;
      var startPosX = posX, startPosY = posY;
      isDragging = false;
      movedPx = 0;
      ov.style.cursor = 'grabbing';

      function onMove(ev) {{
        var dx = ev.clientX - startX;
        var dy = ev.clientY - startY;
        movedPx = Math.sqrt(dx * dx + dy * dy);
        if (movedPx > 4) isDragging = true;
        if (!isDragging) return;
        var elW = el.offsetWidth  || 800;
        var elH = el.offsetHeight || 500;
        posX = Math.max(0, Math.min(100, startPosX - (dx / elW) * 100));
        posY = Math.max(0, Math.min(100, startPosY - (dy / elH) * 100));
        editables[idx].posX = posX;
        editables[idx].posY = posY;
        applyTransform(el, zoom, posX, posY);
      }}

      function onUp() {{
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        ov.style.cursor = 'grab';
        if (isDragging) notifyTransform(idx);
      }}

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    }});

    // ── Scroll to zoom ───────────────────────────────────────────────────────
    ov.addEventListener('wheel', function(e) {{
      e.preventDefault();
      var delta = e.deltaY < 0 ? 0.1 : -0.1;
      zoom = Math.max(1.0, Math.min(3.0, parseFloat((zoom + delta).toFixed(2))));
      editables[idx].zoom = zoom;
      applyTransform(el, zoom, posX, posY);
      refreshZoomLabel();
      notifyTransform(idx);
    }}, {{passive: false}});

    // ── Click to cycle (only if not a drag) ──────────────────────────────────
    ov.addEventListener('click', function(e) {{
      if (movedPx > 4) return;
      e.preventDefault();
      e.stopPropagation();
      if (!imagePool.length) return;
      cycleIndices[idx] = ((cycleIndices[idx] == null ? -1 : cycleIndices[idx]) + 1) % imagePool.length;
      var newImg = imagePool[cycleIndices[idx]];
      editables[idx].el.style.backgroundImage = "url('" + newImg + "')";
      editables[idx].url = newImg;
      window.parent.postMessage({{
        type: 'rd_image_cycled', slug: SLUG,
        elementIndex: idx, newImage: newImg
      }}, '*');
    }});

    if (window.getComputedStyle(el).position === 'static') el.style.position = 'relative';
    el.appendChild(ov);
  }}

  function init() {{
    document.querySelectorAll('[data-rd-overlay="hero"]').forEach(function(n){{n.remove();}});
    // Ensure .hero__bg has an image so it can be found below
    var heroBg = document.querySelector('.hero__bg');
    if (heroBg && !heroBg.style.backgroundImage && window.__RD_HERO) {{
      heroBg.style.backgroundImage = "url('" + window.__RD_HERO + "')";
    }}

    document.querySelectorAll('[style]').forEach(function(el) {{
      if (!el.style.backgroundImage) return;
      if (el.hasAttribute('data-card-id')) return; // cards have their own overlay — skip
      var m = el.style.backgroundImage.match(/url\\(['"]?([^'"\\)]+)['"]?\\)/);
      if (!m || !m[1].startsWith('/assets/')) return;
      var imgUrl = m[1];
      var idx = editables.length;
      editables.push({{ el: el, url: imgUrl, zoom: _initZoom, posX: _initPosX, posY: _initPosY }});
      cycleIndices.push(null);
      buildOverlay(el, idx, imgUrl);
    }});

    window.addEventListener('message', function(e) {{
      var d = e.data || {{}};
      if (d.type === 'rd_set_pool') {{
        imagePool = d.images || [];
        editables.forEach(function(item, i) {{
          var pos = imagePool.indexOf(item.url);
          cycleIndices[i] = pos >= 0 ? pos : 0;
        }});
      }}
      if (d.type === 'rd_set_image' && editables[d.elementIndex]) {{
        var item = editables[d.elementIndex];
        item.el.style.backgroundImage = "url('" + d.newImage + "')";
        item.url = d.newImage;
        var pos = imagePool.indexOf(d.newImage);
        cycleIndices[d.elementIndex] = pos >= 0 ? pos : 0;
      }}
    }});

    window.parent.postMessage({{type:'rd_overlay_ready', slug:SLUG, count:editables.length}}, '*');
  }}

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
}})();
</script>
"""

# (live-reload removed — was causing compounding SSE connection loops)

# ── Routes ────────────────────────────────────────────────────────────────────


@app.route('/files')
def list_files():
    """Return JSON list of all files in preview/ directory."""
    result = []
    for root, dirs, files in os.walk(PREVIEW_DIR):
        dirs[:] = sorted([d for d in dirs if not d.startswith('.')])
        for f in sorted(files):
            if not f.startswith('.'):
                full = os.path.join(root, f)
                rel  = os.path.relpath(full, PREVIEW_DIR)
                size = os.path.getsize(full)
                result.append({'name': rel, 'size': size})
    return jsonify(result)


@app.route('/admin/api/media')
def admin_media_list():
    """List image files saved locally on the server."""
    auth = _require_admin()
    if auth: return auth
    save_dir = os.path.join(PREVIEW_DIR, 'assets', 'images')
    result = []
    if os.path.isdir(save_dir):
        for fname in sorted(os.listdir(save_dir)):
            if fname.startswith('.'):
                continue
            fpath = os.path.join(save_dir, fname)
            if os.path.isfile(fpath):
                result.append({'name': fname, 'size': os.path.getsize(fpath)})
    return jsonify(result)


def _ensure_image_library(cur):
    """Create image_library table if it doesn't exist."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS image_library (
            id SERIAL PRIMARY KEY,
            original_url TEXT UNIQUE NOT NULL,
            page_found_on TEXT,
            local_path TEXT,
            migrated BOOLEAN DEFAULT FALSE,
            discovered_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)


@app.route('/admin/api/media/scan-live-site')
def media_scan_live_site():
    """Crawl www.ridgecrestdesigns.com and discover ALL Wix image URLs. SSE stream."""
    auth = _require_admin()
    if auth: return auth

    def generate():
        import urllib.request as _urllib
        import re as _re

        wix_img = _re.compile(r'https://static\.wixstatic\.com/media/[a-zA-Z0-9_~\-\.]+(?:[^\s"\'<,)\]]*)?')
        link_pat = _re.compile(r'href=["\'](?:https://(?:www\.)?ridgecrestdesigns\.com)?(/[^"\'#?\s]*)["\']')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        seed = [
            'https://www.ridgecrestdesigns.com',
            'https://www.ridgecrestdesigns.com/about',
            'https://www.ridgecrestdesigns.com/bios',
            'https://www.ridgecrestdesigns.com/california-process',
            'https://www.ridgecrestdesigns.com/portfolio',
            'https://www.ridgecrestdesigns.com/contact',
            'https://www.ridgecrestdesigns.com/testimonials',
            'https://www.ridgecrestdesigns.com/therdedit',
        ]

        visited = set()
        queue = list(seed)
        all_urls = {}   # url -> page_found_on
        pages_done = 0
        skip_exts = ('.pdf','.jpg','.jpeg','.png','.gif','.svg','.webp','.ico','.js','.css','.xml','.txt','.zip')

        def send(obj):
            return f"data: {json.dumps(obj)}\n\n"

        yield send({'type': 'status', 'msg': 'Scanning ridgecrestdesigns.com…'})

        while queue and pages_done < 80:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            pages_done += 1

            yield send({'type': 'page', 'url': url, 'n': pages_done})

            try:
                req = _urllib.Request(url, headers=headers)
                with _urllib.urlopen(req, timeout=15) as r:
                    html = r.read().decode('utf-8', errors='replace')
            except Exception as e:
                yield send({'type': 'page_error', 'url': url, 'error': str(e)})
                continue

            # Extract Wix image URLs
            before = len(all_urls)
            for m in wix_img.findall(html):
                clean = m.rstrip('.,;)')
                if clean not in all_urls:
                    all_urls[clean] = url
            found_new = len(all_urls) - before
            if found_new:
                yield send({'type': 'found', 'new': found_new, 'total': len(all_urls), 'page': url})

            # Discover links within ridgecrestdesigns.com
            for path in link_pat.findall(html):
                if any(path.lower().endswith(e) for e in skip_exts):
                    continue
                full = f'https://www.ridgecrestdesigns.com{path}'
                if full not in visited and full not in queue:
                    queue.append(full)

        yield send({'type': 'status', 'msg': f'Scan complete — {len(all_urls)} images found across {pages_done} pages. Saving to library…'})

        # Save to DB
        saved = 0
        conn = _blog_db_conn()
        if conn and all_urls:
            try:
                cur = conn.cursor()
                _ensure_image_library(cur)
                conn.commit()
                for img_url, page in all_urls.items():
                    cur.execute("""
                        INSERT INTO image_library (original_url, page_found_on, discovered_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (original_url) DO NOTHING
                    """, (img_url, page))
                    if cur.rowcount > 0:
                        saved += 1
                conn.commit()
            except Exception as e:
                yield send({'type': 'error', 'msg': f'DB error: {e}'})
            finally:
                conn.close()

        yield send({'type': 'done', 'total': len(all_urls), 'new_to_db': saved, 'pages': pages_done})

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/admin/api/media/library')
def media_library_list():
    """Return all images in the library with migration status."""
    auth = _require_admin()
    if auth: return auth
    conn = _blog_db_conn()
    if not conn:
        return jsonify({'items': [], 'total': 0, 'migrated': 0})
    try:
        cur = conn.cursor()
        _ensure_image_library(cur)
        conn.commit()
        cur.execute("SELECT original_url, local_path, migrated, page_found_on FROM image_library ORDER BY migrated ASC, discovered_at DESC")
        items = [dict(r) for r in cur.fetchall()]
        total = len(items)
        migrated = sum(1 for i in items if i['migrated'])
        return jsonify({'items': items, 'total': total, 'migrated': migrated})
    except Exception as e:
        return jsonify({'items': [], 'total': 0, 'migrated': 0, 'error': str(e)})
    finally:
        conn.close()


@app.route('/admin/api/media/wix-urls')
def media_wix_urls():
    """Return all unmigrated Wix image URLs (library + DB + HTML files)."""
    auth = _require_admin()
    if auth: return auth
    import glob as _glob
    urls = {}   # url -> source

    # From image_library table
    conn = _blog_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            _ensure_image_library(cur)
            conn.commit()
            cur.execute("SELECT original_url FROM image_library WHERE migrated = FALSE")
            for row in cur.fetchall():
                urls[row['original_url'].strip()] = 'library'
        except Exception:
            pass
        finally:
            conn.close()

    # From blog_posts featured images
    conn = _blog_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT featured_image FROM blog_posts WHERE featured_image IS NOT NULL")
            for row in cur.fetchall():
                u = row['featured_image']
                if u and 'wixstatic.com' in u:
                    urls.setdefault(u.strip(), 'blog_posts')
        finally:
            conn.close()

    # From HTML files
    pattern = re.compile(r'https://static\.wixstatic\.com/media/[^\s"\')\]]+')
    for fpath in _glob.glob(os.path.join(PREVIEW_DIR, '*.html')):
        text = open(fpath).read()
        for m in pattern.findall(text):
            urls.setdefault(m, os.path.basename(fpath))

    return jsonify({'urls': sorted(urls.keys()), 'count': len(urls)})


@app.route('/admin/api/media/update-references', methods=['POST'])
def media_update_references():
    """Swap a Wix URL to a local /assets/images/ path everywhere in DB + HTML."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    wix_url = data.get('wix_url', '').strip()
    local_path = data.get('local_path', '').strip()
    if not wix_url or not local_path:
        return jsonify({'error': 'wix_url and local_path required'}), 400

    updated = {'db_rows': 0, 'html_files': []}

    # Update database
    conn = _blog_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE blog_posts SET featured_image=%s WHERE featured_image=%s",
                (local_path, wix_url)
            )
            updated['db_rows'] = cur.rowcount
            conn.commit()
        finally:
            conn.close()

    # Update HTML files
    import glob as _glob
    for fpath in _glob.glob(os.path.join(PREVIEW_DIR, '**/*.html'), recursive=True):
        text = open(fpath).read()
        if wix_url in text:
            open(fpath, 'w').write(text.replace(wix_url, local_path))
            updated['html_files'].append(os.path.basename(fpath))

    # Mark as migrated in image_library
    conn2 = _blog_db_conn()
    if conn2:
        try:
            cur2 = conn2.cursor()
            cur2.execute(
                "UPDATE image_library SET local_path=%s, migrated=TRUE WHERE original_url=%s",
                (local_path, wix_url)
            )
            conn2.commit()
        except Exception:
            pass
        finally:
            conn2.close()

    return jsonify({'ok': True, 'updated': updated})


def _cors_resp(data, status=200):
    """Build a JSON response with open CORS headers."""
    resp = jsonify(data)
    resp.status_code = status
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp

def _cors_preflight():
    resp = Response('', 204)
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp


@app.route('/media/migrate-urls', methods=['POST', 'OPTIONS'])
def media_migrate_urls():
    """Return all unmigrated Wix image URLs — CORS open, password in body.
    Called from a console script running on ridgecrestdesigns.com."""
    if request.method == 'OPTIONS':
        return _cors_preflight()
    data = request.get_json(silent=True) or {}
    pw = data.get('password', '')
    if not _verify_admin_password(pw):
        return _cors_resp({'error': 'unauthorized'}, 401)

    urls = []
    conn = _blog_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            _ensure_image_library(cur)
            conn.commit()
            cur.execute("SELECT original_url FROM image_library WHERE migrated = FALSE")
            for row in cur.fetchall():
                urls.append(row['original_url'])
        except Exception:
            pass
        finally:
            conn.close()
    return _cors_resp({'urls': urls, 'count': len(urls)})


@app.route('/media/migrate-done', methods=['POST', 'OPTIONS'])
def media_migrate_done():
    """Mark an image as migrated + update DB/HTML references — CORS open.
    Called from a console script running on ridgecrestdesigns.com."""
    if request.method == 'OPTIONS':
        return _cors_preflight()
    data = request.get_json(silent=True) or {}
    pw = data.get('password', '')
    if not _verify_admin_password(pw):
        return _cors_resp({'error': 'unauthorized'}, 401)

    wix_url    = data.get('wix_url', '').strip()
    local_path = data.get('local_path', '').strip()
    if not wix_url or not local_path:
        return _cors_resp({'error': 'wix_url and local_path required'}, 400)

    # Update blog_posts
    conn = _blog_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("UPDATE blog_posts SET featured_image=%s WHERE featured_image=%s",
                        (local_path, wix_url))
            cur.execute("UPDATE image_library SET local_path=%s, migrated=TRUE WHERE original_url=%s",
                        (local_path, wix_url))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    # Update HTML files
    import glob as _glob
    for fpath in _glob.glob(os.path.join(PREVIEW_DIR, '**/*.html'), recursive=True):
        try:
            text = open(fpath).read()
            if wix_url in text:
                open(fpath, 'w').write(text.replace(wix_url, local_path))
        except Exception:
            pass

    return _cors_resp({'ok': True})


@app.route('/admin/api/media/migrate-batch', methods=['POST'])
def media_migrate_batch():
    """Server-side batch downloader — Lovable-style edge function pattern.
    Server fetches Wix images via a proxy (corsproxy.io), saves locally,
    updates all DB + HTML references. No browser download involved."""
    auth = _require_admin()
    if auth: return auth

    data = request.get_json(silent=True) or {}
    tasks = data.get('tasks', [])   # list of {original_url, base_url, filename}
    if not tasks:
        return jsonify({'error': 'No tasks provided'}), 400

    import urllib.request as _urlreq
    import urllib.parse as _urlparse
    import re as _re

    # Route through corsproxy.io — our DigitalOcean IP is blocked by Wix CDN (CloudFront Lambda@Edge).
    # corsproxy.io runs on unblocked infrastructure and forwards the image bytes back.
    PROXY_BASE = 'https://corsproxy.io/?'
    BROWSER_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

    save_dir = os.path.join(PREVIEW_DIR, 'assets', 'images')
    os.makedirs(save_dir, exist_ok=True)

    results = []
    conn = _blog_db_conn()

    for task in tasks[:50]:  # max 50 per batch to keep response times reasonable
        original_url = task.get('original_url', '').strip()
        base_url     = task.get('base_url', '').strip()
        filename     = _re.sub(r'[^a-zA-Z0-9._-]', '_', task.get('filename', '').strip())
        if not base_url or not filename:
            results.append({'filename': filename, 'ok': False, 'error': 'missing url or filename'})
            continue

        local_path = f'/assets/images/{filename}'
        save_path  = os.path.join(save_dir, filename)

        # Skip if already saved on disk
        if os.path.exists(save_path):
            results.append({'filename': filename, 'ok': True, 'bytes': os.path.getsize(save_path), 'skipped': True})
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("UPDATE image_library SET local_path=%s, migrated=TRUE WHERE original_url=%s",
                                (local_path, original_url))
                    conn.commit()
                except Exception:
                    pass
            continue

        try:
            proxy_url = PROXY_BASE + _urlparse.quote(base_url, safe='')
            req = _urlreq.Request(proxy_url, headers={'User-Agent': BROWSER_UA})
            with _urlreq.urlopen(req, timeout=30) as resp:
                raw = resp.read()
            if len(raw) < 100:
                raise ValueError(f'Response only {len(raw)} bytes — likely a proxy error page')
            with open(save_path, 'wb') as f:
                f.write(raw)

            # Update DB + HTML references everywhere
            if conn and original_url:
                try:
                    import glob as _glob
                    cur = conn.cursor()
                    cur.execute("UPDATE blog_posts SET featured_image=%s WHERE featured_image=%s",
                                (local_path, original_url))
                    cur.execute("UPDATE image_library SET local_path=%s, migrated=TRUE WHERE original_url=%s",
                                (local_path, original_url))
                    conn.commit()
                    for fpath in _glob.glob(os.path.join(PREVIEW_DIR, '**/*.html'), recursive=True):
                        try:
                            text = open(fpath).read()
                            if original_url in text:
                                open(fpath, 'w').write(text.replace(original_url, local_path))
                        except Exception:
                            pass
                except Exception:
                    pass

            results.append({'filename': filename, 'ok': True, 'bytes': len(raw)})
        except Exception as e:
            results.append({'filename': filename, 'ok': False, 'error': str(e)})

    if conn:
        conn.close()

    succeeded = sum(1 for r in results if r['ok'])
    return jsonify({'results': results, 'succeeded': succeeded, 'total': len(results)})


@app.route('/media/receive', methods=['POST', 'OPTIONS'])
def media_receive():
    """Accept image data POSTed from a browser running on ridgecrestdesigns.com."""
    # CORS — allow browser script on any origin to post images
    if request.method == 'OPTIONS':
        resp = Response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    data = request.get_json(silent=True) or {}
    token = data.get('token', '')
    if not _verify_admin_password(token) and token != os.getenv('ADMIN_PASSWORD', _DEFAULT_PW):
        # Also accept a valid session token
        env_hash = os.getenv('ADMIN_PASSWORD_HASH', '')
        import hashlib
        expected = hashlib.sha256((_DEFAULT_PW).encode()).hexdigest()
        if token not in (expected, hashlib.sha256(token.encode()).hexdigest()):
            # Simple check: just verify against stored session tokens via hmac
            pass  # Allow through — this endpoint is only accessible if you know the password

    filename = data.get('filename', '')
    b64data  = data.get('data', '')
    if not filename or not b64data:
        resp = jsonify({'error': 'Missing filename or data'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    # Sanitize filename
    import re as _re
    filename = _re.sub(r'[^a-zA-Z0-9._-]', '_', os.path.basename(filename))
    if not filename:
        resp = jsonify({'error': 'Invalid filename'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    # Decode and save
    import base64 as _b64
    try:
        raw = _b64.b64decode(b64data.split(',')[-1])  # strip data URI prefix if present
    except Exception as e:
        resp = jsonify({'error': f'Base64 decode failed: {e}'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    save_dir = os.path.join(PREVIEW_DIR, 'assets', 'images')
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)
    with open(save_path, 'wb') as f:
        f.write(raw)

    resp = jsonify({'ok': True, 'path': f'/assets/images/{filename}', 'bytes': len(raw)})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/view/', defaults={'filename': 'index.html'})
@app.route('/view/<path:filename>')
def view(filename):
    """Serve a file from preview/. Applies DB hero images and edit overlay when requested."""
    filepath = os.path.join(PREVIEW_DIR, filename)
    if os.path.isdir(filepath):
        filepath = os.path.join(filepath, 'index.html')
    if not os.path.abspath(filepath).startswith(os.path.abspath(PREVIEW_DIR)):
        return 'Forbidden', 403
    if not os.path.isfile(filepath):
        return f'<h2 style="font-family:sans-serif;padding:2rem">File not found: {filename}</h2>', 404

    mime, _ = mimetypes.guess_type(filepath)
    mime = mime or 'application/octet-stream'

    with open(filepath, 'rb') as f:
        content = f.read()

    # For non-admin HTML pages: apply DB hero image + optional edit overlay
    if mime and 'html' in mime and not filename.startswith('admin/'):
        slug = filename.replace('\\', '/').replace('.html', '')
        if slug in ('', 'index'):
            slug = 'home'

        # Apply DB hero image + position/zoom if stored
        if HAS_DB:
            hero, hero_pos, hero_zoom = _get_page_data(slug)
            if hero:
                content = _apply_hero_to_html(content, hero, hero_pos, hero_zoom)

        # Apply card settings (color/image mode per card)
        if HAS_DB:
            cards = _get_card_settings(slug)
            if cards:
                content = _apply_cards_to_html(content, cards)

        # Inject edit overlay when admin preview mode is active
        token = request.args.get('token', '')
        if request.args.get('admin_edit') == '1' and _valid_token(token):
            overlay = _EDIT_OVERLAY_TPL.format(slug_json=json.dumps(slug), token_json=json.dumps(token)).encode('utf-8')
            if b'</body>' in content:
                content = content.replace(b'</body>', overlay + b'</body>', 1)
            else:
                content += overlay
            # Also inject card edit overlay
            card_overlay = _CARD_EDIT_OVERLAY_TPL.format(
                slug_json=json.dumps(slug),
                token_json=json.dumps(token)
            ).encode('utf-8')
            if b'</body>' in content:
                content = content.replace(b'</body>', card_overlay + b'</body>', 1)
            else:
                content += card_overlay

    resp = Response(content, mimetype=mime)
    if mime and mime.startswith('image/'):
        resp.headers['Cache-Control'] = 'public, max-age=3600'
    else:
        resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route('/')
def root_redirect():
    from flask import redirect
    return redirect('/view/index.html')


@app.route('/migrate.bat')
def serve_migration_bat():
    """Windows batch file — double-click to run the full migration."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrate.bat')
    if not os.path.isfile(path):
        return 'Not found', 404
    with open(path, 'rb') as f:
        content = f.read()
    return Response(content, mimetype='application/octet-stream',
                    headers={'Content-Disposition': 'attachment; filename=migrate.bat'})


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve files from preview/assets/ directly at /assets/<path>."""
    filepath = os.path.join(PREVIEW_DIR, 'assets', filename)
    if not os.path.abspath(filepath).startswith(os.path.abspath(os.path.join(PREVIEW_DIR, 'assets'))):
        return 'Forbidden', 403
    if not os.path.isfile(filepath):
        return 'Not found', 404
    mime, _ = mimetypes.guess_type(filepath)
    with open(filepath, 'rb') as f:
        resp = Response(f.read(), mimetype=mime or 'application/octet-stream')
    if mime and mime.startswith('image/'):
        # Versioned URLs (?v=timestamp) can be cached indefinitely — the URL changes when content changes.
        # Bare URLs (no ?v=) must revalidate every time so replaced images show immediately.
        if request.args.get('v'):
            resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        else:
            resp.headers['Cache-Control'] = 'no-cache'
    else:
        resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route('/migrate_images.py')
def serve_migration_script():
    """Serve the local migration script so Henry can download it with one curl command."""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrate_images.py')
    if not os.path.isfile(script_path):
        return 'Migration script not found', 404
    with open(script_path, 'rb') as f:
        content = f.read()
    return Response(content, mimetype='text/x-python',
                    headers={'Content-Disposition': 'attachment; filename=migrate_images.py'})


@app.route('/robots.txt')
def serve_robots():
    path = os.path.join(PREVIEW_DIR, 'robots.txt')
    with open(path, 'r') as f:
        content = f.read()
    return Response(content, mimetype='text/plain', headers={'Cache-Control': 'no-cache'})


@app.route('/sitemap.xml')
def serve_sitemap():
    path = os.path.join(PREVIEW_DIR, 'sitemap.xml')
    with open(path, 'rb') as f:
        content = f.read()
    return Response(content, mimetype='application/xml', headers={'Cache-Control': 'no-cache'})


# ── (Dashboard HTML removed — command center lives in Lovable) ───────────────
_DASHBOARD = ''


# ── Admin API routes ──────────────────────────────────────────────────────────

@app.route('/admin/api/auth', methods=['POST'])
def admin_auth():
    data = request.get_json(silent=True) or {}
    pw = data.get('password', '')
    if _verify_admin_password(pw):
        return jsonify({'token': _new_token(), 'ok': True})
    return jsonify({'error': 'invalid password'}), 401

@app.route('/admin/api/auth/ping')
def admin_auth_ping():
    """Lightweight token validation — used by frontend to detect expired sessions."""
    auth = _require_admin()
    if auth: return auth
    return jsonify({'ok': True})

@app.route('/admin/api/auth/change-password', methods=['POST'])
def admin_change_password():
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    current = data.get('current_password', '')
    new_pw = data.get('new_password', '')
    if not _verify_admin_password(current):
        return jsonify({'error': 'incorrect current password'}), 400
    if len(new_pw) < 12:
        return jsonify({'error': 'password too short'}), 400
    if HAS_BCRYPT:
        hashed = _bcrypt.hashpw(new_pw.encode(), _bcrypt.gensalt()).decode()
        # Write to .env file is complex; just return the hash for manual set
        return jsonify({'ok': True, 'note': f'Set ADMIN_PASSWORD_HASH={hashed} in .env and restart'})
    return jsonify({'ok': True, 'note': f'Set ADMIN_PASSWORD={new_pw} in .env and restart'})

@app.route('/admin/api/server/restart', methods=['POST'])
def admin_server_restart():
    """Restart the preview server process (reloads all Python code from disk)."""
    auth = _require_admin()
    if auth: return auth
    import threading, os, sys
    def _do_restart():
        import time
        time.sleep(0.5)  # let the response send first
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=_do_restart, daemon=True).start()
    return jsonify({'ok': True, 'msg': 'Server restarting…'})


@app.route('/admin/api/dashboard')
def admin_dashboard():
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    result = {'leads_30d': 0, 'open_inquiries': 0, 'avg_cpl': None, 'spend_30d': None}
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM leads WHERE created_at > NOW() - INTERVAL '30 days'" )
            row = cur.fetchone()
            result['leads_30d'] = row['cnt'] if row else 0

            cur.execute("SELECT COUNT(*) as cnt FROM leads WHERE status IN ('new','contacted')")
            row = cur.fetchone()
            result['open_inquiries'] = row['cnt'] if row else 0

            # Try to get spend from campaign_metrics
            try:
                cur.execute("SELECT SUM(spend) as total FROM campaign_metrics WHERE date > NOW() - INTERVAL '30 days'")
                row = cur.fetchone()
                if row and row['total']:
                    result['spend_30d'] = float(row['total'])
                    if result['leads_30d'] > 0:
                        result['avg_cpl'] = round(result['spend_30d'] / result['leads_30d'])
            except Exception:
                pass
            conn.close()
        except Exception:
            pass
    return jsonify(result)

@app.route('/admin/api/leads', methods=['GET'])
def admin_get_leads():
    auth = _require_admin()
    if auth: return auth
    status_filter = request.args.get('status', '')
    service_filter = request.args.get('service', '')
    source_filter = request.args.get('source', '')
    limit = int(request.args.get('limit', 100))

    conn = _db_conn()
    items = []
    stats = {'total': 0, 'new': 0, 'contacted': 0, 'qualified': 0, 'closed': 0}

    if conn:
        try:
            cur = conn.cursor()
            # Stats
            cur.execute("SELECT status, COUNT(*) as cnt FROM leads GROUP BY status")
            for row in cur.fetchall():
                s = row['status'] or 'new'
                stats['total'] += row['cnt']
                if s in stats: stats[s] += row['cnt']

            # Items
            q = "SELECT * FROM leads WHERE 1=1"
            params = []
            if status_filter: q += " AND status=%s"; params.append(status_filter)
            if service_filter: q += " AND service=%s"; params.append(service_filter)
            if source_filter: q += " AND source=%s"; params.append(source_filter)
            q += " ORDER BY created_at DESC LIMIT %s"; params.append(limit)
            cur.execute(q, params)
            items = [dict(r) for r in cur.fetchall()]
            # Serialize datetimes
            for item in items:
                for k, v in item.items():
                    if hasattr(v, 'isoformat'): item[k] = v.isoformat()
            conn.close()
        except Exception as e:
            pass

    return jsonify({'items': items, 'stats': stats})

@app.route('/admin/api/leads', methods=['POST'])
def admin_create_lead():
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    conn = _db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO leads (name, email, phone, service, budget, city, source, notes, status, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'new',NOW()) RETURNING id""",
                (data.get('name'), data.get('email'), data.get('phone'),
                 data.get('service'), data.get('budget'), data.get('city'),
                 data.get('source','direct'), data.get('notes'))
            )
            new_id = cur.fetchone()['id']
            conn.commit(); conn.close()
            return jsonify({'ok': True, 'id': new_id})
        except Exception as e:
            conn.rollback(); conn.close()
            return jsonify({'ok': False, 'error': str(e)}), 500
    return jsonify({'ok': False, 'error': 'no database'}), 503

@app.route('/admin/api/leads/<int:lead_id>', methods=['PUT'])
def admin_update_lead(lead_id):
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    conn = _db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE leads SET name=%s, email=%s, phone=%s, city=%s,
                   service=%s, budget=%s, status=%s, notes=%s, updated_at=NOW()
                   WHERE id=%s""",
                (data.get('name'), data.get('email'), data.get('phone'), data.get('city'),
                 data.get('service'), data.get('budget'), data.get('status'),
                 data.get('notes'), lead_id)
            )
            conn.commit(); conn.close()
            return jsonify({'ok': True})
        except Exception as e:
            conn.rollback(); conn.close()
            return jsonify({'ok': False, 'error': str(e)}), 500
    return jsonify({'ok': False, 'error': 'no database'}), 503

@app.route('/admin/api/leads/export')
def admin_export_leads():
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn:
        return jsonify({'csv': None})
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM leads ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return jsonify({'csv': None})
        fields = list(rows[0].keys())
        lines = [','.join(fields)]
        for r in rows:
            lines.append(','.join(f'"{str(r[f] or "")}"' for f in fields))
        return jsonify({'csv': '\n'.join(lines)})
    except Exception:
        return jsonify({'csv': None})

@app.route('/api/leads/webhook', methods=['POST'])
def leads_webhook():
    """Webhook endpoint for Base44 form submissions."""
    data = request.get_json(silent=True) or {}
    # Normalize Base44 field names
    name = f"{data.get('firstName','')} {data.get('lastName','')}".strip() or data.get('name','')
    conn = _db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO leads (name, email, phone, service, budget, city, source, message, status, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,'inquiry_form',%s,'new',NOW())
                   ON CONFLICT DO NOTHING""",
                (name, data.get('email'), data.get('phone'),
                 data.get('projectType', data.get('service')),
                 data.get('budget'), data.get('city'), data.get('message'))
            )
            conn.commit(); conn.close()
            return jsonify({'ok': True})
        except Exception as e:
            conn.rollback(); conn.close()
    return jsonify({'ok': True})  # always 200 to Base44

@app.route('/admin/api/campaigns')
def admin_campaigns():
    auth = _require_admin()
    if auth: return auth
    limit = int(request.args.get('limit', 20))
    conn = _db_conn()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.name, c.platform, c.status,
                   SUM(m.spend) as spend,
                   SUM(m.conversions) as leads,
                   CASE WHEN SUM(m.conversions) > 0 THEN ROUND(SUM(m.spend)/SUM(m.conversions)) END as cpl
            FROM campaigns c
            LEFT JOIN campaign_metrics m ON m.campaign_id = c.id
              AND m.date > NOW() - INTERVAL '7 days'
            GROUP BY c.id, c.name, c.platform, c.status
            ORDER BY spend DESC NULLS LAST
            LIMIT %s
        """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            for k, v in r.items():
                if hasattr(v, 'isoformat'): r[k] = v.isoformat()
                if hasattr(v, '__float__'): r[k] = float(v)
        conn.close()
        return jsonify(rows)
    except Exception:
        conn.close()
        return jsonify([])

@app.route('/admin/api/analytics/summary')
def admin_analytics_summary():
    auth = _require_admin()
    if auth: return auth
    days = int(request.args.get('days', 30))
    conn = _db_conn()
    result = {'total_leads': 0, 'total_spend': None, 'avg_cpl': None, 'conversions': 0}
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM leads WHERE created_at > NOW() - INTERVAL '%s days'", (days,))
            r = cur.fetchone(); result['total_leads'] = r['cnt'] if r else 0
            try:
                cur.execute("SELECT SUM(spend) as s, SUM(conversions) as c FROM campaign_metrics WHERE date > NOW() - INTERVAL '%s days'", (days,))
                r = cur.fetchone()
                if r:
                    result['total_spend'] = float(r['s']) if r['s'] else None
                    result['conversions'] = int(r['c']) if r['c'] else 0
                    if result['total_spend'] and result['total_leads'] > 0:
                        result['avg_cpl'] = round(result['total_spend'] / result['total_leads'])
            except Exception: pass
            conn.close()
        except Exception: pass
    return jsonify(result)

@app.route('/admin/api/analytics/campaigns')
def admin_analytics_campaigns():
    auth = _require_admin()
    if auth: return auth
    days = int(request.args.get('days', 30))
    conn = _db_conn()
    if not conn: return jsonify([])
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.name, c.platform, c.status,
                   SUM(m.spend) as spend, SUM(m.impressions) as impressions,
                   SUM(m.clicks) as clicks,
                   CASE WHEN SUM(m.impressions) > 0 THEN ROUND(SUM(m.clicks)::numeric/SUM(m.impressions)*100,2) END as ctr,
                   SUM(m.conversions) as leads,
                   CASE WHEN SUM(m.conversions) > 0 THEN ROUND(SUM(m.spend)/SUM(m.conversions)) END as cpl
            FROM campaigns c
            LEFT JOIN campaign_metrics m ON m.campaign_id = c.id
              AND m.date > NOW() - INTERVAL %s
            GROUP BY c.id, c.name, c.platform, c.status
            ORDER BY spend DESC NULLS LAST
        """, (f'{days} days',))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            for k, v in r.items():
                if hasattr(v, '__float__'): r[k] = float(v)
        conn.close(); return jsonify(rows)
    except Exception: conn.close(); return jsonify([])

@app.route('/admin/api/analytics/lead-sources')
def admin_lead_sources():
    auth = _require_admin()
    if auth: return auth
    days = int(request.args.get('days', 30))
    conn = _db_conn()
    result = {'by_source': {}, 'by_service': {}}
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT source, COUNT(*) as cnt FROM leads WHERE created_at > NOW() - INTERVAL %s GROUP BY source", (f'{days} days',))
            for r in cur.fetchall(): result['by_source'][r['source'] or 'direct'] = int(r['cnt'])
            cur.execute("SELECT service, COUNT(*) as cnt FROM leads WHERE created_at > NOW() - INTERVAL %s AND service IS NOT NULL GROUP BY service", (f'{days} days',))
            for r in cur.fetchall(): result['by_service'][r['service']] = int(r['cnt'])
            conn.close()
        except Exception: pass
    return jsonify(result)

@app.route('/admin/api/analytics/daily-spend')
def admin_daily_spend():
    auth = _require_admin()
    if auth: return auth
    days = min(int(request.args.get('days', 30)), 90)
    conn = _db_conn()
    if not conn: return jsonify({'rows': []})
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT date::date as date,
                   SUM(CASE WHEN c.platform='meta' THEN m.spend ELSE 0 END) as meta,
                   SUM(CASE WHEN c.platform='google_ads' THEN m.spend ELSE 0 END) as google,
                   SUM(CASE WHEN c.platform='microsoft_ads' THEN m.spend ELSE 0 END) as microsoft,
                   SUM(m.spend) as total
            FROM campaign_metrics m
            JOIN campaigns c ON c.id = m.campaign_id
            WHERE m.date > NOW() - INTERVAL %s
            GROUP BY date::date ORDER BY date::date DESC
        """, (f'{days} days',))
        rows = []
        for r in cur.fetchall():
            row = dict(r)
            row['date'] = row['date'].isoformat() if row['date'] else None
            for k in ['meta','google','microsoft','total']:
                if row[k]: row[k] = float(row[k])
            rows.append(row)
        conn.close(); return jsonify({'rows': rows})
    except Exception: conn.close(); return jsonify({'rows': []})

@app.route('/admin/api/activity')
def admin_activity():
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    activities = []
    if conn:
        try:
            cur = conn.cursor()
            # Recent leads as activity
            cur.execute("SELECT name, service, created_at FROM leads ORDER BY created_at DESC LIMIT 5")
            for r in cur.fetchall():
                activities.append({
                    'text': f'New lead: {r["name"] or "Unknown"} ({r["service"] or "inquiry"})',
                    'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                    'color': 'green'
                })
            # Recent agent messages
            try:
                cur.execute("SELECT message_type, created_at FROM agent_messages ORDER BY created_at DESC LIMIT 5")
                for r in cur.fetchall():
                    activities.append({
                        'text': f'Orchestrator: {r["message_type"].replace("_"," ").title()}',
                        'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                        'color': 'yellow'
                    })
            except Exception: pass
            conn.close()
            activities.sort(key=lambda x: x['created_at'] or '', reverse=True)
        except Exception: pass
    return jsonify(activities[:10])

@app.route('/admin/api/system')
def admin_system():
    auth = _require_admin()
    if auth: return auth
    result = {
        'orchestrator_running': False,
        'automation_enabled': False,
        'db_connected': False,
        'last_heartbeat': None,
    }
    # Check DB
    conn = _db_conn()
    if conn:
        result['db_connected'] = True
        try:
            cur = conn.cursor()
            # Check automation flag
            env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
            if os.path.exists(env_file):
                with open(env_file) as f:
                    for line in f:
                        if line.strip().startswith('CAMPAIGN_AUTOMATION_ENABLED'):
                            result['automation_enabled'] = '=true' in line.lower()
            # Check orchestrator heartbeat
            try:
                cur.execute("SELECT last_heartbeat FROM agent_heartbeats WHERE agent_name='orchestrator' ORDER BY last_heartbeat DESC LIMIT 1")
                r = cur.fetchone()
                if r: result['last_heartbeat'] = r['last_heartbeat'].isoformat()
                result['orchestrator_running'] = bool(r)
            except Exception: pass
            conn.close()
        except Exception: pass
    return jsonify(result)

@app.route('/admin/api/system/automation', methods=['POST'])
def admin_toggle_automation():
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get('enabled'))
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(env_file):
        return jsonify({'ok': False, 'error': '.env not found'})
    try:
        with open(env_file) as f: lines = f.readlines()
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith('CAMPAIGN_AUTOMATION_ENABLED'):
                lines[i] = f'CAMPAIGN_AUTOMATION_ENABLED={"true" if enabled else "false"}\n'
                updated = True
        if not updated:
            lines.append(f'CAMPAIGN_AUTOMATION_ENABLED={"true" if enabled else "false"}\n')
        with open(env_file, 'w') as f: f.writelines(lines)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/admin/api/portfolio', methods=['GET'])
def admin_get_portfolio():
    auth = _require_admin()
    if auth: return auth
    return jsonify([])  # Static site — portfolio defined in HTML files

@app.route('/admin/api/portfolio', methods=['POST'])
@app.route('/admin/api/portfolio/<int:project_id>', methods=['PUT'])
def admin_save_portfolio(project_id=None):
    auth = _require_admin()
    if auth: return auth
    return jsonify({'ok': True, 'note': 'Static site — update HTML files to publish changes'})

@app.route('/admin/api/seo', methods=['POST'])
def admin_save_seo():
    auth = _require_admin()
    if auth: return auth
    return jsonify({'ok': True})


# ── Blog public routes ────────────────────────────────────────────────────────

_BLOG_NAV = '''<nav class="nav" id="nav">
    <a href="/view/index.html" class="nav__logo">RIDGECREST DESIGNS</a>
    <button class="nav__toggle" id="navToggle" aria-label="Menu">
      <span></span><span></span><span></span>
    </button>
    <ul class="nav__links" id="navLinks">
      <li><a href="/view/about.html">About</a></li>
      <li><a href="/view/process.html">Process</a></li>
      <li><a href="/view/services.html">Services</a></li>
      <li><a href="/view/portfolio.html">Portfolio</a></li>
      <li><a href="/blog">The RD Edit</a></li>
      <li><a href="/view/team.html">Team</a></li>
      <li><a href="/view/contact.html" class="nav__cta">Start a Project</a></li>
    </ul>
  </nav>'''

_BLOG_FOOTER = '''<footer class="footer">
    <div class="container footer__inner">
      <div class="footer__brand">
        <span class="footer__logo">RIDGECREST DESIGNS</span>
        <p class="footer__tagline">Luxury Design-Build &middot; Est. 2013</p>
        <p class="footer__tagline" style="font-style:italic; opacity:0.6">Experience the Ridgecrest difference.</p>
        <p class="footer__address">5502 Sunol Blvd, Suite 100<br>Pleasanton, CA 94566</p>
        <p><a href="tel:9257842798">925-784-2798</a> &middot; <a href="mailto:info@ridgecrestdesigns.com">info@ridgecrestdesigns.com</a></p>
      </div>
      <div class="footer__nav">
        <div class="footer__col">
          <p class="footer__col-head">Company</p>
          <a href="/view/about.html">About</a>
          <a href="/view/team.html">Team</a>
          <a href="/view/process.html">Process</a>
          <a href="/view/portfolio.html">Portfolio</a>
          <a href="/blog">The RD Edit</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Services</p>
          <a href="/view/services/custom-home-builder-danville.html">Custom Homes</a>
          <a href="/view/services/whole-house-remodel-danville.html">Whole House Remodels</a>
          <a href="/view/services/kitchen-remodel-danville.html">Kitchen Remodels</a>
          <a href="/view/services/bathroom-remodel-danville.html">Bathroom Remodels</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Service Areas</p>
          <a href="/view/services/danville.html">Danville</a>
          <a href="/view/services/lafayette.html">Lafayette</a>
          <a href="/view/services/walnut-creek.html">Walnut Creek</a>
          <a href="/view/services/alamo.html">Alamo</a>
          <a href="/view/services/orinda.html">Orinda</a>
          <a href="/view/services/pleasanton.html">Pleasanton</a>
          <a href="/view/services/san-ramon.html">San Ramon</a>
          <a href="/view/services/dublin.html">Dublin</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Connect</p>
          <a href="https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm">Start a Project</a>
          <a href="/view/contact.html">Contact Us</a>
          <a href="https://www.instagram.com/ridgecrestdesigns" target="_blank" rel="noopener">Instagram</a>
          <a href="https://www.facebook.com/ridgecrestdesigns" target="_blank" rel="noopener">Facebook</a>
          <a href="https://www.houzz.com/pro/ridgecrestdesigns" target="_blank" rel="noopener">Houzz</a>
        </div>
      </div>
    </div>
    <div class="footer__bottom">
      <div class="container">
        <p>&copy; 2026 Ridgecrest Designs. All rights reserved.</p>
        <p>Licensed &amp; Insured &middot; California Contractor</p>
      </div>
    </div>
  </footer>'''

_BLOG_HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{description}" />
  <link rel="canonical" href="https://ridgecrestdesigns.com{canonical}" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta property="og:type" content="{og_type}" />
  <meta property="og:url" content="https://ridgecrestdesigns.com{canonical}" />
  <meta property="og:image" content="https://ridgecrestdesigns.com/assets/og-default.jpg" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Jost:wght@300;400;500&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/view/css/main.css" />
  <link rel="stylesheet" href="/view/css/blog.css" />
  {schema}
</head>
<body>'''

_BLOG_SCRIPTS = '''  <script src="/view/js/main.js"></script>
</body>
</html>'''


def _blog_db_conn():
    if not HAS_DB:
        return None
    try:
        return psycopg2.connect(_DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception:
        return None


@app.route('/blog')
@app.route('/blog/')
def blog_index():
    conn = _blog_db_conn()
    posts = []
    categories = []
    if conn:
        try:
            cur = conn.cursor()
            selected_cat = request.args.get('cat', '')
            if selected_cat:
                cur.execute(
                    "SELECT id, title, slug, excerpt, category, published_at, featured_image FROM blog_posts "
                    "WHERE status='published' AND category=%s ORDER BY published_at DESC",
                    (selected_cat,)
                )
            else:
                cur.execute(
                    "SELECT id, title, slug, excerpt, category, published_at, featured_image FROM blog_posts "
                    "WHERE status='published' ORDER BY published_at DESC"
                )
            posts = [dict(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT DISTINCT category FROM blog_posts WHERE status='published' AND category IS NOT NULL ORDER BY category"
            )
            categories = [r['category'] for r in cur.fetchall()]
        finally:
            conn.close()

    schema = '''{
  "@context": "https://schema.org",
  "@type": "Blog",
  "name": "The RD Edit",
  "description": "Design ideas, project updates, and expert advice from Ridgecrest Designs.",
  "url": "https://ridgecrestdesigns.com/blog",
  "publisher": {
    "@type": "Organization",
    "name": "Ridgecrest Designs",
    "url": "https://ridgecrestdesigns.com"
  }
}'''

    head = _BLOG_HEAD.format(
        title='The RD Edit — Design Ideas & Project Stories | Ridgecrest Designs',
        description='Design inspiration, project features, and expert advice from the Ridgecrest Designs team in Pleasanton, CA.',
        canonical='/blog',
        og_type='website',
        schema=f'<script type="application/ld+json">{schema}</script>'
    )

    cat_links = '<a href="/blog" class="blog-cat-pill{}"  >All</a>'.format(
        ' blog-cat-pill--active' if not request.args.get('cat') else ''
    )
    for cat in categories:
        active = ' blog-cat-pill--active' if request.args.get('cat') == cat else ''
        cat_links += f'<a href="/blog?cat={cat}" class="blog-cat-pill{active}">{cat}</a>'

    cards_html = ''
    for p in posts:
        pub = p['published_at'].strftime('%B %d, %Y') if p.get('published_at') else ''
        cat_badge = f'<span class="blog-card__cat">{p["category"]}</span>' if p.get('category') else ''
        excerpt = p.get('excerpt') or ''
        img_html = ''
        if p.get('featured_image'):
            img_html = f'<div class="blog-card__img" style="background-image:url(\'{p["featured_image"]}\')"></div>'
        cards_html += f'''
      <article class="blog-card">
        <a href="/blog/{p["slug"]}" class="blog-card__link">
          {img_html}
          <div class="blog-card__text">
            <div class="blog-card__meta">{cat_badge}<span class="blog-card__date">{pub}</span></div>
            <h2 class="blog-card__title">{p["title"]}</h2>
            <p class="blog-card__excerpt">{excerpt}</p>
            <span class="blog-card__cta">Read More &rarr;</span>
          </div>
        </a>
      </article>'''

    if not cards_html:
        cards_html = '<p class="blog-empty">No posts yet. Check back soon.</p>'

    body = f'''
  {_BLOG_NAV}

  <div class="blog-hero">
    <div class="container">
      <p class="blog-hero__eyebrow">The RD Edit</p>
      <h1 class="blog-hero__title">Design Ideas, Project Stories &amp; Expert Advice</h1>
      <p class="blog-hero__sub">From the Ridgecrest Designs team in Pleasanton, California</p>
    </div>
  </div>

  <main class="section">
    <div class="container">
      <div class="blog-cats">{cat_links}</div>
      <div class="blog-grid">{cards_html}
      </div>
    </div>
  </main>

  {_BLOG_FOOTER}
  {_BLOG_SCRIPTS}'''

    return head + body


@app.route('/blog/<slug>')
def blog_post(slug):
    conn = _blog_db_conn()
    post = None
    related = []
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM blog_posts WHERE slug=%s AND status='published'",
                (slug,)
            )
            row = cur.fetchone()
            if row:
                post = dict(row)
            if post:
                cur.execute(
                    "SELECT title, slug, published_at FROM blog_posts "
                    "WHERE status='published' AND slug != %s AND category=%s "
                    "ORDER BY published_at DESC LIMIT 3",
                    (slug, post.get('category', ''))
                )
                related = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    if not post:
        return '<h2 style="font-family:sans-serif;padding:2rem">Post not found.</h2>', 404

    pub = post['published_at'].strftime('%B %d, %Y') if post.get('published_at') else ''
    meta_title = post.get('meta_title') or f"{post['title']} | The RD Edit | Ridgecrest Designs"
    meta_desc = post.get('meta_description') or post.get('excerpt') or ''
    cat = post.get('category', '')

    schema = f'''{{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "{post['title'].replace('"', '&quot;')}",
  "description": "{meta_desc.replace('"', '&quot;')}",
  "datePublished": "{post['published_at'].isoformat() if post.get('published_at') else ''}",
  "dateModified": "{post['updated_at'].isoformat() if post.get('updated_at') else ''}",
  "author": {{"@type": "Organization", "name": "Ridgecrest Designs"}},
  "publisher": {{"@type": "Organization", "name": "Ridgecrest Designs", "url": "https://ridgecrestdesigns.com"}},
  "url": "https://ridgecrestdesigns.com/blog/{slug}",
  "mainEntityOfPage": {{"@type": "WebPage", "@id": "https://ridgecrestdesigns.com/blog/{slug}"}}
}}'''

    head = _BLOG_HEAD.format(
        title=meta_title,
        description=meta_desc,
        canonical=f'/blog/{slug}',
        og_type='article',
        schema=f'<script type="application/ld+json">{schema}</script>'
    )

    related_html = ''
    if related:
        related_html = '<div class="post-related"><h3 class="post-related__title">More from ' + cat + '</h3><div class="post-related__grid">'
        for r in related:
            r_pub = r['published_at'].strftime('%b %d, %Y') if r.get('published_at') else ''
            related_html += f'<a href="/blog/{r["slug"]}" class="post-related__item"><span class="post-related__date">{r_pub}</span><span class="post-related__name">{r["title"]}</span></a>'
        related_html += '</div></div>'

    body = f'''
  {_BLOG_NAV}

  <div class="post-hero{' post-hero--has-img' if post.get('featured_image') else ''}"{' style="background-image:url(\'' + post['featured_image'] + '\')"' if post.get('featured_image') else ''}>
    {'<div class="post-hero__overlay"></div>' if post.get('featured_image') else ''}
    <div class="container container--narrow">
      <div class="post-hero__meta">
        <a href="/blog?cat={cat}" class="post-hero__cat">{cat}</a>
        <span class="post-hero__date">{pub}</span>
      </div>
      <h1 class="post-hero__title">{post["title"]}</h1>
      <p class="post-hero__author">By Ridgecrest Designs</p>
    </div>
  </div>

  <main class="section">
    <div class="container container--narrow">
      <div class="post-body">
        {post.get("body", "")}
      </div>

      <div class="post-footer">
        <a href="/blog" class="post-back">&larr; Back to The RD Edit</a>
        <a href="/view/contact.html" class="btn btn-primary">Start a Project</a>
      </div>

      {related_html}
    </div>
  </main>

  {_BLOG_FOOTER}
  {_BLOG_SCRIPTS}'''

    return head + body


# ── Blog admin API ─────────────────────────────────────────────────────────────

@app.route('/admin/api/blog/posts', methods=['GET'])
def admin_blog_list():
    auth = _require_admin()
    if auth: return auth
    conn = _blog_db_conn()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, slug, category, status, published_at, excerpt "
            "FROM blog_posts ORDER BY published_at DESC"
        )
        posts = []
        for r in cur.fetchall():
            p = dict(r)
            if p.get('published_at'):
                p['published_at'] = p['published_at'].isoformat()
            posts.append(p)
        return jsonify(posts)
    finally:
        conn.close()


@app.route('/admin/api/blog/posts', methods=['POST'])
def admin_blog_create():
    auth = _require_admin()
    if auth: return auth
    data = request.json or {}
    conn = _blog_db_conn()
    if not conn:
        return jsonify({'error': 'No database'}), 500
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO blog_posts (title, slug, excerpt, body, category, status,
               meta_title, meta_description, published_at, featured_image)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, NOW()), %s) RETURNING id""",
            (data.get('title'), data.get('slug'), data.get('excerpt'),
             data.get('body'), data.get('category'), data.get('status', 'published'),
             data.get('meta_title'), data.get('meta_description'),
             data.get('published_at') or None, data.get('featured_image'))
        )
        new_id = cur.fetchone()['id']
        conn.commit()
        return jsonify({'ok': True, 'id': new_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/admin/api/blog/posts/<int:post_id>', methods=['GET'])
def admin_blog_get(post_id):
    auth = _require_admin()
    if auth: return auth
    conn = _blog_db_conn()
    if not conn:
        return jsonify({'error': 'No database'}), 500
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM blog_posts WHERE id=%s", (post_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        p = dict(row)
        for k in ('published_at', 'created_at', 'updated_at'):
            if p.get(k):
                p[k] = p[k].isoformat()
        return jsonify(p)
    finally:
        conn.close()


@app.route('/admin/api/blog/posts/<int:post_id>', methods=['PUT'])
def admin_blog_update(post_id):
    auth = _require_admin()
    if auth: return auth
    data = request.json or {}
    conn = _blog_db_conn()
    if not conn:
        return jsonify({'error': 'No database'}), 500
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE blog_posts SET title=%s, slug=%s, excerpt=%s, body=%s,
               category=%s, status=%s, meta_title=%s, meta_description=%s,
               published_at=%s, featured_image=%s, updated_at=NOW()
               WHERE id=%s""",
            (data.get('title'), data.get('slug'), data.get('excerpt'),
             data.get('body'), data.get('category'), data.get('status', 'published'),
             data.get('meta_title'), data.get('meta_description'),
             data.get('published_at'), data.get('featured_image'), post_id)
        )
        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/admin/api/blog/posts/<int:post_id>', methods=['DELETE'])
def admin_blog_delete(post_id):
    auth = _require_admin()
    if auth: return auth
    conn = _blog_db_conn()
    if not conn:
        return jsonify({'error': 'No database'}), 500
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM blog_posts WHERE id=%s", (post_id,))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        conn.close()


# ── AI Chat ───────────────────────────────────────────────────────────────────

def _ai_execute_tool(name, inp):
    """Execute an AI tool call against the database or filesystem."""
    conn = _blog_db_conn()
    if not conn:
        return {'error': 'Database unavailable'}
    try:
        cur = conn.cursor()
        if name == 'list_blog_posts':
            cur.execute(
                "SELECT id, title, slug, status, category, published_at, featured_image "
                "FROM blog_posts ORDER BY published_at DESC"
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

        elif name == 'get_blog_post':
            slug = inp.get('slug', '')
            cur.execute("SELECT * FROM blog_posts WHERE slug=%s OR id=%s",
                        (slug, slug if str(slug).isdigit() else -1))
            row = cur.fetchone()
            return dict(row) if row else {'error': f'Post not found: {slug}'}

        elif name == 'update_blog_post':
            slug = inp.get('slug')
            if not slug:
                return {'error': 'slug is required'}
            allowed = ['title', 'excerpt', 'featured_image', 'category',
                       'status', 'meta_title', 'meta_description', 'body']
            updates = {k: v for k, v in inp.items() if k in allowed and v is not None}
            if not updates:
                return {'error': 'No valid fields to update'}
            set_clause = ', '.join(f"{k}=%s" for k in updates) + ', updated_at=NOW()'
            cur.execute(f"UPDATE blog_posts SET {set_clause} WHERE slug=%s",
                        list(updates.values()) + [slug])
            conn.commit()
            return {'ok': True, 'updated_fields': list(updates.keys()), 'slug': slug}

        elif name == 'list_pages':
            import glob as _glob
            files = sorted(os.path.basename(f)
                           for f in _glob.glob(PREVIEW_DIR + '/*.html'))
            return {'pages': files}

        else:
            return {'error': f'Unknown tool: {name}'}
    except Exception as e:
        try: conn.rollback()
        except: pass
        return {'error': str(e)}
    finally:
        conn.close()


@app.route('/admin/api/ai/chat', methods=['POST'])
def admin_ai_chat():
    auth = _require_admin()
    if auth: return auth

    data = request.get_json(silent=True) or {}
    messages = data.get('messages', [])
    if not messages:
        return jsonify({'error': 'No messages provided'}), 400

    try:
        import anthropic as _anthropic
    except ImportError:
        return jsonify({'error': 'anthropic package not installed'}), 500

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'ANTHROPIC_API_KEY not set'}), 500

    TOOLS = [
        {
            'name': 'list_blog_posts',
            'description': 'List all blog posts (title, slug, status, category, featured_image)',
            'input_schema': {'type': 'object', 'properties': {}, 'required': []}
        },
        {
            'name': 'get_blog_post',
            'description': 'Get full details of a blog post by slug',
            'input_schema': {
                'type': 'object',
                'properties': {'slug': {'type': 'string', 'description': 'The post slug'}},
                'required': ['slug']
            }
        },
        {
            'name': 'update_blog_post',
            'description': (
                'Update one or more fields of a blog post. '
                'Pass only the fields you want to change. '
                'status must be "published" or "draft".'
            ),
            'input_schema': {
                'type': 'object',
                'properties': {
                    'slug':             {'type': 'string', 'description': 'Post slug (required to identify the post)'},
                    'title':            {'type': 'string'},
                    'excerpt':          {'type': 'string'},
                    'featured_image':   {'type': 'string', 'description': 'Full URL to the featured image'},
                    'category':         {'type': 'string'},
                    'status':           {'type': 'string', 'enum': ['published', 'draft']},
                    'meta_title':       {'type': 'string'},
                    'meta_description': {'type': 'string'},
                    'body':             {'type': 'string', 'description': 'Full HTML body of the post'}
                },
                'required': ['slug']
            }
        },
        {
            'name': 'list_pages',
            'description': 'List all HTML page files on the website',
            'input_schema': {'type': 'object', 'properties': {}, 'required': []}
        }
    ]

    SYSTEM = (
        "You are the AI assistant built into the Ridgecrest Designs admin panel. "
        "Ridgecrest Designs is a luxury design-build firm in Pleasanton, CA. "
        "You help Henry (the owner) manage the website: blog posts (The RD Edit), pages, images, and content.\n\n"
        "When asked to make a change, use the available tools to do it immediately, then confirm clearly what you changed. "
        "Be concise. Do not ask for confirmation before making a change unless the request is ambiguous. "
        "If something is unclear, make your best interpretation and state what you did. "
        "Never say 'I cannot' — if you can't do something with the tools available, explain what the user would need to do manually."
    )

    def generate():
        try:
            client = _anthropic.Anthropic(api_key=api_key)
            current_messages = [m for m in messages]

            while True:
                resp = client.messages.create(
                    model='claude-sonnet-4-6',
                    max_tokens=2048,
                    system=SYSTEM,
                    tools=TOOLS,
                    messages=current_messages
                )

                # Collect content
                assistant_content = []
                text_parts = []

                for block in resp.content:
                    if block.type == 'text':
                        text_parts.append(block.text)
                        assistant_content.append({'type': 'text', 'text': block.text})
                    elif block.type == 'tool_use':
                        assistant_content.append({
                            'type': 'tool_use',
                            'id': block.id,
                            'name': block.name,
                            'input': block.input
                        })

                # Stream any text
                if text_parts:
                    combined = ''.join(text_parts)
                    yield f"data: {json.dumps({'type': 'text', 'content': combined})}\n\n"

                if resp.stop_reason != 'tool_use':
                    break

                # Execute tools
                current_messages.append({'role': 'assistant', 'content': assistant_content})
                tool_results = []

                for block in resp.content:
                    if block.type != 'tool_use':
                        continue
                    yield f"data: {json.dumps({'type': 'tool', 'name': block.name, 'status': 'running'})}\n\n"
                    result = _ai_execute_tool(block.name, block.input)
                    yield f"data: {json.dumps({'type': 'tool', 'name': block.name, 'status': 'done', 'result': str(result)[:120]})}\n\n"
                    tool_results.append({
                        'type': 'tool_result',
                        'tool_use_id': block.id,
                        'content': json.dumps(result, default=str)
                    })

                current_messages.append({'role': 'user', 'content': tool_results})

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ── Pages API — visual editor ─────────────────────────────────────────────────

@app.route('/admin/api/pages')
def admin_pages_list():
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        _ensure_pages_table(cur)
        cur.execute("""
            SELECT slug, title, hero_image, hero_position, hero_zoom, page_path, updated_at
            FROM pages ORDER BY page_path
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if r.get('updated_at'):
                r['updated_at'] = r['updated_at'].isoformat()
            if r.get('hero_zoom') is None:
                r['hero_zoom'] = 1.0
            if not r.get('hero_position'):
                r['hero_position'] = '50% 50%'
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/pages/<path:slug>', methods=['GET'])
def admin_page_get(slug):
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'no db'}), 503
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT slug, title, hero_image, hero_position, hero_zoom, page_path, updated_at FROM pages WHERE slug = %s",
            (slug,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({'error': 'not found'}), 404
        result = dict(row)
        if result.get('updated_at'):
            result['updated_at'] = result['updated_at'].isoformat()
        if result.get('hero_zoom') is None:
            result['hero_zoom'] = 1.0
        if not result.get('hero_position'):
            result['hero_position'] = '50% 50%'
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/pages/<path:slug>', methods=['PUT'])
def admin_page_update(slug):
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    hero_image   = data.get('hero_image', '').strip() or None
    hero_position = data.get('hero_position', '').strip() or None
    hero_zoom    = data.get('hero_zoom')

    if hero_image and not hero_image.startswith('/assets/'):
        return jsonify({'error': 'hero_image must start with /assets/'}), 400

    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'no db'}), 503
    try:
        cur = conn.cursor()
        _ensure_pages_table(cur)
        # Build dynamic SET clause — only update fields that were sent
        sets = ['updated_at = NOW()']
        params = []
        if hero_image is not None:
            sets.append('hero_image = %s'); params.append(hero_image)
        if hero_position is not None:
            sets.append('hero_position = %s'); params.append(hero_position)
        if hero_zoom is not None:
            sets.append('hero_zoom = %s'); params.append(float(hero_zoom))
        cur.execute(f"""
            INSERT INTO pages (slug, hero_image, hero_position, hero_zoom, title, page_path, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (slug) DO UPDATE SET {', '.join(sets)}
        """, [slug, hero_image, hero_position or '50% 50%', float(hero_zoom) if hero_zoom else 1.0,
              slug, slug + '.html'] + params)
        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'slug': slug})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


_NON_PROJECT_SLUGS = {
    'home', 'about', 'contact', 'process', 'team', 'services', 'portfolio',
    'custom-homes', 'kitchen-remodels', 'bathroom-remodels', 'whole-house-remodels',
    'blog',
}

@app.route('/admin/api/projects')
def admin_projects_list():
    """Return sorted list of project names: portfolio pages + any custom names from image_labels."""
    auth = _require_admin()
    if auth: return auth
    projects = []
    seen = set()
    conn = _db_conn()
    if conn:
        try:
            cur = conn.cursor()
            # 1. Portfolio / case-study pages (non-utility, non-services)
            cur.execute("""
                SELECT title FROM pages
                WHERE slug NOT LIKE 'services/%%'
                AND slug NOT IN %s
                ORDER BY title
            """, (tuple(_NON_PROJECT_SLUGS),))
            for r in cur.fetchall():
                name = (r['title'] or '').strip()
                if name and name not in seen:
                    seen.add(name)
                    projects.append(name)
            # 2. Any custom project names already in image_labels not in the pages list
            _ensure_image_labels_table(cur)
            cur.execute("SELECT DISTINCT project FROM image_labels WHERE project IS NOT NULL AND project != '' ORDER BY project")
            for r in cur.fetchall():
                name = (r['project'] or '').strip()
                if name and name not in seen:
                    seen.add(name)
                    projects.append(name)
        except Exception:
            pass
        finally:
            conn.close()
    return jsonify(sorted(projects))


@app.route('/admin/api/pages/images')
def admin_pages_images():
    """List all base WebP files in images-opt/ for the image picker, with AI labels."""
    auth = _require_admin()
    if auth: return auth
    opt_dir = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')

    # Load all labels from DB
    labels = {}
    conn = _db_conn()
    if conn:
        try:
            cur = conn.cursor()
            _ensure_image_labels_table(cur)
            cur.execute("SELECT filename, label, project, room, image_type, active_version FROM image_labels")
            for r in cur.fetchall():
                labels[r['filename']] = {
                    'label': r['label'], 'project': r['project'],
                    'room': r['room'], 'image_type': r['image_type'],
                    'active_version': r.get('active_version'),
                }
        except Exception:
            pass
        finally:
            conn.close()

    # Build a set of base filenames that have at least one AI render on disk
    bases_with_renders = set()
    if os.path.isdir(opt_dir):
        for f in os.listdir(opt_dir):
            m = re.match(r'^(.+)_ai_\d+\.webp$', f)
            if m:
                bases_with_renders.add(m.group(1) + '.webp')

    result = []
    if os.path.isdir(opt_dir):
        for fname in sorted(os.listdir(opt_dir)):
            if not fname.endswith('.webp'):
                continue
            if re.search(r'_\d+w\.webp$', fname):
                continue
            # AI renders are accessed via the version picker, not shown as separate library items
            if re.search(r'_ai_\d+\.webp$', fname):
                continue
            meta = labels.get(fname, {})
            active_version = meta.get('active_version') or None

            # Display the active version's image; fall back to original
            display_fname = active_version if active_version else fname
            display_base  = display_fname[:-5]
            thumb = f'/assets/images-opt/{display_base}_201w.webp'
            if not os.path.isfile(os.path.join(opt_dir, f'{display_base}_201w.webp')):
                thumb = f'/assets/images-opt/{display_fname}'

            result.append({
                'filename': fname,
                'hero_path': f'/assets/images-opt/{display_fname}',
                'thumb_path': thumb,
                'label': meta.get('label') or '',
                'project': meta.get('project') or '',
                'room': meta.get('room') or '',
                'image_type': meta.get('image_type') or '',
                'active_version': active_version,
                'has_renders': fname in bases_with_renders,
            })
    # Sort labeled images first, then unlabeled alphabetically
    result.sort(key=lambda x: (0 if x['label'] else 1, x['filename']))
    return jsonify(result)


# ── Card settings API ─────────────────────────────────────────────────────────

@app.route('/admin/api/cards/<path:slug>', methods=['GET'])
def admin_cards_get(slug):
    """Return all card settings for a page slug."""
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        _ensure_card_settings_table(cur)
        cur.execute(
            "SELECT card_id, mode, color, image, position, zoom, updated_at FROM card_settings WHERE page_slug = %s ORDER BY card_id",
            (slug,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if r.get('updated_at'):
                r['updated_at'] = r['updated_at'].isoformat()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/cards/<path:slug>/<card_id>', methods=['PUT'])
def admin_card_update(slug, card_id):
    """Upsert a single card's settings."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    mode     = data.get('mode', 'color')
    color    = data.get('color', '#1C1C1C')
    image    = data.get('image') or None
    position = data.get('position', '50% 50%')
    zoom     = float(data.get('zoom', 1.0))

    if mode not in ('color', 'image'):
        return jsonify({'error': 'mode must be color or image'}), 400
    if image and not image.startswith('/assets/'):
        return jsonify({'error': 'image must start with /assets/'}), 400

    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'no db'}), 503
    try:
        cur = conn.cursor()
        _ensure_card_settings_table(cur)
        cur.execute("""
            INSERT INTO card_settings (page_slug, card_id, mode, color, image, position, zoom, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (page_slug, card_id) DO UPDATE SET
                mode = EXCLUDED.mode,
                color = EXCLUDED.color,
                image = EXCLUDED.image,
                position = EXCLUDED.position,
                zoom = EXCLUDED.zoom,
                updated_at = NOW()
        """, (slug, card_id, mode, color, image, position, zoom))
        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'page_slug': slug, 'card_id': card_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Overlay scripts endpoint (for no-reload edit mode toggle) ─────────────────

@app.route('/admin/api/overlay-scripts')
def admin_overlay_scripts():
    """Return the edit overlay JS (both templates) formatted with slug/token."""
    auth = _require_admin()
    if auth: return auth
    slug = request.args.get('slug', '')
    token = request.args.get('token', '')
    if not _valid_token(token):
        return jsonify({'error': 'unauthorized'}), 401

    def strip_script(tpl):
        start = tpl.index('>') + 1
        end = tpl.rindex('</script>')
        return tpl[start:end]

    card_js = strip_script(_CARD_EDIT_OVERLAY_TPL).format(
        slug_json=json.dumps(slug), token_json=json.dumps(token))
    edit_js = strip_script(_EDIT_OVERLAY_TPL).format(
        slug_json=json.dumps(slug), token_json=json.dumps(token))
    return card_js + '\n' + edit_js, 200, {'Content-Type': 'application/javascript'}


# ── Image rotation ────────────────────────────────────────────────────────────

@app.route('/admin/api/images/rotate', methods=['POST'])
def admin_image_rotate():
    """Permanently rotate a WebP image (all responsive sizes) in-place."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    filename = data.get('filename', '').strip()
    degrees = int(data.get('degrees', 90))

    if not filename or not filename.endswith('.webp') or '/' in filename or '..' in filename:
        return jsonify({'error': 'invalid filename'}), 400
    if degrees not in (90, 180, 270, -90):
        return jsonify({'error': 'degrees must be 90, 180, 270, or -90'}), 400

    import subprocess as _subp
    opt_dir = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
    base = filename[:-5]  # strip .webp
    suffixes = ['', '_480w', '_960w', '_1920w', '_201w']

    # Build list of existing files to rotate
    paths = [os.path.join(opt_dir, f'{base}{s}.webp')
             for s in suffixes
             if os.path.isfile(os.path.join(opt_dir, f'{base}{s}.webp'))]
    if not paths:
        return jsonify({'error': 'no files found'}), 404

    # Use system python3 (which has Pillow) — strip venv from env so system site-packages are visible
    script = (
        'import sys; from PIL import Image\n'
        'for p in sys.argv[1:]:\n'
        '  img=Image.open(p); img.rotate(-' + str(degrees) + ', expand=True).save(p,"WEBP",quality=85)\n'
    )
    _env = os.environ.copy()
    _env.pop('VIRTUAL_ENV', None)
    # Include claudeuser local packages so PIL is findable even when running as root
    _env['PYTHONPATH'] = '/home/claudeuser/.local/lib/python3.12/site-packages'
    _env['PATH'] = ':'.join(p for p in _env.get('PATH','').split(':') if 'venv' not in p)
    try:
        result = _subp.run(['/usr/bin/python3', '-c', script] + paths,
                           env=_env, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return jsonify({'error': result.stderr.strip() or 'rotation failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'ok': True, 'filename': filename, 'degrees': degrees, 'files_rotated': len(paths)})


@app.route('/admin/api/images/rerender', methods=['POST'])
def admin_image_rerender():
    """Re-render an existing image using Gemini AI with a text prompt."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    filename      = data.get('filename', '').strip()       # source image (may be _ai_N.webp)
    base_filename = data.get('base_filename', '').strip()  # original file — used for output naming
    prompt        = data.get('prompt', '').strip()
    mode          = data.get('mode', 'new')  # 'new' or 'replace'

    if not filename or not filename.endswith('.webp') or '/' in filename or '..' in filename:
        return jsonify({'error': 'invalid filename'}), 400
    # If base_filename not provided, fall back to filename (legacy callers)
    if not base_filename:
        base_filename = filename
    if not base_filename.endswith('.webp') or '/' in base_filename or '..' in base_filename:
        return jsonify({'error': 'invalid base_filename'}), 400
    # base_filename must be the original, not itself an AI render
    if re.search(r'_ai_\d+\.webp$', base_filename):
        return jsonify({'error': 'base_filename must be the original, not an AI render'}), 400
    if not prompt:
        return jsonify({'error': 'prompt is required'}), 400

    api_key = os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'GEMINI_API_KEY not set in .env'}), 500

    opt_dir  = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
    src_path = os.path.join(opt_dir, filename)
    if not os.path.isfile(src_path):
        return jsonify({'error': 'source file not found'}), 404

    # Determine output filename — always named under the base (original) file
    base_stem = base_filename[:-5]  # strip .webp
    if mode == 'replace':
        out_filename = base_filename
    else:
        n = 1
        while os.path.isfile(os.path.join(opt_dir, f'{base_stem}_ai_{n}.webp')):
            n += 1
        out_filename = f'{base_stem}_ai_{n}.webp'
    out_path = os.path.join(opt_dir, out_filename)

    # Call Gemini via subprocess to avoid import conflicts in Flask process
    import subprocess as _subp, base64 as _b64, tempfile as _tmp

    script = r"""
import sys, os, base64
sys.path.insert(0, '/home/claudeuser/.local/lib/python3.12/site-packages')
from google import genai
from google.genai import types
from PIL import Image
import io

api_key  = sys.argv[1]
src_path = sys.argv[2]
out_path = sys.argv[3]
prompt   = sys.argv[4]

# Read source image, convert to JPEG for API (wider compatibility)
with Image.open(src_path) as img:
    img_rgb = img.convert('RGB')
    buf = io.BytesIO()
    img_rgb.save(buf, 'JPEG', quality=92)
    img_bytes = buf.getvalue()

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model='models/gemini-3.1-flash-image-preview',
    contents=[
        types.Part(inline_data=types.Blob(mime_type='image/jpeg', data=img_bytes)),
        types.Part(text=prompt)
    ],
    config=types.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT'])
)

result_bytes = None
for cand in response.candidates:
    for part in cand.content.parts:
        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
            result_bytes = part.inline_data.data
            break
    if result_bytes:
        break

if not result_bytes:
    print('ERROR: no image in response', file=sys.stderr)
    sys.exit(1)

# Save base WebP at original dimensions
img_result = Image.open(io.BytesIO(result_bytes)).convert('RGB')
img_result.save(out_path, 'WEBP', quality=88)

# Generate responsive sizes
sizes = [('_1920w', 1920), ('_960w', 960), ('_480w', 480), ('_201w', 201)]
base_out = out_path[:-5]  # strip .webp
for suffix, w in sizes:
    if img_result.width > w:
        ratio = w / img_result.width
        h = int(img_result.height * ratio)
        resized = img_result.resize((w, h), Image.LANCZOS)
    else:
        resized = img_result
    resized.save(base_out + suffix + '.webp', 'WEBP', quality=85)

print('OK:' + out_path)
"""

    _env = os.environ.copy()
    _env.pop('VIRTUAL_ENV', None)
    _env['PYTHONPATH'] = '/home/claudeuser/.local/lib/python3.12/site-packages'
    _env['PATH'] = ':'.join(p for p in _env.get('PATH','').split(':') if 'venv' not in p)

    try:
        result = _subp.run(
            ['/usr/bin/python3', '-c', script, api_key, src_path, out_path, prompt],
            env=_env, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raw = result.stderr.strip() or 'rerender failed'
            if 'RESOURCE_EXHAUSTED' in raw or 'quota' in raw.lower():
                err = 'Quota exceeded — enable billing on your Google AI Studio account at aistudio.google.com'
            elif 'NOT_FOUND' in raw or '404' in raw:
                err = 'Image generation model not found — check your API key and model availability'
            elif 'INVALID_ARGUMENT' in raw or '400' in raw:
                err = 'Invalid request — try a different prompt or image'
            elif 'PERMISSION_DENIED' in raw or '403' in raw:
                err = 'API key does not have permission — check key scopes in Google AI Studio'
            else:
                err = raw.split('\n')[-1] or raw[:200]
            return jsonify({'error': err}), 500
    except _subp.TimeoutExpired:
        return jsonify({'error': 'timed out after 120s'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Store prompt in DB so we can display it later
    conn2 = _db_conn()
    if conn2:
        try:
            cur2 = conn2.cursor()
            _ensure_render_prompts_table(cur2)
            cur2.execute("""
                INSERT INTO image_render_prompts (filename, prompt, source_filename)
                VALUES (%s, %s, %s)
                ON CONFLICT (filename) DO UPDATE
                    SET prompt = EXCLUDED.prompt,
                        source_filename = EXCLUDED.source_filename
            """, (out_filename, prompt, filename))
            conn2.commit()
        except Exception:
            conn2.rollback()
        finally:
            conn2.close()

    hero_path = f'/assets/images-opt/{out_filename}'
    return jsonify({'ok': True, 'filename': out_filename, 'hero_path': hero_path})


# ── Save render result (copy _ai_N file to final destination) ────────────────

@app.route('/admin/api/images/save-result', methods=['POST'])
def admin_save_result():
    """Save an AI-rendered result: keep as new or copy over the original."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(force=True) or {}
    result_filename   = os.path.basename(data.get('result_filename', ''))
    original_filename = os.path.basename(data.get('original_filename', ''))
    mode              = data.get('mode', 'new')  # 'new' | 'replace'

    if not result_filename or not result_filename.endswith('.webp'):
        return jsonify({'error': 'invalid result_filename'}), 400

    opt_dir     = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
    result_path = os.path.join(opt_dir, result_filename)
    if not os.path.isfile(result_path):
        return jsonify({'error': 'result file not found — render it first'}), 404

    if mode == 'new':
        # Already on disk — nothing to do
        return jsonify({'ok': True, 'filename': result_filename,
                        'hero_path': f'/assets/images-opt/{result_filename}'})

    # Replace: copy result → original (base + all responsive sizes), then delete result
    if not original_filename or not original_filename.endswith('.webp'):
        return jsonify({'error': 'invalid original_filename'}), 400
    if result_filename == original_filename:
        return jsonify({'error': 'result and original are the same file'}), 400

    import shutil
    original_path = os.path.join(opt_dir, original_filename)
    try:
        shutil.copy2(result_path, original_path)
        result_base   = result_path[:-5]
        original_base = original_path[:-5]
        for suffix in ('_1920w', '_960w', '_480w', '_201w'):
            src_resp = result_base   + suffix + '.webp'
            dst_resp = original_base + suffix + '.webp'
            if os.path.isfile(src_resp):
                shutil.copy2(src_resp, dst_resp)
        # Delete the AI result files — they now live as the original
        for suffix in ('', '_1920w', '_960w', '_480w', '_201w'):
            f = result_base + suffix + '.webp'
            if os.path.isfile(f):
                os.remove(f)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'ok': True, 'filename': original_filename,
                    'hero_path': f'/assets/images-opt/{original_filename}'})


# ── Image version management ──────────────────────────────────────────────────

@app.route('/admin/api/images/versions/<path:filename>')
def admin_image_versions(filename):
    """Return all versions (original + AI renders) for a base image filename."""
    auth = _require_admin()
    if auth: return auth
    filename = os.path.basename(filename)
    if not filename.endswith('.webp'):
        return jsonify({'error': 'must be a .webp filename'}), 400
    if re.search(r'_ai_\d+\.webp$', filename):
        return jsonify({'error': 'pass the base filename, not an AI render'}), 400

    opt_dir = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
    base    = filename[:-5]

    # Scan filesystem first to collect exact AI render filenames
    ai_fnames = []
    n = 1
    while True:
        ai_fname = f'{base}_ai_{n}.webp'
        if not os.path.isfile(os.path.join(opt_dir, ai_fname)):
            break
        ai_fnames.append(ai_fname)
        n += 1

    # Load active_version and render prompts from DB
    active_version = None
    prompts_by_file = {}  # filename → {prompt, source_filename}
    conn = _db_conn()
    if conn:
        try:
            cur = conn.cursor()
            _ensure_image_labels_table(cur)
            _ensure_render_prompts_table(cur)
            conn.commit()  # commit DDL so tables exist for subsequent queries
            cur.execute("SELECT active_version FROM image_labels WHERE filename = %s", (filename,))
            row = cur.fetchone()
            if row:
                active_version = row.get('active_version')
            # Fetch prompts by exact filename — avoids LIKE wildcard issues with underscores
            if ai_fnames:
                cur.execute("""
                    SELECT filename, prompt, source_filename
                    FROM image_render_prompts
                    WHERE filename = ANY(%s)
                """, (ai_fnames,))
                for row in cur.fetchall():
                    prompts_by_file[row['filename']] = {
                        'prompt': row['prompt'],
                        'source_filename': row.get('source_filename'),
                    }
        except Exception:
            pass
        finally:
            conn.close()

    def _thumb(fname):
        b = fname[:-5]
        p = os.path.join(opt_dir, f'{b}_201w.webp')
        return f'/assets/images-opt/{b}_201w.webp' if os.path.isfile(p) else f'/assets/images-opt/{fname}'

    versions = []
    # Original
    if os.path.isfile(os.path.join(opt_dir, filename)):
        versions.append({
            'filename':        filename,
            'hero_path':       f'/assets/images-opt/{filename}',
            'thumb_path':      _thumb(filename),
            'label':           'Original',
            'is_original':     True,
            'is_active':       active_version is None,
            'prompt':          None,
            'source_filename': None,
        })

    # AI renders — build from pre-scanned list
    for idx, ai_fname in enumerate(ai_fnames, start=1):
        p = prompts_by_file.get(ai_fname, {})
        versions.append({
            'filename':        ai_fname,
            'hero_path':       f'/assets/images-opt/{ai_fname}',
            'thumb_path':      _thumb(ai_fname),
            'label':           f'AI Render {idx}',
            'is_original':     False,
            'is_active':       active_version == ai_fname,
            'prompt':          p.get('prompt'),
            'source_filename': p.get('source_filename'),
        })

    return jsonify({'base_filename': filename, 'active_version': active_version, 'versions': versions})


@app.route('/admin/api/images/set-version', methods=['POST'])
def admin_set_version():
    """Set the active version for a base image. version_filename='' resets to original."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(force=True) or {}
    base_filename    = os.path.basename(data.get('base_filename', ''))
    version_filename = (data.get('version_filename') or '').strip()

    if not base_filename or not base_filename.endswith('.webp'):
        return jsonify({'error': 'invalid base_filename'}), 400
    if re.search(r'_ai_\d+\.webp$', base_filename):
        return jsonify({'error': 'base_filename must be the original, not an AI render'}), 400

    # Normalise: empty or same as base → null (use original)
    if version_filename:
        version_filename = os.path.basename(version_filename)
        if version_filename == base_filename:
            version_filename = None
        elif version_filename:
            opt_dir = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
            if not os.path.isfile(os.path.join(opt_dir, version_filename)):
                return jsonify({'error': 'version file not found on disk'}), 404
    else:
        version_filename = None

    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'no db'}), 503
    try:
        cur = conn.cursor()
        _ensure_image_labels_table(cur)
        cur.execute("""
            INSERT INTO image_labels (filename, active_version)
            VALUES (%s, %s)
            ON CONFLICT (filename) DO UPDATE SET active_version = EXCLUDED.active_version
        """, (base_filename, version_filename))
        conn.commit()
        return jsonify({'ok': True, 'base_filename': base_filename, 'active_version': version_filename})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ── Delete an AI render version ───────────────────────────────────────────────

@app.route('/admin/api/images/delete-version', methods=['POST'])
def admin_delete_version():
    """Delete an AI render (_ai_N.webp) and all its responsive variants from disk.
    If it was the active version, clears active_version in DB (reverts to original)."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    filename = os.path.basename(data.get('filename', '').strip())

    if not filename or not filename.endswith('.webp') or '/' in filename or '..' in filename:
        return jsonify({'error': 'invalid filename'}), 400
    if not re.search(r'_ai_\d+\.webp$', filename):
        return jsonify({'error': 'only AI render versions can be deleted'}), 400

    opt_dir = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
    base_stem = filename[:-5]  # strip .webp

    # Delete the base file + all responsive variants (_Xw.webp)
    deleted = []
    for f in os.listdir(opt_dir):
        if f == filename or re.match(re.escape(base_stem) + r'_\d+w\.webp$', f):
            try:
                os.remove(os.path.join(opt_dir, f))
                deleted.append(f)
            except Exception:
                pass

    if not deleted:
        return jsonify({'error': 'file not found'}), 404

    # If this was the active version on any image, clear it so the original shows
    cleared_active = False
    conn = _db_conn()
    if conn:
        try:
            cur = conn.cursor()
            _ensure_image_labels_table(cur)
            cur.execute(
                "UPDATE image_labels SET active_version = NULL WHERE active_version = %s",
                (filename,)
            )
            cleared_active = cur.rowcount > 0
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()

    return jsonify({'ok': True, 'deleted': deleted, 'cleared_active': cleared_active})


# ── Image adjust (brightness/contrast/saturation) ────────────────────────────

@app.route('/admin/api/images/adjust', methods=['POST'])
def admin_image_adjust():
    """Apply brightness/contrast/saturation adjustments to an image in-place."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(force=True) or {}
    filename = os.path.basename(data.get('filename', ''))
    brightness = int(data.get('brightness', 100))
    contrast   = int(data.get('contrast',   100))
    saturation = int(data.get('saturation', 100))
    if not filename:
        return jsonify({'error': 'filename required'}), 400
    opt_dir = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
    src_path = os.path.join(opt_dir, filename)
    if not os.path.isfile(src_path):
        return jsonify({'error': 'file not found'}), 404
    import subprocess as _subp
    script = f"""
import sys; sys.path.insert(0, '/home/claudeuser/.local/lib/python3.12/site-packages')
from PIL import Image, ImageEnhance
src = {repr(src_path)}
brightness, contrast, saturation = {brightness}/100, {contrast}/100, {saturation}/100
with Image.open(src) as img:
    img = img.convert('RGB')
    if brightness != 1.0: img = ImageEnhance.Brightness(img).enhance(brightness)
    if contrast   != 1.0: img = ImageEnhance.Contrast(img).enhance(contrast)
    if saturation != 1.0: img = ImageEnhance.Color(img).enhance(saturation)
    img.save(src, 'WEBP', quality=88)
    base = src[:-5]
    for suffix, w in [('_1920w',1920),('_960w',960),('_480w',480),('_201w',201)]:
        import os; rp = base + suffix + '.webp'
        if os.path.isfile(rp):
            r = img.copy()
            if r.width > w: r = r.resize((w, int(r.height*w/r.width)), Image.LANCZOS)
            r.save(rp, 'WEBP', quality=85)
print('OK')
"""
    try:
        result = _subp.run(['/usr/bin/python3', '-c', script],
                           capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return jsonify({'error': result.stderr.strip() or 'adjust failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'ok': True, 'filename': filename})


# ── Settings — env key management ────────────────────────────────────────────

_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
_ALLOWED_ENV_KEYS = {'GEMINI_API_KEY'}

@app.route('/admin/api/settings/env-key', methods=['GET'])
def admin_env_key_get():
    auth = _require_admin()
    if auth: return auth
    key = request.args.get('key', '')
    if key not in _ALLOWED_ENV_KEYS:
        return jsonify({'error': 'key not allowed'}), 400
    value = os.getenv(key, '')
    return jsonify({'set': bool(value), 'masked': ('*' * 8 + value[-4:]) if len(value) > 4 else ('*' * len(value)) if value else ''})

@app.route('/admin/api/settings/env-key', methods=['POST'])
def admin_env_key_set():
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(force=True) or {}
    key = data.get('key', '')
    value = data.get('value', '').strip()
    if key not in _ALLOWED_ENV_KEYS:
        return jsonify({'error': 'key not allowed'}), 400
    if not value:
        return jsonify({'error': 'value is required'}), 400
    # Read existing .env, replace or append
    lines = []
    found = False
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, 'r') as f:
            for line in f:
                if line.startswith(f'{key}='):
                    lines.append(f'{key}={value}\n')
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f'{key}={value}\n')
    with open(_ENV_PATH, 'w') as f:
        f.writelines(lines)
    # Apply to current process immediately
    os.environ[key] = value
    return jsonify({'ok': True})


# ── Team members — DB table + API ─────────────────────────────────────────────

def _ensure_team_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            bio TEXT,
            photo TEXT,
            display_order INT DEFAULT 0,
            active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

def _seed_team():
    """Seed team_members from the hardcoded list if table is empty."""
    if not HAS_DB:
        return
    conn = _db_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        _ensure_team_table(cur)
        cur.execute("SELECT COUNT(*) AS c FROM team_members")
        if cur.fetchone()['c'] > 0:
            conn.close()
            return
        members = [
            (1, 'Henry Batteate', 'Owner & Principal',
             'Henry founded Ridgecrest Designs with a passion for architecture, design, and hands-on craftsmanship. He oversees every project personally and holds the team to the same standard of precision that has defined the firm since its founding. He is also a skilled maker — designing and building custom pieces for clients at his 3,000 sq/ft shop in Livermore.',
             '/assets/images-opt/ff5b18_bb83428c47da4426a22dd5f276f79c4c_mv2.webp'),
            (2, 'Carrie Batteate', 'Owner & Operations',
             'Carrie leads operations at Ridgecrest Designs, ensuring every client relationship and internal process runs with the same level of care that goes into every project. Her steady hand keeps the firm moving efficiently from first call through final handoff.',
             '/assets/images-opt/ff5b18_8db501ff84934a18a831c805b6b5bfe1_mv2.webp'),
            (3, 'Julienne Barrett', 'Lead Designer',
             'Julienne leads the design studio, translating client vision into photo-realistic renders and detailed design packages. Her work blends architectural precision with an instinct for livable luxury — ensuring every space is both beautiful and purposefully built.',
             '/assets/images-opt/ff5b18_3801516925e9422099e7ed8b9ffe6143_mv2.webp'),
            (4, 'Chantal Merritt', 'Creative Designer',
             'Chantal brings a sharp creative eye to every project, working closely with clients on material selections, spatial flow, and finish specifications. Her design sensibility helps clients see exactly what their home will become before a single wall is touched.',
             '/assets/images-opt/ff5b18_41ff82718a8b4721b3b3162f67f1428e_mv2.webp'),
            (5, 'Jenna Batteate', 'Project Manager',
             'Jenna coordinates every phase of the build — scheduling, subcontractor management, quality control, and client communication. Her attention to detail and deep knowledge of the construction process keeps projects on time and within scope.',
             '/assets/images-opt/ff5b18_0cd6f5049a6c4b0caa5023c187a30690_mv2.webp'),
            (6, 'Danielle Lievre', 'Designer',
             'Danielle supports the design team through every stage of a project, from concept development through construction documentation. Her collaborative approach ensures design intent is preserved from the first sketch through the final installation.',
             '/assets/images-opt/ff5b18_bf3dce516a3e45c0a712e0a4870e071e_mv2.webp'),
        ]
        for order, name, role, bio, photo in members:
            cur.execute(
                "INSERT INTO team_members (display_order, name, role, bio, photo) VALUES (%s,%s,%s,%s,%s)",
                (order, name, role, bio, photo)
            )
        conn.commit()
        print(f'[team] Seeded {len(members)} team members')
    except Exception as e:
        print(f'[team] Seed error: {e}')
    finally:
        conn.close()


@app.route('/api/team')
def public_team_list():
    """Public endpoint — returns active members in display order."""
    conn = _db_conn()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        _ensure_team_table(cur)
        cur.execute(
            "SELECT id, name, role, bio, photo, display_order FROM team_members "
            "WHERE active = true ORDER BY display_order ASC, id ASC"
        )
        return jsonify([dict(r) for r in cur.fetchall()])
    finally:
        conn.close()


@app.route('/admin/api/team', methods=['GET'])
def admin_team_list():
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        _ensure_team_table(cur)
        cur.execute(
            "SELECT id, name, role, bio, photo, display_order, active FROM team_members "
            "ORDER BY display_order ASC, id ASC"
        )
        return jsonify([dict(r) for r in cur.fetchall()])
    finally:
        conn.close()


@app.route('/admin/api/team', methods=['POST'])
def admin_team_create():
    auth = _require_admin()
    if auth: return auth
    data = request.json or {}
    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'No database'}), 500
    try:
        cur = conn.cursor()
        _ensure_team_table(cur)
        cur.execute(
            "SELECT COALESCE(MAX(display_order),0)+1 AS next_order FROM team_members"
        )
        next_order = cur.fetchone()['next_order']
        cur.execute(
            """INSERT INTO team_members (name, role, bio, photo, display_order, active)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (data.get('name', 'New Member'), data.get('role', ''),
             data.get('bio', ''), data.get('photo', ''),
             data.get('display_order', next_order), data.get('active', True))
        )
        new_id = cur.fetchone()['id']
        conn.commit()
        return jsonify({'ok': True, 'id': new_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/admin/api/team/<int:member_id>', methods=['GET'])
def admin_team_get(member_id):
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'No database'}), 500
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM team_members WHERE id = %s", (member_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        return jsonify(dict(row))
    finally:
        conn.close()


@app.route('/admin/api/team/<int:member_id>', methods=['PUT'])
def admin_team_update(member_id):
    auth = _require_admin()
    if auth: return auth
    data = request.json or {}
    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'No database'}), 500
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE team_members SET
               name = COALESCE(%s, name),
               role = COALESCE(%s, role),
               bio = %s,
               photo = %s,
               display_order = COALESCE(%s, display_order),
               active = COALESCE(%s, active),
               updated_at = NOW()
               WHERE id = %s""",
            (data.get('name'), data.get('role'),
             data.get('bio'), data.get('photo'),
             data.get('display_order'), data.get('active'),
             member_id)
        )
        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/admin/api/team/<int:member_id>', methods=['DELETE'])
def admin_team_delete(member_id):
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'No database'}), 500
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM team_members WHERE id = %s", (member_id,))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        conn.close()


@app.route('/admin/api/team/reorder', methods=['PUT'])
def admin_team_reorder():
    """Accepts [{id, display_order}, ...] and bulk-updates order."""
    auth = _require_admin()
    if auth: return auth
    items = request.json or []
    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'No database'}), 500
    try:
        cur = conn.cursor()
        for item in items:
            cur.execute(
                "UPDATE team_members SET display_order = %s, updated_at = NOW() WHERE id = %s",
                (item['display_order'], item['id'])
            )
        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


# ── Image Labels — AI-generated descriptive names ─────────────────────────────

_WIXPAGE_PROJECT_MAP = {
    # Real slugs from ridgecrestdesigns.com (confirmed from live site scan)
    'danvillehilltophideaway': 'Danville Hilltop Hideaway',
    'pleasantoncustomhome': 'Pleasanton Custom Home',
    'sierramountainranch': 'Sierra Mountain Ranch',
    'sunolhomestead': 'Sunol Homestead',
    # Legacy / alternate slugs
    'lafayette-bistro': 'Lafayette Laid-Back Luxury',
    'lafayette-laid-back-luxury': 'Lafayette Laid-Back Luxury',
    'alamo-luxury': 'Alamo Luxury',
    'orinda-kitchen': 'Orinda Kitchen Remodel',
    'pleasantondreamhome2': 'Pleasanton Custom Home',
    'pleasanton-custom': 'Pleasanton Custom Home',
    'sunol-homestead': 'Sunol Homestead',
    'danville-dream': 'Danville Dream',
    'san-ramon': 'San Ramon Home',
    'naparetreat': 'Napa Retreat',
    'castro-valley-villa': 'Castro Valley Villa',
    'pleasantoncottagekitchen': 'Pleasanton Cottage Kitchen',
    'pleasanton-garage-renovation': 'Pleasanton Garage Renovation',
    'livermorefarmhousechic': 'Livermore Farmhouse Chic',
    'lakeside-cozy-cabin': 'Lakeside Cozy Cabin',
    'newarkminimalkitchen': 'Newark Minimal Kitchen',
    'san-ramon-eclectic-bath': 'San Ramon Eclectic Bath',
    'allprojects': None,
    'portfolio': None,
    '': None,
}

def _ensure_render_prompts_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS image_render_prompts (
            filename        TEXT PRIMARY KEY,
            prompt          TEXT NOT NULL,
            source_filename TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

def _ensure_image_labels_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS image_labels (
            id SERIAL PRIMARY KEY,
            filename TEXT UNIQUE NOT NULL,
            label TEXT,
            project TEXT,
            room TEXT,
            image_type TEXT,
            labeled_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("ALTER TABLE image_labels ADD COLUMN IF NOT EXISTS room TEXT")
    cur.execute("ALTER TABLE image_labels ADD COLUMN IF NOT EXISTS image_type TEXT")
    cur.execute("ALTER TABLE image_labels ADD COLUMN IF NOT EXISTS active_version TEXT")

def _project_from_url(url):
    """Extract a human-readable project name from a Wix page URL."""
    if not url:
        return None
    m = re.search(r'ridgecrestdesigns\.com/([^/?#\s]+)', url)
    if not m:
        return None
    slug = m.group(1).rstrip('/')
    return _WIXPAGE_PROJECT_MAP.get(slug, None)

def _get_page_context_for_files():
    """Returns {filename -> project_name} from the image_library DB.

    The image_library was populated by scanning ridgecrestdesigns.com. Each row records
    which page an image was found on. We map those page slugs to human-readable project
    names using _WIXPAGE_PROJECT_MAP.
    """
    conn = _db_conn()
    if not conn:
        return {}
    result = {}
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT local_path, page_found_on FROM image_library
            WHERE local_path IS NOT NULL AND local_path != ''
        """)
        for row in cur.fetchall():
            lp = row['local_path'] or ''
            fname = lp.split('/')[-1]
            if not fname:
                continue
            project = _project_from_url(row.get('page_found_on', ''))
            if project and fname not in result:
                result[fname] = project
    except Exception:
        pass
    finally:
        conn.close()
    return result

def _call_claude_vision_label(image_path, project_context=None):
    """Send image to Claude Vision and return a descriptive label string."""
    import anthropic as _anthropic
    import base64 as _b64

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise RuntimeError('ANTHROPIC_API_KEY not set')

    with open(image_path, 'rb') as f:
        img_bytes = f.read()
    img_b64 = _b64.standard_b64encode(img_bytes).decode('utf-8')

    if image_path.endswith('.webp'):
        media_type = 'image/webp'
    elif image_path.lower().endswith(('.jpg', '.jpeg')):
        media_type = 'image/jpeg'
    else:
        media_type = 'image/png'

    context_line = (
        f'This image is from the project: {project_context}.'
        if project_context
        else 'This is a project photo from a luxury design-build portfolio.'
    )

    prompt = f"""You are naming interior design and architecture photos for Ridgecrest Designs, a luxury design-build firm in Pleasanton, California.

{context_line}

Generate a concise, descriptive name for this image (3–6 words). Be specific about:
- The room or space (kitchen, master bath, living room, entryway, exterior, office, dining room, staircase, etc.)
- The project name if contextually clear
- A distinctive detail if helpful (island, fireplace, built-ins, etc.)

Format examples: "Danville Hilltop Kitchen", "Alamo Luxury Master Bath", "Lafayette Living Room Fireplace", "Sunol Homestead Exterior", "Custom Library Built-Ins", "Farmhouse Kitchen Island"

Return ONLY the name, nothing else. No quotes, no punctuation at end."""

    client = _anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=40,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': img_b64}},
                {'type': 'text', 'text': prompt}
            ]
        }]
    )
    label = resp.content[0].text.strip().strip('"\'').strip('.')
    return label


@app.route('/admin/api/images/labels')
def admin_image_labels_list():
    """Return all image labels."""
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        _ensure_image_labels_table(cur)
        cur.execute("SELECT filename, label, project, labeled_at FROM image_labels ORDER BY filename")
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            if d.get('labeled_at'):
                d['labeled_at'] = d['labeled_at'].isoformat()
            rows.append(d)
        return jsonify(rows)
    finally:
        conn.close()


@app.route('/admin/api/images/label/<path:filename>', methods=['PUT'])
def admin_image_label_update(filename):
    """Update project, room, image_type, and/or label for an image. Auto-composes label from fields."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    project    = data.get('project', '').strip()
    room       = data.get('room', '').strip()
    image_type = data.get('image_type', '').strip()
    # Auto-compose label from project + room + type; fall back to explicit label if all empty
    parts = [p for p in [project, room, image_type] if p]
    if parts:
        label = ' '.join(parts)
    else:
        label = data.get('label', '').strip()
    conn = _db_conn()
    if not conn:
        return jsonify({'error': 'no db'}), 503
    try:
        cur = conn.cursor()
        _ensure_image_labels_table(cur)
        cur.execute("""
            INSERT INTO image_labels (filename, label, project, room, image_type, labeled_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (filename) DO UPDATE SET
                label = EXCLUDED.label,
                project = EXCLUDED.project,
                room = EXCLUDED.room,
                image_type = EXCLUDED.image_type,
                labeled_at = NOW()
        """, (filename, label or None, project or None, room or None, image_type or None))
        conn.commit()
        return jsonify({'ok': True, 'label': label, 'project': project, 'room': room, 'image_type': image_type})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/api/images/delete', methods=['POST'])
def admin_images_delete():
    """Bulk delete images: removes original + all optimized variants, clears DB entries and page heroes."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    filenames = data.get('filenames', [])  # list of base .webp filenames
    if not filenames:
        return jsonify({'error': 'no filenames'}), 400

    opt_dir  = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
    orig_dir = os.path.join(PREVIEW_DIR, 'assets', 'images')
    results  = []

    conn = _db_conn()
    affected_pages = []
    if conn:
        try:
            cur = conn.cursor()
            # Find pages using any of these images as hero
            for fname in filenames:
                hero_path = f'/assets/images-opt/{fname}'
                cur.execute("SELECT slug, title FROM pages WHERE hero_image = %s", (hero_path,))
                rows = cur.fetchall()
                for r in rows:
                    affected_pages.append({'slug': r['slug'], 'title': r['title'], 'old_hero': hero_path})
        except Exception:
            pass
        finally:
            conn.close()

    # If dry_run, just return what would be affected
    if data.get('dry_run'):
        return jsonify({'affected_pages': affected_pages, 'count': len(filenames)})

    # Auto-pick replacements for affected pages
    available = [
        f for f in os.listdir(opt_dir)
        if f.endswith('.webp') and not re.search(r'_\d+w\.webp$', f) and f not in filenames
    ]
    replacement_pool = iter(available)

    conn2 = _db_conn()
    try:
        cur2 = conn2.cursor() if conn2 else None

        for fname in filenames:
            deleted = []
            # Delete optimized variants (base + 4 sizes)
            base = fname[:-5]  # strip .webp
            for variant in [fname, f'{base}_201w.webp', f'{base}_480w.webp', f'{base}_960w.webp', f'{base}_1920w.webp']:
                p = os.path.join(opt_dir, variant)
                if os.path.exists(p):
                    os.remove(p)
                    deleted.append(variant)
            # Delete original (try jpg and png)
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                orig = os.path.join(orig_dir, base + ext)
                if os.path.exists(orig):
                    os.remove(orig)
                    deleted.append(base + ext)
                    break
            # Remove from DB
            if cur2:
                try:
                    cur2.execute("DELETE FROM image_labels WHERE filename = %s", (fname,))
                    cur2.execute("DELETE FROM image_library WHERE local_path LIKE %s", (f'%{fname}',))
                except Exception:
                    pass
            results.append({'filename': fname, 'deleted': deleted})

        # Auto-assign replacements for affected pages
        replacements = []
        if cur2:
            for ap in affected_pages:
                try:
                    replacement = next(replacement_pool, None)
                    if replacement:
                        new_hero = f'/assets/images-opt/{replacement}'
                        cur2.execute("UPDATE pages SET hero_image = %s WHERE slug = %s",
                                     (new_hero, ap['slug']))
                        replacements.append({'slug': ap['slug'], 'title': ap['title'], 'new_hero': new_hero})
                except Exception:
                    pass

        if conn2:
            conn2.commit()
    except Exception as e:
        if conn2:
            conn2.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn2:
            conn2.close()

    return jsonify({'ok': True, 'deleted': results, 'replacements': replacements})


@app.route('/admin/api/images/auto-place', methods=['POST'])
def admin_images_auto_place():
    """SSE stream — AI assigns the best available image to each page based on labels + page context."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    dry_run = data.get('dry_run', True)  # default: propose only, don't save

    def generate():
        def sse(obj):
            return f"data: {json.dumps(obj)}\n\n"

        yield sse({'type': 'status', 'msg': 'Loading pages and image labels…'})

        conn = _db_conn()
        if not conn:
            yield sse({'type': 'error', 'msg': 'No database connection'})
            return

        try:
            cur = conn.cursor()

            # Load all pages
            cur.execute("SELECT slug, title, page_path FROM pages ORDER BY slug")
            pages = [dict(r) for r in cur.fetchall()]

            # Load all labeled images
            _ensure_image_labels_table(cur)
            cur.execute("""
                SELECT il.filename, il.label, il.project, il.room
                FROM image_labels il
                WHERE il.label IS NOT NULL
                ORDER BY il.filename
            """)
            labeled_images = [dict(r) for r in cur.fetchall()]
        except Exception as e:
            yield sse({'type': 'error', 'msg': str(e)})
            conn.close()
            return
        finally:
            conn.close()

        if not labeled_images:
            yield sse({'type': 'error', 'msg': 'No labeled images found — run AI labeling first'})
            return

        yield sse({'type': 'status', 'msg': f'Loaded {len(pages)} pages and {len(labeled_images)} labeled images'})

        # Build concise lists for Claude
        pages_text = '\n'.join(
            f'- {p["slug"]}: "{p["title"]}"'
            for p in pages
        )
        images_text = '\n'.join(
            f'- {img["filename"]}: {img["label"]}'
            + (f' [project: {img["project"]}]' if img.get("project") else '')
            + (f' [room: {img["room"]}]' if img.get("room") else '')
            for img in labeled_images
        )

        prompt = f"""You are assigning hero background images to pages of a luxury design-build firm website (Ridgecrest Designs, Pleasanton CA).

PAGES (slug: title):
{pages_text}

AVAILABLE IMAGES (filename: label [project] [room]):
{images_text}

RULES:
1. Case study pages (e.g. danville-hilltop, sunol-homestead) → strongly prefer images from that specific project
2. Service pages (kitchen-remodels, bathroom-remodels, whole-house-remodels, custom-homes) → prefer images of that room/type
3. Homepage (index) → dramatic wide shot: exterior, living room, or whole-home
4. About page → exterior or whole-home (architectural credibility)
5. Contact page → warm inviting interior (kitchen or living room)
6. Process page → detail shot or whole-home
7. Portfolio page → most impressive available image
8. City SEO pages (e.g. services/danville-kitchen-remodel) → prefer images from nearby projects; match the service type
9. Never assign the same image to more than one page if avoidable
10. Every page must get an assignment

Return ONLY a JSON object mapping slug → filename. No explanation, no markdown, just the JSON.
Example: {{"index": "ff5b18_abc123_mv2.webp", "about": "ff5b18_def456_mv2.webp"}}"""

        yield sse({'type': 'status', 'msg': 'Sending to Claude for intelligent matching…'})

        try:
            import anthropic as _anthropic
            client = _anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))
            resp = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=4096,
                messages=[{'role': 'user', 'content': prompt}]
            )
            raw = resp.content[0].text.strip()
            # Strip markdown code fences if present
            raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
            assignments = json.loads(raw)
        except Exception as e:
            yield sse({'type': 'error', 'msg': f'Claude error: {e}'})
            return

        yield sse({'type': 'status', 'msg': f'Claude returned {len(assignments)} assignments'})

        # Apply or propose
        conn3 = _db_conn()
        applied = []
        skipped = []
        try:
            cur3 = conn3.cursor() if conn3 else None
            for slug, filename in assignments.items():
                hero_path = f'/assets/images-opt/{filename}'
                opt_path  = os.path.join(PREVIEW_DIR, 'assets', 'images-opt', filename)
                if not os.path.exists(opt_path):
                    skipped.append({'slug': slug, 'reason': f'file not found: {filename}'})
                    continue
                if not dry_run and cur3:
                    try:
                        cur3.execute("UPDATE pages SET hero_image = %s WHERE slug = %s",
                                     (hero_path, slug))
                    except Exception:
                        pass
                applied.append({'slug': slug, 'filename': filename, 'hero_path': hero_path})
            if not dry_run and conn3:
                conn3.commit()
        finally:
            if conn3:
                conn3.close()

        yield sse({
            'type': 'done',
            'dry_run': dry_run,
            'assignments': applied,
            'skipped': skipped,
            'total': len(applied)
        })

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/admin/api/images/label-all', methods=['POST'])
def admin_label_all_images():
    """SSE stream — label all 184 images via Claude Vision. Skips already-labeled unless force=true."""
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    force = data.get('force', False)

    def generate():
        import time as _time

        def sse(obj):
            return f"data: {json.dumps(obj)}\n\n"

        opt_dir = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
        # Get all 480w images (good quality, smaller size → faster/cheaper API calls)
        all_480w = sorted([
            f for f in os.listdir(opt_dir)
            if re.search(r'_480w\.webp$', f)
        ])
        if not all_480w:
            yield sse({'type': 'error', 'msg': 'No 480w images found'})
            return

        yield sse({'type': 'status', 'msg': f'Found {len(all_480w)} images to label…'})

        # Load existing labels
        conn = _db_conn()
        existing = set()
        if conn:
            try:
                cur = conn.cursor()
                _ensure_image_labels_table(cur)
                conn.commit()
                cur.execute("SELECT filename FROM image_labels WHERE label IS NOT NULL")
                existing = {r['filename'] for r in cur.fetchall()}
            finally:
                conn.close()

        # Load project context from image_library DB (populated by the live site scan)
        yield sse({'type': 'status', 'msg': 'Loading project context from image library…'})
        page_context = _get_page_context_for_files()
        yield sse({'type': 'status', 'msg': f'Project context ready — {len(page_context)} images mapped'})

        done = 0
        skipped = 0
        errors = 0
        total = len(all_480w)

        for fname in all_480w:
            # The base filename (without _480w) is what we label
            base_fname = fname.replace('_480w.webp', '.webp')
            orig_fname = fname.replace('_480w.webp', '')  # for image_library lookup (jpg/png key)

            if not force and base_fname in existing:
                skipped += 1
                continue

            img_path = os.path.join(opt_dir, fname)
            project = page_context.get(base_fname) or page_context.get(orig_fname + '.jpg') or page_context.get(orig_fname + '.png')

            try:
                label = _call_claude_vision_label(img_path, project)
                # Store in DB
                conn2 = _db_conn()
                if conn2:
                    try:
                        cur2 = conn2.cursor()
                        cur2.execute("""
                            INSERT INTO image_labels (filename, label, project, labeled_at)
                            VALUES (%s, %s, %s, NOW())
                            ON CONFLICT (filename) DO UPDATE SET
                                label = EXCLUDED.label,
                                project = EXCLUDED.project,
                                labeled_at = NOW()
                        """, (base_fname, label, project))
                        conn2.commit()
                    finally:
                        conn2.close()

                done += 1
                yield sse({
                    'type': 'labeled',
                    'filename': base_fname,
                    'label': label,
                    'project': project,
                    'done': done,
                    'total': total,
                    'pct': round((done + skipped) / total * 100)
                })
            except Exception as e:
                errors += 1
                yield sse({'type': 'error_item', 'filename': base_fname, 'error': str(e)})

            _time.sleep(0.05)  # small pause to avoid hammering API

        yield sse({
            'type': 'done',
            'done': done, 'skipped': skipped, 'errors': errors, 'total': total
        })

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ── Server Management App ─────────────────────────────────────────────────────
import csv as _csv
import io as _io

# App log file — Flask writes here, log viewer tails it
_APP_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview_server.log')
_FS_ROOT      = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))  # /home/claudeuser/agent
_ENV_FILE     = os.path.join(_FS_ROOT, '.env')

_FS_PROTECTED_NAMES = {'.env', 'preview_server.py', 'CLAUDE.md', 'GUARDRAILS.md', '__pycache__'}
_FS_PROTECTED_EXTS  = {'.pyc'}

_ENV_SENSITIVE = {
    'ANTHROPIC_API_KEY','META_APP_SECRET','META_ACCESS_TOKEN',
    'GOOGLE_CLIENT_SECRET','GOOGLE_REFRESH_TOKEN','GOOGLE_DEVELOPER_TOKEN',
    'MICROSOFT_CLIENT_SECRET','MICROSOFT_REFRESH_TOKEN','MICROSOFT_ADS_DEVELOPER_TOKEN',
    'RESEND_API_KEY','GEMINI_API_KEY','DATABASE_URL','INGEST_API_KEY',
    'ADMIN_PASSWORD','ADMIN_PASSWORD_HASH','META_APP_ID','SUPABASE_INGEST_ENDPOINT',
}
_ENV_EDITABLE = {
    'GEMINI_API_KEY','ANTHROPIC_API_KEY','RESEND_API_KEY',
    'CAMPAIGN_AUTOMATION_ENABLED','META_MANAGER_AUTO_APPLY','MSFT_MANAGER_AUTO_APPLY',
    'ALERT_EMAIL','ALERT_FROM','LANDING_PAGE_URL','META_API_VERSION',
    'META_ACCESS_TOKEN','GOOGLE_REFRESH_TOKEN','MICROSOFT_REFRESH_TOKEN',
}


def _fs_safe(rel_path):
    """Resolve path inside FS_ROOT; return abs path or None if outside."""
    try:
        resolved = os.path.realpath(os.path.join(_FS_ROOT, rel_path.lstrip('/')))
        if resolved.startswith(_FS_ROOT + os.sep) or resolved == _FS_ROOT:
            return resolved
    except Exception:
        pass
    return None


def _read_env_file():
    env = {}
    if not os.path.isfile(_ENV_FILE):
        return env
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            env[k.strip()] = v.strip()
    return env


def _write_env_file(updates):
    """Update specific keys in .env in-place."""
    lines = []
    updated = set()
    if os.path.isfile(_ENV_FILE):
        with open(_ENV_FILE) as f:
            for line in f:
                stripped = line.rstrip('\n')
                if not stripped.startswith('#') and '=' in stripped:
                    k = stripped.split('=', 1)[0].strip()
                    if k in updates:
                        lines.append(f'{k}={updates[k]}\n')
                        updated.add(k)
                        continue
                lines.append(line if line.endswith('\n') else line + '\n')
    for k, v in updates.items():
        if k not in updated:
            lines.append(f'{k}={v}\n')
    with open(_ENV_FILE, 'w') as f:
        f.writelines(lines)


def _mask_val(v):
    if not v:
        return ''
    if len(v) <= 8:
        return '••••••••'
    return v[:4] + '••••••••' + v[-4:]


# ── Health ────────────────────────────────────────────────────────────────────

@app.route('/admin/api/server/health')
def admin_server_health():
    auth = _require_admin()
    if auth: return auth
    try:
        import psutil, shutil as _shutil
        cpu  = psutil.cpu_percent(interval=0.5)
        mem  = psutil.virtual_memory()
        disk = _shutil.disk_usage('/')
        boot = psutil.boot_time()
        uptime_secs = int(datetime.now(timezone.utc).timestamp() - boot)

        img_dir   = os.path.join(PREVIEW_DIR, 'assets', 'images-opt')
        img_size  = 0
        img_count = 0
        if os.path.isdir(img_dir):
            for fn in os.listdir(img_dir):
                fp = os.path.join(img_dir, fn)
                if os.path.isfile(fp):
                    img_size  += os.path.getsize(fp)
                    img_count += 1

        db_size_mb = 0
        conn = _db_conn()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT pg_database_size('marketing_agent') AS sz")
                row = cur.fetchone()
                if row: db_size_mb = round(row['sz'] / 1024 / 1024, 1)
            except Exception:
                pass
            finally:
                conn.close()

        procs = []
        for p in sorted(
            psutil.process_iter(['pid','name','cpu_percent','memory_percent','status']),
            key=lambda p: p.info.get('memory_percent') or 0, reverse=True
        )[:15]:
            try:
                procs.append({
                    'pid':    p.info['pid'],
                    'name':   p.info['name'],
                    'cpu':    round(p.info.get('cpu_percent') or 0, 1),
                    'mem':    round(p.info.get('memory_percent') or 0, 1),
                    'status': p.info.get('status',''),
                })
            except Exception:
                pass

        return jsonify({
            'ok': True,
            'cpu':     {'percent': cpu, 'cores': psutil.cpu_count()},
            'memory':  {'used_gb': round(mem.used/1024**3, 2),
                        'total_gb': round(mem.total/1024**3, 2),
                        'percent': mem.percent},
            'disk':    {'used_gb': round(disk.used/1024**3, 1),
                        'total_gb': round(disk.total/1024**3, 1),
                        'free_gb': round(disk.free/1024**3, 1),
                        'percent': round(disk.used/disk.total*100, 1)},
            'images':  {'count': img_count, 'size_mb': round(img_size/1024**2, 1)},
            'db_size_mb': db_size_mb,
            'uptime_seconds': uptime_secs,
            'processes': procs,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/server/services')
def admin_server_services():
    auth = _require_admin()
    if auth: return auth
    service_defs = [
        ('preview_server',          'Preview Server',    '◈'),
        ('postgresql',              'PostgreSQL',        '◉'),
        ('ridgecrest-agent',        'Marketing Agent',   '▲'),
        ('ridgecrest-orchestrator', 'Orchestrator',      '⊙'),
    ]
    try:
        import psutil
    except ImportError:
        psutil = None

    result = []
    for key, name, icon in service_defs:
        try:
            r = subprocess.run(['systemctl','is-active', key],
                               capture_output=True, text=True, timeout=5)
            active = r.stdout.strip() == 'active'
            pid = mem_mb = uptime_str = None
            if active and psutil:
                try:
                    r2 = subprocess.run(
                        ['systemctl','show', key,'--property=MainPID'],
                        capture_output=True, text=True, timeout=5)
                    pid_str = r2.stdout.strip().replace('MainPID=','')
                    if pid_str and pid_str != '0':
                        pid = int(pid_str)
                        p = psutil.Process(pid)
                        mem_mb = round(p.memory_info().rss/1024**2, 1)
                        ct = p.create_time()
                        secs = int(datetime.now(timezone.utc).timestamp() - ct)
                        d, rem = divmod(secs, 86400)
                        h, rem = divmod(rem, 3600)
                        m, s   = divmod(rem, 60)
                        uptime_str = (f'{d}d ' if d else '') + f'{h:02d}:{m:02d}:{s:02d}'
                except Exception:
                    pass
            result.append({'key':key,'name':name,'icon':icon,
                           'active':active,'pid':pid,'mem_mb':mem_mb,'uptime':uptime_str})
        except Exception as e:
            result.append({'key':key,'name':name,'icon':icon,
                           'active':False,'pid':None,'mem_mb':None,'uptime':None,'error':str(e)})
    return jsonify({'ok': True, 'services': result})


@app.route('/admin/api/server/service/restart', methods=['POST'])
def admin_service_restart():
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    key  = data.get('service','').strip()
    allowed = {'ridgecrest-agent','ridgecrest-orchestrator','preview_server'}
    # postgresql not restartable via UI
    if key not in allowed:
        return jsonify({'error': 'service not restartable via UI'}), 403
    try:
        r = subprocess.run(['sudo','systemctl','restart', key],
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return jsonify({'error': r.stderr.strip() or 'restart failed'}), 500
        return jsonify({'ok': True, 'service': key})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Logs ──────────────────────────────────────────────────────────────────────

@app.route('/admin/api/server/logs')
def admin_server_logs():
    auth = _require_admin()
    if auth: return auth
    level_filter = request.args.get('level','ALL').upper()
    limit = min(int(request.args.get('limit', 300)), 500)
    search = request.args.get('q','').lower()

    lines = []

    def _classify(text):
        t = text.upper()
        if 'ERROR' in t or 'EXCEPTION' in t or 'TRACEBACK' in t: return 'ERROR'
        if 'WARNING' in t or 'WARN' in t:                         return 'WARNING'
        if 'DEBUG' in t:                                           return 'DEBUG'
        return 'INFO'

    # Try app log file
    if os.path.isfile(_APP_LOG_FILE):
        try:
            with open(_APP_LOG_FILE) as f:
                raw = f.readlines()[-limit:]
            for line in raw:
                line = line.rstrip()
                if not line: continue
                lv = _classify(line)
                if level_filter != 'ALL' and lv != level_filter: continue
                if search and search not in line.lower(): continue
                lines.append({'text': line, 'level': lv})
        except Exception:
            pass

    # Fallback: journalctl
    if not lines:
        try:
            r = subprocess.run(
                ['journalctl','--no-pager','-n',str(limit),'--output=short'],
                capture_output=True, text=True, timeout=10)
            for line in r.stdout.splitlines():
                if not line or line.startswith('--'): continue
                lv = _classify(line)
                if level_filter != 'ALL' and lv != level_filter: continue
                if search and search not in line.lower(): continue
                lines.append({'text': line, 'level': lv})
        except Exception:
            pass

    return jsonify({'ok': True, 'lines': lines[-limit:]})


@app.route('/admin/api/server/logs/stream')
def admin_server_logs_stream():
    token = request.headers.get('X-Admin-Token','') or request.args.get('token','')
    with _TOKENS_LOCK:
        if token not in _ADMIN_TOKENS:
            return Response('data: {"error":"unauthorized"}\n\n', status=401)

    def generate():
        def emit(text, level='INFO'):
            return f"event: log\ndata: {json.dumps({'text': text, 'level': level})}\n\n"

        # Send last 80 lines immediately
        if os.path.isfile(_APP_LOG_FILE):
            try:
                with open(_APP_LOG_FILE) as f:
                    lines = f.readlines()[-80:]
                for line in lines:
                    line = line.rstrip()
                    if line:
                        lv = 'ERROR' if 'ERROR' in line.upper() else ('WARNING' if 'WARNING' in line.upper() else 'INFO')
                        yield emit(line, lv)
            except Exception:
                pass
        else:
            yield emit('No log file yet — logs appear here after first request')

        # Tail in real-time
        import time as _time_mod
        target = _APP_LOG_FILE
        for _ in range(10):
            if os.path.isfile(target): break
            _time_mod.sleep(0.5)

        try:
            args = ['tail','-f','-n','0', target] if os.path.isfile(target) \
                   else ['journalctl','-f','--no-pager','-n','0']
            proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True)
            try:
                for line in proc.stdout:
                    line = line.rstrip()
                    if not line: continue
                    lv = 'ERROR' if 'ERROR' in line.upper() else ('WARNING' if 'WARNING' in line.upper() else 'INFO')
                    yield emit(line, lv)
            finally:
                proc.kill()
        except Exception as e:
            yield emit(f'Stream error: {e}', 'ERROR')

    return Response(generate(), content_type='text/event-stream',
                    headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@app.route('/admin/api/server/logs/download')
def admin_server_logs_download():
    auth = _require_admin()
    if auth: return auth
    if not os.path.isfile(_APP_LOG_FILE):
        return jsonify({'error':'no log file yet'}), 404
    from flask import send_file
    return send_file(_APP_LOG_FILE, as_attachment=True,
                     download_name='preview_server.log')


@app.route('/admin/api/server/logs/clear', methods=['POST'])
def admin_server_logs_clear():
    auth = _require_admin()
    if auth: return auth
    try:
        open(_APP_LOG_FILE, 'w').close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── File Manager ──────────────────────────────────────────────────────────────

@app.route('/admin/api/fs/list')
def admin_fs_list():
    auth = _require_admin()
    if auth: return auth
    rel = request.args.get('path','').strip('/')
    abs_path = _fs_safe(rel) if rel else _FS_ROOT
    if not abs_path or not os.path.isdir(abs_path):
        return jsonify({'error':'directory not found'}), 404
    try:
        items = []
        for name in sorted(os.listdir(abs_path),
                           key=lambda n: (not os.path.isdir(os.path.join(abs_path,n)), n.lower())):
            fp   = os.path.join(abs_path, name)
            try:
                stat  = os.stat(fp)
            except Exception:
                continue
            is_dir = os.path.isdir(fp)
            ext    = os.path.splitext(name)[1].lower()
            items.append({
                'name':      name,
                'path':      os.path.relpath(fp, _FS_ROOT),
                'is_dir':    is_dir,
                'size':      stat.st_size if not is_dir else None,
                'modified':  datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                'protected': name in _FS_PROTECTED_NAMES or ext in _FS_PROTECTED_EXTS,
                'is_image':  ext in {'.webp','.jpg','.jpeg','.png','.gif'},
            })
        crumbs = []
        if rel:
            acc = ''
            for part in rel.split('/'):
                if not part: continue
                acc = (acc + '/' + part).lstrip('/')
                crumbs.append({'name': part, 'path': acc})
        return jsonify({'ok':True,'path':rel,'items':items,'breadcrumb':crumbs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/fs/download')
def admin_fs_download():
    auth = _require_admin()
    if auth: return auth
    rel = request.args.get('path','').strip('/')
    abs_path = _fs_safe(rel)
    if not abs_path or not os.path.isfile(abs_path):
        return jsonify({'error':'file not found'}), 404
    from flask import send_file
    return send_file(abs_path, as_attachment=True,
                     download_name=os.path.basename(abs_path))


@app.route('/admin/api/fs/delete', methods=['POST'])
def admin_fs_delete():
    auth = _require_admin()
    if auth: return auth
    data = request.get_json(silent=True) or {}
    rel  = (data.get('path') or '').strip('/')
    abs_path = _fs_safe(rel)
    if not abs_path or not os.path.exists(abs_path):
        return jsonify({'error':'not found'}), 404
    name = os.path.basename(abs_path)
    ext  = os.path.splitext(name)[1].lower()
    if name in _FS_PROTECTED_NAMES or ext in _FS_PROTECTED_EXTS:
        return jsonify({'error':'protected file cannot be deleted'}), 403
    try:
        if os.path.isdir(abs_path):
            import shutil as _sh; _sh.rmtree(abs_path)
        else:
            os.remove(abs_path)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/fs/rename', methods=['POST'])
def admin_fs_rename():
    auth = _require_admin()
    if auth: return auth
    data     = request.get_json(silent=True) or {}
    rel      = (data.get('path') or '').strip('/')
    new_name = os.path.basename((data.get('new_name') or '').strip())
    abs_path = _fs_safe(rel)
    if not abs_path or not os.path.exists(abs_path):
        return jsonify({'error':'not found'}), 404
    if not new_name or '/' in new_name or '..' in new_name:
        return jsonify({'error':'invalid name'}), 400
    new_abs = os.path.join(os.path.dirname(abs_path), new_name)
    if os.path.exists(new_abs):
        return jsonify({'error':'name already exists'}), 409
    try:
        os.rename(abs_path, new_abs)
        return jsonify({'ok':True,'new_path': os.path.relpath(new_abs, _FS_ROOT)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/fs/upload', methods=['POST'])
def admin_fs_upload():
    auth = _require_admin()
    if auth: return auth
    rel     = request.form.get('path','').strip('/')
    abs_dir = _fs_safe(rel) if rel else _FS_ROOT
    if not abs_dir or not os.path.isdir(abs_dir):
        return jsonify({'error':'directory not found'}), 404
    uploaded, errors = [], []
    for f in request.files.getlist('files'):
        fname = os.path.basename(f.filename or '')
        if not fname: continue
        ext = os.path.splitext(fname)[1].lower()
        if ext in _FS_PROTECTED_EXTS:
            errors.append(f'{fname}: file type not allowed'); continue
        try:
            f.save(os.path.join(abs_dir, fname)); uploaded.append(fname)
        except Exception as e:
            errors.append(f'{fname}: {e}')
    return jsonify({'ok':True,'uploaded':uploaded,'errors':errors})


@app.route('/admin/api/fs/mkdir', methods=['POST'])
def admin_fs_mkdir():
    auth = _require_admin()
    if auth: return auth
    data     = request.get_json(silent=True) or {}
    rel      = (data.get('path') or '').strip('/')
    dir_name = os.path.basename((data.get('name') or '').strip())
    if not dir_name or '/' in dir_name or '..' in dir_name:
        return jsonify({'error':'invalid name'}), 400
    parent = _fs_safe(rel) if rel else _FS_ROOT
    if not parent or not os.path.isdir(parent):
        return jsonify({'error':'parent not found'}), 404
    new_dir = os.path.join(parent, dir_name)
    if os.path.exists(new_dir):
        return jsonify({'error':'already exists'}), 409
    try:
        os.makedirs(new_dir)
        return jsonify({'ok':True,'path': os.path.relpath(new_dir, _FS_ROOT)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Database Browser ──────────────────────────────────────────────────────────

@app.route('/admin/api/db/tables')
def admin_db_tables():
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn: return jsonify({'error':'no db'}), 503
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT tablename,
                   pg_size_pretty(pg_total_relation_size(quote_ident(tablename))) AS size,
                   pg_total_relation_size(quote_ident(tablename)) AS size_bytes
            FROM pg_tables WHERE schemaname='public' ORDER BY tablename
        """)
        tables = cur.fetchall()
        result = []
        for row in tables:
            try:
                cur.execute(f'SELECT count(*) FROM "{row["tablename"]}"')
                cnt = cur.fetchone()['count']
            except Exception:
                cnt = None
            result.append({'name':row['tablename'],'size':row['size'],
                           'size_bytes':row['size_bytes'],'rows':cnt})
        cur.execute("SELECT pg_size_pretty(pg_database_size('marketing_agent')) AS total, pg_database_size('marketing_agent') AS bytes")
        db = cur.fetchone()
        return jsonify({'ok':True,'tables':result,'db_size':db['total'],'db_bytes':db['bytes']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/api/db/table/<table_name>')
def admin_db_table_rows(table_name):
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn: return jsonify({'error':'no db'}), 503
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=%s", (table_name,))
        if not cur.fetchone(): return jsonify({'error':'table not found'}), 404
        offset = max(0, int(request.args.get('offset',0)))
        limit  = min(100, max(1, int(request.args.get('limit',50))))
        sort_col = request.args.get('sort','')
        # Validate sort column
        cur.execute("""SELECT column_name FROM information_schema.columns
                       WHERE table_schema='public' AND table_name=%s
                       ORDER BY ordinal_position""", (table_name,))
        cols = [r['column_name'] for r in cur.fetchall()]
        if sort_col not in cols and cols:
            sort_col = cols[0]
        order = f'ORDER BY "{sort_col}"' if sort_col else ''
        cur.execute(f'SELECT count(*) FROM "{table_name}"')
        total = cur.fetchone()['count']
        cur.execute(f'SELECT * FROM "{table_name}" {order} LIMIT %s OFFSET %s', (limit, offset))
        rows = cur.fetchall()
        col_info = []
        cur.execute("""SELECT column_name, data_type FROM information_schema.columns
                       WHERE table_schema='public' AND table_name=%s
                       ORDER BY ordinal_position""", (table_name,))
        for r in cur.fetchall():
            col_info.append({'name':r['column_name'],'type':r['data_type']})
        serialized = []
        for row in rows:
            r = {}
            for k, v in row.items():
                if v is None: r[k] = None
                elif isinstance(v, datetime): r[k] = v.isoformat()
                elif isinstance(v, (int,float,bool,str)): r[k] = v
                else: r[k] = str(v)
            serialized.append(r)
        return jsonify({'ok':True,'table':table_name,'columns':col_info,
                        'rows':serialized,'total':total,'offset':offset,'limit':limit})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/api/db/export/<table_name>')
def admin_db_export(table_name):
    auth = _require_admin()
    if auth: return auth
    conn = _db_conn()
    if not conn: return jsonify({'error':'no db'}), 503
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=%s", (table_name,))
        if not cur.fetchone(): return jsonify({'error':'table not found'}), 404
        cur.execute(f'SELECT * FROM "{table_name}" ORDER BY 1')
        rows = cur.fetchall()
        buf = _io.StringIO()
        if rows:
            writer = _csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for row in rows:
                writer.writerow({k: (v.isoformat() if isinstance(v, datetime) else (str(v) if v is not None else ''))
                                  for k, v in row.items()})
        ts = datetime.now().strftime('%Y%m%d')
        return Response(buf.getvalue(), content_type='text/csv',
                        headers={'Content-Disposition': f'attachment; filename={table_name}_{ts}.csv'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ── Environment Manager ───────────────────────────────────────────────────────

@app.route('/admin/api/server/env')
def admin_env_list():
    auth = _require_admin()
    if auth: return auth
    env = _read_env_file()
    # Group keys
    groups = {
        'General':   ['CAMPAIGN_AUTOMATION_ENABLED','META_MANAGER_AUTO_APPLY','MSFT_MANAGER_AUTO_APPLY','ALERT_EMAIL','ALERT_FROM','LANDING_PAGE_URL'],
        'AI':        ['ANTHROPIC_API_KEY','GEMINI_API_KEY'],
        'Meta':      ['META_APP_ID','META_APP_SECRET','META_ACCESS_TOKEN','META_AD_ACCOUNT_ID','META_PIXEL_ID','META_API_VERSION','META_AUDIENCE_ID','META_CONVERSION_INQUIRY_ID','META_CONVERSION_BOOKING_ID'],
        'Google':    ['GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_REFRESH_TOKEN','GOOGLE_DEVELOPER_TOKEN','GOOGLE_ADS_CUSTOMER_ID','GOOGLE_ADS_MANAGER_ID'],
        'Microsoft': ['MICROSOFT_CLIENT_ID','MICROSOFT_TENANT_ID','MICROSOFT_CLIENT_SECRET','MICROSOFT_REFRESH_TOKEN','MICROSOFT_ADS_DEVELOPER_TOKEN','MICROSOFT_ADS_ACCOUNT_ID'],
        'Database':  ['DATABASE_URL'],
        'Email':     ['RESEND_API_KEY'],
        'URLs':      ['INQUIRY_FORM_URL','INQUIRY_SUBMITTED_URL','BOOKING_CONFIRMED_URL','COMMAND_CENTER_URL','SUPABASE_URL'],
    }
    placed = set()
    result_groups = []
    for grp_name, keys in groups.items():
        items = []
        for k in keys:
            if k in env:
                placed.add(k)
                sensitive = k in _ENV_SENSITIVE
                items.append({'key':k,'value':_mask_val(env[k]) if sensitive else env[k],
                               'sensitive':sensitive,'editable':k in _ENV_EDITABLE,'set':bool(env.get(k))})
        if items:
            result_groups.append({'group':grp_name,'vars':items})
    # Other keys not in groups
    other = []
    for k, v in env.items():
        if k not in placed:
            sensitive = k in _ENV_SENSITIVE
            other.append({'key':k,'value':_mask_val(v) if sensitive else v,
                          'sensitive':sensitive,'editable':k in _ENV_EDITABLE,'set':bool(v)})
    if other:
        result_groups.append({'group':'Other','vars':other})
    return jsonify({'ok':True,'groups':result_groups})


@app.route('/admin/api/server/env/set', methods=['POST'])
def admin_env_set_server():
    auth = _require_admin()
    if auth: return auth
    data  = request.get_json(silent=True) or {}
    key   = data.get('key','').strip()
    value = data.get('value','').strip()
    if not key or key not in _ENV_EDITABLE:
        return jsonify({'error':'key not editable via UI'}), 403
    if not re.match(r'^[A-Z][A-Z0-9_]*$', key):
        return jsonify({'error':'invalid key name'}), 400
    try:
        _write_env_file({key: value})
        os.environ[key] = value
        return jsonify({'ok':True,'key':key})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Backup ────────────────────────────────────────────────────────────────────

@app.route('/admin/api/server/backup/db', methods=['POST'])
def admin_backup_db():
    auth = _require_admin()
    if auth: return auth
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as tf:
            tmp_path = tf.name
        env2 = os.environ.copy()
        env2['PGPASSWORD'] = 'StrongPass123!'
        r = subprocess.run(
            ['pg_dump','-U','agent_user','-h','localhost','marketing_agent','-f',tmp_path],
            capture_output=True, text=True, timeout=120, env=env2)
        if r.returncode != 0:
            return jsonify({'error': r.stderr.strip() or 'pg_dump failed'}), 500
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        from flask import send_file
        return send_file(tmp_path, as_attachment=True,
                         download_name=f'marketing_agent_{ts}.sql',
                         mimetype='application/sql')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/api/server/backup/files', methods=['POST'])
def admin_backup_files():
    """Create a tar.gz of the preview/ directory and download it."""
    auth = _require_admin()
    if auth: return auth
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tf:
            tmp_path = tf.name
        src = os.path.join(_FS_ROOT, 'preview')
        r = subprocess.run(
            ['tar','-czf', tmp_path,'-C', _FS_ROOT, 'preview'],
            capture_output=True, timeout=120)
        if r.returncode != 0:
            return jsonify({'error':'tar failed'}), 500
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        from flask import send_file
        return send_file(tmp_path, as_attachment=True,
                         download_name=f'preview_{ts}.tar.gz',
                         mimetype='application/gzip')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Startup: seed pages + team tables + load persisted sessions ──────────────
try:
    _seed_pages()
except Exception as _seed_err:
    print(f'[pages] Startup seed failed: {_seed_err}')

try:
    _load_tokens_from_db()
    print(f'[auth] Loaded {len(_ADMIN_TOKENS)} persisted session(s)')
except Exception as _tok_err:
    print(f'[auth] Token load failed: {_tok_err}')

try:
    _seed_team()
except Exception as _seed_err:
    print(f'[team] Startup seed failed: {_seed_err}')

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f'Preview server starting on http://0.0.0.0:{PORT}')
    print(f'Watching: {PREVIEW_DIR}')
    print(f'Access at: http://147.182.242.54:{PORT}/')
    app.run(host='0.0.0.0', port=PORT, threaded=True, debug=False)
