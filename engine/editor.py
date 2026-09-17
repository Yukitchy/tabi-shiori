#!/usr/bin/env python3
"""アルバムから要らない写真・動画を消すローカル編集ページ。

  python3 engine/editor.py <slug> [port]

127.0.0.1 にしか口を開けないので、このMacの前にいる人（ユウキ）しか触れない。
公開ページ側に編集機能は一切出ない＝他の人には消せない。
消す → album.json から除去 → packs/docs 両方のファイル削除 → build → commit → push まで1クリック。
"""
import json, sys, os, subprocess, pathlib, http.server, socketserver, urllib.parse, webbrowser

ROOT = pathlib.Path(__file__).resolve().parent.parent
SLUG = sys.argv[1] if len(sys.argv) > 1 else ''
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8791


def pack(slug): return ROOT / 'packs' / slug


def slugs():
    return sorted(p.name for p in (ROOT / 'packs').iterdir() if (p / 'album.json').exists())


def items(slug):
    return json.load(open(pack(slug) / 'album.json'))['items']


def drop(slug, keys):
    """keys = ['001','042',...] を album.json と実ファイルから消す"""
    A = pack(slug) / 'album.json'
    db = json.load(open(A))
    keep, gone = [], []
    for i in db['items']:
        (gone if i['f'][:3] in keys else keep).append(i)
    db['items'] = keep
    A.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding='utf-8')
    for base in (pack(slug) / 'album', ROOT / 'docs' / slug / 'album'):
        for i in gone:
            for f in base.glob(i['f'][:3] + '.*'):
                os.remove(f)
    return len(gone), len(keep)


def publish(slug, n):
    """build → commit → push。結果を人が読める1行で返す"""
    out = []
    r = subprocess.run([sys.executable, str(ROOT / 'engine' / 'build.py'), slug],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        return 'ビルド失敗: ' + (r.stderr or r.stdout)[-400:]
    out.append('ページを作り直しました')
    subprocess.run(['git', 'add', '-A'], cwd=ROOT, capture_output=True)
    c = subprocess.run(['git', 'commit', '-m', f'{slug}: アルバムから{n}点を削除'],
                       cwd=ROOT, capture_output=True, text=True)
    if c.returncode and 'nothing to commit' not in (c.stdout + c.stderr):
        return ' / '.join(out) + ' / コミット失敗: ' + (c.stderr or c.stdout)[-300:]
    p = subprocess.run(['git', 'push', 'origin', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    if p.returncode:
        return ' / '.join(out) + ' / push失敗（あとで手で押してください）: ' + (p.stderr or '')[-300:]
    out.append('GitHubへpushしました（公開ページへの反映は1〜2分）')
    return ' / '.join(out)


PAGE = '''<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>アルバムの編集 — %(slug)s</title>
<style>
:root{--ink:#202020;--ac:#e3350d;--line:#e3e8ee;--mute:#645f5e}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font-family:"Hiragino Sans","Zen Kaku Gothic New",sans-serif;font-weight:700;padding:0 0 96px}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);padding:14px 16px;z-index:5}
h1{margin:0;font-size:20px}
.sub{font-size:13px;color:var(--mute);font-weight:500;margin-top:4px}
.sub a{color:var(--ac)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;padding:16px}
figure{margin:0;position:relative;cursor:pointer}
img,video{display:block;width:100%%;aspect-ratio:1;object-fit:cover;border-radius:12px;background:#eef2f6}
figcaption{font-size:11px;color:var(--mute);font-weight:500;margin-top:3px;font-variant-numeric:tabular-nums}
figure.kill img,figure.kill video{opacity:.35;outline:4px solid var(--ac);outline-offset:-4px}
figure.kill:after{content:"消す";position:absolute;left:8px;top:8px;background:var(--ac);color:#fff;font-size:12px;padding:4px 9px;border-radius:999px}
.vt{position:absolute;right:8px;top:8px;background:rgba(0,0,0,.6);color:#fff;font-size:11px;padding:3px 7px;border-radius:999px}
#bar{position:fixed;left:0;right:0;bottom:0;background:var(--ink);color:#fff;display:flex;align-items:center;gap:12px;padding:14px 16px;box-shadow:0 -2px 12px rgba(0,0,0,.25)}
#bar .n{flex:1;font-size:15px}
button{font-family:inherit;font-weight:900;font-size:15px;border:0;border-radius:10px;padding:12px 18px;cursor:pointer}
.go{background:var(--ac);color:#fff}.go[disabled]{opacity:.4;cursor:default}
.clr{background:transparent;color:#fff;border:2px solid rgba(255,255,255,.5)}
#msg{padding:12px 16px;font-size:14px;background:#fff7e6;border-bottom:1px solid var(--line);display:none}
</style></head><body>
<header><h1>アルバムの編集</h1>
<div class="sub">%(slug)s ／ %(n)d点　—　消したいものを押して、下の赤いボタンで確定。<a href="%(url)s" target="_blank">公開ページを見る</a></div></header>
<div id="msg"></div>
<div class="grid">%(cells)s</div>
<div id="bar"><span class="n">消したいものを押してください</span>
<button class="clr" type="button" onclick="sel.clear();paint()">選択解除</button>
<button class="go" id="go" disabled>消して公開ページも更新</button></div>
<script>
const sel=new Set(),figs=[...document.querySelectorAll('figure')],go=document.getElementById('go'),n=document.querySelector('#bar .n'),msg=document.getElementById('msg');
function paint(){figs.forEach(f=>f.classList.toggle('kill',sel.has(f.dataset.k)));
 n.textContent=sel.size?sel.size+'点を消します':'消したいものを押してください';go.disabled=!sel.size;}
figs.forEach(f=>f.addEventListener('click',e=>{if(e.target.tagName==='VIDEO')return;
 const k=f.dataset.k;sel.has(k)?sel.delete(k):sel.add(k);paint();}));
go.addEventListener('click',async()=>{
 if(!confirm(sel.size+'点を消します。公開ページも更新されます。よろしいですか？'))return;
 go.disabled=true;go.textContent='処理中…';
 const r=await fetch('/delete',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({slug:%(slugj)s,keys:[...sel]})});
 const j=await r.json();
 msg.style.display='block';msg.textContent=j.msg;
 setTimeout(()=>location.reload(),1200);
});
</script></body></html>'''


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, body, ctype='text/html; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path.startswith('/media/'):
            rel = urllib.parse.unquote(u.path[len('/media/'):])
            slug, _, name = rel.partition('/')
            f = pack(slug) / 'album' / name
            if not f.exists() or '..' in rel:
                return self._send(404, b'not found', 'text/plain')
            ct = 'video/mp4' if f.suffix == '.mp4' else 'image/jpeg'
            return self._send(200, f.read_bytes(), ct)
        slug = (urllib.parse.parse_qs(u.query).get('slug', [SLUG]) or [''])[0]
        if slug not in slugs():
            body = '<meta charset="utf-8"><h1>どのアルバム？</h1><ul>' + ''.join(
                f'<li><a href="/?slug={s}">{s}</a></li>' for s in slugs()) + '</ul>'
            return self._send(200, body.encode())
        I = items(slug)
        cells = ''
        for i in I:
            k = i['f'][:3]
            t = i['taken'][11:]
            if i['kind'] == 'video':
                cells += (f'<figure data-k="{k}"><video src="/media/{slug}/{k}.mp4" preload="metadata" muted></video>'
                          f'<span class="vt">動画</span><figcaption>{k} {t}</figcaption></figure>')
            else:
                cells += (f'<figure data-k="{k}"><img loading="lazy" src="/media/{slug}/{k}.jpg" alt="">'
                          f'<figcaption>{k} {t}</figcaption></figure>')
        body = PAGE % {'slug': slug, 'n': len(I), 'cells': cells,
                       'slugj': json.dumps(slug),
                       'url': f'https://yukitchy.github.io/tabi-shiori/{slug}/'}
        return self._send(200, body.encode())

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != '/delete':
            return self._send(404, b'{}', 'application/json')
        raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        req = json.loads(raw or b'{}')
        slug, keys = req.get('slug', ''), req.get('keys', [])
        if slug not in slugs() or not keys:
            return self._send(400, json.dumps({'msg': '対象がありません'}).encode(), 'application/json')
        n, left = drop(slug, keys)
        msg = f'{n}点を消しました（残り{left}点）。' + publish(slug, n)
        return self._send(200, json.dumps({'msg': msg}, ensure_ascii=False).encode(), 'application/json')


if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('127.0.0.1', PORT), H) as s:
        url = f'http://127.0.0.1:{PORT}/' + (f'?slug={SLUG}' if SLUG else '')
        print('アルバム編集ページ:', url)
        try: webbrowser.open(url)
        except Exception: pass
        s.serve_forever()
