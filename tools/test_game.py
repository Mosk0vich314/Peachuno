from playwright.sync_api import sync_playwright
from fake_relay import BUS, DROP, STUB, FILE, mk

with sync_playwright() as p:
    b = p.chromium.launch()
    ctxA = b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    ctxB = b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    A = mk(ctxA, FILE)
    A.fill('#nameIn', 'Patrizio'); A.click('#btnGo'); A.wait_for_timeout(900)
    code = A.evaluate('S.code')
    topic = 'peachuno-' + code.lower()
    print('partita:', code, '| topic:', topic, '| messaggi:', len(BUS.get(topic, [])),
          '| byte del primo messaggio:', len(BUS[topic][0]))
    A.screenshot(path='/tmp/n_invite.png')

    # ingresso digitando il codice, non con il link
    B = mk(ctxB, FILE)
    B.fill('#nameIn', 'Giulia'); B.fill('#codeIn', code.lower()); B.click('#btnJoin')
    B.wait_for_timeout(4000); A.wait_for_timeout(800)
    print('A vede il secondo giocatore:', A.evaluate('S.players[1] && S.players[1].name'))
    print('B è in lobby:', B.evaluate('S && S.status'))
    A.screenshot(path='/tmp/n_lobby.png')

    A.click('#btnStart'); A.wait_for_timeout(900)
    print('avvio → A:', A.evaluate('S.status'), '| B:', B.evaluate('S.status'),
          '| tocca a:', A.evaluate('S.players[S.turn].name'))

    # 40 mosse casuali alternate, con risoluzione delle fasi
    step = """() => {
      if (!S || S.status !== 'playing') return 'fine';
      const mi = myIdx();
      if (S.phase){
        const ph = S.phase;
        if (ph.t === 'cancel' && mi === 1 - ph.by){
          const nos = S.players[mi].hand.filter(c => C(c).kind === 'skip');
          return commit(s => resolveCancel(s, (nos.length && Math.random() < 0.5) ? nos[0] : null)) || 'cancel';
        }
        if (ph.t === 'armaPlace' && mi === ph.by)
          return commit(s => resolveArmaPlace(s, Math.random() < 0.5 ? 'angel' : 'devil')) || 'armaPlace';
        if (ph.t === 'arma' && mi === 1 - ph.by) return commit(s => resolveArma(s, Math.round(Math.random()))) || 'arma';
        if (ph.t === 'armaColor' && mi === ph.who) return commit(s => resolveArmaColor(s, 'blue')) || 'armaColor';
        if (ph.t === 'reveal' && mi === ph.by){
          const h = S.players[1-mi].hand.filter(c => !S.revealed.includes(c));
          if (h.length) return commit(s => resolveReveal(s, h[0])) || 'reveal';
        }
        return 'attendo';
      }
      if (!isMine()) return 'non tocca a me';
      // ho appena pescato: o gioco quella carta o passo
      if (S.drawn != null && Math.random() < 0.35) return commit(s => passDraw(s)) || 'passa';
      const ok = S.players[mi].hand.filter(c => playable(c, S));
      if (!ok.length) return S.drawn != null ? (commit(s => passDraw(s)) || 'passa')
                                             : (commit(s => doDraw(s)) || 'pesca');
      const ci = ok[Math.floor(Math.random()*ok.length)], k = C(ci).kind;
      const ch = k === 'jester' ? {color:'blue', rank:3}
               : (C(ci).color === null && k !== 'duel') ? {color:'blue'} : null;
      return commit(s => playFromHand(s, mi, ci, ch)) || ('gioca ' + k);
    }"""
    for i in range(60):
        for pg in (A, B):
            pg.evaluate(step)
            pg.wait_for_timeout(140)
        if A.evaluate('S.status') == 'over':
            break
    A.wait_for_timeout(600); B.wait_for_timeout(600)
    sizes = [len(m) for m in BUS[topic]]
    print('mosse scambiate:', len(BUS[topic]), '| messaggio più grande:', max(sizes), 'byte (limite 4096)')
    print('stati allineati:', A.evaluate('S.v') == B.evaluate('S.v'),
          '| A:', A.evaluate('[S.v, S.status, S.players.map(p=>p.hand.length)]'),
          '| B:', B.evaluate('[S.v, S.status, S.players.map(p=>p.hand.length)]'))
    A.screenshot(path='/tmp/n_game.png')

    # rivincita, così la prova di riconnessione avviene a partita viva
    if A.evaluate('S.status') == 'over':
        A.evaluate('() => rematch()'); A.wait_for_timeout(700)
        A.click('#btnStart'); A.wait_for_timeout(900)
        for i in range(6):
            for pg in (A, B): pg.evaluate(step); pg.wait_for_timeout(140)
    print('--- test riconnessione ---')
    B.evaluate('() => { Net.ws.readyState = 3; Net.ws = null; Net.topic = null }')
    vB = B.evaluate('S.v')
    for i in range(10):
        A.evaluate(step); A.wait_for_timeout(150)
    print('B congelato a v =', B.evaluate('S.v'), '(era', vB, ') mentre A è a v =', A.evaluate('S.v'))
    B.evaluate('() => { Net.tries = 0; Net.start(topicOf(S.code)) }')
    B.wait_for_timeout(1500)
    print('dopo la riconnessione B è a v =', B.evaluate('S.v'), '| allineato:', A.evaluate('S.v') == B.evaluate('S.v'))

    print('--- test messaggio perso ---')
    # faccio muovere chi ha il turno, poi butto via il messaggio: deadlock finto
    mover = A if A.evaluate('isMine()') else B
    other = B if mover is A else A
    DROP['n'] = 1                      # la prossima pubblicazione sparisce nel nulla
    r = mover.evaluate(step); mover.wait_for_timeout(400)
    other.wait_for_timeout(800)
    vM, vO = mover.evaluate('S.v'), other.evaluate('S.v')
    print('mossa persa (' + str(r) + ') → chi muove v =', vM, ', l\'altro fermo a v =', vO)
    print('attendo il battito…')
    for _ in range(16):
        A.wait_for_timeout(1200); B.wait_for_timeout(1200)
        if A.evaluate('S.v') == B.evaluate('S.v'): break
    print('recuperato:', A.evaluate('S.v') == B.evaluate('S.v'),
          '| A v =', A.evaluate('S.v'), 'B v =', B.evaluate('S.v'),
          '| mani identiche:', A.evaluate('JSON.stringify(S.players.map(p=>p.hand.length))') == B.evaluate('JSON.stringify(S.players.map(p=>p.hand.length))'))
    b.close()
print('FATTO')
