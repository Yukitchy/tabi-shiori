"""シェアカード(1200x630)とアイコン(180)を作る: python3 engine/ogcard.py <slug>（build.py の後に実行し、もう一度 build.py）
型はC案「写真4枚＋白い札」（2026-10-16 ユウキ選定）。trip.json の "og" で写真とトリミング位置を指定する:
  "og": {"icon":"岩", "yotei":{"label":"…","photos":[["img/x.jpg","50% 50%"],…4枚]}, "kiroku":{"photos":[["album/072.jpg","50% 50%"],…4枚]}}
写真のパスは docs/<slug>/ からの相対。札の数字は 予定=cover.nums、記録=kiroku/data.json の全日の合計。
出力は packs/<slug>/img/ と docs/<slug>/img/ の両方に og-yotei.png・og-kiroku.png・icon.png。
X はカード下端に字をかぶせるので、札は中央より上に置く。"""
import json,sys,re,pathlib,subprocess,tempfile,html,shutil
ROOT=pathlib.Path(__file__).resolve().parent.parent
CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
e=html.escape
CSS='''<link href="https://fonts.googleapis.com/css2?family=Inter:wght@800&family=Zen+Kaku+Gothic+New:wght@700;900&display=swap" rel="stylesheet">
<style>*{margin:0;padding:0;box-sizing:border-box}html,body{width:1200px;height:630px;overflow:hidden;background:#fff;color:#111;font-family:"Zen Kaku Gothic New",sans-serif;font-feature-settings:"palt"}
.g{position:absolute;inset:0;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:312px 312px;gap:6px}.g img{display:block;width:100%;height:100%;min-height:0;object-fit:cover}
.f{position:absolute;left:50%;top:44%;transform:translate(-50%,-50%);background:#fff;padding:30px 50px 32px;border-radius:22px;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,.35);min-width:520px}
.f .d{font-weight:700;font-size:24px;color:var(--c);letter-spacing:.06em}
.f h1{font-weight:900;font-size:84px;line-height:1.1;margin:6px 0 10px;white-space:nowrap}
.f .s{display:flex;justify-content:center;gap:26px;font-weight:700;font-size:21px;color:#444}.f .s b{font-family:Inter;font-weight:800;font-size:34px;color:#111;margin:0 2px 0 6px}
.ico{width:180px;height:180px;display:grid;place-items:center;background:#0b6fc2}
.ico b{width:120px;height:120px;border:10px solid #fff;border-radius:26px;display:grid;place-items:center;color:#fff;font-weight:900;font-size:62px}
</style>'''
def shot(body,out,w=1200,h=630):
    with tempfile.NamedTemporaryFile('w',suffix='.html',delete=False,encoding='utf-8') as f:
        f.write(f'<!doctype html><meta charset="utf-8">{CSS}<body style="width:{w}px;height:{h}px">{body}');p=f.name
    pathlib.Path(out).unlink(missing_ok=True)
    # Chrome は撮った後の終了処理で落ちて非0を返すことがある → 終了コードでなく画像ができたかで判定する
    subprocess.run([CHROME,'--headless=new','--disable-gpu','--hide-scrollbars','--force-device-scale-factor=1',f'--window-size={w},{h}',
                    '--virtual-time-budget=6000',f'--screenshot={out}','file://'+p],capture_output=True)
    pathlib.Path(p).unlink()
    if not pathlib.Path(out).exists():raise SystemExit(f'撮影に失敗: {out}')
def card(D,color,label,title,nums,photos):
    g=''.join(f'<img src="{(D/p).as_uri()}" style="object-position:{pos}">' for p,pos in photos)
    s=''.join(f'<span>{e(k)}<b>{e(n)}</b>{e(u)}</span>' for k,n,u in nums)
    return f'<div class="g">{g}</div><div class="f" style="--c:{color}"><p class="d">{e(label)}</p><h1>{e(title)}</h1><p class="s">{s}</p></div>'
def split(v):  # '200m' -> ('200','m')
    m=re.match(r'([\d.,:]+)(.*)',v);return (m[1],m[2]) if m else (v,'')
def main(slug):
    P=ROOT/'packs'/slug;D=ROOT/'docs'/slug;d=json.load(open(P/'trip.json',encoding='utf-8'));o=d['og']
    out={}
    y=o['yotei'];out['og-yotei.png']=card(D,'#0b6fc2',y.get('label') or d['date_label'],d['title'],
        [(k,*split(v)) for k,v,_ in d['cover']['nums']],y['photos'])
    kd=D/'kiroku'/'data.json'
    if o.get('kiroku') and kd.exists():
        days=[x for x in json.load(open(kd,encoding='utf-8'))['days'] if x.get('count')];tot=lambda k:str(sum(x['nums'][k] for x in days))
        lab=f'{days[0]["label"]} {days[0]["k"]}' if len(days)==1 else f'{d["date_label"]}　{len(days)}日間'
        out['og-kiroku.png']=card(D,days[0]['color'],lab,d.get('kiroku_title') or d['title']+' の記録',
            [('',tot('km'),'km'),('',tot('stops'),'駅'),('',tot('photos'),'枚')],o['kiroku']['photos'])
    for name,body in out.items(): shot(body,P/'img'/name)
    shot(f'<div class="ico"><b>{e(o["icon"])}</b></div>',P/'img'/'icon.png',180,180)
    for name in [*out,'icon.png']:
        (D/'img').mkdir(parents=True,exist_ok=True);shutil.copy(P/'img'/name,D/'img'/name);print('wrote',P/'img'/name)
if __name__=='__main__':main(sys.argv[1])
