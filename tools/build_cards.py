"""Prende i PNG in assets/cards/ e li rimette dentro index.html.

Non guarda i fogli: quelli li ritaglia cut_cards.py. Qui si legge la cartella,
si comprime ogni carta in WebP e si riscrive la riga `const ASSETS_RAW = …`.
Vuol dire che puoi aprire un PNG, ritoccarlo a mano, rilanciare questo script e
ritrovartelo nel gioco.

    cd tools && python build_cards.py

Serve pillow. Stampa quanto pesa il totale: e' quasi tutto il peso di
index.html, quindi se cresce troppo si abbassa QUALITY o WIDTH.
"""

import base64
import io
import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_DIR = os.path.join(ROOT, 'assets', 'cards')
ASSETS_JSON = os.path.join(ROOT, 'assets', 'assets.json')
HTML = os.path.join(ROOT, 'index.html')

WIDTH = 168        # quanto sono larghe le carte dentro il gioco, in pixel
QUALITY = 72

COLOURS = ('green', 'red', 'orange', 'blue')
EXPECTED = ([f'n{r}_{c}' for r in range(10) for c in COLOURS]
            + [f'{k}_{c}' for k in ('skip', 'rev', 'draw2') for c in COLOURS]
            + ['wild_a', 'wild_b', 'draw4_a', 'draw4_b', 'draw4_c',
               'duel', 'angel', 'devil', 'jester', 'jester_b'])


def enc(im):
    im = im.convert('RGB')
    im = im.resize((WIDTH, max(1, round(im.height * WIDTH / im.width))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=QUALITY, method=6)
    return base64.b64encode(buf.getvalue()).decode(), len(buf.getvalue())


def inject(assets_path, html_path):
    """Rimpiazza la riga ASSETS_RAW dentro index.html con le immagini appena lette."""
    data = open(assets_path, encoding='utf-8').read()
    html = open(html_path, encoding='utf-8').read()
    new, hits = re.subn(r'const ASSETS_RAW = .*?;\n',
                        lambda _: 'const ASSETS_RAW = ' + data + ';\n', html,
                        count=1, flags=re.S)
    if not hits:
        sys.exit('non ho trovato la riga ASSETS_RAW in ' + html_path)
    open(html_path, 'w', encoding='utf-8').write(new)
    print('scritto', os.path.relpath(html_path, ROOT), len(new), 'byte')


if __name__ == '__main__':
    if not os.path.isdir(CARDS_DIR):
        sys.exit('manca %s: lancia prima cut_cards.py' % os.path.relpath(CARDS_DIR, ROOT))

    found = {os.path.splitext(f)[0]: os.path.join(CARDS_DIR, f)
             for f in sorted(os.listdir(CARDS_DIR)) if f.lower().endswith('.png')}

    missing = [k for k in EXPECTED if k not in found]
    extra = [k for k in found if k not in EXPECTED]
    if missing:
        sys.exit('mancano %d carte: %s' % (len(missing), ', '.join(missing)))
    if extra:
        print('!! ignoro file che non sono carte:', ', '.join(extra))

    assets, total, ratios = {}, 0, set()
    for key in EXPECTED:
        with Image.open(found[key]) as im:
            ratios.add(round(im.width / im.height, 3))
            assets[key], n = enc(im)
        total += n

    print('carte:', len(assets), '| totale', total, 'byte')
    if len(ratios) > 1:
        print('!! proporzioni diverse fra le carte:', sorted(ratios),
              '\n   il CSS di .card ne usa una sola, quelle diverse verranno ritagliate')

    with open(ASSETS_JSON, 'w', encoding='utf-8') as f:
        json.dump(assets, f)
    inject(ASSETS_JSON, HTML)
