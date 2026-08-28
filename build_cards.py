import numpy as np, io, json, base64, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # radice del repo
U = os.path.join(ROOT, 'sheets') + os.sep
SHEETS = {
    'A': U + 'sheet-a.jpeg',   # righe: 9 / 0 / Rivela / Armageddon Armageddon Angioletto Diavoletto
    'B': U + 'sheet-b.jpeg',   # righe: 1 / 2 / 3 / 4
    'C': U + 'sheet-c.jpeg',   # righe: 5 / 6 / 7 / 8
    'D': U + 'sheet-d.jpeg',   # righe: Jolly / NO! / +4 +4 +2 +2 / +2 +2 +4 Giullare
}
REF = {'green': (183,221,56), 'red': (251,181,181), 'orange': (253,168,114), 'blue': (145,186,252)}
_c = {}


def sheet(k):
    if k not in _c: _c[k] = Image.open(SHEETS[k]).convert('RGB')
    return _c[k]


def face(k, r, col, pad=6):
    """One printed card, cut out of its cell in the 4x4 grid."""
    im = sheet(k); W, H = im.size; cw, ch = W/4, H/4
    im = im.crop((int(col*cw), int(r*ch), int((col+1)*cw), int((r+1)*ch)))
    a = np.asarray(im).astype(np.int16)
    ys, xs = np.where(a.min(axis=2) < 235)                 # via il margine bianco della pagina
    im = im.crop((xs.min(), ys.min(), xs.max()+1, ys.max()+1))
    w, h = im.size
    im = im.crop((pad, pad, w-pad, h-pad))                 # via il filetto nero del riquadro
    b = np.asarray(im).astype(np.int16)
    ink = (b.max(axis=2) - b.min(axis=2) > 18) | (b.max(axis=2) < 205)
    ys, xs = np.where(ink)
    return im.crop((xs.min(), ys.min(), xs.max()+1, ys.max()+1))


def colour_of(im):
    """Vota su tutta la carta: il colore pieno del bordo copre piu' pixel di ogni altra tinta."""
    a = np.asarray(im).astype(np.int16).reshape(-1, 3)
    best, votes = None, -1
    for k, ref in REF.items():
        d = np.abs(a - np.array(ref)).max(axis=1)
        n = int((d < 34).sum())
        if n > votes: best, votes = k, n
    return best


def enc(im, width=168, q=72):
    im = im.resize((width, max(1, round(im.height*width/im.width))), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'WEBP', quality=q, method=6)
    return base64.b64encode(buf.getvalue()).decode(), len(buf.getvalue())


NUM_ROWS = {9:('A',0), 0:('A',1), 1:('B',0), 2:('B',1), 3:('B',2), 4:('B',3),
            5:('C',0), 6:('C',1), 7:('C',2), 8:('C',3)}
ACTION_ROWS = {'skip': [('D',1,c) for c in range(4)],
               'rev':  [('A',2,c) for c in range(4)],
               'draw2':[('D',2,2), ('D',2,3), ('D',3,0), ('D',3,1)]}
FIXED = {'wild_a':('D',0,0), 'wild_b':('D',0,2), 'draw4_a':('D',2,0), 'draw4_b':('D',2,1),
         'draw4_c':('D',3,2), 'duel':('A',3,0), 'angel':('A',3,2), 'devil':('A',3,3),
         'jester':('D',3,3), 'jester_b':('D',3,3)}

def inject(assets_path, html_path):
    """Rimpiazza la riga ASSETS_RAW dentro index.html con le immagini appena estratte."""
    import re
    data = open(assets_path).read()
    html = open(html_path).read()
    new, hits = re.subn(r'const ASSETS_RAW = .*?;\n',
                        lambda _: 'const ASSETS_RAW = ' + data + ';\n', html, count=1, flags=re.S)
    if not hits:
        raise SystemExit('non ho trovato la riga ASSETS_RAW in ' + html_path)
    open(html_path, 'w').write(new)
    print('scritto', html_path, len(new), 'byte')


if __name__ == '__main__':
    assets, total, seen = {}, 0, {}
    for rank, (sh, row) in NUM_ROWS.items():
        for col in range(4):
            im = face(sh, row, col)
            key = 'n%d_%s' % (rank, colour_of(im))
            if key in assets: print('!! doppione', key, sh, row, col)
            assets[key], n = enc(im); total += n
    for kind, cells in ACTION_ROWS.items():
        for cell in cells:
            im = face(*cell)
            key = '%s_%s' % (kind, colour_of(im))
            if key in assets: print('!! doppione', key, cell)
            assets[key], n = enc(im); total += n
    for key, cell in FIXED.items():
        assets[key], n = enc(face(*cell)); total += n
    missing = [f'n{r}_{c}' for r in range(10) for c in REF if f'n{r}_{c}' not in assets] \
            + [f'{k}_{c}' for k in ACTION_ROWS for c in REF if f'{k}_{c}' not in assets]
    print('carte:', len(assets), '| mancanti:', missing or 'nessuna', '| totale', total, 'byte')
    out = os.path.join(ROOT, 'tools', 'assets.json')
    json.dump(assets, open(out, 'w'))
    inject(out, os.path.join(ROOT, 'index.html'))
