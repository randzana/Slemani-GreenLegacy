// The live map: open spots by dirtiness, municipality pins, trash bins and neighbourhood areas.
// Markers are kept by id and updated in place, so an open popup survives the 10-second refresh.
// Homes are never drawn here: their locations stay private (households are only counted).
import { T } from './strings.js';
import { esc, ku, decimal, LEVEL_COLOURS, level, pill, icon } from './core.js';

// areas: one blue hue, light to dark by open spots; fixed steps, so a colour means the same count every refresh
const AREA_COLOURS = ['#B7D3F6', '#86B6EF', '#5598E7', '#2A78D6', '#1C5CAB'];
const AREA_STEPS = [1, 2, 4, 7, 11];
const areaColour = open => AREA_COLOURS[AREA_STEPS.filter(s => open >= s).length - 1];
const areaStyle = h => h.open > 0
  ? { color: '#184F95', weight: 1.5, opacity: .9, fillColor: areaColour(h.open), fillOpacity: .42, dashArray: null }
  : { color: '#184F95', weight: 1.5, opacity: .8, fillOpacity: 0, dashArray: '5 5' };
const stepLabel = i => (i === AREA_STEPS.length - 1 ? `${ku(AREA_STEPS[i])}+`
  : AREA_STEPS[i + 1] - 1 === AREA_STEPS[i] ? ku(AREA_STEPS[i]) : `${ku(AREA_STEPS[i])}–${ku(AREA_STEPS[i + 1] - 1)}`);
const PIN_CLASS = { tree_planting: 'tree', cleanup_target: 'clean', watering_point: 'water' };

export const legendHtml = () =>
  LEVEL_COLOURS.map((c, i) => `<span><i class="dot" style="background:${c}"></i>${esc(T.dirtinessN(ku(i + 1)))}</span>`).join('')
  + `<span><i class="dot" style="background:#1E7A4A"></i>${esc(T.legendClean)}</span>`
  + Object.entries(T.pinTypes).map(([, [name, emoji]]) => `<span>${emoji} ${esc(name)}</span>`).join('')
  + `<span>🗑️ ${esc(T.filter.bins)}</span>`
  + `<span data-area-legend hidden>${esc(T.legendAreas)} `
  + AREA_COLOURS.map((c, i) => `<i class="sw" style="background:${c}"></i>${stepLabel(i)}`).join(' ') + '</span>';

function keep(markers, layer, seen) {
  for (const [id, m] of markers) {
    if (!seen.has(id)) { layer.removeLayer(m); markers.delete(id); }
  }
}

function upsert(markers, layer, id, make, latlng, popup) {
  let m = markers.get(id);
  if (!m) {
    m = make().bindPopup(popup, { maxWidth: 300 }).addTo(layer);
    markers.set(id, m);
  } else {
    m.setLatLng(latlng);
    if (m.getPopup().getContent() !== popup) m.setPopupContent(popup);
  }
  return m;
}

export class LiveMap {
  constructor(element, centre) {
    // zoom bottom-left: the top corners hold the filters and the new-pin/bin buttons, bottom-right the legend
    this.map = L.map(element, { zoomControl: false, attributionControl: true }).setView(centre, 13);
    L.control.zoom({ position: 'bottomleft' }).addTo(this.map);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(this.map);
    this.areaLayer = L.featureGroup().addTo(this.map);
    this.spotLayer = L.layerGroup().addTo(this.map);
    this.pinLayer = L.layerGroup().addTo(this.map);
    this.binLayer = L.layerGroup().addTo(this.map);
    this.spotMarkers = new Map();
    this.pinMarkers = new Map();
    this.binMarkers = new Map();
    this.areas = new Map();
    this.data = { spots: [], pins: [], bins: [] };
    this.filter = 'all';
    this.fitted = false;
    this.placing = null;
    this.temp = null;
    this.map.on('click', e => this.#click(e));
  }

  shows(kind) { return this.filter === 'all' || this.filter === kind; }

  setFilter(filter) {
    this.filter = filter;
    this.setSpots(this.data.spots);
    this.setPins(this.data.pins);
    this.setBins(this.data.bins);
  }

  setSpots(spots) {
    this.data.spots = spots;
    const seen = new Set();
    if (this.shows('reports')) {
      for (const s of spots) {
        seen.add(s.id);
        const clean = s.status === 'clean';
        const style = { radius: clean ? 7 : 6 + s.dirtiness * 2, weight: 2, color: '#fff',
                        fillColor: clean ? '#1E7A4A' : LEVEL_COLOURS[s.dirtiness - 1], fillOpacity: .92 };
        const popup = `<div class="popup">
          <img class="photo" src="${esc(s.photo_url)}" alt="">
          <div class="row">${level(s.dirtiness)} ${pill(T.status[s.status] || s.status, clean ? 'green' : s.status === 'needs_review' ? 'amber' : 'red')}</div>
          <dl class="facts"><dt>${esc(T.litterCount)}</dt><dd>${ku(s.litter_count)}</dd></dl>
          ${s.description ? `<p class="small muted">${esc(s.description)}</p>` : ''}</div>`;
        const m = upsert(this.spotMarkers, this.spotLayer, s.id, () => L.circleMarker([s.lat, s.lon], style), [s.lat, s.lon], popup);
        m.setStyle(style).setRadius(style.radius);
      }
    }
    keep(this.spotMarkers, this.spotLayer, seen);
    this.#fitOnce();
  }

  setPins(pins) {
    this.data.pins = pins;
    const seen = new Set();
    for (const p of pins) {
      if (!this.shows(p.category)) continue;
      seen.add(p.id);
      const [name, emoji] = T.pinTypes[p.category] || T.pinTypes.tree_planting;
      const done = p.status !== 'active';
      const popup = `<div class="popup">
        <div class="row">${pill(name, 'green')} ${pill(T.pinStatus[p.status] || p.status, done ? '' : 'blue')}</div>
        <h4>${esc(p.title)}</h4>
        <p class="small muted">${esc(p.description)}</p>
        <dl class="facts">
          <dt>${esc(T.pinTarget)}</dt><dd>${ku(p.target_count)}</dd>
          <dt>${esc(T.pinParticipants)}</dt><dd>${esc(T.people(ku(p.participant_count || 0)))}</dd>
          <dt>${esc(T.pinReward)}</dt><dd>${esc(T.points(ku(p.reward_points)))}</dd>
          ${p.neighbourhood_name ? `<dt>${esc(T.neighbourhood)}</dt><dd>${esc(p.neighbourhood_name)}</dd>` : ''}
        </dl>
        <div class="row">
          <button class="btn btn-secondary btn-sm" data-action="pin-participants" data-id="${p.id}">${icon('users', 'sm')}${esc(T.participants)}</button>
          <button class="btn btn-ghost btn-sm" data-action="pin-toggle" data-id="${p.id}">${esc(done ? T.reopen : T.complete)}</button>
          <button class="btn btn-danger-soft btn-sm" data-action="pin-delete" data-id="${p.id}">${esc(T.del)}</button>
        </div></div>`;
      const make = () => L.marker([p.lat, p.lon], { icon: L.divIcon({
        className: '', iconSize: [36, 36], iconAnchor: [18, 36], popupAnchor: [0, -34],
        html: `<div class="marker ${PIN_CLASS[p.category] || 'tree'} ${done ? 'done' : ''}"><span>${emoji}</span></div>` }) });
      const m = upsert(this.pinMarkers, this.pinLayer, p.id, make, [p.lat, p.lon], popup);
      m.getElement()?.querySelector('.marker')?.classList.toggle('done', done);
    }
    keep(this.pinMarkers, this.pinLayer, seen);
    this.#fitOnce();
  }

  setBins(bins) {
    this.data.bins = bins;
    const seen = new Set();
    if (this.shows('bins')) {
      for (const b of bins) {
        seen.add(b.id);
        const [type, emoji, colour] = T.binTypes[b.bin_type] || T.binTypes.general;
        const tone = b.status === 'full' ? 'red' : b.status === 'maintenance' ? 'amber' : 'green';
        const popup = `<div class="popup">
          <div class="row"><span class="code">${esc(b.code)}</span> ${pill(T.binStatus[b.status] || b.status, tone)}</div>
          <h4>${esc(b.name)}</h4>
          <dl class="facts">
            <dt>${esc(T.binType)}</dt><dd>${emoji} ${esc(type)}</dd>
            <dt>${esc(T.capacity)}</dt><dd>${esc(T.liters(ku(b.capacity_liters)))}</dd>
            <dt>${esc(T.disposals)}</dt><dd>${esc(T.times(ku(b.disposal_count || 0)))}</dd>
            ${b.neighbourhood_name ? `<dt>${esc(T.neighbourhood)}</dt><dd>${esc(b.neighbourhood_name)}</dd>` : ''}
          </dl>
          <div class="row">
            <button class="btn btn-secondary btn-sm" data-action="bin-qr" data-id="${b.id}">${icon('qr', 'sm')}${esc(T.qr)}</button>
            <button class="btn btn-ghost btn-sm" data-action="bin-sticker" data-id="${b.id}">${icon('download', 'sm')}${esc(T.sticker)}</button>
            <button class="btn btn-ghost btn-sm" data-action="bin-status" data-id="${b.id}" data-status="${b.status === 'full' ? 'active' : 'full'}">
              ${esc(b.status === 'full' ? T.binStatus.active : T.binStatus.full)}</button>
          </div></div>`;
        const html = `<div class="bin-marker ${b.status === 'full' ? 'full' : ''}" style="border-color:${colour}">${emoji}</div>`;
        const binIcon = () => L.divIcon({ className: '', html, iconSize: [32, 32], iconAnchor: [16, 16], popupAnchor: [0, -18] });
        const m = upsert(this.binMarkers, this.binLayer, b.id, () => L.marker([b.lat, b.lon], { icon: binIcon() }), [b.lat, b.lon], popup);
        if (m.glDrawn !== undefined && m.glDrawn !== html) m.setIcon(binIcon());   // the status (or type) changed
        m.glDrawn = html;
      }
    }
    keep(this.binMarkers, this.binLayer, seen);
    this.#fitOnce();
  }

  /** Neighbourhood boundaries, rebuilt only when a shape changes (an open popup survives). */
  setAreas(hoods, legend) {
    const seen = new Set();
    for (const h of hoods) {
      if (!h.boundary) continue;
      const key = JSON.stringify(h.boundary);
      let area = this.areas.get(h.id);
      if (!area || area.key !== key) {
        if (area) this.areaLayer.removeLayer(area.layer);
        area = { key, layer: L.geoJSON(h.boundary).bindPopup('').bindTooltip('', { sticky: true }) };
        this.areas.set(h.id, area);
        this.areaLayer.addLayer(area.layer);
      }
      area.layer.setStyle(areaStyle(h)).setTooltipContent(esc(h.name)).setPopupContent(`<div class="popup"><h4>${esc(h.name)}</h4>
        <dl class="facts"><dt>${esc(T.areaPoints)}</dt><dd>${ku(h.points)}</dd><dt>${esc(T.areaCitizens)}</dt><dd>${ku(h.citizens)}</dd>
          <dt>${esc(T.areaOpen)}</dt><dd>${ku(h.open)}</dd><dt>${esc(T.areaCleaned)}</dt><dd>${ku(h.cleaned)}</dd>
          ${h.avg_dirtiness == null ? '' : `<dt>${esc(T.areaAvg)}</dt><dd>${decimal(h.avg_dirtiness)}</dd>`}</dl></div>`);
      area.layer.bringToBack();
      seen.add(h.id);
    }
    for (const [id, area] of this.areas) {
      if (!seen.has(id)) { this.areaLayer.removeLayer(area.layer); this.areas.delete(id); }
    }
    const tag = legend?.querySelector('[data-area-legend]');
    if (tag) tag.hidden = !this.areas.size;
    this.#fitOnce();
  }

  /** The next click on the map is a position for a new pin or bin. */
  startPlacing(onPick) {
    this.placing = onPick;
    this.map.getContainer().style.cursor = 'crosshair';
  }

  cancelPlacing() {
    this.placing = null;
    this.map.getContainer().style.cursor = '';
  }

  mark(latlng) {
    this.clearMark();
    this.temp = L.marker(latlng).addTo(this.map);
  }

  clearMark() {
    if (this.temp) this.map.removeLayer(this.temp);
    this.temp = null;
  }

  focus(kind, id) {
    const markers = { spot: this.spotMarkers, pin: this.pinMarkers, bin: this.binMarkers }[kind];
    const m = markers?.get(Number(id));
    if (!m) return false;
    this.map.setView(m.getLatLng(), 17);
    m.openPopup();
    return true;
  }

  invalidate() { this.map.invalidateSize(); }

  #click(e) {
    if (!this.placing) return;
    const pick = this.placing;
    this.cancelPlacing();
    this.mark(e.latlng);
    pick(e.latlng);
  }

  // first load only: zoom to everything on the map, or to the neighbourhoods while it is empty
  #fitOnce() {
    if (this.fitted) return;
    const points = [...this.data.spots, ...this.data.pins, ...this.data.bins].map(x => [x.lat, x.lon]);
    if (points.length) this.map.fitBounds(points, { maxZoom: 16, padding: [60, 60] });
    else if (this.areas.size) this.map.fitBounds(this.areaLayer.getBounds(), { padding: [20, 20] });
    else return;
    this.fitted = true;
  }
}
