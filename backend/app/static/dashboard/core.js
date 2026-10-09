// Shared pieces: the API client, formatting, icons, toasts, dialogs and safe re-rendering.
import { T } from './strings.js';

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

// ---------------------------------------------------------------- formatting
const KU_DIGITS = '٠١٢٣٤٥٦٧٨٩';
export const ku = n => String(n ?? '').replace(/\d/g, d => KU_DIGITS[d]);
export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const thousands = n => ku(Math.round(Number(n) || 0).toLocaleString('en-US'));
export const dinar = n => `${thousands(n)} ${T.dinar}`;
export const signed = n => (n > 0 ? '+' : n < 0 ? '−' : '') + ku(Math.abs(n || 0));
export const decimal = n => ku(n).replace('.', '٫');
const pad = n => String(n).padStart(2, '0');
// "٩ تشرینی یەکەم ٢٠٢٦ · ١٤:٠٥": browsers have no Sorani month names, so they come from strings.js
export function dateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return ku(`${d.getDate()} ${T.months[d.getMonth()]} ${d.getFullYear()} · ${pad(d.getHours())}:${pad(d.getMinutes())}`);
}
export const clock = d => ku(d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
/** "2026-10" → "تشرینی یەکەم ٢٠٢٦" */
export function monthName(ym) {
  const [y, m] = String(ym).split('-').map(Number);
  return ku(m ? `${T.months[m - 1]} ${y}` : ym);
}
export function ago(iso) {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
  if (minutes < 1) return T.justNow;
  if (minutes < 60) return T.minutesAgo(ku(minutes));
  if (minutes < 48 * 60) return T.hoursAgo(ku(Math.round(minutes / 60)));
  return T.daysAgo(ku(Math.round(minutes / 1440)));
}

// dirtiness 1..5, yellow to red (the same scale the app and the map use)
export const LEVEL_COLOURS = ['#E9C46A', '#E0A030', '#D9822B', '#C4532F', '#9E2A2B'];
export const level = n => `<span class="level" style="background:${LEVEL_COLOURS[(n || 1) - 1]}">${ku(n)}</span>`;
export const pill = (text, tone = '', dot = true) => `<span class="pill ${tone} ${dot ? '' : 'no-dot'}">${esc(text)}</span>`;
export const icon = (name, cls = '') => `<svg class="icon ${cls}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
export const empty = (iconName, title, text = '') =>
  `<div class="empty">${icon(iconName)}<strong>${esc(title)}</strong>${text ? `<p>${esc(text)}</p>` : ''}</div>`;
export const skeleton = (rows = 4) =>
  `<div class="skeleton-rows">${'<div class="skeleton"></div>'.repeat(rows)}</div>`;

// ---------------------------------------------------------------- API
export class ApiError extends Error {
  constructor(status, code, message, body) {
    super(message);
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

const TOKEN_KEY = 'gl_staff_token';
export const session = {
  token: (() => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } })(),
  user: null,
  onLost: () => {},
  save(token) {
    this.token = token;
    try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY); } catch { /* storage blocked */ }
  },
};

export const connection = {
  online: true,
  listeners: new Set(),
  set(online) {
    if (online === this.online) return;
    this.online = online;
    this.listeners.forEach(fn => fn(online));
  },
};

/** JSON in and out. Throws ApiError with the server's Kurdish message for any non-2xx answer;
 *  a 401 (or 403: a citizen token) ends the session. `raw: true` returns the Response (files). */
export async function api(path, { method = 'GET', body, raw = false } = {}) {
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json', ...(session.token ? { Authorization: `Bearer ${session.token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    connection.set(false);
    throw new ApiError(0, 'network', T.errorNetwork);
  }
  connection.set(true);
  if ((res.status === 401 || res.status === 403) && !path.startsWith('/auth/')) {
    session.onLost();
    throw new ApiError(res.status, 'unauthorized', T.sessionEnded);
  }
  if (raw && res.ok) return res;
  let data = null;
  try { data = await res.json(); } catch { /* not JSON */ }
  if (!res.ok) throw new ApiError(res.status, data?.error || 'error', data?.message || T.errorGeneric, data);
  return data;
}

/** Download a file that needs the staff token (a plain <a href> would send none). */
export async function download(path, filename) {
  const res = await api(path, { raw: true });
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

// ---------------------------------------------------------------- feedback
export function toast(message, type = 'info') {
  const box = $('#toasts');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.setAttribute('role', type === 'error' ? 'alert' : 'status');
  el.innerHTML = `${icon(type === 'error' ? 'alert' : 'check')}<div class="grow">${esc(message)}</div>
    <button type="button" aria-label="${esc(T.close)}">${icon('x', 'sm')}</button>`;
  el.querySelector('button').onclick = () => el.remove();
  box.append(el);
  setTimeout(() => el.remove(), type === 'error' ? 7000 : 4000);
}

export const failed = err => toast(err?.message || T.errorGeneric, 'error');

/** Runs an action with the button showing it is busy (a double click sends one request). */
export async function busy(button, action) {
  if (button?.classList.contains('is-busy')) return undefined;
  button?.classList.add('is-busy');
  if (button) button.disabled = true;
  try {
    return await action();
  } finally {
    if (button) {
      button.classList.remove('is-busy');
      button.disabled = false;
    }
  }
}

/** Our own confirm dialog: the browser's one cannot be styled and blocks the page. */
export function confirmDialog({ title = T.confirmTitle, message = '', confirm = T.yes, danger = false }) {
  const dialog = $('#confirm-dialog');
  $('#confirm-title', dialog).textContent = title;
  $('#confirm-message', dialog).textContent = message;
  const ok = $('#confirm-ok', dialog);
  ok.textContent = confirm;
  ok.className = `btn ${danger ? 'btn-danger' : 'btn-primary'}`;
  dialog.returnValue = '';
  dialog.showModal();
  return new Promise(resolve => dialog.addEventListener('close', () => resolve(dialog.returnValue === 'ok'), { once: true }));
}

export function showImage(src, caption = '') {
  const dialog = $('#image-dialog');
  $('#image-dialog-img', dialog).src = src;
  $('#image-dialog-caption', dialog).textContent = caption;
  dialog.showModal();
}

// ---------------------------------------------------------------- re-rendering
/** Someone is typing or choosing in this box: a refresh must not wipe it. */
export const typing = box =>
  (box.contains(document.activeElement) && document.activeElement.matches('input, select, textarea'))
  || !!box.querySelector('.reject-form:not([hidden])');

const lastKeys = new WeakMap();
/** Replaces the box's HTML only when the data changed and nobody is typing in it. Values edited inside a
 *  [data-guard="<key>"] survive the redraw when an element with the same key is drawn again. */
export function render(box, data, html, { force = false } = {}) {
  const key = JSON.stringify(data);
  if (!force && (lastKeys.get(box) === key || typing(box))) return false;
  lastKeys.set(box, key);
  const edited = new Map($$('[data-guard] [data-dirty]', box).map(el => [el.closest('[data-guard]').dataset.guard, el.value]));
  box.innerHTML = typeof html === 'function' ? html() : html;
  edited.forEach((value, guard) => {
    const el = $(`[data-guard="${CSS.escape(guard)}"] input, [data-guard="${CSS.escape(guard)}"] select`, box);
    if (el) { el.value = value; el.setAttribute('data-dirty', ''); }
  });
  return true;
}
export const forget = box => lastKeys.delete(box);

// inputs mark themselves while edited, so a redraw puts the edit back
document.addEventListener('input', e => {
  if (e.target.matches('[data-guard] input, [data-guard] select')) e.target.setAttribute('data-dirty', '');
});
