"""Ritaglia le 62 carte dai quattro fogli e le salva una per una in assets/cards/.

Il punto delicato e' che i fogli **non sono una griglia regolare**: le carte sono
scansionate storte di qualche pixel, i margini fra una e l'altra cambiano, e su
alcuni fogli restano le linee guida della stampa. Dividere l'immagine in sedici
rettangoli uguali (com'era prima) taglia via un pezzo di carta da una parte e
lascia entrare il vicino dall'altra.

Qui invece ogni carta viene **trovata**: si marca tutto quello che non e' carta
bianca, si prendono le isole di pixel collegate, e si tengono quelle grandi
quanto una carta. Le linee guida sono sottili e si scartano da sole.

    cd tools && python cut_cards.py            # scrive solo le carte mancanti
    cd tools && python cut_cards.py --force    # rifa' tutto da capo

Serve pillow, numpy, scipy. Dopo aver ritoccato a mano i PNG in assets/cards/,
si rimettono nel gioco con build_cards.py (che non rilegge i fogli).
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRID = os.path.join(ROOT, 'grid')
CARDS_DIR = os.path.join(ROOT, 'assets', 'cards')

SHEETS = {
    'A': 'sheet-a.jpeg',   # righe: 9 / 0 / Rivela / Armageddon Armageddon Angioletto Diavoletto
    'B': 'sheet-b.jpeg',   # righe: 1 / 2 / 3 / 4
    'C': 'sheet-c.jpeg',   # righe: 5 / 6 / 7 / 8
    'D': 'sheet-d.jpeg',   # righe: Jolly / NO! / +4 +4 +2 +2 / +2 +2 +4 Giullare
}

# Tutte le carte finiscono a questa misura: e' la mediana dei ritagli veri
# (~298x464) ed e' la stessa proporzione che .card usa nel CSS, cosi' il browser
# non ne ritaglia un altro pezzo per farcele stare.
CARD_W, CARD_H = 298, 464

# I quattro colori del mazzo, campionati dal bordo pieno delle carte.
REF = {'green': (183, 221, 56), 'red': (251, 181, 181),
       'orange': (253, 168, 114), 'blue': (145, 186, 252)}

PAPER = 225        # sotto questo grigio non e' piu' carta bianca
MIN_W, MAX_W = 250, 360
MIN_H, MAX_H = 400, 520

_sheets = {}


def sheet(k):
    if k not in _sheets:
        path = os.path.join(GRID, SHEETS[k])
        if not os.path.exists(path):
            sys.exit('manca il foglio ' + path)
        _sheets[k] = Image.open(path).convert('RGB')
    return _sheets[k]


def find_cards(k):
    """Le 16 carte del foglio, ordinate per riga e poi per colonna.

    Ritorna una lista di 16 riquadri (x0, y0, x1, y1) in coordinate del foglio.
    """
    im = sheet(k)
    a = np.asarray(im).astype(np.int16)
    ink = ndimage.binary_closing(a.min(axis=2) < PAPER, np.ones((7, 7)))
    lab, n = ndimage.label(ink)

    boxes = []
    for i, (sy, sx) in enumerate(ndimage.find_objects(lab), start=1):
        w, h = sx.stop - sx.start, sy.stop - sy.start
        if not (MIN_W < w < MAX_W and MIN_H < h < MAX_H):
            continue
        # Se una linea guida tocca la carta, l'isola sporge di qualche pixel.
        # Le righe e le colonne della carta vera sono piene per quasi tutta la
        # loro lunghezza, quelle della linea quasi per niente: si tagliano via.
        m = lab[sy, sx] == i
        cols = np.where(m.sum(0) / m.shape[0] > .5)[0]
        rows = np.where(m.sum(1) / m.shape[1] > .5)[0]
        if not len(cols) or not len(rows):
            continue
        boxes.append((sx.start + int(cols[0]), sy.start + int(rows[0]),
                      sx.start + int(cols[-1]) + 1, sy.start + int(rows[-1]) + 1))

    if len(boxes) != 16:
        sys.exit('foglio %s: ho trovato %d carte invece di 16' % (k, len(boxes)))

    boxes.sort(key=lambda b: b[1])                       # per riga
    out = []
    for r in range(4):
        out += sorted(boxes[r * 4:(r + 1) * 4], key=lambda b: b[0])   # per colonna
    return out


_cells = {}


def face(k, row, col):
    """La carta nella cella (riga, colonna) del foglio, gia' portata a misura."""
    if k not in _cells:
        _cells[k] = find_cards(k)
    box = _cells[k][row * 4 + col]
    return sheet(k).crop(box).resize((CARD_W, CARD_H), Image.LANCZOS)


def colour_of(im):
    """Vota su tutta la carta: il colore pieno del bordo copre piu' pixel di ogni altra tinta."""
    a = np.asarray(im).astype(np.int16).reshape(-1, 3)
    best, votes = None, -1
    for k, ref in REF.items():
        n = int((np.abs(a - np.array(ref)).max(axis=1) < 34).sum())
        if n > votes:
            best, votes = k, n
    return best


# Dove sta ogni carta sui fogli. Nelle righe di numeri e di carte azione
# l'ordine dei colori cambia da riga a riga, quindi il colore non si scrive a
# mano: lo decide colour_of contando i pixel.
NUM_ROWS = {9: ('A', 0), 0: ('A', 1), 1: ('B', 0), 2: ('B', 1), 3: ('B', 2), 4: ('B', 3),
            5: ('C', 0), 6: ('C', 1), 7: ('C', 2), 8: ('C', 3)}
ACTION_ROWS = {'skip':  [('D', 1, c) for c in range(4)],
               'rev':   [('A', 2, c) for c in range(4)],
               'draw2': [('D', 2, 2), ('D', 2, 3), ('D', 3, 0), ('D', 3, 1)]}
FIXED = {'wild_a': ('D', 0, 0), 'wild_b': ('D', 0, 2),
         'draw4_a': ('D', 2, 0), 'draw4_b': ('D', 2, 1), 'draw4_c': ('D', 3, 2),
         'duel': ('A', 3, 0), 'angel': ('A', 3, 2), 'devil': ('A', 3, 3),
         'jester': ('D', 3, 3), 'jester_b': ('D', 3, 3)}


def all_cards():
    """{chiave: immagine} per tutte e 62 le carte."""
    out = {}
    for rank, (sh, row) in NUM_ROWS.items():
        for col in range(4):
            im = face(sh, row, col)
            key = 'n%d_%s' % (rank, colour_of(im))
            if key in out:
                print('!! doppione', key, sh, row, col)
            out[key] = im
    for kind, cells in ACTION_ROWS.items():
        for cell in cells:
            im = face(*cell)
            key = '%s_%s' % (kind, colour_of(im))
            if key in out:
                print('!! doppione', key, cell)
            out[key] = im
    for key, cell in FIXED.items():
        out[key] = face(*cell)
    return out


def contact_sheet(cards, path, per_row=8, w=150):
    """Un provino con tutte le carte ritagliate, per controllarle a colpo d'occhio."""
    keys = sorted(cards)
    h = round(w * CARD_H / CARD_W)
    rows = -(-len(keys) // per_row)
    out = Image.new('RGB', (per_row * (w + 8) + 8, rows * (h + 8) + 8), (30, 18, 42))
    for i, k in enumerate(keys):
        out.paste(cards[k].resize((w, h), Image.LANCZOS),
                  (8 + (i % per_row) * (w + 8), 8 + (i // per_row) * (h + 8)))
    out.save(path)
    return path


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='ritaglia le carte dai fogli in grid/')
    ap.add_argument('--force', action='store_true',
                    help='riscrive anche le carte gia' ' presenti (perdi i ritocchi a mano)')
    args = ap.parse_args()

    os.makedirs(CARDS_DIR, exist_ok=True)
    cards = all_cards()

    missing = [f'n{r}_{c}' for r in range(10) for c in REF if f'n{r}_{c}' not in cards] \
            + [f'{k}_{c}' for k in ACTION_ROWS for c in REF if f'{k}_{c}' not in cards]
    print('carte:', len(cards), '| mancanti:', missing or 'nessuna')

    written, kept = 0, 0
    for key, im in sorted(cards.items()):
        path = os.path.join(CARDS_DIR, key + '.png')
        if os.path.exists(path) and not args.force:
            kept += 1
            continue
        im.save(path, optimize=True)
        written += 1

    print('scritte', written, 'carte in', os.path.relpath(CARDS_DIR, ROOT))
    if kept:
        print('lasciate stare', kept, 'gia\' presenti (--force per rifarle)')

    # Il provino si rifa' leggendo la cartella, non i ritagli appena calcolati:
    # cosi' mostra anche le carte ritoccate a mano.
    on_disk = {k: Image.open(os.path.join(CARDS_DIR, k + '.png')).convert('RGB')
               for k in cards}
    print('provino:', os.path.relpath(
        contact_sheet(on_disk, os.path.join(ROOT, 'assets', 'contact-sheet.png')), ROOT))
