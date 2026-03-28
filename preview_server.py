#!/usr/bin/env python3
"""
Ridgecrest Preview Server — port 8081
Serves /root/agent/preview/ with live auto-reload on file changes.
Dashboard at http://<server-ip>:8081/
"""
from flask import Flask, Response, jsonify, render_template_string
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import mimetypes
import os

PREVIEW_DIR = '/root/agent/preview'
PORT = 8081
os.makedirs(PREVIEW_DIR, exist_ok=True)

app = Flask(__name__)

# ── SSE client registry ───────────────────────────────────────────────────────
_clients: list = []
_clients_lock = threading.Lock()

def _notify_all():
    with _clients_lock:
        for ev in list(_clients):
            ev.set()

# ── Watchdog file watcher ─────────────────────────────────────────────────────
class _ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if not event.is_directory:
            _notify_all()

_observer = Observer()
_observer.schedule(_ChangeHandler(), PREVIEW_DIR, recursive=True)
_observer.start()

# ── Auto-reload script injected into every HTML response ──────────────────────
_RELOAD_SCRIPT = b'''<script>
(function(){
  var es = new EventSource('/sse-reload');
  es.onmessage = function(){ location.reload(); };
  es.onerror   = function(){ setTimeout(function(){ location.reload(); }, 2000); };
})();
</script>'''

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/sse-reload')
def sse_reload():
    """SSE stream — sends 'reload' when any file in preview/ changes."""
    ev = threading.Event()
    with _clients_lock:
        _clients.append(ev)

    def stream():
        try:
            while True:
                fired = ev.wait(timeout=25)
                if fired:
                    yield 'data: reload\n\n'
                    ev.clear()
                else:
                    yield ': heartbeat\n\n'
        finally:
            with _clients_lock:
                if ev in _clients:
                    _clients.remove(ev)

    return Response(
        stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*',
        }
    )


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


@app.route('/view/', defaults={'filename': 'index.html'})
@app.route('/view/<path:filename>')
def view(filename):
    """Serve a file from preview/ — inject reload script into HTML."""
    filepath = os.path.join(PREVIEW_DIR, filename)
    # Security: prevent path traversal
    if not os.path.abspath(filepath).startswith(os.path.abspath(PREVIEW_DIR)):
        return 'Forbidden', 403
    if not os.path.isfile(filepath):
        return f'<h2 style="font-family:sans-serif;padding:2rem">File not found: {filename}</h2>', 404

    mime, _ = mimetypes.guess_type(filepath)
    mime = mime or 'application/octet-stream'

    with open(filepath, 'rb') as f:
        content = f.read()

    if mime and 'html' in mime:
        if b'</body>' in content:
            content = content.replace(b'</body>', _RELOAD_SCRIPT + b'</body>', 1)
        else:
            content += _RELOAD_SCRIPT

    resp = Response(content, mimetype=mime)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/')
def dashboard():
    return render_template_string(_DASHBOARD)


# ── Dashboard HTML ─────────────────────────────────────────────────────────────
_DASHBOARD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Preview — Ridgecrest</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0f1117;
    color: #e2e8f0;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  /* ── Toolbar ── */
  .toolbar {
    background: #1a1f2e;
    border-bottom: 1px solid #2d3748;
    padding: 0 16px;
    height: 48px;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
    z-index: 10;
  }

  .logo {
    font-size: 13px;
    font-weight: 700;
    color: #a78bfa;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
    margin-right: 4px;
  }

  .divider { width: 1px; height: 24px; background: #2d3748; }

  .device-group { display: flex; gap: 4px; }
  .device-btn {
    background: #2d3748;
    border: 1px solid #3d4a5e;
    color: #94a3b8;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .device-btn:hover { background: #3d4a5e; color: #e2e8f0; }
  .device-btn.active { background: #4f46e5; border-color: #4f46e5; color: white; }

  .url-bar {
    flex: 1;
    background: #0f1117;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    color: #64748b;
    font-family: monospace;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .url-bar span { color: #a78bfa; }

  .reload-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #64748b;
    white-space: nowrap;
  }
  .reload-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #22c55e;
    transition: background 0.3s;
  }
  .reload-dot.firing { background: #f59e0b; animation: flash 0.4s ease; }
  @keyframes flash { 0%{transform:scale(1)} 50%{transform:scale(1.8)} 100%{transform:scale(1)} }

  .client-count { font-size: 11px; color: #475569; }

  /* ── Body ── */
  .body { display: flex; flex: 1; overflow: hidden; }

  /* ── Sidebar ── */
  .sidebar {
    width: 220px;
    background: #1a1f2e;
    border-right: 1px solid #2d3748;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    overflow: hidden;
  }
  .sidebar-header {
    padding: 12px 14px 8px;
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border-bottom: 1px solid #2d3748;
    flex-shrink: 0;
  }
  .file-list { flex: 1; overflow-y: auto; padding: 6px 0; }
  .file-item {
    padding: 7px 14px;
    font-size: 12px;
    font-family: monospace;
    color: #94a3b8;
    cursor: pointer;
    transition: all 0.1s;
    display: flex;
    align-items: center;
    gap: 8px;
    border-left: 2px solid transparent;
  }
  .file-item:hover { background: #2d3748; color: #e2e8f0; }
  .file-item.active { background: #2d374880; color: #a78bfa; border-left-color: #4f46e5; }
  .file-icon { font-size: 10px; opacity: 0.6; }
  .file-size { margin-left: auto; font-size: 10px; color: #475569; }
  .sidebar-footer {
    padding: 10px 14px;
    border-top: 1px solid #2d3748;
    font-size: 11px;
    color: #475569;
  }
  .sidebar-footer strong { color: #64748b; display: block; margin-bottom: 2px; }

  /* ── Preview area ── */
  .preview-area {
    flex: 1;
    background: #0a0e18;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    position: relative;
  }

  .device-label {
    position: absolute;
    top: 12px;
    font-size: 11px;
    color: #2d3748;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-weight: 600;
    pointer-events: none;
  }

  .frame-wrapper {
    position: relative;
    transition: all 0.3s ease;
    box-shadow: 0 8px 64px rgba(0,0,0,0.6);
  }

  iframe#preview {
    display: block;
    border: none;
    background: white;
    transition: width 0.3s ease, height 0.3s ease;
  }

  /* Scrollbar styling */
  .file-list::-webkit-scrollbar { width: 4px; }
  .file-list::-webkit-scrollbar-track { background: transparent; }
  .file-list::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 2px; }
</style>
</head>
<body>

<!-- Toolbar -->
<div class="toolbar">
  <span class="logo">Preview</span>
  <div class="divider"></div>
  <div class="device-group">
    <button class="device-btn" onclick="setDevice('mobile')" data-device="mobile">Mobile</button>
    <button class="device-btn" onclick="setDevice('tablet')" data-device="tablet">Tablet</button>
    <button class="device-btn" onclick="setDevice('desktop')" data-device="desktop">Desktop</button>
    <button class="device-btn active" onclick="setDevice('full')" data-device="full">Full</button>
  </div>
  <div class="divider"></div>
  <div class="url-bar" id="urlBar"><span>147.182.242.54:8081</span>/view/<span id="urlPath">index.html</span></div>
  <div class="reload-indicator">
    <div class="reload-dot" id="reloadDot"></div>
    <span id="reloadStatus">Live</span>
  </div>
  <div class="client-count" id="clientCount"></div>
</div>

<!-- Body -->
<div class="body">

  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-header">Files</div>
    <div class="file-list" id="fileList">
      <div style="padding:16px 14px;font-size:12px;color:#475569">Loading...</div>
    </div>
    <div class="sidebar-footer">
      <strong>Preview Dir</strong>
      /root/agent/preview/
    </div>
  </div>

  <!-- Preview -->
  <div class="preview-area" id="previewArea">
    <span class="device-label" id="deviceLabel">Full Width</span>
    <div class="frame-wrapper" id="frameWrapper">
      <iframe id="preview" src="/view/index.html" width="100%" height="100%"></iframe>
    </div>
  </div>

</div>

<script>
  var currentFile = 'index.html';

  // ── Device presets ──────────────────────────────────────────────────────────
  var DEVICES = {
    mobile:  { w: 390,  h: 844,  label: 'Mobile  390 × 844' },
    tablet:  { w: 768,  h: 1024, label: 'Tablet  768 × 1024' },
    desktop: { w: 1440, h: 900,  label: 'Desktop  1440 × 900' },
    full:    { w: null, h: null,  label: 'Full Width' }
  };

  function setDevice(mode) {
    document.querySelectorAll('.device-btn').forEach(function(b){
      b.classList.toggle('active', b.dataset.device === mode);
    });
    var area   = document.getElementById('previewArea');
    var wrapper= document.getElementById('frameWrapper');
    var iframe = document.getElementById('preview');
    var label  = document.getElementById('deviceLabel');
    var d = DEVICES[mode];
    label.textContent = d.label;

    if (mode === 'full') {
      var aw = area.clientWidth  - 40;
      var ah = area.clientHeight - 40;
      wrapper.style.transform = '';
      wrapper.style.transformOrigin = '';
      iframe.style.width  = aw + 'px';
      iframe.style.height = ah + 'px';
    } else {
      var aw = area.clientWidth  - 40;
      var ah = area.clientHeight - 60;
      var scale = Math.min(aw / d.w, ah / d.h, 1);
      iframe.style.width  = d.w + 'px';
      iframe.style.height = d.h + 'px';
      wrapper.style.transformOrigin = 'top center';
      wrapper.style.transform = 'scale(' + scale + ')';
    }
  }

  window.addEventListener('resize', function(){
    var activeBtn = document.querySelector('.device-btn.active');
    if (activeBtn) setDevice(activeBtn.dataset.device);
  });
  setTimeout(function(){ setDevice('full'); }, 50);

  // ── File sidebar ────────────────────────────────────────────────────────────
  function loadFiles() {
    fetch('/files').then(function(r){ return r.json(); }).then(function(files){
      var el = document.getElementById('fileList');
      if (!files.length) {
        el.innerHTML = '<div style="padding:16px 14px;font-size:12px;color:#475569">No files yet</div>';
        return;
      }
      el.innerHTML = files.map(function(f){
        var ext = f.name.split('.').pop();
        var icons = { html:'◈', css:'◉', js:'◆', png:'▣', jpg:'▣', svg:'▣' };
        var icon = icons[ext] || '◻';
        var kb = (f.size / 1024).toFixed(1);
        var active = f.name === currentFile ? ' active' : '';
        return '<div class="file-item' + active + '" onclick="loadFile(\'' + f.name + '\')">'
          + '<span class="file-icon">' + icon + '</span>'
          + f.name
          + '<span class="file-size">' + kb + 'k</span>'
          + '</div>';
      }).join('');
    }).catch(function(){});
  }

  function loadFile(name) {
    currentFile = name;
    document.getElementById('urlPath').textContent = name;
    document.getElementById('preview').src = '/view/' + name + '?t=' + Date.now();
    loadFiles();
    var activeBtn = document.querySelector('.device-btn.active');
    if (activeBtn) setDevice(activeBtn.dataset.device);
  }

  loadFiles();
  setInterval(loadFiles, 5000);

  // ── SSE reload indicator ─────────────────────────────────────────────────────
  var reloadCount = 0;
  var es = new EventSource('/sse-reload');
  var dot = document.getElementById('reloadDot');
  var status = document.getElementById('reloadStatus');

  es.onmessage = function(){
    reloadCount++;
    dot.classList.add('firing');
    status.textContent = 'Reloaded ×' + reloadCount;
    setTimeout(function(){ dot.classList.remove('firing'); }, 500);
    setTimeout(loadFiles, 800);
  };

  es.onerror = function(){
    dot.style.background = '#ef4444';
    status.textContent = 'Reconnecting...';
    setTimeout(function(){
      dot.style.background = '#22c55e';
      status.textContent = 'Live';
    }, 3000);
  };
</script>
</body>
</html>'''


if __name__ == '__main__':
    print(f'Preview server starting on http://0.0.0.0:{PORT}')
    print(f'Watching: {PREVIEW_DIR}')
    print(f'Access at: http://147.182.242.54:{PORT}/')
    app.run(host='0.0.0.0', port=PORT, threaded=True, debug=False)
