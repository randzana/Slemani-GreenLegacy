// The dashboard shell: text, theme, sign-in, the router (#overview, #map, ...), sidebar badges and the
// 10-second refresh of the visible view only (paused while the tab is hidden).
import { T } from './strings.js';
import { $, $$, api, session, connection, clock, ku, toast, failed, busy } from './core.js';
import { views, bindActions, bindPinDialog, bindBinDialog, setRefresher, cancelPlacing } from './views.js';

const NAMES = Object.keys(views);
const REFRESH_MS = 10000;
let current = 'overview';
let running = null;
let again = false;

// ---------------------------------------------------------------- text from strings.js
const lookup = key => key.split('.').reduce((o, k) => (o == null ? o : o[k]), T);
function translate() {
  $$('[data-t]').forEach(el => { const v = lookup(el.dataset.t); if (typeof v === 'string') el.textContent = v; });
  $$('[data-t-placeholder]').forEach(el => { el.placeholder = lookup(el.dataset.tPlaceholder) || ''; });
  $$('[data-t-aria]').forEach(el => {
    const v = lookup(el.dataset.tAria) || '';
    el.setAttribute('aria-label', v);
    el.title = v;
  });
}

// ---------------------------------------------------------------- theme: system, light, dark
const THEMES = ['system', 'light', 'dark'];
const THEME_ICON = { system: 'monitor', light: 'sun', dark: 'moon' };
const THEME_NAME = { system: T.themeSystem, light: T.themeLight, dark: T.themeDark };
const media = window.matchMedia('(prefers-color-scheme: dark)');
let theme = (() => { try { return localStorage.getItem('gl_theme') || 'system'; } catch { return 'system'; } })();

function applyTheme() {
  const dark = theme === 'dark' || (theme === 'system' && media.matches);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  const btn = $('#theme-btn');
  $('use', btn).setAttribute('href', `#i-${THEME_ICON[theme]}`);
  const label = `${T.theme}: ${THEME_NAME[theme]}`;
  btn.title = label;
  btn.setAttribute('aria-label', label);
}

// ---------------------------------------------------------------- badges and the live indicator
function badges(s) {
  const set = (id, n) => { $(`#${id}`).textContent = n ? ku(n) : ''; };
  set('review-count', s.needs_review);
  set('places-count', s.pending_places);
  set('bin-count', s.bins_full);
  set('voucher-count', s.vouchers_waiting);
}

connection.listeners.add(online => {
  $('#live').classList.toggle('offline', !online);
  if (!online) {
    $('#live-text').textContent = T.offline;
    toast(T.errorNetwork, 'error');
  }
});

// ---------------------------------------------------------------- refresh
async function refresh() {
  if (!session.token || $('#app').hidden) return;
  if (running) { again = true; return; }
  running = (async () => {
    try {
      const stats = await api('/admin/stats');
      badges(stats);
      await views[current].load(stats);
      $('#live-text').textContent = T.updatedAt(clock(new Date()));
    } catch (err) {
      if (err.code !== 'unauthorized' && err.code !== 'network') failed(err);
    }
  })();
  await running;
  running = null;
  if (again) {
    again = false;
    await refresh();
  }
}
setRefresher(refresh);

// ---------------------------------------------------------------- router
function show(name) {
  if (current === 'map' && name !== 'map') cancelPlacing();
  current = name;
  $$('.view').forEach(v => { v.hidden = v.dataset.view !== name; });
  $$('.nav-item').forEach(a => (a.dataset.tab === name ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current')));
  const [title, sub] = T.views[name];
  $('#page-title').textContent = title;
  $('#page-sub').textContent = sub;
  document.title = `${title} · ${T.appTitle}`;
  $('#app').classList.remove('drawer-open');
  $('#content').scrollTo?.(0, 0);
  refresh();
}
const route = () => {
  const name = location.hash.slice(1);
  show(NAMES.includes(name) ? name : 'overview');
};

// ---------------------------------------------------------------- sign in and out
function showLogin(message = '') {
  $('#app').hidden = true;
  $('#login').hidden = false;
  $('#login-error').textContent = message;
  $('#login-form').elements.login.focus();
}

function showApp(user) {
  const name = user.name || T.staff;
  $('#who-name').textContent = name;
  $('#who-phone').textContent = user.phone || user.email || '';
  $('#who-initial').textContent = name.trim().charAt(0);
  $('#login').hidden = true;
  $('#app').hidden = false;
  route();
}

session.onLost = () => {
  session.save(null);
  showLogin(T.sessionEnded);
};

function bindShell() {
  $('#login-form').addEventListener('submit', e => {
    e.preventDefault();
    const f = e.target.elements;
    busy($('[type=submit]', e.target), async () => {
      $('#login-error').textContent = '';
      try {
        // "phone" too: a server from before email logins only reads that field
        const who = f.login.value.trim();
        const data = await api('/auth/login', { method: 'POST', body: { login: who, phone: who, password: f.password.value } });
        if (data.user.role !== 'staff') {
          $('#login-error').textContent = T.notStaff;
          return;
        }
        session.save(data.token);
        f.password.value = '';
        showApp(data.user);
      } catch (err) {
        $('#login-error').textContent = err.message;
      }
    });
  });
  $('#logout').addEventListener('click', () => { session.save(null); showLogin(); });
  $('#theme-btn').addEventListener('click', () => {
    theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
    try { localStorage.setItem('gl_theme', theme); } catch { /* storage blocked */ }
    applyTheme();
  });
  media.addEventListener('change', applyTheme);
  $('#refresh-btn').addEventListener('click', e => busy(e.currentTarget, refresh));
  $('#menu-btn').addEventListener('click', () => $('#app').classList.toggle('drawer-open'));
  $('#scrim').addEventListener('click', () => $('#app').classList.remove('drawer-open'));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') $('#app').classList.remove('drawer-open'); });
  document.addEventListener('click', e => {
    const close = e.target.closest('[data-close]');
    if (close) close.closest('dialog')?.close();
  });
  window.addEventListener('hashchange', route);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  setInterval(() => { if (!document.hidden) refresh(); }, REFRESH_MS);
}

async function start() {
  translate();
  applyTheme();
  bindShell();
  bindActions();
  bindPinDialog();
  bindBinDialog();
  Object.values(views).forEach(v => v.init?.());
  if (!session.token) { showLogin(); return; }
  try {
    const me = await api('/me');
    if (me.role !== 'staff') { session.save(null); showLogin(T.notStaff); return; }
    showApp(me);
  } catch (err) {
    if (err.code !== 'unauthorized') showLogin(err.message);
  }
}

start();
