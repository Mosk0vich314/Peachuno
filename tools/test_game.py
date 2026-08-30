from playwright.sync_api import sync_playwright
from fake_relay import BUS, DROP, FULL, STUB, FILE, mk

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

    # ── quanto chiacchierano stando fermi ───────────────────────────────────
    # ntfy.sh regala 250 messaggi ogni 12 ore per indirizzo IP, e se siete sullo
    # stesso wifi l'IP è uno solo. Col battito fisso a ~8 secondi erano quindici
    # messaggi al minuto per guardarsi la mano: la quota finiva in venti minuti
    # e la partita moriva senza dirlo. Qui si misura da fermi, partendo dal caso
    # peggiore (battito appena azzerato, come subito dopo una mossa).
    print('--- traffico da fermi ---')
    IDLE, TETTO = 60, 8
    for pg in (A, B):
        pg.evaluate('() => { beatStep = 0; lastSync = Date.now(); lastPing = Date.now() }')
    prima = len(BUS[topic])
    A.wait_for_timeout(IDLE * 1000)
    spesi = len(BUS[topic]) - prima
    print('%d messaggi in %d secondi da fermi (tetto %d, col battito fisso erano ~15)'
          % (spesi, IDLE, TETTO))
    assert spesi <= TETTO, 'il battito è tornato a chiacchierare: %d messaggi' % spesi
    print('quota ntfy: %.0f minuti di partita ferma prima dei 250 messaggi'
          % (250.0 / max(spesi, 1) * IDLE / 60))

    # ── il relay che dice di no non deve restare invisibile ─────────────────
    # Era questo il guasto vero: la POST in `no-cors` non lasciava leggere il
    # 429, il pallino guardava solo la WebSocket (e ricevere non costa niente),
    # quindi il gioco restava verde e buttava via ogni mossa in silenzio.
    print('--- relay pieno (429) ---')
    FULL['on'] = True
    A.evaluate('() => push()'); A.wait_for_timeout(800)
    rosso = A.evaluate("() => document.querySelector('#netdot2').classList.contains('off')")
    print('Net.full:', A.evaluate('Net.full'), '| pallino rosso:', rosso,
          '| avviso:', A.evaluate("() => document.querySelector('#toast').textContent"))
    assert A.evaluate('Net.full') and rosso, 'il 429 è passato inosservato'
    # e quando il relay riparte si torna verde da soli: basta il primo messaggio
    # che passa, quindi anche solo il battito, senza dover toccare niente.
    # da fermi in lobby si deve poter uscire dal guaio: l'avviso dice cosa fare
    # e il tasto per ricaricare c'e' anche li' (il menu con la ☰ vive solo
    # dentro la partita, quindi in lobby non era raggiungibile)
    print('avviso in lobby:', A.evaluate("() => document.querySelector('#netWarn').textContent.slice(0, 60)"))
    assert 'wifi' in A.evaluate("() => document.querySelector('#netWarn').textContent"), 'avviso quota assente'
    assert A.evaluate("() => !!document.querySelector('#btnUpdateLobby')"), 'in lobby manca Aggiorna il gioco'
    FULL['on'] = False
    A.evaluate('() => push()'); A.wait_for_timeout(800)
    print('relay di nuovo libero → Net.full:', A.evaluate('Net.full'),
          '| pallino verde:', not A.evaluate("() => document.querySelector('#netdot2').classList.contains('off')"))
    assert not A.evaluate('Net.full'), 'resta bloccato anche quando il relay riparte'

    b.close()
print('FATTO')
