#!/usr/bin/env python3
"""iPhone書き出しフォルダ -> packs/<slug>/album/ + album.json : python3 engine/album.py <slug> <folder>"""
import json,sys,re,subprocess,pathlib,datetime
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parent.parent
FF='/opt/homebrew/bin/ffmpeg';SIPS='/usr/bin/sips';MDLS='/usr/bin/mdls'
IMG={'.jpg','.jpeg','.png','.heic'};VID={'.mov','.mp4'}
run=lambda a:subprocess.run(a,capture_output=True).returncode
def _dms(v,ref):
    d,m,s=(float(x) for x in v);x=d+m/60+s/3600
    return -x if str(ref).upper().startswith(('S','W')) else x
def pil_meta(p):
    """(dt,lat,lng) / PILが読めなければ None"""
    try:
        with Image.open(p) as im: ex=im.getexif()
    except Exception: return None
    dt=lat=lng=None
    try: dt=ex.get_ifd(0x8769).get(36867)
    except Exception: pass
    dt=dt or ex.get(306)
    if dt:
        try: dt=datetime.datetime.strptime(str(dt).strip()[:19],'%Y:%m:%d %H:%M:%S')
        except Exception: dt=None
    try:
        g=ex.get_ifd(0x8825)
        if g and g.get(2) and g.get(4): lat=_dms(g[2],g.get(1,'N'));lng=_dms(g[4],g.get(3,'E'))
    except Exception: pass
    return dt,lat,lng
def mdls_meta(p):
    o=subprocess.run([MDLS,'-name','kMDItemContentCreationDate','-name','kMDItemLatitude','-name','kMDItemLongitude',str(p)],capture_output=True,text=True).stdout
    g=dict((k,v.strip()) for k,v in re.findall(r'(kMDItem\w+)\s+=\s+(.+)',o))
    dt=None;m=re.match(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) ([+-]\d{4})',g.get('kMDItemContentCreationDate',''))
    if m:
        try: dt=datetime.datetime.strptime(m.group(1)+m.group(2),'%Y-%m-%d %H:%M:%S%z').astimezone().replace(tzinfo=None)
        except Exception: pass
    def num(k):
        try: return float(g.get(k,''))
        except ValueError: return None
    return dt,num('kMDItemLatitude'),num('kMDItemLongitude')
def meta(p):
    sc=p.parent/'meta.json'  # 任意のサイドカー {ファイル名:{taken,lat,lng}}（Immichプレビュー等EXIFの無い素材用）
    if sc.exists():
        m=json.load(open(sc)).get(p.name)
        if m: return datetime.datetime.strptime(m['taken'][:16],'%Y-%m-%dT%H:%M'),m.get('lat'),m.get('lng')
    dt,lat,lng=pil_meta(p) or (None,None,None)
    if dt is None or lat is None:
        m=mdls_meta(p);dt=dt or m[0];lat=m[1] if lat is None else lat;lng=m[2] if lng is None else lng
    return dt or datetime.datetime.fromtimestamp(p.stat().st_mtime),lat,lng
def ingest(slug,src):
    P=ROOT/'packs'/slug;A=P/'album.json';out=P/'album';out.mkdir(parents=True,exist_ok=True)
    db=json.load(open(A)) if A.exists() else {'items':[]}
    have={i['src'] for i in db['items']};n=max([int(i['f'][:3]) for i in db['items']]+[0])
    fresh=[f for f in sorted(pathlib.Path(src).iterdir()) if f.suffix.lower() in IMG|VID and f.name not in have]
    for (dt,lat,lng),f in sorted(((meta(f),f) for f in fresh),key=lambda x:x[0][0]):
        n+=1;k=f'{n:03d}';v=f.suffix.lower() in VID
        if v:
            run([FF,'-y','-i',str(f),'-vf','scale=-2:720','-c:v','libx264','-crf','26','-preset','fast','-c:a','aac','-b:a','96k','-movflags','+faststart',str(out/f'{k}.mp4')])
            if run([FF,'-y','-ss','1','-i',str(f),'-frames:v','1',str(out/f'{k}.jpg')]) or not (out/f'{k}.jpg').exists():
                run([FF,'-y','-ss','0','-i',str(f),'-frames:v','1',str(out/f'{k}.jpg')])
        else:
            run([SIPS,'-s','format','jpeg','-s','formatOptions','80','-Z','1600',str(f),'--out',str(out/f'{k}.jpg')])
        db['items'].append({'f':f'{k}.mp4' if v else f'{k}.jpg','kind':'video' if v else 'photo','src':f.name,'taken':dt.strftime('%Y-%m-%dT%H:%M'),'lat':lat,'lng':lng,'cap':''})
    db['items'].sort(key=lambda i:i['taken'])
    A.write_text(json.dumps(db,ensure_ascii=False,indent=1),encoding='utf-8')
    I=db['items'];print(f"{slug}: +{len(fresh)} / 写真{sum(1 for i in I if i['kind']=='photo')}枚 動画{sum(1 for i in I if i['kind']=='video')}本 GPSあり{sum(1 for i in I if i['lat'] is not None)}件")
if __name__=='__main__':
    if len(sys.argv)!=3: sys.exit('usage: python3 engine/album.py <slug> <source_folder>')
    ingest(sys.argv[1],sys.argv[2])
