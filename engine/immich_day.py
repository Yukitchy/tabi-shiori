#!/usr/bin/env python3
"""Immichの撮影日(JST)の写真/動画を取り込む（冪等）: python3 engine/immich_day.py iwate-2026-10 2026-10-17
srv(yuki-srv)で撮影日で絞って縮小 -> rsync -> 向き補正 -> album.ingest -> 1400px/540pに最終圧縮。Immichは読むだけ。PNG(スクショ)と日時なしは除外。"""
import sys,subprocess,json,pathlib,datetime,shutil
from PIL import Image,ImageOps
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import album
slug,day=sys.argv[1],sys.argv[2]
ROOT=album.ROOT;W=ROOT/'.work'/('iw-'+day);W.mkdir(parents=True,exist_ok=True)
SSH=['ssh','-o','LogLevel=ERROR','yuukiichihara@yuki-srv']
d0=datetime.date.fromisoformat(day);dm=(d0-datetime.timedelta(days=2)).isoformat()
SRV=r'''
export PATH=$PATH:/usr/local/bin; D=/tmp/iwd_%(day)s; mkdir -p $D/out; cd $D
docker exec immich_postgres psql -U postgres -d immich -At -F"|" -c "select id,\"originalFileName\",type,\"originalPath\" from asset where \"deletedAt\" is null and \"createdAt\">='%(dm)s'" | sed 's#|/data#|/Volumes/PhotoArchive/immich-library#' > cand.txt
cat > one.sh <<'EOS'
#!/bin/bash
IFS='|' read id name type path <<< "$1"; F=/Users/yuukiichihara/bin; o=$PWD/out; day=$2
case "$name" in *.PNG|*.png) exit 0;; esac
if [ "$type" = IMAGE ]; then
 d=$(/usr/bin/sips -g creation "$path" 2>/dev/null | awk '/creation/{print $2}' | tr : -)
 [ "$d" = "$day" ] || exit 0
 [ -f $o/$id.jpg ] || /usr/bin/sips -s format jpeg -s formatOptions 85 -Z 1800 "$path" --out $o/$id.jpg >/dev/null 2>&1; echo "$id|$name" > $o/$id.name
else
 ct=$($F/ffprobe -v error -show_entries format_tags=creation_time -of csv=p=0 "$path" 2>/dev/null)
 [ -n "$ct" ] || exit 0
 j=$(date -j -u -f %%Y-%%m-%%dT%%H:%%M:%%S "${ct%%.*}" +%%s); jd=$(date -u -r $((j+32400)) +%%Y-%%m-%%d)
 [ "$jd" = "$day" ] || exit 0
 [ -f $o/$id.mp4 ] || $F/ffmpeg -y -loglevel error -i "$path" -vf scale=-2:720 -c:v libx264 -crf 28 -preset fast -c:a aac -b:a 80k -movflags +faststart $o/$id.mp4
 $F/ffprobe -v error -show_entries format_tags=com.apple.quicktime.location.ISO6709,creation_time -of default=nw=1 "$path" > $o/$id.tags; echo "$id|$name" > $o/$id.name
fi
EOS
chmod +x one.sh; cat cand.txt | xargs -P 6 -I{} ./one.sh {} %(day)s; ls out | wc -l
'''%{'day':day,'dm':dm}
subprocess.run(SSH+['bash -s'],input=SRV,text=True,check=True)
subprocess.run(['rsync','-a','-e','ssh -o LogLevel=ERROR',f'yuukiichihara@yuki-srv:/tmp/iwd_{day}/out/',str(W/'raw')+'/'],check=True)
raw=W/'raw';st=W/'stage';st.mkdir(exist_ok=True);side={}
for nf in sorted(raw.glob('*.name')):
    i,name=nf.read_text().strip().split('|');stem=pathlib.Path(name).stem
    if (raw/f'{i}.jpg').exists():
        with Image.open(raw/f'{i}.jpg') as im:
            t=ImageOps.exif_transpose(im);ex=t.getexif();ex[274]=1;t.save(st/f'{stem}.jpg',quality=85,exif=ex)
    else:
        t=dict(l.split('=',1) for l in (raw/f'{i}.tags').read_text().split('\n') if '=' in l)
        z=datetime.datetime.strptime(t['TAG:creation_time'][:19],'%Y-%m-%dT%H:%M:%S')+datetime.timedelta(hours=9)
        m={'taken':z.strftime('%Y-%m-%dT%H:%M')}
        g=t.get('TAG:com.apple.quicktime.location.ISO6709','')
        import re;mm=re.match(r'([+-]\d+\.\d+)([+-]\d+\.\d+)',g)
        if mm:m['lat']=float(mm[1]);m['lng']=float(mm[2])
        shutil.copy(raw/f'{i}.mp4',st/f'{stem}.mp4');side[f'{stem}.mp4']=m
(st/'meta.json').write_text(json.dumps(side))
before={i['f'] for i in json.load(open(ROOT/'packs'/slug/'album.json'))['items']} if (ROOT/'packs'/slug/'album.json').exists() else set()
album.ingest(slug,st)
out=ROOT/'packs'/slug/'album'
for i in json.load(open(ROOT/'packs'/slug/'album.json'))['items']:
    if i['f'] in before: continue
    p=out/i['f']
    if i['kind']=='photo':
        with Image.open(p) as im:
            im.thumbnail((1400,1400));im.convert('RGB').save(p,quality=78,optimize=True)
    else:
        t=out/'t.mp4';album.run([album.FF,'-y','-i',str(p),'-vf','scale=-2:540','-c:v','libx264','-crf','30','-preset','fast','-c:a','aac','-b:a','64k','-movflags','+faststart',str(t)]);t.replace(p)
