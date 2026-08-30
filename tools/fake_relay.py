"""Il relay finto che i due browser di prova si scambiano al posto di ntfy.sh.

Sostituisce WebSocket e fetch dentro la pagina con un bus in memoria, cosi' i
test girano senza rete. Lo usano test_game.py (sincronizzazione) e
test_rules.py (le regole della casa).
"""

import os

BUS = {}          # topic -> lista di messaggi
DROP = {'n': 0}   # quante prossime pubblicazioni buttare via, per il test della mossa persa
FULL = {'on': False}   # il relay ha finito i messaggi: risponde 429 a tutto


def pub(t, m):
    """Restituisce il codice di stato, come fa ntfy: 200, oppure 429 a quota finita."""
    if FULL['on']:
        return 429
    if DROP['n'] > 0:
        DROP['n'] -= 1
        return 200
    BUS.setdefault(t, []).append(m)
    return 200


def sub(t, i):
    return BUS.get(t, [])[i:]


def reset():
    BUS.clear()
    DROP['n'] = 0
    FULL['on'] = False


FILE = 'file://' + os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'index.html')

STUB = """
class FakeWS {
  constructor(url){
    this.url = url; this.readyState = 0;
    this.topic = url.match(/\\/\\/[^/]+\\/([^/]+)\\/ws/)[1];
    this.idx = 0;
    setTimeout(() => { this.readyState = 1; if (this.onopen) this.onopen(); this.loop() }, 30);
  }
  async loop(){
    while (this.readyState === 1){
      const arr = await window.__sub(this.topic, this.idx);
      for (const m of arr){
        this.idx++;
        if (this.onmessage) this.onmessage({data: JSON.stringify({event:'message', topic:this.topic, message:m})});
      }
      await new Promise(r => setTimeout(r, 100));
    }
  }
  close(){ this.readyState = 3; if (this.onclose) this.onclose() }
}
window.WebSocket = FakeWS;
const _f = window.fetch;
window.fetch = (url, opt) => {
  if (typeof url === 'string' && url.indexOf('ntfy.sh') >= 0 && opt && opt.method === 'POST'){
    // il gioco legge lo stato della risposta per accorgersi del 429: qui glielo diamo
    return window.__pub(url.split('/').pop(), opt.body).then(st => new Response('', {status: st || 200}));
  }
  return _f(url, opt);
};
"""


def mk(ctx, url):
    pg = ctx.new_page()
    pg.expose_function('__pub', pub)
    pg.expose_function('__sub', sub)
    pg.add_init_script(STUB)
    pg.goto(url)
    pg.set_viewport_size({'width': 390, 'height': 844})
    pg.wait_for_timeout(500)
    return pg


def two_players(b, names=('Patrizio', 'Giulia')):
    """Due telefoni, la partita creata dal primo e il secondo entrato col codice."""
    A = mk(b.new_context(viewport={'width': 390, 'height': 844}), FILE)
    A.fill('#nameIn', names[0]); A.click('#btnGo'); A.wait_for_timeout(900)
    code = A.evaluate('S.code')
    B = mk(b.new_context(viewport={'width': 390, 'height': 844}), FILE)
    B.fill('#nameIn', names[1]); B.fill('#codeIn', code.lower()); B.click('#btnJoin')
    B.wait_for_timeout(4000); A.wait_for_timeout(800)
    return A, B, code
