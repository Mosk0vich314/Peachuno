"""Prova le regole della casa una per una, forzando la mano invece di giocare a caso.

test_game.py gioca una partita intera a mosse casuali e guarda che i due telefoni
restino allineati: serve per la sincronizzazione, ma su una regola precisa non ti
da' garanzie (magari quella carta non e' mai uscita). Qui invece ogni prova si
costruisce lo stato che le serve con `commit`, fa la mossa, e controlla il
risultato.

    cd tools && python test_rules.py       # richiede playwright + chromium
"""

import sys

from playwright.sync_api import sync_playwright

from fake_relay import two_players

fails = []


def check(name, got, want):
    ok = got == want
    print(('  ok  ' if ok else '  NO  ') + name + ('' if ok else '\n        ho: %r\n        voglio: %r' % (got, want)))
    if not ok:
        fails.append(name)


def setup(page, js):
    """Forza lo stato della partita e aspetta che arrivi anche all'altro telefono."""
    page.evaluate('() => commit(s => { %s })' % js)
    page.wait_for_timeout(500)


# Chi ha il turno e' sempre A: le prove partono da li'.
FORCE_TURN = """
  s.turn = s.players.findIndex(p => p.name === 'Patrizio');
  s.phase = null; s.pending = 0; s.pendingType = null; s.uno = null; s.drawn = null;
"""


def art(page, name):
    return page.evaluate("() => CARDS.findIndex(c => c.art === '%s')" % name)


with sync_playwright() as p:
    b = p.chromium.launch()

    # ─────────────── pescare e poter giocare la carta pescata ───────────────
    print('\n— pesco e la carta pescata si puo\' giocare —')
    A, B, code = two_players(b)
    A.click('#btnStart'); A.wait_for_timeout(900)
    # in mano solo carte inutili, in cima al mazzo un 5 rosa giocabile
    setup(A, FORCE_TURN + """
      s.discard = [CARDS.findIndex(c => c.art === 'n5_red')]; s.color = 'red';
      s.players[s.turn].hand = ['n9_blue','n8_blue','n4_green'].map(a => CARDS.findIndex(c => c.art === a));
      s.deck.push(CARDS.findIndex(c => c.art === 'n3_red'));
    """)
    check('prima di pescare non ho niente da giocare',
          A.evaluate('() => S.players[S.turn].hand.some(c => playable(c, S))'), False)
    turn_before = A.evaluate('S.turn')
    A.click('#drawPile'); A.wait_for_timeout(600)        # si pesca toccando il mazzo
    check('il mazzo cliccato pesca', A.evaluate('() => S.players[S.turn].hand.length'), 4)
    check('il turno non e\' passato', A.evaluate('S.turn'), turn_before)
    check('la carta pescata e\' segnata', A.evaluate('() => C(S.drawn).art'), 'n3_red')
    check('posso giocare solo quella',
          A.evaluate('() => S.players[S.turn].hand.filter(c => playable(c, S)).map(c => C(c).art)'), ['n3_red'])
    check('non posso pescare due volte', A.evaluate('() => canDraw()'), False)
    A.evaluate('() => commit(s => playFromHand(s, s.turn, s.drawn, null))'); A.wait_for_timeout(600)
    check('giocata la carta pescata', A.evaluate('() => C(S.discard[S.discard.length-1]).art'), 'n3_red')
    check('ora il turno e\' passato', A.evaluate('S.turn'), 1 - turn_before)

    print('\n— pesco, e' + '’' + ' giocabile, ma preferisco tenermela —')
    setup(A, FORCE_TURN + """
      s.discard = [CARDS.findIndex(c => c.art === 'n5_red')]; s.color = 'red';
      s.players[s.turn].hand = ['n9_blue','n8_blue'].map(a => CARDS.findIndex(c => c.art === a));
      s.deck.push(CARDS.findIndex(c => c.art === 'n3_red'));
    """)
    turn_before = A.evaluate('S.turn')
    A.evaluate('() => commit(s => doDraw(s))'); A.wait_for_timeout(400)
    A.evaluate('() => commit(s => passDraw(s))'); A.wait_for_timeout(600)
    check('passando, il turno passa', A.evaluate('S.turn'), 1 - turn_before)
    check('la carta pescata resta in mano', A.evaluate('() => S.players[%d].hand.length' % turn_before), 3)
    check('drawn azzerato', A.evaluate('S.drawn'), None)

    # ─────────────── il NO! che nega un NO! ───────────────
    print('\n— un NO! si nega con un altro NO! —')
    setup(A, FORCE_TURN + """
      s.discard = [CARDS.findIndex(c => c.art === 'n5_red')]; s.color = 'red';
      const no = k => CARDS.map((c,i) => [c,i]).filter(([c]) => c.art === k).map(([,i]) => i);
      s.players[s.turn].hand = [no('skip_red')[0], no('skip_red')[1], CARDS.findIndex(c => c.art === 'n9_blue')];
      s.players[1-s.turn].hand = [no('skip_blue')[0], CARDS.findIndex(c => c.art === 'n8_green')];
    """)
    a_idx = A.evaluate('S.turn')
    A.evaluate("() => commit(s => playFromHand(s, s.turn, s.players[s.turn].hand[0], null))")
    A.wait_for_timeout(600)
    check('giocare un NO! apre la contesa', A.evaluate('() => S.phase && S.phase.t'), 'cancel')
    check('la contesa parte da zero', A.evaluate('() => S.phase.depth'), 0)
    check('tocca rispondere a lei', A.evaluate('() => S.phase.by'), a_idx)
    # lei annulla con il suo NO!
    B.evaluate("() => commit(s => resolveCancel(s, s.players[1-s.phase.by].hand.find(c => C(c).kind === 'skip')))")
    B.wait_for_timeout(700)
    check('dopo il suo NO! tocca a lui rilanciare', A.evaluate('() => S.phase && [S.phase.t, S.phase.depth, S.phase.by]'),
          ['cancel', 1, 1 - a_idx])
    # lui rilancia con il secondo NO!: due NO! -> il primo vale lo stesso
    A.evaluate("() => commit(s => resolveCancel(s, s.players[1-s.phase.by].hand.find(c => C(c).kind === 'skip')))")
    A.wait_for_timeout(700)
    check('con due NO! la contesa e\' chiusa', A.evaluate('() => S.phase'), None)
    check('il NO! di partenza vale: turno saltato, rigioca lui', A.evaluate('S.turn'), a_idx)
    check('tre carte sugli scarti oltre alla prima', A.evaluate('() => S.discard.length'), 4)

    print('\n— un solo NO! annulla davvero —')
    setup(A, FORCE_TURN + """
      s.discard = [CARDS.findIndex(c => c.art === 'n5_red')]; s.color = 'red';
      s.opts.specials = true;
      s.players[s.turn].hand = [CARDS.findIndex(c => c.kind === 'duel'), CARDS.findIndex(c => c.art === 'n9_blue')];
      s.players[1-s.turn].hand = [CARDS.findIndex(c => c.art === 'skip_blue'), CARDS.findIndex(c => c.art === 'n8_green')];
    """)
    a_idx = A.evaluate('S.turn')
    n_before = A.evaluate('() => S.players[1-S.turn].hand.length')
    A.evaluate("() => commit(s => playFromHand(s, s.turn, s.players[s.turn].hand[0], null))")
    A.wait_for_timeout(600)
    B.evaluate("() => commit(s => resolveCancel(s, s.players[1-s.phase.by].hand.find(c => C(c).kind === 'skip')))")
    B.wait_for_timeout(700)
    check('Armageddon annullato: nessuna fase aperta', A.evaluate('() => S.phase'), None)
    check('rigioca chi aveva lanciato la speciale', A.evaluate('S.turn'), a_idx)
    check('nessuno ha pescato 8', A.evaluate('() => S.players[%d].hand.length' % a_idx), 1)

    # ─────────────── Armageddon: il bluff ───────────────
    print('\n— Armageddon: decido io quale segnalino le metto davanti —')
    setup(A, FORCE_TURN + """
      s.discard = [CARDS.findIndex(c => c.art === 'n5_red')]; s.color = 'red';
      s.opts.specials = true;
      s.players[s.turn].hand = [CARDS.findIndex(c => c.kind === 'duel'), CARDS.findIndex(c => c.art === 'n9_blue')];
      s.players[1-s.turn].hand = [CARDS.findIndex(c => c.art === 'n8_green')];
    """)
    a_idx = A.evaluate('S.turn')
    A.evaluate("() => commit(s => playFromHand(s, s.turn, s.players[s.turn].hand[0], null))")
    A.wait_for_timeout(600)
    check('prima tocca a chi la gioca', A.evaluate('() => S.phase && [S.phase.t, S.phase.by]'), ['armaPlace', a_idx])
    check('lei non puo\' ancora scegliere', B.evaluate('() => S.phase.t'), 'armaPlace')
    # le metto davanti il Diavoletto
    A.evaluate("() => commit(s => resolveArmaPlace(s, 'devil'))"); A.wait_for_timeout(600)
    check('adesso sceglie lei', A.evaluate('() => S.phase.t'), 'arma')
    check('davanti a me l\'Angioletto, davanti a lei il Diavoletto',
          A.evaluate('() => S.phase.slots'), ['angel', 'devil'])
    # lei prende quello che ha davanti (slot 1): e' il Diavoletto, pesca 8
    B.evaluate('() => commit(s => resolveArma(s, 1))'); B.wait_for_timeout(700)
    check('lei ha pescato 8', A.evaluate('() => S.players[%d].hand.length' % (1 - a_idx)), 9)
    check('sceglie il colore chi ha l\'Angioletto', A.evaluate('() => [S.phase.t, S.phase.who]'), ['armaColor', a_idx])

    print('\n— e se lei prende quello davanti a lui, pesco io —')
    setup(A, FORCE_TURN + """
      s.discard = [CARDS.findIndex(c => c.art === 'n5_red')]; s.color = 'red';
      s.opts.specials = true;
      s.players[s.turn].hand = [CARDS.findIndex(c => c.kind === 'duel'), CARDS.findIndex(c => c.art === 'n9_blue')];
      s.players[1-s.turn].hand = [CARDS.findIndex(c => c.art === 'n8_green')];
    """)
    a_idx = A.evaluate('S.turn')
    A.evaluate("() => commit(s => playFromHand(s, s.turn, s.players[s.turn].hand[0], null))"); A.wait_for_timeout(500)
    A.evaluate("() => commit(s => resolveArmaPlace(s, 'devil'))"); A.wait_for_timeout(500)
    B.evaluate('() => commit(s => resolveArma(s, 0))'); B.wait_for_timeout(700)   # prende l'Angioletto
    check('pesca 8 chi resta col Diavoletto', A.evaluate('() => S.players[%d].hand.length' % a_idx), 9)
    check('il colore lo sceglie lei', A.evaluate('() => S.phase.who'), 1 - a_idx)

    # ─────────────── UNO: la penalità scatta da sola ───────────────
    print('\n— non dico UNO entro 5 secondi: pesco 2 —')
    setup(A, FORCE_TURN + """
      s.discard = [CARDS.findIndex(c => c.art === 'n5_red')]; s.color = 'red';
      s.players[s.turn].hand = ['n9_blue','n3_red'].map(a => CARDS.findIndex(c => c.art === a));
      s.players[1-s.turn].hand = [CARDS.findIndex(c => c.art === 'n8_green')];
    """)
    a_idx = A.evaluate('S.turn')
    A.evaluate("() => commit(s => playFromHand(s, s.turn, CARDS.findIndex(c => c.art === 'n3_red'), null))")
    A.wait_for_timeout(700)
    check('con una carta sola parte il conto alla rovescia',
          A.evaluate('() => S.uno && [S.uno.p, S.uno.called]'), [a_idx, False])
    check('resto con una carta sola', A.evaluate('() => S.players[%d].hand.length' % a_idx), 1)
    # nessuno tocca niente: i 5 secondi passano
    A.wait_for_timeout(7000); B.wait_for_timeout(1500); A.wait_for_timeout(1500)
    check('scaduto il tempo ho pescato 2', A.evaluate('() => S.players[%d].hand.length' % a_idx), 3)
    check('la finestra UNO si e\' chiusa', A.evaluate('S.uno'), None)
    check('i due telefoni sono d\'accordo',
          A.evaluate('() => [S.v, S.players.map(p => p.hand.length)]'),
          B.evaluate('() => [S.v, S.players.map(p => p.hand.length)]'))

    print('\n— dico UNO in tempo: non pesco niente —')
    setup(A, FORCE_TURN + """
      s.discard = [CARDS.findIndex(c => c.art === 'n5_red')]; s.color = 'red';
      s.players[s.turn].hand = ['n9_blue','n3_red'].map(a => CARDS.findIndex(c => c.art === a));
      s.players[1-s.turn].hand = [CARDS.findIndex(c => c.art === 'n8_green')];
    """)
    a_idx = A.evaluate('S.turn')
    A.evaluate("() => commit(s => playFromHand(s, s.turn, CARDS.findIndex(c => c.art === 'n3_red'), null))")
    A.wait_for_timeout(400)
    A.evaluate("() => commit(s => { s.uno.called = true; say(s, 'UNO!') })")
    A.wait_for_timeout(7000); B.wait_for_timeout(1200)
    check('detto in tempo, resto con una carta', A.evaluate('() => S.players[%d].hand.length' % a_idx), 1)

    b.close()

print('\n' + ('FATTO: tutto a posto' if not fails else 'FALLITE %d prove: %s' % (len(fails), ', '.join(fails))))
sys.exit(1 if fails else 0)
