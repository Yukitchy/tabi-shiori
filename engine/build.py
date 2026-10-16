#!/usr/bin/env python3
"""tabi-shiori engine: packs/<slug>/trip.json + img/ -> docs/<slug>/index.html"""
import json,zlib,sys,shutil,html,pathlib,datetime,re,hashlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
def esc(s):return html.escape(s,quote=True)
def emp(s):return re.sub(r"\*\*(.+?)\*\*",r"<b>\1</b>",esc(s))

# --- アルバムの「選んで保存」（album.json があるページだけ出る） ---
ALBUM_CSS='''
.bigbtn{display:block;text-align:center;text-decoration:none;width:100%;background:var(--ac);color:#fff;font-weight:900;font-size:17px;padding:14px;border-radius:12px;border:0;box-shadow:0 4px 0 0 var(--shadow);cursor:pointer;font-family:inherit}
.bigbtn:active{transform:translateY(4px);box-shadow:none}
.selhelp{font-size:12px;color:var(--ash);text-align:center;font-weight:500}
.grid figure{position:relative}
.saveb{position:absolute;right:6px;bottom:6px;background:rgba(255,255,255,.94);color:var(--ink);font-size:12px;font-weight:900;text-decoration:none;padding:7px 12px;border-radius:999px;box-shadow:0 1px 4px rgba(0,0,0,.3)}
.grid figure:has(figcaption) .saveb{bottom:28px}
.selb{display:none;position:absolute;left:6px;top:6px;width:38px;height:38px;border-radius:50%;border:3px solid #fff;background:rgba(0,0,0,.35);box-shadow:0 1px 4px rgba(0,0,0,.35);cursor:pointer;padding:0}
.selb:after{content:"";position:absolute;left:9px;top:3px;width:12px;height:20px;border:solid #fff;border-width:0 4px 4px 0;transform:rotate(45deg);opacity:0}
body.selecting .selb{display:block}
body.selecting .grid img,body.selecting .grid video{opacity:.62}
.grid figure.on img,.grid figure.on video{opacity:1;outline:4px solid var(--ac);outline-offset:-4px;border-radius:14px}
.grid figure.on .selb{background:var(--ac);border-color:#fff}
.grid figure.on .selb:after{opacity:1}
body.selecting .saveb{display:none}
@media(hover:hover) and (pointer:fine){.saveb{opacity:0;transition:opacity .15s}.grid figure:hover .saveb,.saveb:focus-visible{opacity:1}}
body.selecting .grid{padding-bottom:86px}
#selbar{position:fixed;left:0;right:0;bottom:0;z-index:20;background:var(--ink);color:#fff;padding:12px 14px calc(12px + env(safe-area-inset-bottom));display:none;align-items:center;gap:10px;box-shadow:0 -2px 12px rgba(0,0,0,.25)}
body.selecting #selbar{display:flex}
#selbar .n{font-size:15px;font-weight:900;flex:1 1 auto;min-width:0}
#selbar button{font-family:inherit;font-weight:900;font-size:15px;border:0;border-radius:10px;padding:12px 16px;cursor:pointer}
#selbar .go{background:var(--ac);color:#fff}
#selbar .go[disabled]{opacity:.45;cursor:default}
#selbar .cancel{background:transparent;color:#fff;border:2px solid rgba(255,255,255,.5);padding:10px 14px}
'''
BIG_CSS='''
.lead{font-size:19px;line-height:1.85}
.pts li{font-size:20px;line-height:1.6}
.pts li i{width:30px;height:30px;font-size:15px}
.pts{gap:14px}
.pts li{grid-template-columns:34px 1fr}
.pts li small{font-size:16px;line-height:1.7}
.eyebrow{font-size:15px}
.nums dt{font-size:13.5px}
.nums dd{font-size:26px}
.nums dd small{font-size:13px}
.hub .who{font-size:17px}
.hub .date{font-size:21px}
.hint{font-size:15px}
.links a{font-size:15px;padding:8px 14px}
.grid figcaption{font-size:15px}
.selhelp{font-size:15px}
.saveb{font-size:15px;padding:9px 15px}
.s h2{font-size:clamp(32px,9vw,46px)}
.note{font-size:17px}
.credit{font-size:13px}
'''
SELECT_JS='''
(function(){
 var figs=[...document.querySelectorAll('.grid figure[data-k],.belt figure[data-k]')];
 var bar=document.getElementById('selbar'),mode=document.getElementById('selmode');
 if(!figs.length||!bar||!mode)return;
 var n=bar.querySelector('.n'),go=bar.querySelector('.go'),cancel=bar.querySelector('.cancel');
 var sel=new Set();
 function paint(){
  figs.forEach(function(f){f.classList.toggle('on',sel.has(f.dataset.k))});
  figs.forEach(function(f){var b=f.querySelector('.selb');if(b)b.setAttribute('aria-pressed',sel.has(f.dataset.k)?'true':'false')});
  n.textContent=sel.size?sel.size+'枚を選んでいます':'保存したい写真を押してください';
  go.disabled=!sel.size;go.textContent=sel.size?sel.size+'枚を保存':'保存';
 }
 mode.addEventListener('click',function(){
  document.body.classList.add('selecting');paint();
  var s0=figs[0].closest('section');s0&&s0.scrollIntoView({behavior:'smooth'});
 });
 cancel.addEventListener('click',function(){sel.clear();document.body.classList.remove('selecting');paint()});
 figs.forEach(function(f){
  f.addEventListener('click',function(e){
   if(!document.body.classList.contains('selecting'))return;
   if(e.target.tagName==='VIDEO')return;
   e.preventDefault();
   var k=f.dataset.k;if(sel.has(k))sel.delete(k);else sel.add(k);paint();
  });
 });
 function load(src){return new Promise(function(res,rej){var s=document.createElement('script');s.src=src;s.onload=res;s.onerror=rej;document.head.appendChild(s)})}
 go.addEventListener('click',async function(){
  if(!sel.size)return;
  var keys=figs.filter(function(f){return sel.has(f.dataset.k)}).map(function(f){return {k:f.dataset.k,ext:f.dataset.ext}});
  var old=go.textContent;go.disabled=true;
  try{
   if(!window.JSZip){go.textContent='準備中…';await load('https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js')}
   var zip=new JSZip();
   for(var i=0;i<keys.length;i++){
    go.textContent='保存中 '+(i+1)+'/'+keys.length;
    var r=await fetch(MEDIA+keys[i].k+'.'+keys[i].ext);
    zip.file(SLUG+'-'+keys[i].k+'.'+keys[i].ext,await r.blob());
   }
   go.textContent='まとめています…';
   var blob=await zip.generateAsync({type:'blob'});
   var u=URL.createObjectURL(blob),a=document.createElement('a');
   a.href=u;a.download=SLUG+'-写真'+keys.length+'枚.zip';document.body.appendChild(a);a.click();a.remove();
   setTimeout(function(){URL.revokeObjectURL(u)},4000);
   go.textContent=old;go.disabled=false;
  }catch(err){
   go.textContent='1枚ずつ保存します';
   for(var j=0;j<keys.length;j++){
    var a2=document.createElement('a');a2.href=MEDIA+keys[j].k+'.'+keys[j].ext;
    a2.download=SLUG+'-'+keys[j].k+'.'+keys[j].ext;document.body.appendChild(a2);a2.click();a2.remove();
    await new Promise(function(r){setTimeout(r,350)});
   }
   go.textContent=old;go.disabled=false;
  }
 });
 paint();
})();
'''
# --- 別タブの一覧ページ docs/<slug>/list/ （下タブで 今日の流れ/写真/動画/MAP を切替） ---
LIST_CSS = """
:root{--bg:#fff;--card:#f6f9fc;--ink:#202020;--mute:#645f5e;--ash:#8a8482;--line:#e3e8ee;--ac:%(ac)s;--shadow:%(sh)s;--wash:%(wa)s;color-scheme:light}
*{box-sizing:border-box;min-width:0}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:{fontstack}"Hiragino Sans","Noto Sans JP",sans-serif;font-weight:700;-webkit-font-smoothing:antialiased;overflow-x:hidden}
body{padding-bottom:calc(72px + env(safe-area-inset-bottom))}
.wrap{max-width:min(620px,100%%);margin:0 auto;padding:0 20px}
header{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.94);backdrop-filter:saturate(1.6) blur(10px);border-bottom:1px solid var(--line)}
header .wrap{padding-top:14px;padding-bottom:12px}
header .date{display:inline-block;background:var(--ac);color:#fff;font-weight:900;font-size:13px;padding:4px 13px;border-radius:999px;letter-spacing:.02em}
header h1{margin:7px 0 0;font-size:22px;font-weight:900;letter-spacing:-.025em;line-height:1.25}
main{padding:22px 0 8px}
.panel{display:none}
.panel.on{display:block}
.eyebrow{font-size:12px;letter-spacing:.12em;color:var(--ac);font-weight:900}
.ptitle{font-size:clamp(26px,7vw,34px);font-weight:900;letter-spacing:-.03em;line-height:1.15;margin:4px 0 2px}
.ptitle em{font-style:normal;color:var(--ac)}
.count{font-size:13px;color:var(--ash);font-weight:500;margin:0 0 16px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.grid figure{margin:0;position:relative}
.grid img,.grid video{display:block;width:100%%;aspect-ratio:1;object-fit:cover;border-radius:14px;background:#e9eef3}
.grid .w2{grid-column:1/-1}.grid .w2 video{aspect-ratio:16/9;background:#000}
.grid figcaption{font-size:12px;color:var(--mute);font-weight:500;margin-top:4px}
.tday{display:flex;align-items:baseline;gap:10px;margin:26px 0 10px;padding-top:14px;border-top:2px solid var(--ink)}
.tday:first-of-type{margin-top:6px}
.tday b{font-size:15px;font-weight:900;color:var(--ac);font-variant-numeric:tabular-nums}
.tday span{font-size:14px;font-weight:700;color:var(--mute)}
#map{height:calc(100vh - 250px);min-height:360px;border-radius:20px;overflow:hidden;background:#e9eef3}
#map img{max-width:none}
.flow{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.flow li{display:grid;grid-template-columns:96px 1fr;gap:14px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:12px;cursor:pointer;transition:border-color .15s,transform .15s}
.flow li:hover{border-color:var(--ac);transform:translateY(-1px)}
.flow img{width:96px;height:96px;object-fit:cover;border-radius:14px;background:#e9eef3;display:block}
.flow .tm{font-size:12px;font-weight:900;color:var(--ac);font-variant-numeric:tabular-nums;letter-spacing:.06em}
.flow h3{margin:3px 0 5px;font-size:18px;font-weight:900;line-height:1.3;letter-spacing:-.02em}
.flow p{margin:0;font-size:13.5px;color:var(--mute);font-weight:500;line-height:1.65}
nav{position:fixed;left:0;right:0;bottom:0;z-index:30;background:rgba(255,255,255,.96);backdrop-filter:saturate(1.6) blur(10px);border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom)}
nav .wrap{display:grid;grid-template-columns:repeat(4,1fr);padding:0 20px}
nav button{position:relative;font-family:inherit;background:none;border:0;padding:16px 2px 15px;cursor:pointer;color:var(--ash);font-weight:900;font-size:14px;letter-spacing:.02em;white-space:nowrap}
nav button:after{content:"";position:absolute;left:50%%;top:0;width:0;height:3px;background:var(--ac);border-radius:0 0 3px 3px;transition:width .18s,left .18s}
nav button.on{color:var(--ac)}
nav button.on:after{left:20%%;width:60%%}
@media(min-width:700px){.grid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:400px){nav .wrap{padding:0 8px}nav button{font-size:13px;letter-spacing:0}}
"""
LIST_BIG = """
header h1{font-size:25px}
.flow h3{font-size:21px}
.flow p{font-size:16px}
.flow .tm{font-size:14px}
.flow li{grid-template-columns:112px 1fr}
.flow img{width:112px;height:112px}
.grid figcaption{font-size:15px}
.count{font-size:15px}
.eyebrow{font-size:15px}
.tday b{font-size:18px}.tday span{font-size:17px}
nav button{font-size:15px}
@media(max-width:400px){nav button{font-size:13px;letter-spacing:0}}
.saveb{font-size:15px;padding:9px 15px}
.selhelp{font-size:15px}
"""
LIST_JS = """
var tabs=[...document.querySelectorAll('nav button')],panels=[...document.querySelectorAll('.panel')];
function show(k){
 tabs.forEach(function(b){b.classList.toggle('on',b.dataset.t===k)});
 panels.forEach(function(p){p.classList.toggle('on',p.dataset.t===k)});
 try{location.hash=k}catch(e){}
 scrollTo(0,0);
 if(k==='map'&&window.__map){
  var m=window.__map;
  [0,120,400].forEach(function(t){setTimeout(function(){m.invalidateSize();window.__fit&&window.__fit();},t)});
 }
}
tabs.forEach(function(b){b.addEventListener('click',function(){show(b.dataset.t)})});
document.querySelectorAll('.flow li').forEach(function(li){
 li.addEventListener('click',function(){show('photo');
  var t=document.getElementById('t'+li.dataset.i);if(t)t.scrollIntoView({behavior:'smooth',block:'start'});});
});
show((location.hash||'#flow').slice(1)||'flow');
addEventListener('hashchange',function(){show((location.hash||'#flow').slice(1)||'flow')});
"""

def build_list(slug,d,items,O):
    L=O/'list'; L.mkdir(parents=True,exist_ok=True)
    big = d.get('text')=='large'
    photos=[i for i in items if i['kind']=='photo']
    videos=[i for i in items if i['kind']=='video']
    gps=[i for i in items if i.get('lat') is not None]

    def cell(i,w2=False):
        k=i['f'][:3]; ext='mp4' if i['kind']=='video' else 'jpg'
        cap=f'<figcaption>{esc(i.get("cap",""))}</figcaption>' if i.get('cap') else ''
        sv=f'<a class="saveb" href="../album/{k}.{ext}" download="{slug}-{k}.{ext}">保存</a>'
        sb='<button class="selb" type="button" aria-pressed="false" aria-label="選ぶ"></button>'
        if i['kind']=='video':
            return (f'<figure class="w2" data-k="{k}" data-ext="mp4"><video controls playsinline preload="none" '
                    f'poster="../album/{k}.jpg" src="../album/{k}.mp4"></video>{sb}{sv}{cap}</figure>')
        return (f'<figure data-k="{k}" data-ext="jpg"><a href="../album/{k}.jpg" target="_blank" rel="noopener">'
                f'<img loading="lazy" src="../album/{k}.jpg" alt=""></a>{sb}{sv}{cap}</figure>')

    # 写真タブ: 行程の時刻で見出しを打つ
    marks=[]
    for n,sec in enumerate(d.get('sections',[])):
        t=sec.get('day','')
        if ':' in t: marks.append((t,n,re.sub('<[^>]+>','',sec.get('h',''))))
    groups=[]  # 空の見出しを出さないよう、先に写真を各区間へ振り分ける
    for i in photos:
        hm=i['taken'][11:16]
        cur=None
        for t,n,label in marks:
            if hm>=t: cur=(t,n,label)
        if not groups or groups[-1][0]!=cur: groups.append([cur,[]])
        groups[-1][1].append(i)
    photogrid=''
    for head,grp in groups:
        if head:
            t,n,label=head
            photogrid+=f'<div class="tday" id="t{n}"><b>{esc(t)}</b><span>{esc(label)}</span></div>'
        photogrid+='<div class="grid">'+''.join(cell(i) for i in grp)+'</div>'

    vg=''.join(cell(i) for i in videos)
    flow=''
    for n,sec in enumerate(d.get('sections',[])):
        flow+=(f'<li data-i="{n}">'+(f'<img loading="lazy" src="../img/{esc(sec["photo"])}.jpg" alt="">' if sec.get('photo') else '<span class="noimg" style="width:96px;height:96px;border-radius:14px;background:#e9eef3;display:block"></span>')+
               f'<div><div class="tm">{esc(sec.get("day",""))}</div><h3>{re.sub("<[^>]+>","",sec.get("h",""))}</h3>'
               f'<p>{esc(sec.get("lead","")[:90])}{"…" if len(sec.get("lead",""))>90 else ""}</p></div></li>')

    mapjs=''
    if gps:
        MP=json.dumps([{'lat':i['lat'],'lng':i['lng'],'f':'../album/'+i['f'][:3]+'.jpg'} for i in gps],ensure_ascii=False)
        mapjs=('var MP='+MP+',MC='+json.dumps(d['accent'])+';(function(){var el=document.getElementById("map");if(!el||!window.L)return;'
               'var m=L.map(el,{scrollWheelZoom:false}),pts=MP.map(function(p){return [p.lat,p.lng]});'
               'L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"&copy; OpenStreetMap"}).addTo(m);'
               'MP.forEach(function(p){L.circleMarker([p.lat,p.lng],{radius:7,weight:2,color:"#fff",fillColor:MC,fillOpacity:1}).addTo(m)'
               '.bindPopup(\'<img src="\'+p.f+\'" style="width:160px;display:block;border-radius:8px">\')});'
               'if(pts.length>1)L.polyline(pts,{color:MC,weight:3,opacity:.7}).addTo(m);'
               'window.__map=m;window.__fit=function(){m.fitBounds(L.latLngBounds(pts),{padding:[26,26]})};window.__fit();})();')

    css=(LIST_CSS % {'ac':d['accent'],'sh':d['accent_shadow'],'wa':d['accent_wash']})+ALBUM_CSS+(LIST_BIG if big else '')
    page=('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
          f'<title>{esc(d["title"])} — 一覧</title><meta name="robots" content="noindex">'
          '{fontlink}'
          '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
          '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>'
          f'<style>{css}</style></head><body>'
          f'<header><div class="wrap"><span class="date">{esc(d["date_label"])}</span><h1>{esc(d["title"])}</h1></div></header><main>'
          f'<section class="panel" data-t="flow"><div class="wrap"><div class="eyebrow">9か所</div>'
          f'<h2 class="ptitle"><em>今日</em>の流れ</h2><p class="count">押すと、その時間の写真へ飛びます。</p>'
          f'<ul class="flow">{flow}</ul></div></section>'
          f'<section class="panel" data-t="photo"><div class="wrap"><div class="eyebrow">アルバム</div>'
          f'<h2 class="ptitle"><em>写真</em> {len(photos)}枚</h2>'
          '<p class="count">1枚だけでいいときは、写真の右下の「保存」を押してください。</p>'
          '<button class="bigbtn" id="selmode" type="button">写真を選んで保存する</button>'
          f'{photogrid}</div></section>'
          f'<section class="panel" data-t="video"><div class="wrap"><div class="eyebrow">アルバム</div>'
          f'<h2 class="ptitle"><em>動画</em> {len(videos)}本</h2><p class="count">押すと再生します。</p>'
          f'<div class="grid">{vg}</div></div></section>'
          f'<section class="panel" data-t="map"><div class="wrap"><div class="eyebrow">地図</div>'
          f'<h2 class="ptitle"><em>行った</em>ところ</h2><p class="count">写真の位置 {len(gps)}件</p>'
          f'<div id="map"></div></div></section>'
          '</main>'
          '<div id="selbar"><span class="n"></span><button class="cancel" type="button">やめる</button>'
          '<button class="go" type="button" disabled>保存</button></div>'
          '<nav><div class="wrap"><button data-t="flow">今日の流れ</button>'
          '<button data-t="photo">写真</button>'
          '<button data-t="video">動画</button>'
          '<button data-t="map">MAP</button></div></nav>'
          f'<script>const SLUG={json.dumps(slug)},MEDIA="../album/";{mapjs}{LIST_JS}{SELECT_JS}</script></body></html>')
    (L/'index.html').write_text(page,encoding='utf-8'); print('built',L/'index.html',len(page))

MON = ("JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC")

BRAND_CSS = """
.sig{position:relative;padding:44px 22px 74px;max-width:min(560px,100%);margin:0 auto;text-align:center;scroll-snap-align:start}
.sig:before{content:"";position:absolute;left:22px;right:22px;top:0;border-top:1px solid var(--line)}
.sig .mark{position:absolute;right:64px;top:-54px;width:96px;height:96px;border:2.5px solid var(--ac);border-radius:50%;
 opacity:.34;transform:rotate(-13deg);display:grid;place-content:center;gap:2px;color:var(--ac);pointer-events:none}
.sig .mark b{font-size:9.5px;letter-spacing:.14em;font-weight:900;display:block}
.sig .mark i{font-style:normal;font-size:14px;font-weight:900;letter-spacing:.02em;display:block}
.sig .mark s{text-decoration:none;font-size:7.5px;letter-spacing:.1em;display:block;opacity:.85}
.sig .by{position:relative;margin:0;font-size:15px;font-weight:700;color:var(--mute)}
.sig .by b{color:var(--ink);font-weight:900;font-size:19px;display:block;margin-top:3px;letter-spacing:-.01em}
.sig .ct{margin:14px 0 0;font-size:13px;font-weight:900;display:flex;gap:8px;justify-content:center;flex-wrap:wrap}
.sig .ct a{color:var(--ac);text-decoration:none;border-bottom:1.5px solid var(--wash);padding-bottom:1px}
.sig .ct span{color:var(--line)}
.sig .cr{margin:16px 0 0;font-size:10.5px;color:var(--ash);font-weight:500;line-height:1.7}
"""

def brandsig(slug, lang, built):
    """Visible credit + contact at the foot of every page, plus an invisible build
    fingerprint. ponytail: a fingerprint proves a copy came from here, it cannot
    stop one — anything shipped to a browser is readable."""
    f = ROOT/'brand.json'
    if not f.exists(): return '', '', ''
    b = json.load(open(f, encoding='utf-8')); t = b.get(lang) or b['ja']
    year = built[:4]
    fp = hashlib.sha256(f"{slug}|{built}|{b['name']}".encode()).hexdigest()[:12]
    meta = (f'<meta name="author" content="{esc(b["name"])}">'
            f'<meta name="copyright" content="© {year} {esc(b["name"])}. All rights reserved.">'
            f'<link rel="author" href="{esc(b["site"])}">')
    stamp = f'{int(built[8:10])} {MON[int(built[5:7])-1]}'
    sig = (f'<footer class="sig" data-build="{fp}">'
           f'<div class="mark" aria-hidden="true"><b>{esc(b["place"]).upper()}</b>'
           f'<i>{stamp}</i><s>{year} · {fp[:6]}</s></div>'
           f'<p class="by">{esc(t["by"])}<b>{esc(b["name"])}</b></p>'
           f'<p class="ct"><a href="{esc(b["site"])}" target="_blank" rel="noopener">{esc(b["site_label"])}</a>'
           f'<span>·</span><a href="mailto:{esc(b["mail"])}">{esc(b["mail"])}</a></p>'
           f'<p class="cr">© {year} {esc(b["name"])}. {esc(t["note"])}</p></footer>'
           f'<!-- tabi-shiori · {slug} · built {built} · © {year} {b["name"]} · {b["site"]} · sig {fp} -->')
    return meta, sig, BRAND_CSS

LABELS={
 'ja':{'end':'おわり','pre':'出発の前に','prep':'準備','roles':'分担','book':'予約 →','scroll':'下にスクロールで','car':'車',
       'pick':"'いま選んでいるのは <b>'+PICKS[k].label+'</b>。'+PICKS[k].next17+'。<br>変えたいときは別の案の「この案にする」を押してください。'",
       'nopick':'まだ選んでいません。下の案を見て、気に入ったものを押してください。'},
 'en':{'end':'FINALLY','pre':'BEFORE YOU GO','prep':'PACKING','roles':'WHO DOES WHAT','book':'Book →','scroll':'Scroll down:','car':'CAR',
       'pick':"'You picked <b>'+PICKS[k].label+'</b>. '+PICKS[k].next17+'.<br>To change it, press another plan.'",
       'nopick':'Nothing picked yet. Look through the plans below and press the one you like.',
       'pickfor':'Pick for ','slothead':'Your picks so far:','slotfoot':'Send me a screenshot of this box, or just the numbers. To change one, press another option for the same day.'},
 'zh':{'end':'最后','pre':'出发之前','prep':'准备','roles':'分工','book':'预约 →','scroll':'向下滑动：','car':'车',
       'pick':"'你现在选的是 <b>'+PICKS[k].label+'</b>。'+PICKS[k].next17+'。<br>想换的话，按另一个方案的「就选这个」。'",
       'nopick':'还没有选。看看下面的方案，按你喜欢的那个。'},
}


TABS_CSS='''
:root{--bar:0px}html.tabbed{--bar:96px}html.tabbed.t1{--bar:52px}
html.tabbed body{padding-top:var(--bar)}
html.tabbed #deck{height:calc(100vh - var(--bar));height:calc(100dvh - var(--bar))}
html.tabbed .s{min-height:calc(100vh - var(--bar));min-height:calc(100dvh - var(--bar));padding-top:18px;padding-bottom:22px}
html.tabbed .rail{top:calc(50% + var(--bar)/2)}
html.tabbed .langsw{top:calc(var(--bar) + 6px)}
.tabs{position:fixed;left:0;right:0;top:0;height:var(--bar);z-index:9;background:rgba(255,255,255,.97);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:3px 12px 0}
.tabs>div{max-width:536px;margin:0 auto;display:flex;gap:6px}
.tabs .t2{margin-top:3px}
.tabs a,.tabs span{flex:1 1 0;min-height:44px;display:flex;align-items:center;justify-content:center;text-align:center;text-decoration:none;font-weight:900;border-radius:12px;border:2px solid var(--line);background:var(--card);color:var(--mute)}
.tabs .t1r a{font-size:16px}
.tabs .t2 a,.tabs .t2 span{font-size:14px;background:#fff;border-radius:999px}
.tabs a.on{background:var(--ac);border-color:var(--ac);color:#fff}
.tabs span.off{opacity:.38}
/* 1節=1画面に収める詰め */
html.tabbed .s{gap:8px}
html.tabbed .s h2{font-size:clamp(24px,7vw,32px)}
html.tabbed .photo{aspect-ratio:auto;height:min(19dvh,160px)}
html.tabbed .vid{max-height:22dvh}
html.tabbed .lead{font-size:14px;line-height:1.6}
html.tabbed .pts{gap:6px}html.tabbed .pts li{font-size:15px;line-height:1.4}
html.tabbed .pts li small{font-size:12px;line-height:1.5}
html.tabbed .tt ul{margin-bottom:8px}html.tabbed .tt li{padding:5px 2px}
html.tabbed .tt li b,html.tabbed .tt li .tm{font-size:14px}html.tabbed .tt li small{font-size:12px;line-height:1.45}
html.tabbed .note{padding:9px 12px;font-size:12.5px;line-height:1.55}
html.tabbed .links{gap:5px}html.tabbed .links a{padding:4px 10px}
html.tabbed .mv{margin-bottom:0}
html.tabbed .nums div{padding:8px 6px}
html.tabbed .tile img,html.tabbed .tile .noimg{aspect-ratio:auto;height:clamp(44px,10dvh,84px)}html.tabbed .tile .cb{padding:6px 8px 7px}html.tabbed .tile small{margin-top:0}
html.tabbed .tiles{gap:8px}
.f1 .photo,.f1 .vid,.f1 .vcap{display:none}
html.tabbed .f3 .tile img,html.tabbed .f3 .tile .noimg{display:none}
html.tabbed .f2 .lead{font-size:13px;line-height:1.5}html.tabbed .f2 .pts{gap:4px}html.tabbed .f2 .pts li{font-size:14px}html.tabbed .f2 .pts li small{font-size:11.5px;line-height:1.4}
html.tabbed .f2 .tt li{padding:3px 2px}html.tabbed .f2 .tt li small{font-size:11.5px}html.tabbed .f2 .links a{font-size:11.5px}html.tabbed .f2 .tt ul{margin-bottom:5px}
'''
STOP_CSS='''
.stop{gap:10px}.stop h2{font-size:clamp(24px,7vw,34px)}
.heroc{grid-template-columns:1fr}.heroc figure{grid-column:auto}
.heroc img,.heroc video{aspect-ratio:4/3;max-height:36dvh;height:auto}
.belt{display:flex;gap:8px;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;overscroll-behavior-x:contain;-webkit-overflow-scrolling:touch;scrollbar-width:thin;padding-bottom:4px}
.belt figure{flex:0 0 70%;scroll-snap-align:start}
.belt img,.belt .w2 video{aspect-ratio:4/3;max-height:22dvh;height:auto}
.rmap{height:38dvh;min-height:200px;border-radius:20px;overflow:hidden;background:#e9eef3}.rmap img{max-width:none}
.pin{width:26px;height:26px;border-radius:50%;background:var(--ac);color:#fff;border:2px solid #fff;font:900 12px/22px sans-serif;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.4)}
details.more summary{cursor:pointer;text-align:center;font-weight:900;font-size:14px;color:var(--ac);padding:12px;margin-top:8px;border:2px solid var(--wash);border-radius:12px;list-style:none}
details.more[open] summary{margin-bottom:8px}
.vc{border-left:3px solid var(--ac);padding:2px 0 2px 12px;display:grid;gap:8px}
.vc .vt{font-size:12px;font-weight:900;letter-spacing:.1em;color:var(--ac)}
.vc .vg{margin:0;font-size:14px;line-height:1.7}
.vc ul{list-style:none;margin:0;padding:0;display:grid;gap:5px}
.vc li{display:grid;grid-template-columns:40px 1fr;gap:8px;font-size:13px;line-height:1.55}
.vc time{font-size:11px;color:var(--ash);font-variant-numeric:tabular-nums;padding-top:2px}
'''.replace("\\'","'")
STOPMAP_JS=''';(function(){if(!window.L)return;Object.keys(SM).forEach(function(id){var el=document.getElementById(id);if(!el)return;var P=SM[id],m=L.map(el,{scrollWheelZoom:false}),pts=P.map(function(p){return [p.lat,p.lng]});
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"&copy; OpenStreetMap"}).addTo(m);
if(pts.length>1)L.polyline(pts,{color:MC,weight:3,opacity:.7}).addTo(m);
P.forEach(function(p){L.marker([p.lat,p.lng],{icon:L.divIcon({className:"",html:'<div class="pin">'+p.n+'</div>',iconSize:[26,26],iconAnchor:[13,13]})}).addTo(m).bindPopup('<b>'+p.name+'</b><br>'+p.t+'<img src="'+p.f+'" style="width:160px;display:block;border-radius:8px;margin-top:4px">')});
var l=pts[pts.length-1],near=pts.filter(function(q){return Math.abs(q[0]-l[0])<1.2&&Math.abs(q[1]-l[1])<1.2});
var fit=function(){m.fitBounds(L.latLngBounds(near.length>1?near:pts),{padding:[30,30]})};fit();
new IntersectionObserver(function(es,o){es.forEach(function(e){if(e.isIntersecting){m.invalidateSize();fit();o.disconnect()}})}).observe(el)})})();'''.replace("\\'","'")
def record_html(stops,items,cell,P,voice,numsblk,AP='album/'):
    """立ち寄り地点セクション群 -> (html, 地図データ)。日ごとに「今日の数字」＋経路地図＋地点ごとの1画面"""
    out='';SM={};byk={i['f']:i for i in items}
    def hm(s):return s[11:16]
    def vcblk(v):
        return (f'<div class="vc"><div class="vt">その場の会話</div><p class="vg">{esc(v["gist"])}</p><ul>'
                +''.join(f'<li><time>{esc(t)}</time><span>{esc(x)}</span></li>' for t,x in v.get('lines',[]))+'</ul></div>')
    days=sorted({s['day'] for s in stops})
    for day in days:
        S=[s for s in stops if s['day']==day];lab=f'{int(day[5:7])}/{int(day[8:10])}';dd=f'{int(day[8:10])}日'
        its=[i for s in S for i in s['items']];nV=sum(1 for i in its if i['kind']=='video')
        tot=sum(s['km'] or 0 for s in S);ns=sum(1 for s in S if s['kind']=='stop')
        vm=sum((datetime.datetime.fromisoformat(v['to'])-datetime.datetime.fromisoformat(v['from'])).seconds//60 for v in (voice or {}).get('items',[]) if v['from'][:10]==day)
        t0=min(i['taken'] for i in its);t1=max(i['taken'] for i in its)
        n1=[('移動距離',f'{tot:.0f}km','直線の合計'),('立ち寄り',f'{ns}か所',''),('時間帯',hm(t0),'〜 '+hm(t1))]
        n2=[('写真',f'{len(its)-nV}枚',''),('動画',f'{nV}本','')]+([('会話の記録',f'{vm}分','胸レコ')] if vm else [])
        mp=[];
        for s in S:
            if s['kind']=='stop' and s['lat'] is not None:
                mp.append({'lat':s['lat'],'lng':s['lng'],'n':len(mp)+1,'name':s['name'],'t':f'{hm(s["t0"])}〜{hm(s["t1"])}','f':AP+s['items'][0]['f'][:3]+'.jpg'})
        if mp: SM[f'map-{day}']=mp
        out+=(f'<section class="s" id="g-d{int(day[8:10])}" data-clock="{dd}の記録"><div class="eyebrow">{dd}の記録</div><h2><em>今日の</em><span>数字</span></h2>{numsblk(n1)}{numsblk(n2)}'
              +(f'<div class="rmap" id="map-{day}"></div>' if mp else '')+'</section>')
        for s in S:
            if s['kind']=='voice':
                out+=f'<section class="s" data-clock="{esc(s["name"])}"><div class="eyebrow">{hm(s["t0"])}〜{hm(s["t1"])}</div><h2><em>{esc(s["name"])}</em></h2>{vcblk(s["voice"])}</section>';continue
            k=s['km'];mv=''
            if k is not None:
                mv=('📍 前の地点と同じ場所' if k<.3 else f'{"🚄" if k>100 else "🚗"} 前の地点から約{k:.0f}km' if k>=10 else f'🚗 前の地点から約{k:.1f}km')
                mv=f'<div class="mv">{mv}</div>'
            I=s['items'];ph=[i for i in I if i['kind']=='photo']
            # 1地点=1画面: 代表写真1枚(大)＋残りは横スワイプの帯。会話がある地点は会話→帯
            vcb=vcblk(s['voice']) if s['voice'] else ''
            if vcb: hero=None;rest=I
            else:
                hero=max(ph,key=lambda i:(P/'album'/i['f']).stat().st_size) if len(I)>8 and ph else (ph or I)[0]
                rest=[i for i in I if i is not hero]
            g=(f'<div class="grid heroc">{cell(hero)}</div>' if hero else '')+vcb+(f'<div class="grid belt">{"".join(cell(i) for i in rest)}</div>' if rest else '')
            tm=hm(s['t0']) if s['t0']==s['t1'] or hm(s['t0'])==hm(s['t1']) else f'{hm(s["t0"])}〜{hm(s["t1"])}'
            out+=(f'<section class="s stop" data-clock="{esc(s["name"])}">{mv}<div class="eyebrow">{tm}</div><h2><em>{esc(s["name"])}</em></h2>{g}</section>')
    if voice and voice.get('note'): out=out[:-10]+f'<p class="selhelp">{esc(voice["note"])}</p></section>'
    return out,SM

def build(slug):
    P=ROOT/'packs'/slug; d=json.load(open(P/'trip.json'))
    cr=json.load(open(P/'credits.json')) if (P/'credits.json').exists() else {}
    LANG=d.get('lang','ja')
    T=LABELS.get(LANG,LABELS['ja'])
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
    pts=lambda L:'<ul class="pts">'+''.join(f'<li><i>{i+1}</i><span>{esc(a)}<small>{emp(b)}</small></span></li>' for i,(a,b) in enumerate(L))+'</ul>'
    links=lambda L:'<div class="links">'+''.join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(t)}</a>' for t,u in L)+'</div>' if L else ''
    def photo(k,eager=False):
        c=cr.get(k,{}); cap=f'<a href="{esc(c["page"])}" target="_blank" rel="noopener">{esc(c.get("title",""))}</a> {esc(c.get("lic",""))}' if c else ''
        return f'<figure class="photo"><img src="img/{k}.jpg" alt="" loading="{"eager" if eager else "lazy"}" {"fetchpriority=\"high\"" if eager else ""}><figcaption>{cap}</figcaption></figure>'
    def numsblk(L):
        return '<dl class="nums">'+''.join(f'<div><dt>{esc(a)}</dt><dd>{esc(bb)}<small>{esc(cc)}</small></dd></div>' for a,bb,cc in L)+'</dl>' if L else ''
    ch=d.get('choices')
    chs=''
    if ch:
        chs+=f'<section class="s" data-clock="{esc(ch.get("clock",""))}"><div class="eyebrow">{esc(ch["day"])}</div><h2>{ch["h"]}</h2><p class="lead">{emp(ch["lead"])}</p><div class="picked" id="picked">{esc(T["nopick"])}</div></section>'
        for o in ch['options']:
            chs+=(f'<section class="s" data-clock="{esc(o.get("clock",""))}"><div class="opt" data-k="{esc(o["key"])}" id="opt-{esc(o["key"])}">'
                  f'<span class="badge">{esc(o["badge"])}　{esc(o["label"])}</span><h2>{o["h"]}</h2>{photo(o["photo"])}'
                  f'<p class="lead">{emp(o["lead"])}</p>'
                  +(f'<div class="meta"><span>{esc(o["drive"])}</span><span>{esc(o["arrive"])}</span></div>' if o.get('drive') else numsblk(o.get('nums',[])))
                  +f'{pts(o["pts"])}{links(o.get("links",[]))}'
                  # days がある案は日ごとにボタンを出す（1ページで2日ぶん選ばせる用）
                  +(''.join(f'<button class="pick" data-k="{esc(o["key"])}" data-d="{esc(dd)}">{esc(T["pickfor"])}{esc(dd)}</button>' for dd in o['days'])
                    if o.get('days') else f'<button class="pick" data-k="{esc(o["key"])}">この案にする</button>')
                  +'</div></section>')
    def vid(v):
        if not v: return ''
        return (f'<div class="vid"><iframe src="https://www.youtube-nocookie.com/embed/{esc(v["id"])}?rel=0" title="{esc(v["cap"])}" '
                f'loading="lazy" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
                f'<p class="vcap">{esc(v["cap"])}</p>')
    def tiles(L):
        # 2列タイル＋タップで詳細ダイアログ（patrick-tokyo-day の型）
        if not L: return ''
        out='<div class="tiles">'; pops=''
        for i,t in enumerate(L):
            pid=f'pop-{zlib.crc32(t["name"].encode())}'; ph=t.get('photo') or {}
            img=f'<img src="{esc(ph["src"])}" alt="料理の例: {esc(t["genre"])}" loading="lazy">' if ph.get('src') else '<span class="noimg"></span>'
            out+=f'<button type="button" class="tile" data-pop="{pid}">{img}<span class="cb"><span class="gn">{esc(t["genre"])}</span><b>{esc(t["name"])}</b><small>{esc((t.get("hours") or "").split("（")[0])}</small></span></button>'
            rows=''.join(f'<p class="rt">{esc(x)}</p>' for x in [t.get('area') and t.get('from') and f'{t["area"]}・{t["from"]}' or t.get('area') or t.get('from'),
                         t.get('hours') and f'営業 {t["hours"]}', t.get('closed') and f'定休 {t["closed"]}'] if x)
            rt=f'<p class="rt"><span class="st">★ {esc(t["rating"])}</span></p>' if t.get('rating') else ''
            lk=''.join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{lab} ↗</a>' for lab,u in [('地図',t.get('map')),('くわしく',t.get('url'))] if u)
            pops+=(f'<dialog class="pop" id="{pid}" aria-label="{esc(t["name"])}"><button type="button" class="pclose" aria-label="閉じる">✕</button>'
                   +(f'<img class="pimg" src="{esc(ph["src"])}" alt="">' if ph.get('src') else '')
                   +f'<div class="pbody"><p class="gn">{esc(t["genre"])}</p><h3>{esc(t["name"])}</h3>{rt}<p class="pt">{esc(t.get("what") or "")}</p>{rows}<p class="pl">{lk}</p>'
                   +(f'<p class="pc">写真は料理の例で、お店の写真ではありません。{esc(ph.get("credit",""))}</p>' if ph.get('src') else '')+'</div></dialog>')
        js=("<script>if(!window.__tiles){window.__tiles=1;document.addEventListener('click',function(e){var t=e.target.closest('.tile');if(t){document.getElementById(t.dataset.pop).showModal();return}"
            "var c=e.target.closest('.pclose');if(c){c.closest('dialog').close();return}if(e.target.tagName==='DIALOG')e.target.close()})}</script>")
        return out+'</div>'+pops+js
    def sec(s,gid=''):
        head = vid(s.get('video')) if s.get('video') else (photo(s['photo']) if s.get('photo') else '')
        return (f'<section class="s"{f" id={chr(34)}{gid}{chr(34)}" if gid else ""} data-clock="{esc(s.get("clock",""))}">'+(f'<div class="mv">{esc(s["move"])}</div>' if s.get('move') else '')+f'<div class="eyebrow">{esc(s["day"])}</div><h2>{s["h"]}</h2>{head}'
                f'<p class="lead">{emp(s["lead"])}</p>{tiles(s.get("tiles",[]))}{numsblk(s.get("nums",[]))}{pts(s.get("pts",[]))}{tt(s.get("tt",[]))}{links(s.get("links",[]))}</section>')
    pres=''.join(sec(s) for s in d.get('pre_sections',[]))
    secs='';plan_days=[]  # 予定ページの日ジャンプ用: 各日(「16日 朝」の数字)の最初のセクションに id
    for s in d['sections']:
        m=re.match(r'(\d+)日',s.get('day',''));gid=''
        if m and int(m[1]) not in plan_days: plan_days.append(int(m[1]));gid=f'g-d{m[1]}'
        secs+=sec(s,gid)
    # --- アルバム（album.json があるときだけ） ---
    album='';lfhead='';mapjs='';AP='../album/';rec_days=[];ogrec=''
    AJ=P/'album.json'
    items=json.load(open(AJ))['items'] if AJ.exists() else []
    if items:
        (O/'album').mkdir(parents=True,exist_ok=True)
        for f in (P/'album').glob('*'): shutil.copy(f,O/'album'/f.name)
        gps=[i for i in items if i.get('lat') is not None]
        # ponytail: 100m格子でざっくり重複排除。厳密なクラスタリングが要るなら差し替え
        spots=len({(round(i['lat']/.0009),round(i['lng']/.0011)) for i in gps})
        nP=sum(1 for i in items if i['kind']=='photo');nV=len(items)-nP
        intro=(f'<section class="s" id="album" data-clock="アルバム"><div class="eyebrow">アルバム</div><h2><em>旅の</em><span>記録</span></h2>'
               f'{numsblk([("写真",f"{nP}枚",""),("動画",f"{nV}本",""),("場所",f"{spots}","GPSあり")])}'
               '<a class="bigbtn" href="../list/" target="_blank" rel="noopener">写真と動画を一覧で見る</a>'
               '<button class="bigbtn" id="selmode" type="button" style="margin-top:8px">写真を選んで保存する</button>'
               '<p class="selhelp">1枚だけでいいときは、写真の右下の「保存」を押してください。</p></section>')
        def cell(i):
            k=i['f'][:3];cap=f'<figcaption>{esc(i.get("cap",""))}</figcaption>' if i.get('cap') else ''
            ext='mp4' if i['kind']=='video' else 'jpg'
            sv=f'<a class="saveb" href="{AP}{k}.{ext}" download="{slug}-{k}.{ext}">保存</a>'
            sb='<button class="selb" type="button" aria-pressed="false" aria-label="選ぶ"></button>'
            return (f'<figure class="w2" data-k="{k}" data-ext="{ext}"><video controls playsinline preload="none" poster="{AP}{k}.jpg" src="{AP}{k}.mp4"></video>{sb}{sv}{cap}</figure>'
                    if i['kind']=='video' else
                    f'<figure data-k="{k}" data-ext="{ext}"><a href="{AP}{k}.jpg" target="_blank" rel="noopener"><img loading="lazy" src="{AP}{k}.jpg" alt=""></a>{sb}{sv}{cap}</figure>')
        import stops as ST
        voice=json.load(open(P/'voice.json')) if (P/'voice.json').exists() else None
        stops=ST.make(items,P,voice) if d.get('stops') else []  # trip.json に "stops": true で「道のり」表示
        if stops:
            recs,SM=record_html(stops,items,cell,P,voice,numsblk,AP)
            album=recs+intro;rec_days=sorted({int(x['day'][8:10]) for x in stops})
            ph=[i for i in items if i['kind']=='photo' and (P/'album'/i['f']).stat().st_size<700000]
            ogrec=max(ph,key=lambda i:(P/'album'/i['f']).stat().st_size)['f'] if ph else ''
        else:
          album=intro
          days={}
          for i in items: days.setdefault(i['taken'][:10],[]).append(i)
          for ymd,L in days.items():
            lab=f'{int(ymd[5:7])}/{int(ymd[8:10])}'
            rec_days.append(lab)
            album+=f'<section class="s" id="g-r{len(rec_days)}" data-clock="{lab}"><div class="eyebrow">{lab}</div><div class="grid">{"".join(cell(i) for i in L)}</div></section>'
        if gps and not stops:
            album+='<section class="s" data-clock="地図"><div class="eyebrow">地図</div><h2><em>行った</em><span>ところ</span></h2><div id="map"></div></section>'
            lfhead=('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
                    '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>')
            MP=json.dumps([{'lat':i['lat'],'lng':i['lng'],'f':AP+i['f'][:3]+'.jpg','cap':i.get('cap','')} for i in gps],ensure_ascii=False)
            mapjs=('\nconst MP='+MP+',MC='+json.dumps(d['accent'])+';(function(){var el=document.getElementById("map");if(!el||!window.L)return;'
                   'var m=L.map(el,{scrollWheelZoom:false}),pts=MP.map(function(p){return [p.lat,p.lng]});'
                   'L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"&copy; <a href=\\"https://www.openstreetmap.org/copyright\\">OpenStreetMap</a>"}).addTo(m);'
                   'MP.forEach(function(p){L.circleMarker([p.lat,p.lng],{radius:7,weight:2,color:"#fff",fillColor:MC,fillOpacity:1}).addTo(m)'
                   '.bindPopup(\'<img src="\'+p.f+\'" style="width:160px;display:block;border-radius:8px">\'+(p.cap?\'<div style="margin-top:4px">\'+p.cap+\'</div>\':""))});'
                   'if(pts.length>1)L.polyline(pts,{color:MC,weight:3,opacity:.7}).addTo(m);'
                   'var fit=function(){m.fitBounds(L.latLngBounds(pts),{padding:[30,30]})};fit();'
                   'new IntersectionObserver(function(es,o){es.forEach(function(e){if(e.isIntersecting){m.invalidateSize();fit();o.disconnect()}})}).observe(el);})();')
        if stops and SM:
            lfhead=('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
                    '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>')
            mapjs='\nconst SM='+json.dumps(SM,ensure_ascii=False)+',MC='+json.dumps(d['accent'])+STOPMAP_JS
    albumcss=(ALBUM_CSS+(STOP_CSS if d.get('stops') else '')) if items else ''
    bigcss=BIG_CSS if d.get('text')=='large' else ''
    selectjs=('\nconst SLUG='+json.dumps(slug)+',MEDIA="'+AP+'";'+SELECT_JS) if items else ''
    selbar=('<div id="selbar"><span class="n"></span><button class="cancel" type="button">やめる</button>'
            '<button class="go" type="button" disabled>保存</button></div>') if items else ''
    pickmsg=T['pick']
    picks_json=json.dumps({o['key']:{'label':o['label'],'next17':o.get('next17','')} for o in (ch['options'] if ch else [])},ensure_ascii=False)
    c=d['cover']; nums=''.join(f'<div><dt>{esc(a)}</dt><dd>{esc(b)}<small>{esc(cc)}</small></dd></div>' for a,b,cc in c['nums'])
    car=d.get('car'); rows=''.join(f'<li><b>{esc(n)}<small>{esc(t)}</small></b><a href="{esc(u)}" target="_blank" rel="noopener">{esc(T["book"])}</a></li>' for n,t,u in (car or {}).get('rows',[]))
    pack=''.join(f'<li><b>{esc(a)}</b><span>{esc(b)}</span></li>' for a,b in d.get('pack',{}).get('items',[]))
    roles=''.join(f'<li><b>{esc(a)}</b><span>{esc(b)}</span></li>' for a,b in d.get('roles',[]))
    rl=d['rail']; mk=rl.get('marker'); ac2=rl.get('accent2') or {}
    marker=(f'<span class="car emo" id="car">{esc(mk[0])}</span>' if mk else '<svg class="car" id="car" viewBox="0 0 26 40" aria-hidden="true">'+'<rect x="1.5" y="4" width="23" height="33" rx="7" fill="var(--ac)"/><rect x="0" y="10" width="26" height="5" rx="2.5" fill="var(--shadow)"/><rect x="0" y="27" width="26" height="5" rx="2.5" fill="var(--shadow)"/><rect x="4" y="7" width="18" height="27" rx="5" fill="var(--ac)"/><path d="M6.5 12h13l-1.6-3.2a2 2 0 0 0-1.8-1.1H9.9a2 2 0 0 0-1.8 1.1L6.5 12z" fill="#eaf3fb"/><path d="M6.5 27h13l-1.6 3.2a2 2 0 0 1-1.8 1.1H9.9a2 2 0 0 1-1.8-1.1L6.5 27z" fill="#cfe2f2"/><rect x="5.5" y="14" width="15" height="11" rx="3" fill="#fff" opacity=".22"/><rect x="6" y="4.6" width="3.6" height="2.2" rx="1.1" fill="#fff8d8"/><rect x="16.4" y="4.6" width="3.6" height="2.2" rx="1.1" fill="#fff8d8"/>'+'</svg>')
    railjs=json.dumps({'mk':mk,'a1':{'ac':d['accent'],'sh':d['accent_shadow'],'wa':d['accent_wash']},'a2':{'ac':ac2.get('accent',d['accent']),'sh':ac2.get('shadow',d['accent_shadow']),'wa':ac2.get('wash',d['accent_wash'])}},ensure_ascii=False)
    carsec=f'''<section class="s" data-clock="{esc(T["pre"])}"><div class="eyebrow">{esc(T["car"])}</div><h2>{car["h"]}</h2><p class="lead">{esc(car["lead"])}</p><ul class="rest">{rows}</ul><p class="note">{emp(car["note"])}</p></section>''' if car else ''
    packsec=f'''<section class="s" data-clock="{esc(T["pre"])}"><div class="eyebrow">{esc(T["prep"])}</div><h2>{esc(d["pack"]["h"])}</h2><ul class="rest">{pack}</ul><div class="eyebrow" style="margin-top:8px">{esc(T["roles"])}</div><ul class="rest">{roles}</ul></section>''' if d.get('pack') else ''
    BUILT=datetime.date.today().isoformat()
    FONT_JA='https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700;900&display=swap'
    FONT_SC='https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@500;700;900&display=swap'
    fontlink=(f'<link rel="stylesheet" href="{FONT_JA}"><link rel="stylesheet" href="{FONT_SC}">'
              if LANG=='zh' else f'<link rel="stylesheet" href="{FONT_JA}">')
    fontstack='"Noto Sans SC","Zen Kaku Gothic New",' if LANG=='zh' else '"Zen Kaku Gothic New",'
    langsw=('<div class="langsw">'+''.join(f'<a href="{esc(u)}">{esc(t)}</a>' for t,u in d.get('alt',[]))+'</div>') if d.get('alt') else ''
    bmeta,bsig,bcss=brandsig(slug,LANG,BUILT)
    endsec=f'''<section class="s end"><div class="eyebrow">{esc(T["end"])}</div><h2>{d["end"]["h"]}</h2><p class="lead">{emp(d["end"]["lead"])}</p><p class="credit">{esc(d["credit"])}</p></section>''' if d.get('end') else ''
    hub=f'''<section class="s hub"><span class="date">{esc(d["date_label"])}</span><h1>{esc(d["title"])}</h1>{photo(c["photo"],True)}<p class="who">{c["who"]}</p><dl class="nums">{nums}</dl><p class="hint">{esc(T["scroll"])} {esc(d["rail"]["top"])} → {esc(d["rail"]["bottom"])}</p></section>'''
    def render(ttl,ogt,ogd,ogi,lfhead,albumcss,hubhtml,body,mapjs,selectjs,selbar,rtop,rbot,railjs,tabs,cls):
      return f'''<!doctype html><html lang="{LANG}"{cls}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(ttl)}</title><meta name="robots" content="noindex">{bmeta}<meta property="og:title" content="{esc(ogt)}"><meta property="og:description" content="{esc(ogd)}"><meta property="og:image" content="{ogi}">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700;900&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>{lfhead}
<style>
:root{{--bg:#fff;--card:#f6f9fc;--ink:#202020;--mute:#645f5e;--ash:#8a8482;--line:#e3e8ee;--ac:{d["accent"]};--shadow:{d["accent_shadow"]};--wash:{d["accent_wash"]};color-scheme:light}}
*{{box-sizing:border-box;min-width:0}}html,body{{margin:0;overflow-x:hidden;overscroll-behavior-x:none;background:var(--bg);color:var(--ink);font-family:"Zen Kaku Gothic New","Hiragino Sans","Noto Sans JP",sans-serif;font-weight:700;-webkit-font-smoothing:antialiased}}
h1,h2,h3,p{{margin:0}}h1,h2{{line-height:1.15;text-wrap:balance;word-break:keep-all;overflow-wrap:anywhere}}
#deck{{height:100vh;height:100dvh;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;touch-action:pan-y pinch-zoom;scroll-snap-type:y mandatory;scroll-behavior:smooth;-webkit-overflow-scrolling:touch}}
.s{{min-height:100vh;min-height:100dvh;scroll-snap-align:start;scroll-snap-stop:always;padding:52px 22px 40px;max-width:min(560px,100%);overflow-x:hidden;display:flex;flex-direction:column;justify-content:center;gap:14px;margin:0 auto}}
.eyebrow{{font-size:12px;letter-spacing:.12em;color:var(--ac);font-weight:900}}
.mv{{display:inline-block;align-self:flex-start;background:var(--wash);color:var(--ac);font-weight:900;font-size:13px;border-radius:999px;padding:5px 12px;margin-bottom:8px}}
.s h2{{font-size:clamp(28px,8vw,40px);font-weight:900;letter-spacing:-.02em}}.s h2 em{{font-style:normal;color:var(--ac)}}.s h2 span,.who span{{white-space:nowrap}}
.lead{{font-size:15px;color:var(--mute);line-height:1.75}}
.tiles{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.tile{{display:block;width:100%;text-align:left;font:inherit;color:inherit;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;padding:0;cursor:pointer}}
.tile img,.tile .noimg{{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;background:#eee}}
.tile .cb{{display:block;padding:8px 10px 10px}}
.tile .gn{{display:block;font-size:10.5px;font-weight:900;letter-spacing:.06em;color:var(--ac)}}
.tile b{{display:block;font-size:14px;line-height:1.3;margin-top:2px}}
.tile small{{display:block;font-size:11px;color:var(--mute);margin-top:2px}}
.tile:hover,.tile:focus-visible{{border-color:var(--ink)}}
dialog.pop{{border:0;border-radius:14px;padding:0;width:min(92vw,420px);max-height:88vh;max-height:88svh;overflow:auto;color:var(--ink);background:#fff;margin:auto}}
dialog.pop::backdrop{{background:rgba(0,0,0,.55)}}
.pop .pimg{{display:block;width:100%;aspect-ratio:4/3;object-fit:cover}}
.pop .pbody{{padding:16px 18px 20px}}
.pop .gn{{font-size:11px;font-weight:900;letter-spacing:.06em;color:var(--ac)}}
.pop h3{{font-size:22px;line-height:1.25;font-weight:900;margin:2px 0 6px}}
.pop .rt{{font-size:13px;color:var(--mute);margin-top:6px}}
.pop .st{{color:var(--ac);font-weight:700}}
.pop .pt{{font-size:15px;line-height:1.6;margin-top:10px}}
.pop .pl{{margin-top:14px;display:flex;gap:10px;flex-wrap:wrap}}
.pop .pl a{{display:inline-block;font-size:13px;font-weight:700;text-decoration:none;color:var(--ink);border:1px solid var(--ink);border-radius:999px;padding:6px 14px}}
.pop .pc{{margin-top:14px;font-size:11px;color:#999;line-height:1.5}}
.pclose{{position:absolute;right:10px;top:10px;width:34px;height:34px;border-radius:50%;border:0;background:rgba(255,255,255,.92);font:inherit;font-size:16px;font-weight:700;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.25)}}
.photo{{margin:0;border-radius:20px;overflow:hidden;background:#e9eef3;aspect-ratio:16/10}}.photo img{{display:block;width:100%;height:100%;object-fit:cover}}
.photo figcaption{{display:none}}
.pts{{list-style:none;margin:0;padding:0;display:grid;gap:10px}}.pts li{{display:grid;grid-template-columns:28px 1fr;gap:10px;align-items:start;font-size:16px;line-height:1.5}}
.pts li i{{font-style:normal;width:24px;height:24px;border-radius:50%;background:var(--ac);color:#fff;font-weight:900;font-size:12px;display:inline-flex;align-items:center;justify-content:center;margin-top:3px}}
.pts li small{{display:block;font-size:12.5px;color:var(--mute);font-weight:500;line-height:1.6}}
.nums{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0;width:100%}}.nums div{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 8px;text-align:center}}
.nums dt{{font-size:12px;color:var(--ash);letter-spacing:.06em}}.nums dd{{margin:0;font-size:22px;font-weight:900;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.2}}.nums dd small{{display:block;font-size:12px;color:var(--mute)}}
.rest{{list-style:none;margin:0;padding:0;border-top:2px solid var(--ink)}}.rest li{{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 2px;border-bottom:1px solid var(--line);font-size:14.5px}}
.rest li b{{font-weight:900;word-break:keep-all;overflow-wrap:break-word;min-width:0;flex:1 1 auto}}
.rest li:has(>span) b{{white-space:nowrap;flex:0 0 auto}}
.rest li>span{{min-width:0}}.rest li span{{color:var(--mute);font-size:12.5px;text-align:right}}.rest li b small{{white-space:normal;word-break:normal;overflow-wrap:anywhere}}
.rest li small{{display:block;font-size:12px;color:var(--ash);font-weight:500;line-height:1.6}}
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
.end{{text-align:center;align-items:center}}.credit{{font-size:12px;color:var(--ash);line-height:1.7;max-width:420px;font-weight:500}}.credit a{{color:inherit}}
.opt{{border:2px solid var(--line);border-radius:20px;padding:14px 14px 16px;display:grid;gap:10px;background:#fff}}
.opt.on{{border-color:var(--ac);box-shadow:0 0 0 4px var(--wash)}}
.badge{{display:inline-block;background:var(--wash);color:var(--ac);font-size:11.5px;font-weight:900;padding:4px 10px;border-radius:999px;letter-spacing:.06em}}
.meta{{display:flex;gap:8px;flex-wrap:wrap;font-size:11.5px;color:var(--mute)}}.meta span{{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:4px 10px}}
.pick{{width:100%;background:var(--ac);color:#fff;font-weight:900;font-size:17px;padding:14px;border-radius:12px;border:0;box-shadow:0 4px 0 0 var(--shadow);cursor:pointer;font-family:inherit}}
.pick:active{{transform:translateY(4px);box-shadow:none}}
.opt .pick+.pick{{margin-top:8px}}.pick.on,.opt.on .pick{{background:var(--ink);box-shadow:0 4px 0 0 #000}}
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
.langsw{{position:fixed;top:10px;right:10px;z-index:8;display:flex;gap:6px}}
.langsw a{{background:rgba(255,255,255,.92);border:1.5px solid var(--ink);color:var(--ink);font-size:12px;font-weight:900;text-decoration:none;padding:6px 12px;border-radius:999px;backdrop-filter:blur(6px)}}
{albumcss}{TABS_CSS if tabs else ''}{bcss}{bigcss}
</style></head><body>
{langsw}{tabs}
<div class="rail" aria-hidden="true"><span class="lab t">{esc(rtop)}</span><span class="track"></span><span class="klabel" id="klabel"></span>{marker}<span class="lab b">{esc(rbot)}</span></div>
<div id="deck">
{hubhtml}
{body}
{bsig}
</div>
{selbar}
<script>
const PICKS={picks_json};const RAIL={railjs};
const box=document.getElementById('picked');
function apply(k){{if(!PICKS[k])return;document.querySelectorAll('.opt').forEach(o=>o.classList.toggle('on',o.dataset.k===k));
 box.innerHTML={pickmsg};}}
if(document.querySelector('.pick[data-d]')){{
 // 日ごとに選ぶモード: {{日: 案key}} をページ別に保存
 const SK='picks:'+{json.dumps(slug)},SLOTS=[...new Set([...document.querySelectorAll('.pick[data-d]')].map(b=>b.dataset.d))];let P={{}};
 try{{P=JSON.parse(localStorage.getItem(SK))||{{}}}}catch(e){{}}
 const draw=()=>{{document.querySelectorAll('.pick[data-d]').forEach(b=>b.classList.toggle('on',P[b.dataset.d]===b.dataset.k));
  const got=SLOTS.filter(d=>PICKS[P[d]]);
  box.innerHTML=got.length?{json.dumps(T.get('slothead',''))}+'<br>'+got.map(d=>d+': <b>'+PICKS[P[d]].label+'</b>').join('<br>')+'<br><small>'+{json.dumps(T.get('slotfoot',''))}+'</small>':{json.dumps(T['nopick'])};}};
 document.querySelectorAll('.pick[data-d]').forEach(b=>b.addEventListener('click',()=>{{P[b.dataset.d]=b.dataset.k;try{{localStorage.setItem(SK,JSON.stringify(P))}}catch(e){{}};draw();box.scrollIntoView({{behavior:'smooth',block:'center'}});}}));
 draw();
}}else{{
document.querySelectorAll('.pick').forEach(b=>b.addEventListener('click',()=>{{try{{localStorage.setItem('pick16',b.dataset.k)}}catch(e){{}};apply(b.dataset.k);box.scrollIntoView({{behavior:'smooth',block:'center'}});}}));
try{{apply(localStorage.getItem('pick16'))}}catch(e){{}}
}}
const deck=document.getElementById('deck'),car=document.getElementById('car'),klabel=document.getElementById('klabel'),rail=document.querySelector('.rail');
const secs=[...document.querySelectorAll('#deck .s')].filter(s=>s.dataset.clock);
const range=()=>Math.max(1,deck.scrollHeight-deck.clientHeight);
let stops=[];
const DAYS=[...document.querySelectorAll('.tabs .t2 a')];
// 1節=1画面: はみ出す節だけ、写真→文字サイズの順に詰める
if(document.documentElement.classList.contains('tabbed')){{
 const fit=()=>secs.forEach(s=>{{s.classList.remove('f1','f2');for(const c of ['f1','f2','f3']){{if(s.offsetHeight<=deck.clientHeight+1)break;s.classList.add(c)}}}});
 fit();addEventListener('resize',fit);addEventListener('load',fit);if(document.fonts)document.fonts.ready.then(fit);
}}
DAYS.forEach(b=>b.addEventListener('click',e=>{{e.preventDefault();const t=document.getElementById(b.dataset.g);if(t)t.scrollIntoView({{behavior:'smooth',block:'start'}})}}));
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
 if(DAYS.length){{const m2=innerHeight/2;let a=DAYS.find(b=>!b.classList.contains('off')||0)||DAYS[0];DAYS.forEach(b=>{{const e=document.getElementById(b.dataset.g);if(e&&e.getBoundingClientRect().top<=m2)a=b}});DAYS.forEach(b=>b.classList.toggle('on',b===a));}}
 const mid=deck.clientHeight/2;
 const cur=secs.find(s=>{{const b=s.getBoundingClientRect();return b.top<=mid&&b.bottom>=mid;}});
 const t=cur?cur.dataset.clock:'';
 klabel.textContent=t;klabel.classList.toggle('on',!!t);
 if(t&&matchMedia('(max-width:480px)').matches){{clearTimeout(window._kt);window._kt=setTimeout(()=>klabel.classList.remove('on'),900);}}
}}
deck.addEventListener('scroll',()=>{{if(!raf)raf=requestAnimationFrame(upd);}},{{passive:true}});
addEventListener('resize',()=>{{build();upd();}});
build();upd();{mapjs}{selectjs}
</script></body></html>'''

    plan_body=f"{pres}{chs}{secs}{carsec}{packsec}{endsec}"
    rail0=d["rail"]
    if not items:
        (O/'index.html').write_text(render(d["title"],d["title"],d["og_desc"],f'img/{c["photo"]}.jpg',lfhead,albumcss,hub,plan_body,mapjs,selectjs,selbar,rail0["top"],rail0["bottom"],railjs,'',''),encoding='utf-8')
        print('built',O/'index.html')
    else:
        # --- 記録があるパック: 予定(index.html)と記録(kiroku/index.html)の2ページ ---
        BASE='https://yukitchy.github.io/tabi-shiori/'+slug+'/'
        def bar(cur,row,hrefs):
            r1=''.join(f'<a href="{h}"{" class=\"on\" aria-current=\"page\"" if k==cur else ""}>{k}</a>' for k,h in hrefs)
            r2=''.join((f'<a href="#{g}" data-g="{g}">{esc(l)}</a>' if g else f'<span class="off">{esc(l)}</span>') for l,g in row)
            return (f'<nav class="tabs" aria-label="ページ切り替え"><div class="t1r">{r1}</div>'+(f'<div class="t2">{r2}</div>' if len(row)>=2 else '')+'</nav>',
                    ' class="tabbed"' if len(row)>=2 else ' class="tabbed t1"')
        # 予定ページ
        prow=([('出発前','g-top')] if d.get('pre_sections') else [])+[(f'{n}日',f'g-d{n}') for n in plan_days]
        pbar,pcls=bar('予定',prow,[('予定','./'),('記録','kiroku/')])
        pbar+='<script>if(location.hash=="#album")location.replace("kiroku/")</script>'
        hub_p=hub.replace('<section class="s hub">','<section class="s hub" id="g-top">',1)
        (O/'index.html').write_text(render(d["title"],d["title"],d["og_desc"],f'img/{c["photo"]}.jpg','','',hub_p,plan_body,'','','',rail0["top"],rail0["bottom"],railjs,pbar,pcls),encoding='utf-8')
        print('built',O/'index.html')
        # 記録ページ
        if d.get('stops'):
            nums=sorted(set(plan_days)|set(rec_days))
            rrow=[(f'{n}日',f'g-d{n}' if n in rec_days else '') for n in nums]+[('アルバム','album')]
            rtop_,rbot_=(f'{nums[0]}日' if nums else rail0["top"]),'アルバム'
        else:
            rrow=[(l,f'g-r{i+1}') for i,l in enumerate(rec_days)]
            rtop_,rbot_=rail0["top"],rail0["bottom"]
        kbar,kcls=bar('記録',rrow,[('予定','../'),('記録','./')])
        K=O/'kiroku';K.mkdir(exist_ok=True)
        ktitle=d.get('kiroku_title') or d["title"]+' の記録'
        rj=json.loads(railjs);rj['a2']=rj['a1']
        if rj['mk']:rj['mk']=[rj['mk'][0]]*2
        kog=BASE+'album/'+ogrec if ogrec else BASE+f'img/{c["photo"]}.jpg'
        (K/'index.html').write_text(render(ktitle,ktitle,d.get('kiroku_desc') or ktitle,kog,lfhead,albumcss,'',album,mapjs,selectjs,selbar,rtop_,rbot_,json.dumps(rj,ensure_ascii=False),kbar,kcls),encoding='utf-8')
        print('built',K/'index.html')
    if items: build_list(slug,d,items,O)
def status(d,has_album=False):
    """アルバムがある＝もう行った。無ければ dates[1] が過ぎていれば done"""
    if has_album: return 'done'
    return 'done' if d.get('dates',[''])[-1]<datetime.date.today().isoformat() else 'plan'
MAP_JS = """
(function(){
 var el=document.getElementById("gmap");if(!el||!window.L||!PINS.length)return;
 var m=L.map(el,{scrollWheelZoom:false,zoomControl:true});
 L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  {maxZoom:18,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(m);
 var pts=PINS.map(function(p){return [p.lat,p.lng]});
 var grp={};PINS.forEach(function(p){var k=Math.round(p.lat*1.8)+","+Math.round(p.lng*1.8);(grp[k]=grp[k]||[]).push(p)});
 Object.keys(grp).forEach(function(k){var g=grp[k];if(g.length<2)return;
  g.forEach(function(p,i){var a=Math.PI*2*i/g.length-Math.PI/2;
   p.dy=p.lat+0.30*Math.sin(a);p.dx=p.lng+0.37*Math.cos(a)})});
 var dpts=PINS.map(function(p){return [p.dy||p.lat,p.dx||p.lng]});
 var line=L.polyline(pts,{color:"#e5382b",weight:2.5,opacity:.85}).addTo(m);
 PINS.forEach(function(p){
  L.marker([p.dy||p.lat,p.dx||p.lng],{icon:L.divIcon({className:"",iconSize:[25,25],iconAnchor:[12,12],
   html:'<div class="pin">'+p.n+"</div>"})}).addTo(m)
   .bindPopup('<div class="pop"><img src="'+p.img+'" alt=""><b>'+p.t+'</b><a href="#t'+p.n+'">この旅へ →</a></div>',{minWidth:126,autoPanPadding:[14,14]});
 });
 var jp=dpts.filter(function(q){return q[0]>30&&q[1]>125});
 var fit=function(v){m.fitBounds(L.latLngBounds(v==="jp"&&jp.length?jp:dpts),{padding:[38,38]})};
 var view="jp";fit(view);
 document.querySelectorAll(".mapbar button").forEach(function(b){
  b.onclick=function(){view=b.dataset.v;fit(view);
   document.querySelectorAll(".mapbar button").forEach(function(o){o.setAttribute("aria-pressed",o===b)})};
 });
 var drawn=false,draw=function(){
  var path=line.getElement();if(!path||drawn)return;drawn=true;
  var L2=path.getTotalLength();
  path.style.transition="none";path.style.strokeDasharray=L2;path.style.strokeDashoffset=L2;
  path.getBoundingClientRect();
  path.style.transition="stroke-dashoffset 1.6s cubic-bezier(.3,.8,.35,1)";path.style.strokeDashoffset=0;
 };
 new IntersectionObserver(function(es,o){es.forEach(function(e){
  if(e.isIntersecting){m.invalidateSize();fit(view);
   if(matchMedia("(prefers-reduced-motion: reduce)").matches){o.disconnect();return}
   setTimeout(draw,320);o.disconnect()}})},{threshold:.25}).observe(el);
})();
"""

IDX_JS = """
var rm=matchMedia("(prefers-reduced-motion: reduce)").matches;
document.querySelectorAll("[data-n]").forEach(function(el){
 var n=+el.dataset.n;
 if(rm){el.textContent=n;return;}
 var t0=null,dur=760+Math.min(n,300);
 requestAnimationFrame(function step(ts){
  if(!t0)t0=ts;var p=Math.min(1,(ts-t0)/dur);
  el.textContent=Math.round(n*(1-Math.pow(1-p,3)));
  if(p<1)requestAnimationFrame(step);
 });
});
"""

IDX_CSS = """
:root{--bg:#fbfaf9;--ink:#1b1a19;--mute:#6b6664;--ash:#a9a29e;--line:#e7e2df;--ac:#e5382b;--paper:#fff;color-scheme:light}
*{box-sizing:border-box;min-width:0}
html,body{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font-family:"Zen Kaku Gothic New","Hiragino Sans","Noto Sans JP",sans-serif;font-weight:700;-webkit-font-smoothing:antialiased}
h1,h2,p{margin:0;line-height:1.18;word-break:keep-all;overflow-wrap:anywhere}
a{color:inherit}
main{max-width:min(600px,100%);margin:0 auto;padding:0 20px 76px}
.hero{padding:46px 0 4px;text-align:center}
.stack{position:relative;height:min(64vw,330px);max-width:min(79%,360px);margin:0 auto 32px}
.stack figure{position:absolute;inset:0;margin:0;padding:8px;background:var(--paper);border-radius:2px;box-shadow:0 12px 26px rgba(38,24,18,.17),0 2px 6px rgba(38,24,18,.1)}
.stack img{display:block;width:100%;height:100%;object-fit:cover;background:#eee}
.stack figure:nth-child(1){transform:rotate(-10deg) translate(-23%,5%) scale(.78)}
.stack figure:nth-child(2){transform:rotate(8deg) translate(22%,-5%) scale(.78)}
.stack figure:nth-child(3){transform:rotate(-2deg) scale(.97)}
.tag{display:inline-block;background:var(--ac);color:#fff;font-weight:900;font-size:14px;letter-spacing:.04em;padding:5px 16px;border-radius:999px}
h1{font-size:clamp(40px,12.5vw,62px);font-weight:900;letter-spacing:-.045em;margin:10px 0 18px}
.nums{display:flex;margin:0 0 6px}
.nums div{flex:1;padding:0 4px;border-left:1px solid var(--line)}
.nums div:first-child{border-left:0}
.nums dt{font-size:10.5px;color:var(--ash);letter-spacing:.1em;margin-bottom:3px}
.nums b{font-weight:900}
.nums dd{margin:0;font-size:29px;font-weight:900;letter-spacing:-.04em;font-variant-numeric:tabular-nums;line-height:1}
.nums i{font-style:normal;font-size:13px;color:var(--mute);margin-left:1px;letter-spacing:0}
.maph{text-align:center;font-size:12px;color:var(--ash);letter-spacing:.14em;margin:38px 0 11px}
.mapwrap{padding:9px;background:var(--paper);border-radius:2px;box-shadow:0 12px 26px rgba(38,24,18,.15),0 2px 6px rgba(38,24,18,.09)}
#gmap{height:min(78vw,340px);width:100%;background:#eeeae7}
.mapbar{display:flex;gap:7px;justify-content:center;margin-top:12px}
.mapbar button{font-family:inherit;font-size:12px;font-weight:900;color:var(--ash);background:none;border:1.6px solid var(--line);border-radius:999px;padding:7px 16px;cursor:pointer}
.mapbar button[aria-pressed="true"]{color:var(--ink);border-color:var(--ink)}
.mapnote{margin-top:10px;text-align:center;font-family:ui-monospace,"SFMono-Regular",Menlo,monospace;font-size:11px;color:var(--ash);letter-spacing:.08em}
.pin{display:grid;place-items:center;width:25px;height:25px;border-radius:999px;background:var(--ac);color:#fff;font-family:"Zen Kaku Gothic New",sans-serif;font-size:11px;font-weight:900;border:2px solid #fff;box-shadow:0 2px 7px rgba(38,24,18,.35)}
.leaflet-container{font-family:inherit;background:#eeeae7}
.leaflet-tile-pane{filter:grayscale(.62) sepia(.16) saturate(.85) brightness(1.04) contrast(.94)}
.leaflet-control-attribution{font-size:9px!important;background:rgba(255,255,255,.72)!important}
.leaflet-bar a{color:var(--ink)!important}
.pop{width:126px;text-align:center}.pop img{width:100%;border-radius:3px;display:block}
.pop b{display:block;font-size:13px;margin-top:6px;letter-spacing:-.02em}
.pop a{display:inline-block;margin-top:6px;font-size:11.5px;font-weight:900;color:var(--ac);text-decoration:none}
.trips{list-style:none;margin:0;padding:0}
.year{display:flex;align-items:center;gap:14px;margin:26px 0 16px;position:sticky;top:0;z-index:5;background:var(--bg);padding:12px 0 8px}
.year span{font-size:38px;font-weight:900;color:var(--ash);letter-spacing:-.03em;line-height:1;font-variant-numeric:tabular-nums}
.year::after{content:"";flex:1;height:1px;background:var(--line)}
.trip{margin:0 0 14px;scroll-margin-top:74px}
.print{display:block;position:relative;padding:9px;background:var(--paper);border-radius:2px;text-decoration:none;box-shadow:0 12px 26px rgba(38,24,18,.15),0 2px 6px rgba(38,24,18,.09);transform:rotate(var(--r));transition:transform .4s cubic-bezier(.2,.8,.25,1),box-shadow .4s}
.print img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;background:#eee}
.stamp{position:absolute;right:22px;bottom:20px;font-family:ui-monospace,"SFMono-Regular",Menlo,monospace;font-size:13px;font-weight:700;letter-spacing:.1em;color:var(--ac);text-shadow:0 0 7px rgba(229,56,43,.5)}
.trip:hover .print,.trip:focus-within .print{transform:rotate(0) translateY(-5px);box-shadow:0 20px 40px rgba(38,24,18,.2),0 3px 8px rgba(38,24,18,.1)}
.meta{padding:16px 4px 26px}
.when{font-size:12.5px;color:var(--mute);letter-spacing:.02em;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.soon{background:var(--ac);color:#fff;font-size:11px;font-weight:900;padding:3px 9px;border-radius:999px;letter-spacing:.06em}
.trip h2{font-size:26px;font-weight:900;letter-spacing:-.035em;margin:6px 0 0}
.peek{display:flex;gap:6px;margin-top:13px}
.peek a{display:block;flex:1;position:relative;border-radius:2px;overflow:hidden;background:#eee;aspect-ratio:1;text-decoration:none}
.peek img{display:block;width:100%;height:100%;object-fit:cover}
.peek b{position:absolute;inset:0;display:grid;place-items:center;background:rgba(27,26,25,.58);color:#fff;font-size:14px;font-weight:900;letter-spacing:-.02em}
.go{display:inline-flex;align-items:center;gap:5px;margin-top:13px;font-size:12.5px;font-weight:900;text-decoration:none;border:1.6px solid var(--ink);border-radius:999px;padding:6px 14px}
.gap{position:relative;height:var(--h);margin:0 0 14px 24px;display:flex;align-items:center}
.gap::before{content:"";position:absolute;left:0;top:-6px;bottom:-6px;width:2px;background:repeating-linear-gradient(to bottom,var(--line) 0 5px,transparent 5px 12px)}
.gap span{margin-left:15px;font-size:11.5px;color:var(--ash);letter-spacing:.07em;font-variant-numeric:tabular-nums}
.since{margin-top:14px;font-family:ui-monospace,"SFMono-Regular",Menlo,monospace;font-size:11.5px;color:var(--ash);letter-spacing:.08em}
.since b{color:var(--ink);font-size:15px;font-weight:900;margin:0 2px;font-variant-numeric:tabular-nums}
@media(prefers-reduced-motion:reduce){.print{transition:none}}
@media(prefers-reduced-motion:no-preference){
.stack figure{animation:fan .85s cubic-bezier(.22,1,.36,1) both}
.stack figure:nth-child(1){--fx:-23%;--fy:5%;--fr:-10deg;--fs:.78;animation-delay:.24s}
.stack figure:nth-child(2){--fx:22%;--fy:-5%;--fr:8deg;--fs:.78;animation-delay:.14s}
.stack figure:nth-child(3){--fx:0;--fy:0;--fr:-2deg;--fs:.97;animation-delay:0s}
@keyframes fan{from{opacity:0;transform:rotate(0) translate(0,14px) scale(.84)}to{opacity:1;transform:rotate(var(--fr)) translate(var(--fx),var(--fy)) scale(var(--fs))}}
@supports (animation-timeline:view()){
.trip,.gap span{animation:lay .1s linear both;animation-timeline:view();animation-range:entry 2% cover 26%}
@keyframes lay{from{opacity:0;transform:translateY(24px) scale(.965)}to{opacity:1;transform:none}}
}}
"""

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
    def mid(I):
        la=sorted(i['lat'] for i in I if i.get('lat') is not None)
        ln=sorted(i['lng'] for i in I if i.get('lng') is not None)
        return (la[len(la)//2],ln[len(ln)//2]) if la else None
    def km(a,b):
        import math
        p1,p2=math.radians(a[0]),math.radians(b[0]);dl=math.radians(b[1]-a[1])
        return 6371*math.acos(max(-1,min(1,math.sin(p1)*math.sin(p2)+math.cos(p1)*math.cos(p2)*math.cos(dl))))
    def gapword(n):
        if n<=1: return '翌日'
        if n<14: return f'{n}日後'
        if n<29: return f'{round(n/7)}週間後'
        return f'{max(1,round(n/30.4))}ヶ月後'
    def thumb(slug,it): return f'../{slug}/album/'+(it['f'] if it['kind']=='photo' else it['f'][:-4]+'.jpg')
    first=T[0]['dates'][0].replace('-','.') if False else T[0][0]['dates'][0].replace('-','.')
    since=(datetime.date.today()-datetime.date.fromisoformat(T[0][0]['dates'][0])).days
    heroes=[t for t in T if status(t[0])=='done'][-3:]
    stack=''.join(f'<figure><img src="../{s}/img/{d["cover"]["photo"]}.jpg" alt=""></figure>' for d,s,_ in heroes)
    cards='';year=None;prev=None;pins=[]
    for d,slug,I in T:
        cur=datetime.date.fromisoformat(d['dates'][0])
        if prev:
            n=(cur-prev).days
            cards+=f'<li class="gap" style="--h:{int(min(118,24+n*.72))}px"><span>{gapword(n)}</span></li>'
        prev=datetime.date.fromisoformat(d['dates'][1])
        c=mid(I) if I else None
        if c: pins.append({'n':len(pins)+1,'lat':c[0],'lng':c[1],'t':d['title'],'d':d['date_label'],
                           'img':f'../{slug}/img/{d["cover"]["photo"]}.jpg'})
        pn=pins[-1]['n'] if c else 0
        y=d['dates'][0][:4]
        if y!=year: year=y;cards+=f'<li class="year"><span>{y}</span></li>'
        rot=(-1.3,1.1,-.8,1.5)[len(cards)%4]
        ymd=d['dates'][0].split('-');st=f"'{ymd[0][2:]} {ymd[1]} {ymd[2]}"
        soon='' if status(d,bool(I))=='done' else '<span class="soon">これから</span>'
        peek=''
        if I:
            ph=[i for i in I if i['kind']!='video'] or I
            if len(ph)>4:
                pick=[ph[int((k+1)*len(ph)/5)] for k in range(4)]
                rest=len(ph)-4
            else: pick=ph;rest=0
            cells=''.join(f'<a href="../{slug}/{"kiroku/" if (ROOT/"docs"/slug/"kiroku").exists() else "#album"}"><img src="{thumb(slug,it)}" alt="" loading="lazy">'
                          +(f'<b>+{rest}</b>' if rest and n==len(pick)-1 else '')+'</a>' for n,it in enumerate(pick))
            peek=f'<div class="peek">{cells}</div>'
        cards+=(f'<li class="trip" id="t{pn}" style="--r:{rot}deg"><a class="print" href="../{slug}/">'
                f'<img src="../{slug}/img/{d["cover"]["photo"]}.jpg" alt="" loading="lazy"><span class="stamp">{st}</span></a>'
                f'<div class="meta"><p class="when">{esc(d["date_label"])}{soon}</p><h2>{esc(d["title"])}</h2>'
                f'{peek}<a class="go" href="../{slug}/">しおりを開く →</a></div></li>')
    dist=round(sum(km((pins[i]['lat'],pins[i]['lng']),(pins[i+1]['lat'],pins[i+1]['lng'])) for i in range(len(pins)-1)))
    pins_json=json.dumps(pins,ensure_ascii=False)
    page=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{label} 旅の記録</title><meta name="robots" content="noindex"><meta property="og:title" content="{label} 旅の記録">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700;900&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>{IDX_CSS}</style></head><body><main>
<div class="hero"><div class="stack">{stack}</div><span class="tag">{label}</span><h1>旅の記録</h1>
<dl class="nums"><div><dt>旅</dt><dd><b data-n="{len(T)}">0</b><i>回</i></dd></div><div><dt>日数</dt><dd><b data-n="{days}">0</b><i>日</i></dd></div><div><dt>写真</dt><dd><b data-n="{shots}">0</b><i>枚</i></dd></div></dl>
<p class="since">{first} から <b data-n="{since}">0</b> 日</p></div>
<p class="maph">行ったところ</p>
<div class="mapwrap"><div id="gmap"></div></div>
<div class="mapbar"><button type="button" data-v="jp" aria-pressed="true">日本</button><button type="button" data-v="all" aria-pressed="false">世界</button></div>
<p class="mapnote">{len(pins)}ヶ所 ・ つないだ線は {dist:,}km</p>
<ul class="trips">{cards}</ul>
</main><script>{IDX_JS}\nvar PINS={pins_json};{MAP_JS}</script></body></html>'''
    O=ROOT/'docs'/who;O.mkdir(parents=True,exist_ok=True);(O/'index.html').write_text(page,encoding='utf-8');print('built',O/'index.html',len(page))
if __name__=='__main__':
    a=sys.argv[1:]
    if a!=['index']:
        for s in [x for x in a if x!='index'] or [p.name for p in (ROOT/'packs').iterdir() if (p/'trip.json').exists()]: build(s)
    build_index()
