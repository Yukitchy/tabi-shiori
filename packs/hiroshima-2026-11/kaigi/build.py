#!/Library/Frameworks/Python.framework/Versions/3.11/bin/python3
"""通話用ページ: src.html -> docs/<slug>/index.html（BudouXで文節の切れ目を焼き込む・CSSは keep-all）"""
import re, sys, pathlib, budoux

SLUG = 'gsmyuj7dky9lzu'
HERE = pathlib.Path(__file__).parent
OUT = HERE.parents[2] / 'docs' / SLUG / 'index.html'

parser = budoux.load_default_japanese_parser()
BLOCK = re.compile(r'(<(p|h1|h2|h3|li|dt|dd|td|th|figcaption|small|b|em|span)(?:\s[^>]*)?>)(.*?)(</\2>)', re.S)
WRAP = re.compile(r'^<span style="[^"]*">(.*)</span>$', re.S)
GLUE = re.compile(r'「[^」​]{1,10}」[。、？！]*|[「（]+[^\s​「（」）]|[^\s​「（][。、？！]*[」）][。、？！」）]*')


def glue(html):
    text = lambda t: GLUE.sub(lambda m: f'<span class="nw">{m[0]}</span>', t)
    return ''.join(p if p.startswith('<') else text(p) for p in re.split(r'(<[^>]+>)', html))


def phrase(inner):
    if not re.search(r'[ぁ-んァ-ヶ一-龠]', inner) or '​' in inner:
        return inner
    out = WRAP.sub(r'\1', parser.translate_html_string(inner))
    out = re.sub(r'(<(?:b|s|ins|strong|em)\b[^>]*>)​', '​\\1', out)
    out = re.sub(r'​((?:<[^>]+>)*[」）、。？！])', r'\1', out)
    out = re.sub(r'([「（](?:<[^>]+>)*)​', r'\1', out)
    out = re.sub(r'「[^」<]{1,10}」', lambda m: m[0].replace('​', ''), out)
    return glue(out)


def build(src):
    # テキストノード単位でBudouXをかける（タグの中身・script・styleは触らない）
    head, sep, body = src.partition('</style>')
    body, sep2, tail = body.partition('<script>')
    out = []
    for tok in re.split(r'(<[^>]+>)', body):
        out.append(tok if tok.startswith('<') else phrase(tok))
    return head + sep + ''.join(out) + sep2 + tail


if __name__ == '__main__':
    assert '​' in phrase('個人的に伺いたいことがあります。')
    src = (HERE / 'src.html').read_text()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(src))
    print(OUT, len(src), '->', OUT.stat().st_size)
