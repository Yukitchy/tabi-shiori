#!/usr/bin/env python3
"""tabi-shiori engine: packs/<slug>/trip.json + img/ -> docs/<slug>/index.html"""
import json,sys,shutil,html,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parent.parent
def esc(s):return html.escape(s,quote=True)
def build(slug):
    P=ROOT/'packs'/slug; d=json.load(open(P/'trip.json'))
    cr=json.load(open(P/'credits.json')) if (P/'credits.json').exists() else {}
    O=ROOT/'docs'/slug; (O/'img').mkdir(parents=True,exist_ok=True)
    for f in (P/'img').glob('*'): shutil.copy(f,O/'img'/f.name)
    def tt(T):
        out=''
        for t in T:
            out+=f'<div class="tt"><div class="tt-cap">{esc(t["cap"])}</div><ul>'
            for cls,name,tm,memo in t['rows']:
                out+=f'<li class="{cls}"><b>{esc(name)}</b><span class="tm">{esc(tm)}</span><small>{esc(memo)}</small></li>'
            out+='</ul></div>'
        return out
    pts=lambda L:'<ul class="pts">'+''.join(f'<li><i>{i+1}</i><span>{esc(a)}<small>{esc(b)}</small></span></li>' for i,(a,b) in enumerate(L))+'</ul>'
    links=lambda L:'<div class="links">'+''.join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(t)}</a>' for t,u in L)+'</div>' if L else ''
    def photo(k,eager=False):
        c=cr.get(k,{}); cap=f'<a href="{esc(c["page"])}" target="_blank" rel="noopener">{esc(c.get("title",""))}</a> {esc(c.get("lic",""))}' if c else ''
        return f'<figure class="photo"><img src="img/{k}.jpg" alt="" loading="{"eager" if eager else "lazy"}" {"fetchpriority=\"high\"" if eager else ""}><figcaption>{cap}</figcaption></figure>'
    ch=d.get('choices')
    chs=''
    if ch:
        chs+=f'<section class="s" data-clock="{esc(ch.get("clock",""))}"><div class="eyebrow">{esc(ch["day"])}</div><h2>{ch["h"]}</h2><p class="lead">{esc(ch["lead"])}</p><div class="picked" id="picked">まだ選んでいません。下の案を見て、気に入ったものを押してください。</div></section>'
        for o in ch['options']:
            chs+=(f'<section class="s" data-clock="{esc(o.get("clock",""))}"><div class="opt" data-k="{esc(o["key"])}" id="opt-{esc(o["key"])}">'
                  f'<span class="badge">{esc(o["badge"])}　{esc(o["label"])}</span><h2>{o["h"]}</h2>{photo(o["photo"])}'
                  f'<p class="lead">{esc(o["lead"])}</p><div class="meta"><span>{esc(o["drive"])}</span><span>{esc(o["arrive"])}</span></div>'
                  f'{pts(o["pts"])}{links(o.get("links",[]))}'
                  f'<button class="pick" data-k="{esc(o["key"])}">この案にする</button></div></section>')
    def numsblk(L):
        return '<dl class="nums">'+''.join(f'<div><dt>{esc(a)}</dt><dd>{esc(bb)}<small>{esc(cc)}</small></dd></div>' for a,bb,cc in L)+'</dl>' if L else ''
    def vid(v):
        if not v: return ''
        return (f'<div class="vid"><iframe src="https://www.youtube-nocookie.com/embed/{esc(v["id"])}?rel=0" title="{esc(v["cap"])}" '
                f'loading="lazy" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
                f'<p class="vcap">{esc(v["cap"])}</p>')
    def sec(s):
        head = vid(s.get('video')) if s.get('video') else photo(s['photo'])
        return (f'<section class="s" data-clock="{esc(s.get("clock",""))}"><div class="eyebrow">{esc(s["day"])}</div><h2>{s["h"]}</h2>{head}'
                f'<p class="lead">{esc(s["lead"])}</p>{numsblk(s.get("nums",[]))}{pts(s["pts"])}{tt(s.get("tt",[]))}{links(s.get("links",[]))}</section>')
    pres=''.join(sec(s) for s in d.get('pre_sections',[]))
    secs=''
    for s in d['sections']:
        secs+=sec(s)
    # --- アルバム（album.json があるときだけ） ---
    album='';lfhead='';mapjs=''
    AJ=P/'album.json'
    items=json.load(open(AJ))['items'] if AJ.exists() else []
    if items:
        (O/'album').mkdir(parents=True,exist_ok=True)
        for f in (P/'album').glob('*'): shutil.copy(f,O/'album'/f.name)
        gps=[i for i in items if i.get('lat') is not None]
        # ponytail: 100m格子でざっくり重複排除。厳密なクラスタリングが要るなら差し替え
        spots=len({(round(i['lat']/.0009),round(i['lng']/.0011)) for i in gps})
        nP=sum(1 for i in items if i['kind']=='photo');nV=len(items)-nP
        album=(f'<section class="s" id="album" data-clock="アルバム"><div class="eyebrow">アルバム</div><h2><em>旅の</em><span>記録</span></h2>'
               f'{numsblk([("写真",f"{nP}枚",""),("動画",f"{nV}本",""),("場所",f"{spots}","GPSあり")])}</section>')
        days={}
        for i in items: days.setdefault(i['taken'][:10],[]).append(i)
        for ymd,L in days.items():
            lab=f'{int(ymd[5:7])}/{int(ymd[8:10])}';cells=''
            for i in L:
                k=i['f'][:3];cap=f'<figcaption>{esc(i.get("cap",""))}</figcaption>' if i.get('cap') else ''
                cells+=(f'<figure class="w2"><video controls playsinline preload="none" poster="album/{k}.jpg" src="album/{k}.mp4"></video>{cap}</figure>'
                        if i['kind']=='video' else
                        f'<figure><a href="album/{k}.jpg" target="_blank" rel="noopener"><img loading="lazy" src="album/{k}.jpg" alt=""></a>{cap}</figure>')
            album+=f'<section class="s" data-clock="{lab}"><div class="eyebrow">{lab}</div><div class="grid">{cells}</div></section>'
        if gps:
            album+='<section class="s" data-clock="地図"><div class="eyebrow">地図</div><h2><em>行った</em><span>ところ</span></h2><div id="map"></div></section>'
            lfhead=('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
                    '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>')
            MP=json.dumps([{'lat':i['lat'],'lng':i['lng'],'f':'album/'+i['f'][:3]+'.jpg','cap':i.get('cap','')} for i in gps],ensure_ascii=False)
            mapjs=('\nconst MP='+MP+',MC='+json.dumps(d['accent'])+';(function(){var el=document.getElementById("map");if(!el||!window.L)return;'
                   'var m=L.map(el,{scrollWheelZoom:false}),pts=MP.map(function(p){return [p.lat,p.lng]});'
                   'L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"&copy; <a href=\\"https://www.openstreetmap.org/copyright\\">OpenStreetMap</a>"}).addTo(m);'
                   'MP.forEach(function(p){L.circleMarker([p.lat,p.lng],{radius:7,weight:2,color:"#fff",fillColor:MC,fillOpacity:1}).addTo(m)'
                   '.bindPopup(\'<img src="\'+p.f+\'" style="width:160px;display:block;border-radius:8px">\'+(p.cap?\'<div style="margin-top:4px">\'+p.cap+\'</div>\':""))});'
                   'if(pts.length>1)L.polyline(pts,{color:MC,weight:3,opacity:.7}).addTo(m);'
                   'var fit=function(){m.fitBounds(L.latLngBounds(pts),{padding:[30,30]})};fit();'
                   'new IntersectionObserver(function(es,o){es.forEach(function(e){if(e.isIntersecting){m.invalidateSize();fit();o.disconnect()}})}).observe(el);})();')
    picks_json=json.dumps({o['key']:{'label':o['label'],'next17':o['next17']} for o in (ch['options'] if ch else [])},ensure_ascii=False)
    c=d['cover']; nums=''.join(f'<div><dt>{esc(a)}</dt><dd>{esc(b)}<small>{esc(cc)}</small></dd></div>' for a,b,cc in c['nums'])
    car=d.get('car'); rows=''.join(f'<li><b>{esc(n)}<small>{esc(t)}</small></b><a href="{esc(u)}" target="_blank" rel="noopener">予約 →</a></li>' for n,t,u in (car or {}).get('rows',[]))
    pack=''.join(f'<li><b>{esc(a)}</b><span>{esc(b)}</span></li>' for a,b in d.get('pack',{}).get('items',[]))
    roles=''.join(f'<li><b>{esc(a)}</b><span>{esc(b)}</span></li>' for a,b in d.get('roles',[]))
    rl=d['rail']; mk=rl.get('marker'); ac2=rl.get('accent2') or {}
    marker=(f'<span class="car emo" id="car">{esc(mk[0])}</span>' if mk else '<svg class="car" id="car" viewBox="0 0 26 40" aria-hidden="true">'+'<rect x="1.5" y="4" width="23" height="33" rx="7" fill="var(--ac)"/><rect x="0" y="10" width="26" height="5" rx="2.5" fill="var(--shadow)"/><rect x="0" y="27" width="26" height="5" rx="2.5" fill="var(--shadow)"/><rect x="4" y="7" width="18" height="27" rx="5" fill="var(--ac)"/><path d="M6.5 12h13l-1.6-3.2a2 2 0 0 0-1.8-1.1H9.9a2 2 0 0 0-1.8 1.1L6.5 12z" fill="#eaf3fb"/><path d="M6.5 27h13l-1.6 3.2a2 2 0 0 1-1.8 1.1H9.9a2 2 0 0 1-1.8-1.1L6.5 27z" fill="#cfe2f2"/><rect x="5.5" y="14" width="15" height="11" rx="3" fill="#fff" opacity=".22"/><rect x="6" y="4.6" width="3.6" height="2.2" rx="1.1" fill="#fff8d8"/><rect x="16.4" y="4.6" width="3.6" height="2.2" rx="1.1" fill="#fff8d8"/>'+'</svg>')
    railjs=json.dumps({'mk':mk,'a1':{'ac':d['accent'],'sh':d['accent_shadow'],'wa':d['accent_wash']},'a2':{'ac':ac2.get('accent',d['accent']),'sh':ac2.get('shadow',d['accent_shadow']),'wa':ac2.get('wash',d['accent_wash'])}},ensure_ascii=False)
    carsec=f'''<section class="s" data-clock="出発の前に"><div class="eyebrow">車</div><h2>{car["h"]}</h2><p class="lead">{esc(car["lead"])}</p><ul class="rest">{rows}</ul><p class="note">{esc(car["note"])}</p></section>''' if car else ''
    packsec=f'''<section class="s" data-clock="出発の前に"><div class="eyebrow">準備</div><h2>{esc(d["pack"]["h"])}</h2><ul class="rest">{pack}</ul><div class="eyebrow" style="margin-top:8px">分担</div><ul class="rest">{roles}</ul></section>''' if d.get('pack') else ''
    endsec=f'''<section class="s end"><div class="eyebrow">おわり</div><h2>{esc(d["end"]["h"])}</h2><p class="lead">{esc(d["end"]["lead"])}</p><p class="credit">{esc(d["credit"])}</p></section>''' if d.get('end') else ''
    page=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(d["title"])}</title><meta name="robots" content="noindex"><meta property="og:title" content="{esc(d["title"])}"><meta property="og:description" content="{esc(d["og_desc"])}"><meta property="og:image" content="img/{c["photo"]}.jpg">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700;900&display=swap">{lfhead}
<style>
:root{{--bg:#fff;--card:#f6f9fc;--ink:#202020;--mute:#645f5e;--ash:#8a8482;--line:#e3e8ee;--ac:{d["accent"]};--shadow:{d["accent_shadow"]};--wash:{d["accent_wash"]};color-scheme:light}}
*{{box-sizing:border-box;min-width:0}}html,body{{margin:0;overflow-x:hidden;overscroll-behavior-x:none;background:var(--bg);color:var(--ink);font-family:"Zen Kaku Gothic New","Hiragino Sans","Noto Sans JP",sans-serif;font-weight:700;-webkit-font-smoothing:antialiased}}
h1,h2,h3,p{{margin:0}}h1,h2{{line-height:1.15;text-wrap:balance;word-break:keep-all;overflow-wrap:anywhere}}
#deck{{height:100vh;height:100dvh;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;touch-action:pan-y pinch-zoom;scroll-snap-type:y proximity;scroll-behavior:smooth;-webkit-overflow-scrolling:touch}}
.s{{min-height:100vh;min-height:100dvh;scroll-snap-align:start;padding:52px 22px 40px;max-width:min(560px,100%);overflow-x:hidden;display:flex;flex-direction:column;justify-content:center;gap:14px;margin:0 auto}}
.eyebrow{{font-size:12px;letter-spacing:.12em;color:var(--ac);font-weight:900}}
.s h2{{font-size:clamp(28px,8vw,40px);font-weight:900;letter-spacing:-.02em}}.s h2 em{{font-style:normal;color:var(--ac)}}.s h2 span,.who span{{white-space:nowrap}}
.lead{{font-size:15px;color:var(--mute);line-height:1.75}}
.photo{{margin:0;border-radius:20px;overflow:hidden;background:#e9eef3;aspect-ratio:16/10}}.photo img{{display:block;width:100%;height:100%;object-fit:cover}}
.photo figcaption{{display:none}}
.pts{{list-style:none;margin:0;padding:0;display:grid;gap:10px}}.pts li{{display:grid;grid-template-columns:28px 1fr;gap:10px;align-items:start;font-size:16px;line-height:1.5}}
.pts li i{{font-style:normal;width:24px;height:24px;border-radius:50%;background:var(--ac);color:#fff;font-weight:900;font-size:12px;display:inline-flex;align-items:center;justify-content:center;margin-top:3px}}
.pts li small{{display:block;font-size:12.5px;color:var(--mute);font-weight:500;line-height:1.6}}
.nums{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0;width:100%}}.nums div{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 8px;text-align:center}}
.nums dt{{font-size:10.5px;color:var(--ash);letter-spacing:.06em}}.nums dd{{margin:0;font-size:22px;font-weight:900;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.2}}.nums dd small{{display:block;font-size:10.5px;color:var(--mute)}}
.rest{{list-style:none;margin:0;padding:0;border-top:2px solid var(--ink)}}.rest li{{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 2px;border-bottom:1px solid var(--line);font-size:14.5px}}
.rest li b{{font-weight:900;word-break:keep-all;overflow-wrap:break-word;min-width:0;flex:1 1 auto}}
.rest li:has(>span) b{{white-space:nowrap;flex:0 0 auto}}
.rest li>span{{min-width:0}}.rest li span{{color:var(--mute);font-size:12.5px;text-align:right}}.rest li b small{{white-space:normal;word-break:normal;overflow-wrap:anywhere}}
.rest li small{{display:block;font-size:11.5px;color:var(--ash);font-weight:500;line-height:1.6}}
.rest li a{{white-space:nowrap;flex:0 0 auto;font-size:12px;font-weight:900;color:#fff;background:var(--ac);border-radius:999px;padding:6px 12px;text-decoration:none}}
.tt{{margin:2px 0 0}}
.tt-cap{{font-size:12px;font-weight:900;letter-spacing:.06em;color:var(--ac);margin-bottom:6px}}
.tt ul{{list-style:none;margin:0 0 14px;padding:0;border-top:2px solid var(--ink)}}
.tt li{{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:9px 2px;border-bottom:1px solid var(--line);align-items:baseline}}
.tt li b{{font-weight:900;font-size:14.5px;white-space:nowrap}}
.tt li .tm{{font-weight:900;font-size:14.5px;font-variant-numeric:tabular-nums;white-space:nowrap}}
.tt li small{{grid-column:1/-1;font-size:12.5px;color:var(--mute);font-weight:500;line-height:1.55}}
.tt li.best{{background:var(--wash);border-radius:10px;padding:9px 8px}}
.tt li.best b:before{{content:"◎ ";color:var(--ac)}}
.tt li.ok b:before{{content:"○ ";color:var(--ash)}}
.tt li.mid b:before{{content:"△ ";color:var(--ash)}}
.tt li.no{{opacity:.5}}.tt li.no b:before{{content:"× ";color:var(--ash)}}
.vid{{position:relative;aspect-ratio:16/9;border-radius:18px;overflow:hidden;background:#000}}
.vid iframe{{position:absolute;inset:0;width:100%;height:100%;border:0}}
.vcap{{font-size:11.5px;color:var(--ash);font-weight:500;margin-top:-8px}}
.note{{background:var(--wash);border-radius:14px;padding:12px 14px;font-size:13px;line-height:1.7;color:var(--ink)}}
.links{{display:flex;flex-wrap:wrap;gap:6px}}.links{{max-width:100%}}.links a{{font-size:12px;overflow-wrap:anywhere;font-weight:900;color:var(--ink);text-decoration:none;border:1.5px solid var(--ink);border-radius:999px;padding:5px 11px}}.links a:after{{content:" →"}}
.hub{{text-align:center;align-items:center}}.hub .date{{display:inline-block;background:var(--ac);color:#fff;font-weight:900;font-size:18px;padding:6px 18px;border-radius:999px}}
.hub h1{{font-size:clamp(34px,10vw,52px);font-weight:900;letter-spacing:-.03em;margin-top:6px}}.hub .who{{font-size:13.5px;color:var(--mute);max-width:26em}}
.hub .photo{{width:100%}}.hint{{font-size:12px;color:var(--ash);text-align:center}}
.end{{text-align:center;align-items:center}}.credit{{font-size:10.5px;color:var(--ash);line-height:1.7;max-width:420px;font-weight:500}}.credit a{{color:inherit}}
.opt{{border:2px solid var(--line);border-radius:20px;padding:14px 14px 16px;display:grid;gap:10px;background:#fff}}
.opt.on{{border-color:var(--ac);box-shadow:0 0 0 4px var(--wash)}}
.badge{{display:inline-block;background:var(--wash);color:var(--ac);font-size:11.5px;font-weight:900;padding:4px 10px;border-radius:999px;letter-spacing:.06em}}
.meta{{display:flex;gap:8px;flex-wrap:wrap;font-size:11.5px;color:var(--mute)}}.meta span{{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:4px 10px}}
.pick{{width:100%;background:var(--ac);color:#fff;font-weight:900;font-size:17px;padding:14px;border-radius:12px;border:0;box-shadow:0 4px 0 0 var(--shadow);cursor:pointer;font-family:inherit}}
.pick:active{{transform:translateY(4px);box-shadow:none}}
.opt.on .pick{{background:var(--ink);box-shadow:0 4px 0 0 #000}}
.picked{{background:var(--wash);border-radius:14px;padding:12px 14px;font-size:13.5px;line-height:1.7}}
.rail{{position:fixed;right:10px;top:50%;transform:translateY(-50%);height:min(56vh,420px);width:44px;pointer-events:none;z-index:5}}
.rail .lab{{position:absolute;left:0;right:0;text-align:center;font-size:11px;font-weight:900}}.rail .lab.t{{top:-36px}}.rail .lab.b{{bottom:-36px}}
.rail .track{{position:absolute;left:50%;top:0;bottom:0;width:14px;margin-left:-7px;background:#e7ecf2;border-radius:999px}}
.rail .track:after{{content:"";position:absolute;left:50%;top:8px;bottom:8px;width:2px;margin-left:-1px;border-radius:2px;background:repeating-linear-gradient(180deg,#fff 0 9px,transparent 9px 18px)}}
.rail .stop{{position:absolute;left:50%;width:11px;height:11px;margin:-5.5px 0 0 -5.5px;border-radius:50%;background:#fff;border:2px solid #c6d1dc;transition:background .3s,border-color .3s,transform .3s}}
.rail .stop.on{{background:var(--ac);border-color:var(--ac);transform:scale(1.3)}}
.rail .car.emo{{font-size:28px;line-height:40px;text-align:center;filter:none}}
:root{{transition:--ac .3s}}
.rail .car{{position:absolute;left:50%;width:26px;height:40px;margin:-20px 0 0 -13px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.22))}}
.rail .klabel{{position:absolute;right:38px;top:0;transform:translateY(-50%);background:var(--ink);color:#fff;font-size:10.5px;font-weight:900;padding:4px 9px;border-radius:999px;white-space:nowrap;opacity:0;transition:opacity .25s;box-shadow:0 1px 4px rgba(0,0,0,.18)}}
.rail .klabel.on{{opacity:1}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.grid figure{{margin:0;min-width:0}}.grid .w2{{grid-column:1/-1}}
.grid img,.grid video{{display:block;width:100%;aspect-ratio:1;object-fit:cover;border-radius:14px;background:#e9eef3}}.grid .w2 video{{aspect-ratio:16/9;background:#000}}
.grid figcaption{{font-size:11.5px;color:var(--mute);font-weight:500;line-height:1.55;margin-top:5px}}
#map{{height:62vh;border-radius:20px;overflow:hidden;background:#e9eef3}}#map img{{max-width:none}}
@media(max-width:480px){{.s{{padding-right:56px}}}}
@media(prefers-reduced-motion:reduce){{#deck{{scroll-behavior:auto}}}}
</style></head><body>
<div class="rail" aria-hidden="true"><span class="lab t">{esc(d["rail"]["top"])}</span><span class="track"></span><span class="klabel" id="klabel"></span>{marker}<span class="lab b">{esc(d["rail"]["bottom"])}</span></div>
<div id="deck">
<section class="s hub"><span class="date">{esc(d["date_label"])}</span><h1>{esc(d["title"])}</h1>{photo(c["photo"],True)}<p class="who">{c["who"]}</p><dl class="nums">{nums}</dl><p class="hint">下にスクロールで {esc(d["rail"]["top"])} → {esc(d["rail"]["bottom"])}</p></section>
{pres}{chs}{secs}{album}
{carsec}
{packsec}
{endsec}
</div>
<script>
const PICKS={picks_json};const RAIL={railjs};
const box=document.getElementById('picked');
function apply(k){{if(!PICKS[k])return;document.querySelectorAll('.opt').forEach(o=>o.classList.toggle('on',o.dataset.k===k));
 box.innerHTML='いま選んでいるのは <b>'+PICKS[k].label+'</b>。'+PICKS[k].next17+'。<br>変えたいときは別の案の「この案にする」を押してください。';}}
document.querySelectorAll('.pick').forEach(b=>b.addEventListener('click',()=>{{try{{localStorage.setItem('pick16',b.dataset.k)}}catch(e){{}};apply(b.dataset.k);box.scrollIntoView({{behavior:'smooth',block:'center'}});}}));
try{{apply(localStorage.getItem('pick16'))}}catch(e){{}}
const deck=document.getElementById('deck'),car=document.getElementById('car'),klabel=document.getElementById('klabel'),rail=document.querySelector('.rail');
const secs=[...document.querySelectorAll('#deck .s')].filter(s=>s.dataset.clock);
const range=()=>Math.max(1,deck.scrollHeight-deck.clientHeight);
let stops=[];
function build(){{
 rail.querySelectorAll('.stop').forEach(e=>e.remove());stops=[];
 secs.forEach(s=>{{
  const p=Math.min(1,Math.max(0,(s.offsetTop+s.offsetHeight/2-deck.clientHeight/2)/range()));
  const i=document.createElement('i');i.className='stop';i.style.top=(p*100)+'%';
  rail.insertBefore(i,car);stops.push({{p,el:i}});
 }});
}}
let raf=0;
function upd(){{raf=0;
 const r=deck.scrollTop/range();
 car.style.top=(r*100)+'%';klabel.style.top=(r*100)+'%';
 const A=r<0.5?RAIL.a1:RAIL.a2;const rs=document.documentElement.style;rs.setProperty('--ac',A.ac);rs.setProperty('--shadow',A.sh);rs.setProperty('--wash',A.wa);
 if(RAIL.mk)car.textContent=r<0.5?RAIL.mk[0]:RAIL.mk[1];
 stops.forEach(o=>o.el.classList.toggle('on',r>=o.p-0.004));
 const mid=deck.clientHeight/2;
 const cur=secs.find(s=>{{const b=s.getBoundingClientRect();return b.top<=mid&&b.bottom>=mid;}});
 const t=cur?cur.dataset.clock:'';
 klabel.textContent=t;klabel.classList.toggle('on',!!t);
}}
deck.addEventListener('scroll',()=>{{if(!raf)raf=requestAnimationFrame(upd);}},{{passive:true}});
addEventListener('resize',()=>{{build();upd();}});
build();upd();{mapjs}
</script></body></html>'''
    (O/'index.html').write_text(page,encoding='utf-8'); print('built',O/'index.html',len(page))
def status(d):
    """dates[1] が過ぎていれば done"""
    return 'done' if d.get('dates',[''])[-1]<datetime.date.today().isoformat() else 'plan'
def build_index(who='yuri',label='ゆりと'):
    T=[]
    for p in sorted((ROOT/'packs').iterdir()):
        if not (p/'trip.json').exists(): continue
        d=json.load(open(p/'trip.json'))
        if d.get('with')!=who: continue
        A=p/'album.json';T.append((d,p.name,json.load(open(A))['items'] if A.exists() else None))
    T.sort(key=lambda t:t[0].get('dates',[''])[0])
    days=sum((datetime.date.fromisoformat(d['dates'][1])-datetime.date.fromisoformat(d['dates'][0])).days+1 for d,_,_ in T if d.get('dates'))
    shots=sum(1 for _,_,I in T if I for i in I if i['kind']=='photo')
    cards=''
    for d,slug,I in T:
        done=status(d)=='done'
        cards+=(f'<li class="card"><a href="../{slug}/"><img src="../{slug}/img/{d["cover"]["photo"]}.jpg" alt="" loading="lazy"></a>'
                f'<div class="b"><span class="badge{" done" if done else ""}">{"行った" if done else "これから"}</span>'
                f'<p class="dl">{esc(d["date_label"])}</p><h2>{esc(d["title"])}</h2>'
                f'<div class="links"><a href="../{slug}/">しおり →</a>'
                +(f'<a href="../{slug}/#album">アルバム →</a>' if I else '')+'</div></div></li>')
    page=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{label} 旅の記録</title><meta name="robots" content="noindex"><meta property="og:title" content="{label} 旅の記録">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700;900&display=swap">
<style>
:root{{--bg:#fff;--card:#faf8f8;--ink:#202020;--mute:#645f5e;--ash:#8a8482;--line:#e6e2e1;--ac:#e5382b;--shadow:#a8271d;--wash:#fde3df;color-scheme:light}}
*{{box-sizing:border-box;min-width:0}}html,body{{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font-family:"Zen Kaku Gothic New","Hiragino Sans","Noto Sans JP",sans-serif;font-weight:700;-webkit-font-smoothing:antialiased}}
h1,h2,p{{margin:0;line-height:1.2;text-wrap:balance;word-break:keep-all;overflow-wrap:anywhere}}
main{{max-width:min(560px,100%);margin:0 auto;padding:44px 22px 56px;display:grid;gap:26px}}
.hub{{text-align:center;display:grid;gap:12px;justify-items:center}}
.date{{display:inline-block;background:var(--ac);color:#fff;font-weight:900;font-size:16px;padding:6px 18px;border-radius:999px}}
h1{{font-size:clamp(34px,10vw,52px);font-weight:900;letter-spacing:-.03em}}
.nums{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0;width:100%}}.nums div{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 8px;text-align:center}}
.nums dt{{font-size:10.5px;color:var(--ash);letter-spacing:.06em}}.nums dd{{margin:0;font-size:22px;font-weight:900;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.2}}
.trips{{list-style:none;margin:0;padding:0;display:grid;gap:18px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:20px;overflow:hidden}}
.card>a{{display:block}}.card img{{display:block;width:100%;aspect-ratio:16/10;object-fit:cover;background:#eee}}
.card .b{{padding:14px 16px 16px;display:grid;gap:7px;justify-items:start}}
.badge{{background:var(--wash);color:var(--ac);font-size:11.5px;font-weight:900;padding:4px 10px;border-radius:999px;letter-spacing:.06em}}
.badge.done{{background:#efeceb;color:var(--ash)}}
.dl{{font-size:12.5px;color:var(--mute);font-weight:700}}.card h2{{font-size:23px;font-weight:900;letter-spacing:-.02em}}
.links{{display:flex;flex-wrap:wrap;gap:6px;margin-top:3px}}
.links a{{font-size:12px;font-weight:900;color:var(--ink);text-decoration:none;border:1.5px solid var(--ink);border-radius:999px;padding:5px 12px}}
</style></head><body><main>
<div class="hub"><span class="date">{label}</span><h1>旅の記録</h1>
<dl class="nums"><div><dt>旅</dt><dd>{len(T)}回</dd></div><div><dt>日数</dt><dd>{days}日</dd></div><div><dt>写真</dt><dd>{shots}枚</dd></div></dl></div>
<ul class="trips">{cards}</ul>
</main></body></html>'''
    O=ROOT/'docs'/who;O.mkdir(parents=True,exist_ok=True);(O/'index.html').write_text(page,encoding='utf-8');print('built',O/'index.html',len(page))
if __name__=='__main__':
    a=sys.argv[1:]
    if a!=['index']:
        for s in [x for x in a if x!='index'] or [p.name for p in (ROOT/'packs').iterdir() if (p/'trip.json').exists()]: build(s)
    build_index()
