/* ============================================================
   Ridgecrest Designs — Admin Panel Shared JS
   ============================================================ */

const Admin = (function() {
  'use strict';

  const TOKEN_KEY = 'rd_admin_token';
  const API = '';  // same origin

  // ── Auth ────────────────────────────────────────────────────
  function getToken() { return sessionStorage.getItem(TOKEN_KEY); }
  function setToken(t) { sessionStorage.setItem(TOKEN_KEY, t); }
  function clearToken() { sessionStorage.removeItem(TOKEN_KEY); }
  function isLoggedIn() { return !!getToken(); }

  function requireAuth() {
    if (!isLoggedIn()) {
      window.location.href = '/view/admin/index.html';
      return false;
    }
    return true;
  }

  function logout() {
    clearToken();
    window.location.href = '/view/admin/index.html';
  }

  // ── API calls ────────────────────────────────────────────────
  async function apiFetch(path, opts = {}) {
    const token = getToken();
    const context = (document.body && document.body.dataset.adminContext) || '';
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    if (token) headers['X-Admin-Token'] = token;
    if (context) headers['X-Admin-Context'] = context;
    const res = await fetch(`/admin/api${path}`, { ...opts, headers });
    if (res.status === 401) { logout(); return null; }
    return res.json();
  }

  async function get(path)       { return apiFetch(path); }
  async function post(path, body) { return apiFetch(path, { method: 'POST', body: JSON.stringify(body) }); }
  async function put(path, body)  { return apiFetch(path, { method: 'PUT',  body: JSON.stringify(body) }); }
  async function del(path)        { return apiFetch(path, { method: 'DELETE' }); }

  // ── Toast ────────────────────────────────────────────────────
  function toast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    el.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${message}</span>`;
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(12px)'; el.style.transition = '0.2s'; setTimeout(() => el.remove(), 200); }, duration);
  }

  // ── Modal helpers ────────────────────────────────────────────
  function openModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.add('open');
  }

  function closeModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.remove('open');
  }

  function initModals() {
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
      btn.addEventListener('click', () => {
        const modal = btn.closest('.modal-overlay');
        if (modal) modal.classList.remove('open');
      });
    });
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', e => {
        if (e.target === overlay) overlay.classList.remove('open');
      });
    });
  }

  // ── Nav active state ─────────────────────────────────────────
  function setActiveNav(page) {
    document.querySelectorAll('.nav-item[data-page]').forEach(el => {
      el.classList.toggle('active', el.dataset.page === page);
    });
  }

  // ── Sidebar toggle (mobile) ──────────────────────────────────
  function initSidebarToggle() {
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (toggle && sidebar) {
      toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    }
  }

  // ── Logout button ────────────────────────────────────────────
  function initLogout() {
    document.querySelectorAll('[data-action="logout"]').forEach(btn => {
      btn.addEventListener('click', logout);
    });
  }

  // ── Date formatting ──────────────────────────────────────────
  function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function formatDateTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' +
           d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  }

  function timeAgo(iso) {
    if (!iso) return '—';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1)   return 'just now';
    if (mins < 60)  return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24)   return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }

  // ── Currency ─────────────────────────────────────────────────
  function formatCurrency(n) {
    if (n === null || n === undefined) return '—';
    return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  // ── Tabs ─────────────────────────────────────────────────────
  function initTabs(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const target = tab.dataset.target;
        if (target) {
          document.querySelectorAll('[data-tab-content]').forEach(c => {
            c.style.display = c.dataset.tabContent === target ? '' : 'none';
          });
        }
      });
    });
  }

  // ── Search filter ────────────────────────────────────────────
  function initSearch(inputId, itemSelector, textSelector) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.addEventListener('input', () => {
      const q = input.value.toLowerCase();
      document.querySelectorAll(itemSelector).forEach(row => {
        const text = (textSelector ? row.querySelector(textSelector)?.textContent : row.textContent) || '';
        row.style.display = text.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

  // ── Session ping — detects expired tokens after server restart ──────────────
  async function verifySession() {
    const token = getToken();
    if (!token) return false;
    try {
      const res = await fetch('/admin/api/auth/ping', {
        headers: { 'X-Admin-Token': token }
      });
      if (res.status === 401) {
        clearToken();
        // Show banner before redirecting
        const banner = document.createElement('div');
        banner.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#ef4444;color:#fff;text-align:center;padding:12px;font-size:14px;z-index:9999;font-family:sans-serif';
        banner.textContent = 'Session expired — redirecting to login…';
        document.body.appendChild(banner);
        setTimeout(() => { window.location.href = '/view/admin/index.html'; }, 1500);
        return false;
      }
    } catch(e) {
      // Network error — don't redirect, just continue
    }
    return true;
  }

  // ── Init ─────────────────────────────────────────────────────
  function init(page) {
    initModals();
    initSidebarToggle();
    initLogout();
    if (page) setActiveNav(page);
    // Async session check — redirects to login if token expired (e.g. after server restart)
    verifySession();
  }

  // ── AI Chat Panel ─────────────────────────────────────────────
  function initAI() {
    if (!isLoggedIn()) return;

    // Inject "Ask AI" button into sidebar footer
    const sidebarFooter = document.querySelector('.sidebar-footer');
    if (sidebarFooter) {
      const aiBtn = document.createElement('button');
      aiBtn.className = 'ai-trigger-btn';
      aiBtn.id = 'aiTriggerBtn';
      aiBtn.innerHTML = '<span class="ai-trigger-icon">✦</span> Ask AI';
      sidebarFooter.insertBefore(aiBtn, sidebarFooter.firstChild);
      aiBtn.addEventListener('click', toggleAIPanel);
    }

    // Inject panel HTML
    const panel = document.createElement('div');
    panel.id = 'aiPanel';
    panel.className = 'ai-panel';
    panel.innerHTML = `
      <div class="ai-panel__header">
        <div class="ai-panel__title">
          <span class="ai-panel__icon">✦</span>
          Ask AI
        </div>
        <button class="ai-panel__close" id="aiPanelClose">✕</button>
      </div>
      <div class="ai-panel__messages" id="aiMessages">
        <div class="ai-msg ai-msg--assistant">
          <div class="ai-msg__content">Hi Henry — tell me what you'd like to change and I'll handle it.</div>
        </div>
      </div>
      <div class="ai-panel__footer">
        <div class="ai-input-row">
          <textarea id="aiInput" class="ai-input" rows="2" placeholder="Change the featured image of the bathroom floor tile post to…"></textarea>
          <button class="ai-send-btn" id="aiSendBtn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </button>
        </div>
        <p class="ai-hint">Enter to send · Shift+Enter for new line</p>
      </div>
    `;
    document.body.appendChild(panel);

    document.getElementById('aiPanelClose').addEventListener('click', closeAIPanel);

    const input = document.getElementById('aiInput');
    const sendBtn = document.getElementById('aiSendBtn');

    input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendAIMessage(); }
    });
    sendBtn.addEventListener('click', sendAIMessage);
  }

  function toggleAIPanel() {
    const panel = document.getElementById('aiPanel');
    if (!panel) return;
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) {
      setTimeout(() => document.getElementById('aiInput')?.focus(), 150);
    }
  }

  function closeAIPanel() {
    document.getElementById('aiPanel')?.classList.remove('open');
  }

  // Conversation history (persisted for session)
  const _aiHistory = [];

  async function sendAIMessage() {
    const input = document.getElementById('aiInput');
    const messages = document.getElementById('aiMessages');
    const sendBtn = document.getElementById('aiSendBtn');
    if (!input || !messages) return;

    const text = input.value.trim();
    if (!text) return;

    // Add user message to UI
    appendAIMessage('user', text);
    _aiHistory.push({ role: 'user', content: text });
    input.value = '';
    input.style.height = '';
    sendBtn.disabled = true;

    // Add assistant placeholder
    const assistantEl = appendAIMessage('assistant', '');
    const contentEl = assistantEl.querySelector('.ai-msg__content');
    let accumulated = '';

    try {
      const res = await fetch('/admin/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': getToken() },
        body: JSON.stringify({ messages: _aiHistory })
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.type === 'text') {
              accumulated += evt.content;
              contentEl.innerHTML = formatAIText(accumulated);
              messages.scrollTop = messages.scrollHeight;
            } else if (evt.type === 'tool') {
              if (evt.status === 'running') {
                const ind = document.createElement('div');
                ind.className = 'ai-tool-indicator';
                ind.dataset.tool = evt.name;
                ind.innerHTML = `<span class="ai-tool-spinner"></span> ${formatToolName(evt.name)}…`;
                contentEl.parentElement.appendChild(ind);
              } else if (evt.status === 'done') {
                const ind = contentEl.parentElement.querySelector(`.ai-tool-indicator[data-tool="${evt.name}"]`);
                if (ind) ind.remove();
              }
            } else if (evt.type === 'done') {
              if (accumulated) _aiHistory.push({ role: 'assistant', content: accumulated });
            } else if (evt.type === 'error') {
              contentEl.textContent = 'Error: ' + evt.message;
            }
          } catch (e) { /* skip malformed */ }
        }
      }
    } catch (e) {
      contentEl.textContent = 'Connection error. Please try again.';
    } finally {
      sendBtn.disabled = false;
      messages.scrollTop = messages.scrollHeight;
    }
  }

  function appendAIMessage(role, text) {
    const messages = document.getElementById('aiMessages');
    const el = document.createElement('div');
    el.className = `ai-msg ai-msg--${role}`;
    el.innerHTML = `<div class="ai-msg__content">${role === 'user' ? escapeHtml(text) : formatAIText(text)}</div>`;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }

  function formatAIText(text) {
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  function formatToolName(name) {
    const map = {
      list_blog_posts: 'Loading posts',
      get_blog_post: 'Reading post',
      update_blog_post: 'Updating post',
      list_pages: 'Loading pages'
    };
    return map[name] || name;
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // Auto-init AI panel when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAI);
  } else {
    initAI();
  }

  // ── Undo button ──────────────────────────────────────────────
  /**
   * Wire up the #undoBtn for page-specific undo.
   * Reads admin context from <body data-admin-context="...">.
   * opts.onSuccess(data) — optional callback fired after a successful undo.
   * Returns a `refresh` function so callers can force a status poll.
   */
  function initUndoButton(opts) {
    opts = opts || {};
    var btn = document.getElementById('undoBtn');
    if (!btn) return function() {};
    var ctx = (document.body && document.body.dataset.adminContext) || '';

    function refresh() {
      var url = '/admin/api/undo/status' + (ctx ? '?context=' + encodeURIComponent(ctx) : '');
      fetch(url, { headers: { 'X-Admin-Token': getToken() || '', 'X-Admin-Context': ctx } })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.available) {
            btn.textContent = '↩ Undo: ' + d.description;
            btn.disabled = false;
            btn.style.borderColor = '#92400e';
            btn.style.color = '#f59e0b';
            btn.style.cursor = 'pointer';
          } else {
            btn.textContent = '↩ Nothing to undo';
            btn.disabled = true;
            btn.style.borderColor = 'var(--border,#2a3748)';
            btn.style.color = 'var(--text-muted,#94a3b8)';
            btn.style.cursor = 'not-allowed';
          }
        }).catch(function() {});
    }

    btn.onclick = function() {
      if (btn.disabled) return;
      btn.textContent = '↩ Undoing…';
      btn.disabled = true;
      fetch('/admin/api/undo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': getToken() || '', 'X-Admin-Context': ctx },
        body: JSON.stringify({ context: ctx })
      }).then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.ok) {
            toast('Undone: ' + d.description, 'success');
            if (opts.onSuccess) opts.onSuccess(d);
          } else {
            toast(d.error || 'Undo failed', 'error');
          }
          setTimeout(refresh, 400);
        }).catch(function() { setTimeout(refresh, 400); });
    };

    refresh();
    return refresh;
  }

  return {
    getToken, setToken, clearToken, isLoggedIn, requireAuth, logout,
    get, post, put, del,
    toast, openModal, closeModal, initModals, initTabs, initSearch,
    setActiveNav, init, initUndoButton,
    formatDate, formatDateTime, timeAgo, formatCurrency
  };
})();
