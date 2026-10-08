#!/Library/Frameworks/Python.framework/Versions/3.11/bin/python3
"""採点6・7の実測: WebKit 390/320・Chromium 1440 で横はみ出し・最小文字・決める節の高さ・スクショ"""
import sys, json, pathlib
from playwright.sync_api import sync_playwright

url = sys.argv[1]
outdir = pathlib.Path(sys.argv[2]); outdir.mkdir(parents=True, exist_ok=True)
JS = """() => {
  const vis = [...document.querySelectorAll('body *')].filter(e => {
    const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' &&
      [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
  });
  const fs = vis.map(e => parseFloat(getComputedStyle(e).fontSize));
  const small = vis.filter(e => parseFloat(getComputedStyle(e).fontSize) < 12).map(e => e.tagName + ':' + e.textContent.trim().slice(0, 20));
  const dec = document.querySelector('#decide');
  return {scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth,
    minFont: Math.min(...fs), small, decideHeight: dec ? dec.getBoundingClientRect().height : null,
    docHeight: document.documentElement.scrollHeight};
}"""
res = {}
with sync_playwright() as p:
    for engine, w, h in [('webkit', 390, 844), ('webkit', 320, 568), ('chromium', 1440, 900)]:
        b = getattr(p, engine).launch()
        pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=2)
        pg.goto(url, wait_until='networkidle')
        pg.wait_for_timeout(600)
        r = pg.evaluate(JS)
        pg.screenshot(path=str(outdir / f'{engine}-{w}.png'), full_page=True)
        pg.screenshot(path=str(outdir / f'top-{engine}-{w}.png'))
        pg.evaluate("document.querySelector('#decide').scrollIntoView()"); pg.wait_for_timeout(200)
        pg.screenshot(path=str(outdir / f'decide-{engine}-{w}.png'))
        res[f'{engine}-{w}'] = r
        b.close()
print(json.dumps(res, ensure_ascii=False, indent=1))
