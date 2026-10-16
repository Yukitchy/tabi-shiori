"""album.json の写真を時刻とGPSで「立ち寄り地点」にまとめる。build.py から使う。
区切り: 30分以上の間隔 or 1km以上の移動。地名: places.json(手書きの既知地点) -> 国土地理院の逆ジオコーダ(geocache.jsonにキャッシュ)。店名は推測しない。"""
import json,math,re,urllib.request,datetime as dt
GEO='https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress?lat=%s&lon=%s'
def km(a,b):
    p=math.pi/180;h=math.sin((b[0]-a[0])*p/2)**2+math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin((b[1]-a[1])*p/2)**2
    return 12742*math.asin(math.sqrt(h))
T=lambda s:dt.datetime.strptime(s[:16],'%Y-%m-%dT%H:%M')
def geocode(P,la,ln):
    """-> (市町村, 町字)。オフラインでキャッシュに無ければ ('','')"""
    f=P/'geocache.json';c=json.loads(f.read_text()) if f.exists() else {}
    k=f'{la:.3f},{ln:.3f}'
    if k not in c:
        try:
            r=json.load(urllib.request.urlopen(GEO%(la,ln),timeout=10))['results']
            if '_muni' not in c:
                s=urllib.request.urlopen('https://maps.gsi.go.jp/js/muni.js',timeout=20).read().decode()
                c['_muni']={a:b.split(',')[3].replace('　','') for a,b in re.findall(r'MUNI_ARRAY\["(\d+)"\] = \'([^\']+)\'',s)}
            c[k]=[c['_muni'].get(str(int(r['muniCd'])),''),r.get('lv01Nm','')]
        except Exception: return ('','')
        f.write_text(json.dumps(c,ensure_ascii=False,indent=0))
    return tuple(c[k])
def make(items,P,voice=None):
    """-> [{day,name,t0,t1,items,lat,lng,km,kind('stop'|'voice'),voice}]（時系列）"""
    pl=json.load(open(P/'places.json')) if (P/'places.json').exists() else {}
    items=sorted(items,key=lambda i:i['taken']);out=[]
    for day in sorted({i['taken'][:10] for i in items}):
        L=[i for i in items if i['taken'][:10]==day];pos=[];last=None
        for i in L:  # GPSなしは直前の位置を引き継ぐ（先頭は次の位置）
            if i.get('lat') is not None: last=(i['lat'],i['lng'])
            pos.append(last)
        nxt=next((p for p in pos if p),None);pos=[p or nxt for p in pos]
        G=[]
        for i,p in zip(L,pos):
            g=G[-1] if G else None
            if g and (T(i['taken'])-T(g['t1'])).total_seconds()<1800 and (p is None or g['pos'] is None or km(p,g['pos'])<1):
                g['items'].append(i);g['t1']=i['taken']
            else: G.append({'items':[i],'t0':i['taken'],'t1':i['taken'],'pos':p})
        for g in G:
            la,ln=g['pos'] if g['pos'] else (None,None);g['name']=None;g['src']='geo'
            if g['pos']:
                for p in pl.get('places',[]):
                    if km(g['pos'],(p['lat'],p['lng']))*1000<=p.get('r',300): g['name']=p['name'];g['src']='place';break
                if not g['name']:
                    muni,town=geocode(P,la,ln);g['muni'],g['town']=muni,town
                    for a in pl.get('addr',[]):
                        if a['match'] in town: g['name']=a['name'];g['src']='place'
                    if not g['name']: g['name']=f'{town}（{muni}）' if town and muni else (muni or town or '地点')
            g['small']=g['src']=='geo' and len(g['items'])<=3 and (T(g['t1'])-T(g['t0'])).total_seconds()<=300
        M=[]  # 小さな地点が続いたら「道中」に1つにまとめる
        for g in G:
            if M and g['small'] and M[-1]['small'] and (T(g['t0'])-T(M[-1]['t1'])).total_seconds()<1800:
                M[-1]['items']+=g['items'];M[-1]['t1']=g['t1'];M[-1]['last']=g.get('muni','')
            else: g['last']=g.get('muni','');M.append(g)
        N=[]  # 同じ既知地点が続けて出たら（間90分未満）1つに
        for g in M:
            if N and g['src']=='place' and N[-1]['src']=='place' and N[-1]['name']==g['name'] and (T(g['t0'])-T(N[-1]['t1'])).total_seconds()<5400:
                N[-1]['items']+=g['items'];N[-1]['t1']=g['t1']
            else: N.append(g)
        M=N
        for g in M:
            if g['small']:
                a,b=g.get('muni',''),g['last'];g['name']='道中（'+(a if a==b else f'{a}〜{b}')+'）' if a else '道中'
        out+=[dict(day=day,name=g['name'],src=g['src'],t0=g['t0'],t1=g['t1'],items=g['items'],lat=g['pos'] and g['pos'][0],lng=g['pos'] and g['pos'][1],kind='stop',voice=None) for g in M]
    # 会話(voice.json): 時間が最も重なる地点にぶら下げる。重ならなければ独立セクション
    for v in (voice or {}).get('items',[]):
        f,t=T(v['from']),T(v['to']);best=None;bo=0
        for s in out:
            if s['kind']!='stop':continue
            o=(min(t,T(s['t1']))-max(f,T(s['t0']))).total_seconds()
            if o>bo:best,bo=s,o
        if best:
            best['voice']=best['voice'] or v; best.setdefault('vs',[]).append(v)
            if best['src']=='geo': best['name']=v['title']
        else: out.append(dict(day=v['from'][:10],name=v['title'],src='voice',t0=v['from'],t1=v['to'],items=[],lat=None,lng=None,kind='voice',voice=v))
    out.sort(key=lambda s:s['t0']);prev={}
    for s in out:  # 前の地点からの距離（直線）
        s['km']=None
        if s['kind']=='stop' and s['lat'] is not None:
            p=prev.get(s['day'])
            if p: s['km']=km(p,(s['lat'],s['lng']))
            prev[s['day']]=(s['lat'],s['lng'])
    return out
if __name__=='__main__':
    import sys,pathlib
    P=pathlib.Path(__file__).resolve().parent.parent/'packs'/sys.argv[1]
    v=json.load(open(P/'voice.json')) if (P/'voice.json').exists() else None
    for s in make(json.load(open(P/'album.json'))['items'],P,v):
        print(s['day'][5:],s['t0'][11:],s['t1'][11:],len(s['items']),s['name'],s['km'] and round(s['km'],1),'VOICE' if s['voice'] else '')
