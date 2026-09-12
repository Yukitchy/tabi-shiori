#!/usr/bin/env python3
"""tabi-shiori engine: packs/<slug>/trip.json + img/ -> docs/<slug>/index.html"""
import json,sys,shutil,html,pathlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
def esc(s):return html.escape(s,quote=True)
def build(slug):
    P=ROOT/'packs'/slug; d=json.load(open(P/'trip.json'))
    cr=json.load(open(P/'credits.json')) if (P/'credits.json').exists() else {}
    O=ROOT/'docs'/slug; (O/'img').mkdir(parents=True,exist_ok=True)
    for f in (P/'img').glob('*'): shutil.copy(f,O/'img'/f.name)
    pts=lambda L:'<ul class="pts">'+''.join(f'<li><i>{i+1}</i><span>{esc(a)}<small>{esc(b)}</small></span></li>' for i,(a,b) in enumerate(L))+'</ul>'
    links=lambda L:'<div class="links">'+''.join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(t)}</a>' for t,u in L)+'</div>' if L else ''
    def photo(k):
        c=cr.get(k,{}); cap=f'<a href="{esc(c["page"])}" target="_blank" rel="noopener">{esc(c.get("title",""))}</a> {esc(c.get("lic",""))}' if c else ''
        return f'<figure class="photo"><img src="img/{k}.jpg" alt="" loading="lazy"><figcaption>{cap}</figcaption></figure>'
    ch=d.get('choices')
    chs=''
    if ch:
        chs+=f'<section class="s"><div class="eyebrow">{esc(ch["day"])}</div><h2>{ch["h"]}</h2><p class="lead">{esc(ch["lead"])}</p><div class="picked" id="picked">まだ選んでいません。下の3つを見て、気に入ったものを押してください。</div></section>'
        for o in ch['options']:
            chs+=(f'<section class="s"><div class="opt" data-k="{esc(o["key"])}" id="opt-{esc(o["key"])}">'
                  f'<span class="badge">{esc(o["badge"])}　{esc(o["label"])}</span><h2>{o["h"]}</h2>{photo(o["photo"])}'
                  f'<p class="lead">{esc(o["lead"])}</p><div class="meta"><span>{esc(o["drive"])}</span><span>{esc(o["arrive"])}</span></div>'
                  f'{pts(o["pts"])}{links(o.get("links",[]))}'
                  f'<button class="pick" data-k="{esc(o["key"])}">この案にする</button></div></section>')
    secs=''
    for s in d['sections']:
        secs+=f'<section class="s"><div class="eyebrow">{esc(s["day"])}</div><h2>{s["h"]}</h2>{photo(s["photo"])}<p class="lead">{esc(s["lead"])}</p>{pts(s["pts"])}{links(s.get("links",[]))}</section>'
    picks_json=json.dumps({o['key']:{'label':o['label'],'next17':o['next17']} for o in (ch['options'] if ch else [])},ensure_ascii=False)
    c=d['cover']; nums=''.join(f'<div><dt>{esc(a)}</dt><dd>{esc(b)}<small>{esc(cc)}</small></dd></div>' for a,b,cc in c['nums'])
    car=d['car']; rows=''.join(f'<li><b>{esc(n)}<small>{esc(t)}</small></b><a href="{esc(u)}" target="_blank" rel="noopener">予約 →</a></li>' for n,t,u in car['rows'])
    pack=''.join(f'<li><b>{esc(a)}</b><span>{esc(b)}</span></li>' for a,b in d['pack']['items'])
    roles=''.join(f'<li><b>{esc(a)}</b><span>{esc(b)}</span></li>' for a,b in d['roles'])
    page=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(d["title"])}</title><meta name="robots" content="noindex"><meta property="og:title" content="{esc(d["title"])}"><meta property="og:description" content="{esc(d["og_desc"])}"><meta property="og:image" content="img/{c["photo"]}.jpg">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700;900&display=swap">
<style>
:root{{--bg:#fff;--card:#f6f9fc;--ink:#202020;--mute:#645f5e;--ash:#8a8482;--line:#e3e8ee;--ac:{d["accent"]};--shadow:{d["accent_shadow"]};--wash:{d["accent_wash"]};color-scheme:light}}
*{{box-sizing:border-box}}html,body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Zen Kaku Gothic New","Hiragino Sans","Noto Sans JP",sans-serif;font-weight:700;-webkit-font-smoothing:antialiased}}
h1,h2,h3,p{{margin:0}}h1,h2{{line-height:1.15;text-wrap:balance;word-break:keep-all;overflow-wrap:anywhere}}
#deck{{height:100vh;height:100dvh;overflow-y:auto;scroll-snap-type:y proximity;scroll-behavior:smooth;-webkit-overflow-scrolling:touch}}
.s{{min-height:100vh;min-height:100dvh;scroll-snap-align:start;padding:52px 22px 40px;display:flex;flex-direction:column;justify-content:center;gap:14px;max-width:560px;margin:0 auto}}
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
.rest li b{{font-weight:900}}.rest li span{{color:var(--mute);font-size:12.5px;text-align:right}}.rest li small{{display:block;font-size:11.5px;color:var(--ash);font-weight:500;line-height:1.6}}
.rest li a{{white-space:nowrap;font-size:12px;font-weight:900;color:#fff;background:var(--ac);border-radius:999px;padding:6px 12px;text-decoration:none}}
.note{{background:var(--wash);border-radius:14px;padding:12px 14px;font-size:13px;line-height:1.7;color:var(--ink)}}
.links{{display:flex;flex-wrap:wrap;gap:6px}}.links a{{font-size:12px;font-weight:900;color:var(--ink);text-decoration:none;border:1.5px solid var(--ink);border-radius:999px;padding:5px 11px}}.links a:after{{content:" →"}}
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
.rail{{position:fixed;right:10px;top:50%;transform:translateY(-50%);height:min(50vh,380px);width:44px;pointer-events:none;z-index:5}}
.rail .lab{{position:absolute;left:0;right:0;text-align:center;font-size:11px;font-weight:900}}.rail .lab.t{{top:-36px}}.rail .lab.b{{bottom:-36px}}
.rail .track{{position:absolute;left:50%;top:0;bottom:0;width:8px;margin-left:-4px;background:#e9eef3;border-radius:999px}}
.rail .knob{{position:absolute;left:50%;top:0;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;background:var(--ac);box-shadow:0 0 0 4px #fff,0 3px 0 4px var(--shadow)}}
@media(max-width:480px){{.s{{padding-right:56px}}}}
@media(prefers-reduced-motion:reduce){{#deck{{scroll-behavior:auto}}}}
</style></head><body>
<div class="rail" aria-hidden="true"><span class="lab t">{esc(d["rail"]["top"])}</span><span class="track"></span><span class="knob" id="knob"></span><span class="lab b">{esc(d["rail"]["bottom"])}</span></div>
<div id="deck">
<section class="s hub"><span class="date">{esc(d["date_label"])}</span><h1>{esc(d["title"])}</h1>{photo(c["photo"])}<p class="who">{c["who"]}</p><dl class="nums">{nums}</dl><p class="hint">下にスクロールで1日目 → 2日目</p></section>
{chs}{secs}
<section class="s"><div class="eyebrow">車</div><h2>{car["h"]}</h2><p class="lead">{esc(car["lead"])}</p><ul class="rest">{rows}</ul><p class="note">{esc(car["note"])}</p></section>
<section class="s"><div class="eyebrow">準備</div><h2>{esc(d["pack"]["h"])}</h2><ul class="rest">{pack}</ul><div class="eyebrow" style="margin-top:8px">分担</div><ul class="rest">{roles}</ul></section>
<section class="s end"><div class="eyebrow">おわり</div><h2>{esc(d["end"]["h"])}</h2><p class="lead">{esc(d["end"]["lead"])}</p><p class="credit">{esc(d["credit"])}</p></section>
</div>
<script>
const PICKS={picks_json};
const box=document.getElementById('picked');
function apply(k){{if(!PICKS[k])return;document.querySelectorAll('.opt').forEach(o=>o.classList.toggle('on',o.dataset.k===k));
 box.innerHTML='いま選んでいるのは <b>'+PICKS[k].label+'</b>。'+PICKS[k].next17+'。<br>変えたいときは別の案の「この案にする」を押してください。';}}
document.querySelectorAll('.pick').forEach(b=>b.addEventListener('click',()=>{{try{{localStorage.setItem('pick16',b.dataset.k)}}catch(e){{}};apply(b.dataset.k);box.scrollIntoView({{behavior:'smooth',block:'center'}});}}));
try{{apply(localStorage.getItem('pick16'))}}catch(e){{}}
const deck=document.getElementById('deck'),knob=document.getElementById('knob');
const upd=()=>{{const r=deck.scrollTop/(deck.scrollHeight-deck.clientHeight||1);knob.style.top=(r*100)+'%';}};deck.addEventListener('scroll',upd,{{passive:true}});upd();
</script></body></html>'''
    (O/'index.html').write_text(page,encoding='utf-8'); print('built',O/'index.html',len(page))
if __name__=='__main__':
    for s in sys.argv[1:] or [p.name for p in (ROOT/'packs').iterdir() if (p/'trip.json').exists()]: build(s)
