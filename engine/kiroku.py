"""記録ページ(kiroku/)を作る: stops.py の出力 -> data.json、core.js/core.css/tpl.html -> kiroku/。build.py から呼ぶ。
日が増えたら（album.json に17日の写真が入れば）駅が自動で続き、日タブが押せるようになり、日ごとに路線の色が変わる。"""
import json,shutil,pathlib,datetime,html
A=pathlib.Path(__file__).resolve().parent/'kiroku'
WD='月火水木金土日'
FALLBACK=['#0b6fc2','#c2410c','#2f855a','#7b3fb0']
def build_kiroku(d,stops,voice,ktitle,kdesc,og,bmeta,K):
    stops=[s for s in stops if s['kind']=='stop' and s['items']]+[s for s in stops if s['kind']=='voice']
    stops.sort(key=lambda s:s['t0']);S=[]
    for s in stops:
        v=[s['voice']] if s['voice'] else []
        if s['kind']=='voice':  # 独立した会話は同じ日の直前の駅にぶら下げる
            p=next((x for x in reversed(S) if x['day']==s['day']),None)
            if p:p['voices'].append(s['voice'])
            continue
        S.append(dict(day=s['day'],name=s['name'],t0=s['t0'][11:16],t1=s['t1'][11:16],lat=s['lat'],lng=s['lng'],
          km=None if s['km'] is None else round(s['km'],1),voices=v,
          items=[dict(f=i['f'],k='v' if i['kind']=='video' else 'p',t=i['taken'][11:16],lat=i.get('lat'),lng=i.get('lng')) for i in s['items']]))
    sd=sorted({s['day'] for s in S});alld=sorted(set(d.get('dates',[]))|set(sd))
    a2=(d.get('rail',{}).get('accent2') or {}).get('accent')
    pal=[d['accent'],a2 or FALLBACK[1]]+FALLBACK[2:]
    days=[]
    for n,day in enumerate(alld):
        dt=datetime.date.fromisoformat(day);L=[s for s in S if s['day']==day]
        for s in L:s['di']=n
        its=[i for s in L for i in s['items']];nV=sum(i['k']=='v' for i in its)
        dd=dict(n=dt.day,day=day,k=f'{n+1}日目',color=pal[n%len(pal)],label=f'{dt.month}月{dt.day}日（{WD[dt.weekday()]}）',count=len(L))
        if L:
            ts=[i['t'] for i in its]
            dd.update(route=f'{L[0]["name"]} → {L[-1]["name"]}',nums=dict(photos=len(its)-nV,videos=nV,km=round(sum(s['km'] or 0 for s in L)),stops=len(L),start=min(ts),end=max(ts)))
        days.append(dd)
    K.mkdir(exist_ok=True)
    (K/'data.json').write_text(json.dumps(dict(title=d['title'],days=days,stops=S),ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    for f in ('core.js','core.css'):shutil.copy(A/f,K/f)
    first=next(x['n'] for x in days if x['count'])
    tabs=''.join(f'<button data-tab="d{x["n"]}"{" class=\"on\"" if x["n"]==first else ""}{"" if x["count"] else " disabled"}>{x["n"]}日</button>' for x in days)+'<button data-tab="album">アルバム</button>'
    e=lambda s:html.escape(s,quote=True)
    page=(A/'tpl.html').read_text(encoding='utf-8').replace('__CSS__',(A/'page.css').read_text(encoding='utf-8')).replace('__ACC__',d['accent'])
    for k,v in (('__TITLE__',e(ktitle)),('__DESC__',e(kdesc)),('__OG__',og),('__BMETA__',bmeta),('__TABS__',tabs)):page=page.replace(k,v)
    (K/'index.html').write_text(page,encoding='utf-8')
