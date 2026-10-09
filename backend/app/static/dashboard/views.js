// The dashboard's pages. Each view loads only its own data (the visible one refreshes every 10 s),
// renders through render() so nothing being typed is wiped, and every button is an action below
// that calls the real API and says what happened.
import { T } from './strings.js';
import {
  $, $$, api, download, esc, ku, thousands, dinar, signed, dateTime, monthName, ago, level, pill, icon, empty, skeleton,
  toast, failed, busy, confirmDialog, showImage, render, forget,
} from './core.js';
import { LiveMap, legendHtml } from './map.js';

const MAP_CENTRE = [35.5613, 45.4373];
export const state = { map: null, bins: [], pins: [] };

const go = view => { if (location.hash !== `#${view}`) location.hash = view; };
const box = id => document.getElementById(id);
const statusTone = { open: 'red', in_progress: 'blue', needs_review: 'amber', clean: 'green' };
const verdictTone = { verified: 'green', review: 'amber', rejected: 'red' };
const placeTone = { pending: 'amber', verified: 'green', rejected: 'red' };
const binTone = { active: 'green', full: 'red', maintenance: 'amber' };
const table = (head, rows) => `<div class="table-wrap"><table class="data"><thead><tr>${head.map(h =>
  `<th class="${h.startsWith('#') ? 'num' : ''}">${esc(h.replace(/^#/, ''))}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
const firstLoad = el => { if (!el.innerHTML.trim()) el.innerHTML = skeleton(); };

// ---------------------------------------------------------------- overview

function kpi(view, label, value, iconName, tone) {
  return `<a class="card kpi" href="#${view}"><div class="kpi-top"><span class="kpi-label">${esc(label)}</span>
    <span class="kpi-icon ${tone}">${icon(iconName)}</span></div><div class="kpi-value">${value}</div></a>`;
}

function attentionItem(view, iconName, tone, title, sub, count) {
  return `<a href="#${view}"><span class="kpi-icon ${tone}">${icon(iconName)}</span>
    <span class="what"><strong>${esc(title)}</strong><small>${esc(sub)}</small></span>
    <span class="count">${ku(count)}</span>${icon('chevron', 'chev')}</a>`;
}

const overview = {
  async load(stats) {
    const [reports, cleanups, hoods] = await Promise.all([api('/admin/reports'), api('/admin/cleanups'), api('/admin/neighbourhoods')]);
    const s = stats;
    render(box('ov-kpis'), s, () => [
      kpi('map', T.kpi.reported, ku(s.reported), 'camera', 'blue'),
      kpi('priority', T.kpi.open, ku(s.open), 'alert', 'red'),
      kpi('log', T.kpi.cleaned, ku(s.cleaned), 'check', 'green'),
      kpi('log', T.kpi.litter, ku(s.litter_removed), 'recycle', 'green'),
      kpi('review', T.kpi.review, ku(s.needs_review), 'eye', 'amber'),
      kpi('league', T.kpi.citizens, ku(s.citizens), 'users', 'violet'),
      kpi('places', T.kpi.homes, ku(s.households), 'home', 'green'),
      kpi('places', T.kpi.businesses, ku(s.businesses), 'store', 'blue'),
    ].join(''));

    const items = [
      s.needs_review && attentionItem('review', 'eye', 'amber', T.attentionReview(ku(s.needs_review)), T.attentionReviewSub, s.needs_review),
      s.pending_places && attentionItem('places', 'home', 'blue', T.attentionPlaces(ku(s.pending_places)), T.attentionPlacesSub, s.pending_places),
      s.bins_full && attentionItem('bins', 'bin', 'red', T.attentionBins(ku(s.bins_full)), T.attentionBinsSub, s.bins_full),
      s.vouchers_waiting && attentionItem('vouchers', 'gift', 'violet', T.attentionVouchers(ku(s.vouchers_waiting)), T.attentionVouchersSub, s.vouchers_waiting),
    ].filter(Boolean);
    render(box('ov-attention'), items, () => (items.length ? `<div class="attention">${items.join('')}</div>`
      : `<div class="all-clear">${icon('check')}${esc(T.allClear)}</div>`));

    const dirtiest = reports.slice(0, 6);
    render(box('ov-dirtiest'), dirtiest, () => (dirtiest.length ? table(
      [T.photo, T.dirtiness, `#${T.litterCount}`, T.age, T.statusCol, ''],
      dirtiest.map(r => `<tr><td><img class="thumb" src="${esc(r.photo_url)}" alt="" data-zoom="${esc(r.photo_url)}"></td>
        <td>${level(r.dirtiness)}</td><td class="num">${ku(r.litter_count)}</td>
        <td class="nowrap">${esc(T.hours(ku(Math.round(r.age_hours))))}</td>
        <td>${pill(T.status[r.status] || r.status, statusTone[r.status])}</td>
        <td class="actions"><button class="btn btn-ghost btn-sm" data-action="show-on-map" data-kind="spot" data-id="${r.id}">${icon('pin', 'sm')}${esc(T.showOnMap)}</button></td></tr>`).join(''))
      : empty('check', T.status.clean, '')));

    const recent = cleanups.slice(0, 5);
    render(box('ov-recent'), recent, () => (recent.length ? `<ul class="people"><ol>${recent.map(c => `<li>
        <img class="thumb" src="${esc(c.after_url || c.before_url)}" alt="" data-zoom="${esc(c.after_url || c.before_url)}">
        <span class="grow"><strong>${esc(c.cleaner)}</strong><br><span class="cell-sub">${esc(T.spot(ku(c.report_id)))} · ${esc(ago(c.created_at))}</span></span>
        ${pill(T.verdict[c.verdict] || c.verdict, verdictTone[c.verdict])}</li>`).join('')}</ol></ul>`
      : empty('broom', T.logFilter.all)));

    const top = hoods.slice(0, 6);
    const best = Math.max(1, ...top.map(h => h.points));
    render(box('ov-hoods'), top, () => (top.length ? `<ul class="people"><ol>${top.map((h, i) => `<li>
        <span class="rank ${i === 0 && h.points > 0 ? 'first' : ''}">${ku(i + 1)}</span>
        <span class="grow"><strong>${esc(h.name)}</strong><div class="bar"><i style="width:${(100 * h.points / best).toFixed(1)}%"></i></div></span>
        <span class="pts">${esc(T.pointsWord(thousands(h.points)))}</span></li>`).join('')}</ol></ul>` : empty('trophy', T.noHoods)));
  },
};

// ---------------------------------------------------------------- live map

const map = {
  ensure() {
    if (!state.map) {
      state.map = new LiveMap(box('map'), MAP_CENTRE);
      box('map-legend').innerHTML = legendHtml();
    }
    state.map.invalidate();
    return state.map;
  },
  init() {
    const chips = box('map-filters');
    chips.innerHTML = Object.entries(T.filter).map(([key, label]) =>
      `<button class="chip" type="button" data-filter="${key}" aria-pressed="${key === 'all'}">${esc(label)}</button>`).join('');
    chips.addEventListener('click', e => {
      const chip = e.target.closest('[data-filter]');
      if (!chip) return;
      $$('[data-filter]', chips).forEach(c => c.setAttribute('aria-pressed', String(c === chip)));
      this.ensure().setFilter(chip.dataset.filter);
    });
  },
  async load() {
    const m = this.ensure();
    const [spots, pins, binData, hoods] = await Promise.all([api('/reports'), api('/admin/pins'), api('/admin/bins'), api('/admin/neighbourhoods')]);
    state.pins = pins;
    state.bins = binData.bins || [];
    m.setAreas(hoods, box('map-legend'));
    m.setSpots(spots);
    m.setPins(pins);
    m.setBins(state.bins);
  },
};

/** "New pin" / "new bin": go to the map, and the next click there is its position. */
export function startPlacing(kind) {
  go('map');
  requestAnimationFrame(() => {
    const m = map.ensure();
    const banner = box('placement');
    $('#placement-text').textContent = kind === 'pin' ? T.placePin : T.placeBin;
    banner.hidden = false;
    m.startPlacing(latlng => {
      banner.hidden = true;
      (kind === 'pin' ? openPinDialog : openBinDialog)(latlng);
    });
  });
}

export function cancelPlacing() {
  state.map?.cancelPlacing();
  state.map?.clearMark();
  box('placement').hidden = true;
}

// ---------------------------------------------------------------- priority, review, cleanup log

const priority = {
  async load() {
    const el = box('priority-list');
    firstLoad(el);
    const rows = await api('/admin/reports');
    render(el, rows, () => (rows.length ? table(
      [`#${T.rankCol}`, T.photo, T.dirtiness, `#${T.litterCount}`, T.age, `#${T.confirmations}`, T.statusCol, T.description, ''],
      rows.map((r, i) => `<tr><td class="num">${ku(i + 1)}</td>
        <td><img class="thumb" src="${esc(r.photo_url)}" alt="" data-zoom="${esc(r.photo_url)}"></td><td>${level(r.dirtiness)}</td>
        <td class="num">${ku(r.litter_count)}</td><td class="nowrap">${esc(T.hours(ku(Math.round(r.age_hours))))}</td>
        <td class="num">${ku(r.confirmations)}</td><td>${pill(T.status[r.status] || r.status, statusTone[r.status])}</td>
        <td class="cell-wrap">${esc(r.description || '')}</td>
        <td class="actions"><button class="btn btn-ghost btn-sm" data-action="show-on-map" data-kind="spot" data-id="${r.id}">${icon('pin', 'sm')}${esc(T.showOnMap)}</button></td></tr>`).join(''))
      : `<div class="card">${empty('check', T.status.clean)}</div>`));
  },
};

function cleanupCard(c, withActions) {
  const after = c.litter_count_after == null ? '—' : ku(c.litter_count_after);
  return `<article class="card review-card">
    <div class="compare">
      <figure><img src="${esc(c.before_url)}" alt="" data-zoom="${esc(c.before_url)}"><figcaption>${esc(T.before(ku(c.litter_count_before ?? 0)))}</figcaption></figure>
      <figure><img src="${esc(c.after_url || '')}" alt="" data-zoom="${esc(c.after_url || '')}"><figcaption>${esc(T.after(after))}</figcaption></figure>
    </div>
    <div class="review-body">
      <div class="review-meta"><strong>${esc(T.spot(ku(c.report_id)))} · ${esc(c.cleaner)}</strong>${pill(T.verdict[c.verdict] || c.verdict, verdictTone[c.verdict])}</div>
      <div class="row small muted">${pill(T.trust(signed(c.cleaner_trust)), c.cleaner_trust < 0 ? 'red' : '', false)} ${esc(dateTime(c.created_at))}</div>
      ${c.reason ? `<p class="small">${esc(c.reason)}</p>` : ''}
      ${withActions ? `<div class="review-actions">
        <button class="btn btn-primary" data-action="review-cleanup" data-id="${c.id}" data-decision="approve">${icon('check', 'sm')}${esc(T.approve)}</button>
        <button class="btn btn-danger-soft" data-action="review-cleanup" data-id="${c.id}" data-decision="reject">${icon('x', 'sm')}${esc(T.reject)}</button></div>` : ''}
    </div></article>`;
}

const review = {
  async load() {
    const el = box('review-list');
    firstLoad(el);
    const rows = (await api('/admin/cleanups?verdict=review')).filter(c => !c.reviewed_at);
    render(el, rows, () => (rows.length ? `<div class="grid-cards">${rows.map(c => cleanupCard(c, true)).join('')}</div>`
      : `<div class="card">${empty('check', T.allClear)}</div>`));
  },
};

let logFilter = 'all';
const log = {
  init() {
    const chips = box('log-filters');
    chips.innerHTML = Object.entries(T.logFilter).map(([k, label]) =>
      `<button class="chip" type="button" data-verdict="${k}" aria-pressed="${k === 'all'}">${esc(label)}</button>`).join('');
    chips.addEventListener('click', e => {
      const chip = e.target.closest('[data-verdict]');
      if (!chip) return;
      $$('[data-verdict]', chips).forEach(c => c.setAttribute('aria-pressed', String(c === chip)));
      logFilter = chip.dataset.verdict;
      this.load().catch(failed);
    });
  },
  async load() {
    const el = box('log-list');
    firstLoad(el);
    const rows = (await api('/admin/cleanups')).filter(c => logFilter === 'all' || c.verdict === logFilter);
    render(el, [logFilter, rows], () => (rows.length ? `<div class="grid-cards">${rows.map(c => cleanupCard(c, false)).join('')}</div>`
      : `<div class="card">${empty('broom', T.noMatch)}</div>`));
  },
};

// ---------------------------------------------------------------- pins

const pins = {
  async load() {
    const el = box('pins-list');
    firstLoad(el);
    const rows = await api('/admin/pins');
    state.pins = rows;
    render(el, rows, () => (rows.length ? table(
      [T.pinType, T.pinTitle, T.statusCol, `#${T.pinTarget}`, T.pinParticipants, `#${T.pinReward}`, T.neighbourhood, T.pinNotified, ''],
      rows.map(p => {
        const [name, emoji] = T.pinTypes[p.category] || T.pinTypes.tree_planting;
        const done = p.status !== 'active';
        return `<tr><td>${pill(`${emoji} ${name}`, 'green', false)}</td>
          <td><div class="cell-main">${esc(p.title)}</div><div class="cell-sub cell-wrap">${esc(p.description)}</div></td>
          <td>${pill(T.pinStatus[p.status] || p.status, done ? '' : 'blue')}</td>
          <td class="num">${ku(p.target_count)}</td>
          <td><button class="btn btn-ghost btn-sm" data-action="pin-participants" data-id="${p.id}">${icon('users', 'sm')}${esc(T.people(ku(p.participant_count || 0)))}</button></td>
          <td class="num">${esc(T.points(ku(p.reward_points)))}</td>
          <td>${esc(p.neighbourhood_name || '—')}</td>
          <td>${p.send_notification ? pill(T.sent, 'green') : pill(T.notSent)}</td>
          <td class="actions">
            <button class="btn btn-ghost btn-sm" data-action="show-on-map" data-kind="pin" data-id="${p.id}" title="${esc(T.showOnMap)}">${icon('pin', 'sm')}</button>
            <button class="btn btn-secondary btn-sm" data-action="pin-toggle" data-id="${p.id}">${esc(done ? T.reopen : T.complete)}</button>
            <button class="btn btn-danger-soft btn-sm btn-icon" data-action="pin-delete" data-id="${p.id}" aria-label="${esc(T.del)}">${icon('trash', 'sm')}</button>
          </td></tr>`;
      }).join(''))
      : `<div class="card">${empty('pin', T.noPins, T.noPinsSub)}</div>`));
  },
};

function openPinDialog(latlng) {
  const dialog = box('pin-dialog');
  const form = $('form', dialog);
  form.reset();
  form.elements.lat.value = latlng.lat.toFixed(6);
  form.elements.lon.value = latlng.lng.toFixed(6);
  form.elements.coords.value = `${latlng.lat.toFixed(5)}, ${latlng.lng.toFixed(5)}`;
  dialog.showModal();
  form.elements.title.focus();
}

export function bindPinDialog() {
  const dialog = box('pin-dialog');
  const form = $('form', dialog);
  dialog.addEventListener('close', () => state.map?.clearMark());
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const f = form.elements;
    await busy($('[type=submit]', form), async () => {
      try {
        await api('/admin/pins', { method: 'POST', body: {
          category: f.category.value, title: f.title.value.trim(), description: f.description.value.trim(),
          lat: Number(f.lat.value), lon: Number(f.lon.value), target_count: Number(f.target.value) || 1,
          reward_points: Number(f.reward.value) || 50, send_notification: f.notify.checked } });
        dialog.close();
        toast(T.pinCreated, 'success');
        refreshVisible();
      } catch (err) { failed(err); }
    });
  });
}

async function openParticipants(id) {
  const dialog = box('participants-dialog');
  $('#pm-title').textContent = '…';
  $('#pm-sub').textContent = '';
  $('#pm-body').innerHTML = skeleton(3);
  dialog.showModal();
  try {
    const data = await api(`/admin/pins/${id}/participants`);
    const [, emoji] = T.pinTypes[data.pin.category] || T.pinTypes.tree_planting;
    $('#pm-title').textContent = `${emoji} ${data.pin.title}`;
    $('#pm-sub').textContent = T.participantsSub(ku(data.pin.target_count), ku(data.count));
    $('#pm-body').innerHTML = data.participants.length ? table([`#`, T.name, T.phone, T.neighbourhood, T.notes, T.registeredAt],
      data.participants.map((u, i) => `<tr><td class="num">${ku(i + 1)}</td><td class="cell-main">${esc(u.user_name)}</td>
        <td><span class="mono">${esc(u.user_phone)}</span></td><td>${esc(u.neighbourhood_name || '—')}</td>
        <td class="cell-wrap">${esc(u.notes || '—')}</td><td class="nowrap small">${esc(dateTime(u.created_at))}</td></tr>`).join(''))
      : empty('users', T.noParticipants, T.noParticipantsSub);
  } catch (err) {
    $('#pm-body').innerHTML = empty('alert', err.message);
  }
}

// ---------------------------------------------------------------- bins

let binFilter = 'all';
const bins = {
  init() {
    const chips = box('bin-filters');
    chips.innerHTML = `<button class="chip" type="button" data-bin-type="all" aria-pressed="true">${esc(T.filter.all)}</button>`
      + Object.entries(T.binTypes).map(([k, [name, emoji]]) =>
        `<button class="chip" type="button" data-bin-type="${k}" aria-pressed="false">${emoji} ${esc(name)}</button>`).join('');
    chips.addEventListener('click', e => {
      const chip = e.target.closest('[data-bin-type]');
      if (!chip) return;
      $$('[data-bin-type]', chips).forEach(c => c.setAttribute('aria-pressed', String(c === chip)));
      binFilter = chip.dataset.binType;
      this.draw();
    });
  },
  async load() {
    firstLoad(box('bins-list'));
    const data = await api('/admin/bins');
    state.bins = data.bins || [];
    const s = data.stats || {};
    render(box('bin-kpis'), s, () => [
      ['total', 'bin', 'blue'], ['active', 'check', 'green'], ['full', 'alert', 'red'], ['disposals', 'recycle', 'amber'],
    ].map(([k, ic, tone]) => `<div class="card kpi"><div class="kpi-top"><span class="kpi-label">${esc(T.binKpi[k])}</span>
      <span class="kpi-icon ${tone}">${icon(ic)}</span></div><div class="kpi-value">${ku(s[k] || 0)}</div></div>`).join(''));
    this.draw();
  },
  draw() {
    const rows = state.bins.filter(b => binFilter === 'all' || b.bin_type === binFilter);
    render(box('bins-list'), [binFilter, rows], () => (rows.length ? table(
      [T.qr, T.binCode, T.name, T.binType, `#${T.capacity}`, T.neighbourhood, T.statusCol, `#${T.disposals}`, ''],
      rows.map(b => {
        const [type, emoji] = T.binTypes[b.bin_type] || T.binTypes.general;
        return `<tr><td><button class="qr-thumb" data-action="bin-qr" data-id="${b.id}" aria-label="${esc(T.qr)}" title="${esc(T.qr)}">
            <img src="${esc(b.qr_data_url)}" alt=""></button></td>
          <td><span class="code">${esc(b.code)}</span></td><td class="cell-main">${esc(b.name)}</td>
          <td class="nowrap">${emoji} ${esc(type)}</td><td class="num">${esc(T.liters(ku(b.capacity_liters)))}</td>
          <td>${esc(b.neighbourhood_name || '—')}</td>
          <td><select class="select input-sm" data-action-change="bin-status" data-id="${b.id}" aria-label="${esc(T.statusCol)}">
            ${Object.entries(T.binStatus).map(([k, label]) => `<option value="${k}" ${k === b.status ? 'selected' : ''}>${esc(label)}</option>`).join('')}
          </select></td>
          <td class="num">${ku(b.disposal_count || 0)}</td>
          <td class="actions">
            <button class="btn btn-ghost btn-sm btn-icon" data-action="show-on-map" data-kind="bin" data-id="${b.id}" aria-label="${esc(T.showOnMap)}">${icon('pin', 'sm')}</button>
            <button class="btn btn-ghost btn-sm" data-action="bin-sticker" data-id="${b.id}">${icon('download', 'sm')}${esc(T.sticker)}</button>
            <button class="btn btn-danger-soft btn-sm btn-icon" data-action="bin-delete" data-id="${b.id}" aria-label="${esc(T.del)}">${icon('trash', 'sm')}</button>
          </td></tr>`;
      }).join(''))
      : `<div class="card">${empty('bin', T.noBins, T.noBinsSub)}</div>`));
  },
};

function openBinDialog(latlng) {
  const dialog = box('bin-dialog');
  const form = $('form', dialog);
  form.reset();
  const at = latlng || { lat: MAP_CENTRE[0], lng: MAP_CENTRE[1] };
  form.elements.lat.value = at.lat.toFixed(6);
  form.elements.lon.value = at.lng.toFixed(6);
  form.elements.coords.value = `${at.lat.toFixed(5)}, ${at.lng.toFixed(5)}`;
  dialog.showModal();
  form.elements.name.focus();
}
export const newBin = () => openBinDialog(null);

export function bindBinDialog() {
  const dialog = box('bin-dialog');
  const form = $('form', dialog);
  dialog.addEventListener('close', () => state.map?.clearMark());
  $('[data-pick]', form).addEventListener('click', () => { dialog.close(); startPlacing('bin'); });
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const f = form.elements;
    await busy($('[type=submit]', form), async () => {
      try {
        const res = await api('/admin/bins', { method: 'POST', body: {
          name: f.name.value.trim(), bin_type: f.bin_type.value, capacity_liters: Number(f.capacity.value) || 240,
          lat: Number(f.lat.value), lon: Number(f.lon.value), code: f.code.value.trim() || undefined } });
        dialog.close();
        toast(T.binCreated, 'success');
        await refreshVisible();
        if (res.bin) openQr(res.bin);
      } catch (err) { failed(err); }
    });
  });
}

function openQr(bin) {
  const dialog = box('qr-dialog');
  const [type] = T.binTypes[bin.bin_type] || T.binTypes.general;
  $('#qr-title').textContent = bin.name;
  $('#qr-img').src = bin.qr_data_url;
  $('#qr-code').textContent = bin.code;
  $('#qr-desc').textContent = `${type} · ${T.liters(ku(bin.capacity_liters))}${bin.neighbourhood_name ? ` · ${bin.neighbourhood_name}` : ''}`;
  dialog.dataset.id = bin.id;
  dialog.showModal();
}

function printQr() {
  const bin = state.bins.find(b => String(b.id) === box('qr-dialog').dataset.id);
  if (!bin) return;
  const w = window.open('', '_blank', 'width=620,height=760');
  if (!w) return;
  w.document.write(`<!doctype html><html dir="rtl"><head><meta charset="utf-8"><title>${esc(bin.code)}</title><style>
    body{font-family:system-ui,Tahoma,sans-serif;text-align:center;padding:40px;margin:0}
    .s{border:4px dashed #0D5C3A;border-radius:18px;padding:28px;display:inline-block;max-width:420px}
    h2{margin:0 0 4px;color:#0D5C3A}.p{color:#444;margin:0 0 12px}img{width:260px;height:260px}
    .c{font:800 24px monospace;background:#E8F5E9;color:#0D5C3A;padding:8px 18px;border-radius:8px;display:inline-block;margin:10px 0}
    .h{font-size:13px;color:#555;border-top:1px solid #ddd;padding-top:12px;margin-top:12px}</style></head><body>
    <div class="s"><h2>${esc(T.printCity)}</h2><p class="p">${esc(T.printProject)}</p><img src="${bin.qr_data_url}" alt="">
    <div class="c">${esc(bin.code)}</div><div>${esc(bin.name)}</div><div class="h">${esc(T.printHow)}</div></div>
    <script>onload=()=>{print();setTimeout(()=>close(),400)}<\/script></body></html>`);
  w.document.close();
}

// ---------------------------------------------------------------- households and businesses

let placeFilter = 'pending';
const places = {
  init() {
    const chips = box('place-filters');
    chips.innerHTML = Object.entries(T.placeFilter).map(([k, label]) =>
      `<button class="chip" type="button" data-place-status="${k}" aria-pressed="${k === 'pending'}">${esc(label)}</button>`).join('');
    chips.addEventListener('click', e => {
      const chip = e.target.closest('[data-place-status]');
      if (!chip) return;
      $$('[data-place-status]', chips).forEach(c => c.setAttribute('aria-pressed', String(c === chip)));
      placeFilter = chip.dataset.placeStatus;
      forget(box('places-list'));
      this.load().catch(failed);
    });
  },
  async load() {
    const el = box('places-list');
    firstLoad(el);
    const rows = await api(`/admin/places?status=${placeFilter}`);
    render(el, [placeFilter, rows], () => (rows.length ? table(
      [T.kind, T.name, T.details, T.neighbourhood, T.owner, T.statusCol, ''],
      rows.map(p => {
        const osm = `https://www.openstreetmap.org/?mlat=${p.lat}&mlon=${p.lon}#map=18/${p.lat}/${p.lon}`;
        return `<tr data-place="${p.id}" data-updated="${esc(p.updated_at)}">
          <td>${pill(T.placeKinds[p.kind], p.kind === 'household' ? 'green' : 'blue', false)}</td>
          <td><div class="cell-main">${esc(p.name)}</div>${p.address ? `<div class="cell-sub">${esc(p.address)}</div>` : ''}</td>
          <td class="nowrap">${p.kind === 'household' ? esc(T.residents(ku(p.residents_count))) : esc(p.category_name)}
            ${p.license_number ? `<div class="cell-sub" title="${esc(T.license)}"><span class="code">${esc(p.license_number)}</span></div>` : ''}</td>
          <td>${esc(p.neighbourhood || '—')}</td>
          <td><div>${esc(p.owner_name)}</div><div class="cell-sub mono">${esc(p.owner_phone)}</div>
            ${p.owner_email ? `<div class="cell-sub mono">${esc(p.owner_email)}</div>` : ''}</td>
          <td>${pill(T.placeStatus[p.verification_status], placeTone[p.verification_status])}
            <div class="cell-sub nowrap" title="${esc(T.registered)}">${esc(ago(p.created_at))}</div>
            ${p.rejection_reason ? `<div class="cell-sub cell-wrap">${esc(p.rejection_reason)}</div>` : ''}</td>
          <td class="actions">
            <a class="btn btn-ghost btn-sm btn-icon" href="${osm}" target="_blank" rel="noopener noreferrer" aria-label="${esc(T.map)}">${icon('external', 'sm')}</a>
            ${p.verification_status !== 'verified' ? `<button class="btn btn-primary btn-sm" data-action="place-verify">${esc(T.approve)}</button>` : ''}
            ${p.verification_status !== 'rejected' ? `<button class="btn btn-danger-soft btn-sm" data-action="place-reject-open">${esc(T.reject)}</button>` : ''}
            <form class="row-form reject-form" hidden>
              <input class="input input-sm" name="reason" maxlength="500" placeholder="${esc(T.reasonHint)}" required>
              <button class="btn btn-danger btn-sm" type="submit">${esc(T.send)}</button>
              <button class="btn btn-ghost btn-sm" type="button" data-action="place-reject-cancel">${esc(T.cancel)}</button>
            </form>
          </td></tr>`;
      }).join(''))
      : `<div class="card">${empty('home', T.noPlaces)}</div>`));
  },
};

async function decidePlace(row, decision, reason) {
  try {
    await api(`/admin/places/${row.dataset.place}/review`, { method: 'POST',
      body: { decision, reason, updated_at: row.dataset.updated } });
    toast(decision === 'verify' ? T.placeVerified : T.placeRejected, 'success');
  } catch (err) {
    failed(err);
    if (err.code !== 'place_changed') return;      // keep the typed reason; only a changed place needs fresh data
  }
  // close this row's reason form, or the typing guard in render() keeps the old row on screen
  $('.reject-form', row).hidden = true;
  if (row.contains(document.activeElement)) document.activeElement.blur();
  forget(box('places-list'));
  await refreshVisible();
}

// ---------------------------------------------------------------- monthly money

const money = {
  init() {
    box('money-month').addEventListener('change', () => { forget(box('money-list')); this.load().catch(failed); });
  },
  async load() {
    const el = box('money-list');
    firstLoad(el);
    const month = box('money-month');
    const data = await api(`/admin/payments${month.value ? `?month=${month.value}` : ''}`);
    if (!month.value) { month.value = data.month; month.max = data.month; }
    for (const kind of ['household', 'business']) {
      const field = box(`money-${kind}`);
      if (!field.value) field.value = data.defaults[kind];
    }
    render(el, data, () => (data.places.length ? table(
      [T.kind, T.name, T.owner, T.phone, T.neighbourhood, T.paidThisMonth],
      data.places.map(p => `<tr data-place="${p.id}"><td>${pill(T.placeKinds[p.kind], p.kind === 'household' ? 'green' : 'blue', false)}</td>
        <td class="cell-main">${esc(p.name)}</td><td>${esc(p.owner_name)}</td><td><span class="mono">${esc(p.owner_phone)}</span></td>
        <td>${esc(p.neighbourhood || '—')}</td>
        <td>${p.paid_iqd !== null ? pill(dinar(p.paid_iqd), 'green')
          : `<div class="row-form" data-guard="${p.id}"><input class="input input-sm num" type="number" min="1" step="1000" value="${esc(data.defaults[p.kind])}">
             <button class="btn btn-primary btn-sm" data-action="credit-place">${esc(T.credit)}</button></div>`}</td></tr>`).join('')
      + `<tr><td colspan="5" class="cell-main">${esc(T.monthTotal)}</td><td class="cell-main">${esc(dinar(data.total_iqd))}</td></tr>`)
      : `<div class="card">${empty('wallet', T.noVerified)}</div>`));
  },
};

// ---------------------------------------------------------------- vouchers

let voucherRows = [];
const vouchers = {
  init() {
    box('voucher-search').addEventListener('input', () => this.draw());
  },
  async load() {
    firstLoad(box('vouchers-list'));
    voucherRows = await api('/admin/redemptions');
    this.draw();
  },
  draw() {
    const q = box('voucher-search').value.trim().toLowerCase();
    const rows = voucherRows.filter(r => !q || [r.voucher, r.name, r.phone, r.reward_name].some(v => String(v || '').toLowerCase().includes(q)));
    render(box('vouchers-list'), [q, rows], () => (rows.length ? table(
      [T.voucherCode, T.reward, `#${T.cost}`, T.citizen, T.phone, T.time, T.handover],
      rows.map(r => `<tr><td><span class="code">${esc(r.voucher)}</span></td><td class="cell-main">${esc(r.reward_name)}</td>
        <td class="num">${ku(r.cost)}</td><td>${esc(r.name)}</td><td><span class="mono">${esc(r.phone)}</span></td>
        <td class="nowrap small">${esc(dateTime(r.created_at))}</td>
        <td>${r.honoured_at ? `${pill(T.handedOver, 'green')} <span class="cell-sub">${esc(dateTime(r.honoured_at))}</span>`
          : `<button class="btn btn-primary btn-sm" data-action="honour" data-id="${r.id}" data-code="${esc(r.voucher)}">${icon('gift', 'sm')}${esc(T.handover)}</button>`}</td></tr>`).join(''))
      : `<div class="card">${empty('gift', voucherRows.length ? T.noMatch : T.noVouchers)}</div>`));
  },
};

// ---------------------------------------------------------------- league

const league = {
  async load() {
    const [hoods, board] = await Promise.all([api('/admin/neighbourhoods'), api('/leaderboard')]);
    const best = Math.max(1, ...hoods.map(h => h.points));
    const count = (h, n) => (h.boundary ? ku(n) : `<span class="muted" title="${esc(T.noBoundary)}">—</span>`);
    const rankOf = (rows, i) => 1 + rows.filter(r => r.points > rows[i].points).length;
    render(box('league-hoods'), hoods, () => (hoods.length ? table(
      [`#${T.rankCol}`, T.neighbourhood, T.areaPoints, `#${T.areaCitizens}`, `#${T.homes}`, `#${T.areaOpen}`, `#${T.areaCleaned}`],
      hoods.map((h, i) => {
        const r = rankOf(hoods, i);
        return `<tr><td class="num"><span class="rank ${r === 1 && h.points > 0 ? 'first' : ''}">${ku(r)}</span></td>
          <td class="cell-main">${esc(h.name)}</td>
          <td><strong>${thousands(h.points)}</strong><div class="bar"><i style="width:${(100 * h.points / best).toFixed(1)}%"></i></div></td>
          <td class="num">${ku(h.citizens)}</td><td class="num">${ku(h.households)}</td>
          <td class="num">${count(h, h.open)}</td><td class="num">${count(h, h.cleaned)}</td></tr>`;
      }).join('')) + (hoods.some(h => !h.boundary) ? `<p class="note" style="margin-top:12px">${icon('info', 'sm')}${esc(T.boundaryNote)}</p>` : '')
      : `<div class="card">${empty('trophy', T.noHoods)}</div>`));
    const people = (board.citizens || []).filter(p => p.points > 0);
    render(box('league-people'), people, () => (people.length ? `<ul class="people"><ol>${people.map((p, i) => {
      const r = rankOf(people, i);
      return `<li><span class="rank ${r === 1 ? 'first' : ''}">${ku(r)}</span>
        <span class="grow"><strong>${esc(p.name)}</strong>${p.neighbourhood ? `<br><span class="cell-sub">${esc(p.neighbourhood)}</span>` : ''}</span>
        <span class="pts">${esc(T.pointsWord(thousands(p.points)))}</span></li>`;
    }).join('')}</ol></ul>` : empty('trophy', T.noPoints)));
  },
};

export const views = { overview, map, priority, review, log, pins, bins, places, money, vouchers, league };

// ---------------------------------------------------------------- actions (buttons anywhere, also in map popups)

let refreshVisible = async () => {};
export const setRefresher = fn => { refreshVisible = fn; };

const byId = (list, id) => list.find(x => String(x.id) === String(id));

/** The printable sticker needs the staff token, so it is fetched, not linked. */
const saveSticker = (button, id) => busy(button, async () => {
  const bin = byId(state.bins, id) || { code: `bin-${id}` };
  try {
    await download(`/admin/bins/${id}/sticker`, `${bin.code}-sticker.png`);
    toast(T.stickerSaved, 'success');
  } catch (err) { failed(err); }
});

export const actions = {
  'show-on-map': el => {
    go('map');
    requestAnimationFrame(async () => {
      map.ensure();
      if (!state.map.focus(el.dataset.kind, el.dataset.id)) {
        await map.load().catch(failed);
        state.map.focus(el.dataset.kind, el.dataset.id);
      }
    });
  },
  'new-pin': () => startPlacing('pin'),
  'new-bin': () => newBin(),
  'place-bin': () => startPlacing('bin'),
  'cancel-placing': () => cancelPlacing(),
  'pin-participants': el => openParticipants(el.dataset.id),
  'pin-toggle': el => busy(el, async () => {
    try {
      const res = await api(`/admin/pins/${el.dataset.id}/toggle`, { method: 'POST' });
      toast(res.status === 'active' ? T.pinReopened : T.pinCompleted, 'success');
      await refreshVisible();
    } catch (err) { failed(err); }
  }),
  'pin-delete': async el => {
    const pin = byId(state.pins, el.dataset.id);
    if (!await confirmDialog({ title: pin?.title || T.confirmTitle, message: T.confirmDeletePin, confirm: T.del, danger: true })) return;
    await busy(el, async () => {
      try {
        await api(`/admin/pins/${el.dataset.id}`, { method: 'DELETE' });
        toast(T.pinDeleted, 'success');
        await refreshVisible();
      } catch (err) { failed(err); }
    });
  },
  'bin-qr': el => { const bin = byId(state.bins, el.dataset.id); if (bin) openQr(bin); },
  'bin-sticker': el => saveSticker(el, el.dataset.id),
  'qr-sticker': el => saveSticker(el, box('qr-dialog').dataset.id),
  'qr-print': () => printQr(),
  'bin-status': (el, value) => busy(el, async () => {
    try {
      await api(`/admin/bins/${el.dataset.id}/status`, { method: 'POST', body: { status: value || el.dataset.status } });
      toast(T.binStatusSet, 'success');
    } catch (err) { failed(err); }
    forget(box('bins-list'));
    await refreshVisible();
  }),
  'bin-delete': async el => {
    const bin = byId(state.bins, el.dataset.id);
    if (!await confirmDialog({ title: bin?.name || T.confirmTitle, message: T.confirmDeleteBin, confirm: T.del, danger: true })) return;
    await busy(el, async () => {
      try {
        await api(`/admin/bins/${el.dataset.id}`, { method: 'DELETE' });
        toast(T.binDeleted, 'success');
        await refreshVisible();
      } catch (err) { failed(err); }
    });
  },
  'review-cleanup': async el => {
    const approve = el.dataset.decision === 'approve';
    if (!approve && !await confirmDialog({ message: T.confirmRejectCleanup, confirm: T.reject, danger: true })) return;
    await busy(el, async () => {
      try {
        await api(`/admin/cleanups/${el.dataset.id}/review`, { method: 'POST', body: { decision: el.dataset.decision } });
        toast(approve ? T.approved : T.rejectedDone, 'success');
      } catch (err) { failed(err); }
      await refreshVisible();
    });
  },
  'place-verify': el => busy(el, () => decidePlace(el.closest('[data-place]'), 'verify')),
  'place-reject-open': el => {
    const form = $('.reject-form', el.closest('[data-place]'));
    form.hidden = false;
    form.elements.reason.focus();
  },
  'place-reject-cancel': el => {
    const form = el.closest('.reject-form');
    form.reset();
    form.hidden = true;
  },
  'credit-place': el => busy(el, async () => {
    const row = el.closest('[data-place]');
    const input = $('input', row);
    const amount = Number.parseInt(input.value, 10);
    try {
      await api(`/admin/places/${row.dataset.place}/payments`, { method: 'POST', body: { month: box('money-month').value, amount_iqd: amount } });
      toast(T.credited(dinar(amount)), 'success');
      input.removeAttribute('data-dirty');
    } catch (err) { failed(err); }
    forget(box('money-list'));
    await refreshVisible();
  }),
  'credit-all': async el => {
    const month = box('money-month').value;
    const home = Number.parseInt(box('money-household').value, 10);
    const shop = Number.parseInt(box('money-business').value, 10);
    if (!await confirmDialog({ message: T.confirmCreditAll(monthName(month), dinar(home), dinar(shop)), confirm: T.credit })) return;
    await busy(el, async () => {
      try {
        const res = await api('/admin/payments', { method: 'POST', body: { month, household_iqd: home, business_iqd: shop } });
        toast(T.creditedMany(ku(res.credited)), 'success');
      } catch (err) { failed(err); }
      forget(box('money-list'));
      await refreshVisible();
    });
  },
  honour: el => busy(el, async () => {
    try {
      await api(`/admin/redemptions/${el.dataset.id}/honour`, { method: 'POST' });
      toast(T.honoured(el.dataset.code), 'success');
    } catch (err) { failed(err); }
    await refreshVisible();
  }),
};

/** One listener for every [data-action] button, the rejection forms, the bin status selects and image zoom. */
export function bindActions() {
  // capture phase: Leaflet stops clicks inside map popups from bubbling up to the document
  document.addEventListener('click', e => {
    const zoom = e.target.closest('[data-zoom]');
    if (zoom && zoom.dataset.zoom) { showImage(zoom.dataset.zoom); return; }
    const el = e.target.closest('[data-action]');
    if (el && actions[el.dataset.action]) {
      e.preventDefault();
      actions[el.dataset.action](el);
    }
  }, true);
  document.addEventListener('change', e => {
    const el = e.target.closest('[data-action-change]');
    if (el && actions[el.dataset.actionChange]) actions[el.dataset.actionChange](el, el.value);
  });
  document.addEventListener('submit', e => {
    const form = e.target.closest('.reject-form');
    if (!form) return;
    e.preventDefault();
    const reason = form.elements.reason.value.trim();
    if (reason) busy($('[type=submit]', form), () => decidePlace(form.closest('[data-place]'), 'reject', reason));
  });
}
