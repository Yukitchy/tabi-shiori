// 3案共通: データ読込・地図・ライトボックス・タブ切替。見た目は各HTML側のCSSで決める。
const IMG = f => '../album/' + f.replace('.mp4', '.jpg');
const SRC = f => '../album/' + f;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

async function loadTrip() {
  const D = await (await fetch('data.json')).json();
  D.all = [];
  D.stops.forEach((s, i) => { s.no = i + 1; s.items.forEach(it => { it.stop = i; it.di = s.di; D.all.push(it); }); });
  return D;
}

// 地図: 経路線・番号ピン・写真ごとの点。opts.color, opts.pin(no,stop)->html, opts.dash
function makeMap(el, D, opts) {
  const map = L.map(el, { zoomControl: false, attributionControl: true, ...(opts.map || {}) });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '&copy; OpenStreetMap' }).addTo(map);
  const pts = D.all.filter(i => i.lat != null);
  // 日ごとの色。前の点から100km超の飛び(新幹線など)は点線
  const col = it => (D.days[it.di] || {}).color || opts.color;
  const jump = (p, q) => Math.hypot((p.lat - q.lat) * 111, (p.lng - q.lng) * 90) > 100;
  let split = 0, run = null;
  pts.forEach((p, k) => {
    if (k && jump(pts[k - 1], p)) { if (!split) split = k; }
    const dash = k > 0 && jump(pts[k - 1], p), key = col(p) + dash;
    if (!run || run.key !== key) { run = { key, dash, c: col(p), ll: k ? [[pts[k - 1].lat, pts[k - 1].lng]] : [] }; run.line = L.polyline(run.ll, dash ? { color: run.c, weight: 3, dashArray: '2 8', opacity: .8 } : { color: run.c, weight: opts.weight || 4, opacity: .9 }).addTo(map); }
    run.ll.push([p.lat, p.lng]); run.line.setLatLngs(run.ll);
  });
  const dots = {};
  pts.forEach(p => {
    dots[p.f] = L.circleMarker([p.lat, p.lng], { radius: 4, color: '#fff', weight: 1.5, fillColor: opts.dot || opts.color, fillOpacity: 1 })
      .addTo(map).on('click', () => api.onDot && api.onDot(p));
  });
  const pins = D.stops.map((s, i) => s.lat == null ? null :
    L.marker([s.lat, s.lng], { icon: L.divIcon({ className: 'pin', html: opts.pin(i + 1, s), iconSize: [30, 30], iconAnchor: [15, 15] }), zIndexOffset: 1000 })
      .addTo(map).on('click', () => api.onPin && api.onPin(i)));
  let lit = null;
  const api = {
    map, dots, pins,
    fly(i, pad) {
      const s = D.stops[i]; if (s.lat == null) return;
      const z = s.items.length > 20 ? 15 : 13;
      const pt = map.project([s.lat, s.lng], z).add(pad || [0, 0]);
      map.flyTo(map.unproject(pt, z), z, { duration: .9 });
      pins.forEach((p, j) => p && p.getElement() && p.getElement().classList.toggle('on', j === i));
    },
    light(f) {
      if (lit && dots[lit]) dots[lit].setStyle({ radius: 4, fillColor: opts.dot || opts.color, weight: 1.5 });
      lit = f; const d = dots[f]; if (!d) return;
      d.setStyle({ radius: 10, fillColor: opts.lit || '#ffcc00', weight: 3 }).bringToFront();
    },
    overview() { map.fitBounds(L.latLngBounds(pts.slice(split).map(p => [p.lat, p.lng])), { padding: [30, 30] }); }
  };
  return api;
}

// 全画面ビュー（前後送り・保存）。list=[{f,t,stop}], onMove(item)
function lightbox(D, list, idx, onMove) {
  let box = $('#lb');
  if (!box) {
    box = document.createElement('div'); box.id = 'lb';
    box.innerHTML = `<div class="lb-top"><span class="lb-cap"></span><a class="lb-save" download>保存</a><button class="lb-x" aria-label="閉じる">×</button></div>
      <div class="lb-stage"></div><button class="lb-prev" aria-label="前へ">‹</button><button class="lb-next" aria-label="次へ">›</button>`;
    document.body.appendChild(box);
    $('.lb-x', box).onclick = () => { box.classList.remove('open'); $('.lb-stage', box).innerHTML = ''; };
    let x0 = null;
    box.addEventListener('touchstart', e => x0 = e.touches[0].clientX, { passive: true });
    box.addEventListener('touchend', e => { if (x0 == null) return; const dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 50) box.go(dx < 0 ? 1 : -1); x0 = null; });
    document.addEventListener('keydown', e => { if (!box.classList.contains('open')) return; if (e.key === 'ArrowRight') box.go(1); if (e.key === 'ArrowLeft') box.go(-1); if (e.key === 'Escape') $('.lb-x', box).click(); });
    $('.lb-prev', box).onclick = () => box.go(-1); $('.lb-next', box).onclick = () => box.go(1);
  }
  box.go = d => { box.i = (box.i + d + box.list.length) % box.list.length; box.show(); };
  box.show = () => {
    const it = box.list[box.i], s = D.stops[it.stop];
    $('.lb-stage', box).innerHTML = it.k === 'v' ? `<video src="${SRC(it.f)}" poster="${IMG(it.f)}" controls playsinline autoplay></video>` : `<img src="${IMG(it.f)}" alt="">`;
    $('.lb-cap', box).textContent = `${box.i + 1}/${box.list.length}　${it.t}　${s.name}`;
    const a = $('.lb-save', box); a.href = SRC(it.f); a.setAttribute('download', 'iwate-' + it.f);
    box.onMove && box.onMove(it);
  };
  box.list = list; box.i = idx; box.onMove = onMove; box.classList.add('open'); box.show();
}

// 上部タブ: [data-tab] = d<日> | album。日タブは onDay(日)、アルバムは初回だけ描く
function setTab(t) { $$('[data-tab]').forEach(x => x.classList.toggle('on', x.dataset.tab === t)); }
function tabs(D, onAlbumOpen, onDay) {
  $$('[data-tab]').forEach(b => b.onclick = () => {
    if (b.disabled) return;
    const t = b.dataset.tab;
    document.body.dataset.view = t === 'album' ? 'album' : 'line';
    setTab(t);
    if (t === 'album') renderAlbum(D, onAlbumOpen); else onDay && onDay(+t.slice(1));
  });
}
function renderAlbum(D, onOpen) {
  const g = $('#album'); if (g.dataset.done) return; g.dataset.done = 1;
  g.innerHTML = D.stops.map((s, i) => s.items.length ? `<h3><b style="background:${D.days[s.di].color}">${s.no}</b>${esc(s.name)}<small>${D.days[s.di].n}日 ${s.t0}</small></h3><div class="grid">` +
    s.items.map(it => `<button data-f="${it.f}"><img loading="lazy" src="${IMG(it.f)}" alt="">${it.k === 'v' ? '<i>▶</i>' : ''}</button>`).join('') + '</div>' : '').join('');
  g.onclick = e => { const b = e.target.closest('[data-f]'); if (!b) return; const i = D.all.findIndex(x => x.f === b.dataset.f); lightbox(D, D.all, i, onOpen); };
}
const HMS = m => `${Math.floor(m / 60)}時間${m % 60 ? (m % 60) + '分' : ''}`;
const mins = (a, b) => { const [h1, m1] = a.split(':'), [h2, m2] = b.split(':'); return (h2 * 60 + +m2) - (h1 * 60 + +m1); };
