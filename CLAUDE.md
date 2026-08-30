# PeachUNO

Uno a due giocatori con il mazzo illustrato Mochi & Peaches e le regole della casa
di Patrizio e della sua ragazza. Serve a giocare a distanza dal telefono.

Sito statico su GitHub Pages. Nessun backend, nessun account, nessun build step
per pubblicare: si carica `index.html` e basta.

## Regola numero uno

**`index.html` deve restare un unico file autosufficiente.** Niente bundler,
niente `node_modules`, niente file esterni: HTML, CSS, JavaScript e tutte le 60
immagini delle carte (base64 inline) stanno lì dentro. È la ragione per cui il
file pesa ~460 KB, ed è voluto: si scarica una volta e resta in cache.

Le uniche risorse esterne sono i font di Google, con fallback di sistema se non
caricano.

## Struttura

```
index.html             il gioco: unico file da pubblicare
grid/                  le quattro foto originali del mazzo (sheet-a … sheet-d)
assets/cards/          le 62 carte ritagliate, una per file: si possono ritoccare a mano
assets/contact-sheet.png  provino di tutte le carte, per controllarle a colpo d'occhio
assets/assets.json     le stesse carte compresse (rigenerabile, non è una sorgente)
tools/cut_cards.py     ritaglia le carte dai fogli e riempie assets/cards/
tools/build_cards.py   prende assets/cards/ e lo reinietta in index.html
tools/test_game.py     due browser finti che giocano una partita intera
tools/test_rules.py    le regole della casa, una per una, a stato forzato
tools/fake_relay.py    il relay finto in memoria che i due test si scambiano
```

Le carte stanno in `index.html` in base64 perché lo impone la regola numero uno,
ma **la sorgente da cui guardare e modificare è `assets/cards/`**: un PNG per
carta, con il nome della carta. Quello dentro l'HTML è solo il risultato
compilato.

## Le regole della casa

Non sono l'Uno standard. Vengono dal mazzo di carta che i due giocano dal vivo,
quindi **non "correggerle" verso le regole ufficiali.**

- **NO!** (simbolo divieto, la carta che nell'Uno normale è "salta turno"). Fa
  saltare il turno all'avversaria, come al solito. In più può essere giocata
  **fuori turno** per annullare l'effetto di una carta speciale appena giocata.
  Chi annulla ci rimette il proprio turno: la carta NO! finisce sugli scarti (e
  ne cambia il colore) e rigioca chi aveva lanciato la speciale.
  **Anche un NO! si annulla con un NO!**, e si va avanti finché a una delle due
  restano NO! in mano. Alla fine conta solo la parità: un numero **dispari** di
  NO! lascia annullata la carta di partenza, uno **pari** la fa valere lo stesso.
- **Rivela** (i gatti col maglione, che nell'Uno normale sarebbe "cambio giro").
  Non inverte niente. Chi la gioca sceglie **al buio** una posizione nella mano
  avversaria: quella carta resta scoperta per lui da lì in avanti.
- **Armageddon** (angelo e diavolo insieme, sfondo scuro, ×2 nel mazzo). Chi la
  gioca mette Angioletto e Diavoletto coperti, uno davanti a sé e uno davanti
  all'altra, e **sceglie lui quale va dove**: l'altra vede due carte girate e
  basta, quindi il bluff è tutto lì. Poi l'altra ne sceglie uno. Chi si ritrova il **Diavoletto pesca 8
  carte**, chi ha l'**Angioletto sceglie il colore**. Poi le due carte tornano da
  parte. **Angioletto e Diavoletto non sono nel mazzo**, sono due segnalini
  riusati a ogni Armageddon.
- **Giullare** (×2 nel mazzo). Vale come qualunque carta numero di qualunque
  colore: chi la gioca dichiara numero e colore.
- **UNO**: 5 secondi per dirlo, poi peschi 2. La penalità **scatta da sola alla
  scadenza**, non serve che l'altra se ne accorga: il pulsante "Beccala!" serve
  solo ad anticiparla mentre i secondi corrono. Ad applicarla è il telefono
  dell'**altra** (così non basta chiudere l'app per non pescare); se lei ha il
  telefono in tasca ci pensa il battito, con qualche secondo di ritardo.
  Il tasto giallo dell'altra però **si arma solo dopo un secondo**
  (`UNO_GRACE`): senza quella pausa lei ti becca prima che tu abbia visto
  comparire il tuo tasto. Il secondo di grazia lo controlla `catchable()`, che
  è la stessa funzione usata dal render e dall'handler del click — così il
  tasto non può comparire prima di quando la mossa è accettata.
- **Non si chiude con una carta azione.** Se ti resta una carta sola e non è un
  numero, quella carta **non si può giocare**: te la tieni e peschi finché non
  esce un numero. Vale per NO!, Rivela, +2, +4, Jolly, Armageddon **e anche per
  il Giullare**, che per tutto il resto conta come carta numero. Vale pure fuori
  turno: non si chiude annullando con un NO!, quindi se a lei resta solo quello
  la contesa non si apre nemmeno (`canSayNo`).
- **Numeri uguali insieme** (opzionale, `S.opts.sameNum`). Quando cali un numero
  puoi accodare gli altri numeri uguali che hai in mano: quanti vuoi, anche
  nessuno — non sei obbligata a calarli tutti. Il colore lo decide l'ultima
  carta del mucchietto e **l'effetto si applica una volta sola** (due sette con
  la 7-0 accesa scambiano le mani una volta, non due, che sarebbe come non
  scambiarle). È una fase, `S.phase = {t:'chain', by, rank, n}`, e ci entra
  solo il `kind === 'num'`: **il Giullare resta fuori dal mucchietto** anche
  se dichiara quel numero — confermato da Patrizio, non rimetterlo in
  discussione.
- **Pescare**: si tocca il mazzo, **una volta sola per turno**, e poi decidi tu.
  Il turno non si chiude da solo nemmeno se la carta pescata è inutile: puoi
  giocare quella, oppure un'altra che avevi già, oppure passare con il tasto
  **Passa**.

Mazzo: 108 carte classiche + 2 Armageddon + 2 Giullare = **112**.

Tre punti che ho deciso io e che vanno confermati con Patrizio prima di
darli per buoni:

1. Nell'Armageddon lui ha descritto solo il caso in cui l'avversaria pesca il
   Diavoletto. Ho implementato la versione simmetrica (se pesca l'Angioletto,
   sceglie lei il colore e l'altro pesca 8), altrimenti la scelta non sarebbe
   una scommessa.
2. Che annullare con il NO! costi il turno è una mia scelta.
3. Che la catena di NO! si risolva a parità (dispari annulla, pari no) è una mia
   scelta: lui ha detto solo che un NO! si può negare con un NO!.

Un punto che invece **è stato confermato** e non va rimesso in discussione: dopo
aver pescato si può giocare **qualunque** carta giocabile, non solo quella
appena pescata. L'Uno normale direbbe il contrario; qui no.

Il **Giullare dichiarato come 7 o 0** con la regola 7-0 accesa **non** fa
scambiare le mani (lo scambio guarda `c.rank`, che il Giullare non ha):
confermato da Patrizio, va lasciato così.

Le regole opzionali (cumulo +2/+4, pesca finché non puoi, 7-0, il NO! che ferma
anche le carte pesca, carte speciali sì/no) si accendono nella lobby e vivono in
`S.opts`.

Sulla **7-0** c'è una trappola già presa una volta: lo scambio delle mani va
fatto **solo se a chi gioca restano carte**. Chiudendo con un 7 (o uno 0) lo
scambio metteva in mano al vincitore la mano piena dell'altra e all'altra la
mano vuota: nessuna delle due chiudeva più, `endTurn` non vedeva mai una mano a
zero e la partita si piantava lì.

## Come sono fatte le carte

`CARDS` è una lista fissa costruita all'avvio: l'indice in quella lista **è**
l'identità della carta. Mani, mazzo, scarti e carte rivelate sono array di
interi. Questo tiene lo stato piccolo abbastanza da stare in un solo messaggio
(vedi sotto) e rende `revealed` banale da gestire.

Ogni carta è **l'immagine intera ritagliata dal foglio**, non una ricostruzione.
Un tentativo precedente disegnava la cornice in CSS (rettangolo colorato, ovale
bianco, numeri agli angoli) e ci incollava sopra il solo gattino scontornato: il
ritaglio prendeva il rettangolo di ingombro del personaggio, che non coincide
con la sua posizione dentro l'ovale, e i gatti venivano fuori spostati e
tagliati. **Non rifarlo.** Se serve una carta nuova, si ritaglia dal foglio.

Il ritaglio è in due passaggi, apposta: **`cut_cards.py` legge i fogli e riempie
`assets/cards/`, `build_cards.py` legge solo `assets/cards/`.** Così puoi aprire
un PNG, sistemartelo a mano, e rimetterlo nel gioco senza che il ritaglio
automatico te lo ricalpesti.

```
cd tools && python3 cut_cards.py       # fogli → assets/cards/  (pillow, numpy, scipy)
cd tools && python3 build_cards.py     # assets/cards/ → index.html  (pillow)
```

`cut_cards.py` scrive **solo le carte che mancano**: quelle già in
`assets/cards/` le lascia stare, così i ritocchi a mano sopravvivono. Per rifare
tutto da capo serve `--force`. Stampa quante carte ha trovato: devono essere 62 e
"mancanti: nessuna". Riscrive anche `assets/contact-sheet.png`, che è il modo
più veloce per accorgersi di un ritaglio storto.

**I fogli non sono una griglia regolare**, ed è questo il punto delicato. Le
carte sono scansionate storte di qualche pixel, i margini fra una e l'altra
cambiano, e su alcuni fogli restano le linee guida della stampa. Un tentativo
precedente divideva l'immagine in sedici rettangoli uguali: tagliava via un pezzo
di carta da una parte e faceva entrare la vicina dall'altra. **Non rifarlo.**
Adesso ogni carta viene *trovata*: si marca tutto quello che non è carta bianca,
si prendono le isole di pixel collegate e si tengono quelle grandi quanto una
carta (~298×464). Le linee guida sono sottili e si scartano da sole; se una tocca
il bordo di una carta, si taglia guardando quali righe e colonne dell'isola sono
piene quasi per intero. Se un foglio non dà esattamente 16 carte lo script si
ferma invece di indovinare.

Il colore di ogni carta lo decide `colour_of` **contando i pixel** vicini ai
quattro colori di riferimento: nei fogli l'ordine dei colori cambia da riga a
riga, quindi non si può scrivere a mano.

Tutte le carte escono a **298×464**, ed è la stessa proporzione che `.card` usa
nel CSS (`aspect-ratio:.642`). Le due cose vanno tenute insieme: `.card` ha
`object-fit:cover`, quindi se le immagini hanno una proporzione diversa dal
riquadro è il browser a ritagliarle — ed è un ritaglio che nel provino non si
vede. Anche `border-radius:7.5%/4.8%` è preso dagli angoli stampati sulle carte
vere.

## Come si parlano i due telefoni

Non c'è un server. Si usa **ntfy.sh**, un servizio pubblico di messaggistica che
non chiede registrazione. La riga `const RELAY = 'ntfy.sh'` in cima allo script è
l'unico punto da cambiare per usarne un altro.

- **Si pubblica** con una `fetch` POST normale. ntfy risponde con
  `Access-Control-Allow-Origin: *`, e il corpo è testo semplice senza header
  aggiunti, quindi è una richiesta "simple" e il browser non fa il preflight.
  **La risposta va letta**: è l'unico modo per accorgersi di un 429 (vedi la
  quota, qui sotto).
- **Si ascolta** con una WebSocket (`wss://ntfy.sh/<topic>/ws?since=10h`), che ai
  CORS non è soggetta.
- Ogni messaggio è **lo stato completo della partita** in JSON (~1 KB). Vince
  sempre la versione più alta (`S.v`, a parità `ts`, poi l'id del mittente), quindi
  una mossa persa si ricuce da sola.
- Il topic è `peachuno-<codice>` con il codice a 4 caratteri che vedono i
  giocatori. Siccome 4 caratteri sono pochi, dentro ogni messaggio c'è anche
  `S.gid`, un identificativo lungo: chi entra sceglie la partita con `ts` più
  recente e ignora tutto il resto, così una vecchia partita ancora in cache sullo
  stesso codice non disturba.
- **Battito**: se per 9 secondi non passa niente si manda un messaggino con il
  solo numero di versione; chi è avanti rimanda la partita intera. Senza questo,
  una mossa persa lascerebbe i due telefoni fermi ad aspettarsi a vicenda.

### Non c'è un relay solo: ce ne sono tre, e si usano tutti insieme

`RELAYS` in cima al blocco `Net`. Ogni messaggio esce su **tutti**, e si
ascoltano **tutti**. Sembra uno spreco ed è invece la cosa che ha reso il gioco
usabile davvero.

Con il solo `ntfy.sh` non funzionava: regala 250 messaggi ogni 12 ore **contati
per indirizzo IP**, e sui dati mobili l'indirizzo è condiviso con mezzo
operatore (CGNAT), quindi quei 250 se li mangiavano degli sconosciuti. Non c'era
niente da svuotare, e **cambiare rete non serviva** perché anche l'altra rete è
condivisa. Le istanze pubbliche che usiamo adesso danno da 17.280 a un milione
di messaggi ogni 12 ore, e una partita intera ne costa un centinaio.

Se un relay è pieno, giù, o sparisce, gli altri portano avanti la partita e non
te ne accorgi. Il pallino diventa rosso solo se **nessuno** dei tre accetta.

Due cose da non rompere:

1. **Le copie vanno buttate.** Lo stesso messaggio arriva una volta per relay.
   `onRemote` tiene una firma (`gid|by|v|ts`) delle ultime 24 e scarta i doppioni:
   senza, ogni ricucitura partiva in triplice copia — tre `push`, tre battiti — e
   due telefoni disallineati si tiravano dietro una valanga invece di rimettersi
   in pari. La ritrasmissione di uno stato **già visto** si scarta ed è giusto
   così; quella di uno stato **mai arrivato** passa, ed è quella che ricuce.
2. **Il battito continua a rallentare da solo** (`BEAT` 9→20→45→90→180 s,
   `INVITE` 15→30→60→120 s, azzerati da una mossa vera, uno stato nuovo o un
   topic nuovo). Un battito con la stessa versione rinfresca `lastSync` ma
   **non** azzera `beatStep`, se no i due telefoni si tengono svegli a vicenda.

Sono istanze tenute su da volontari. Se una muore si toglie dalla lista; per
trovarne un'altra serve `messages` alto in `curl https://<host>/v1/account`,
`Access-Control-Allow-Origin: *` sulla POST e la WebSocket su
`wss://<host>/<topic>/ws` che risponde `101`.

**Limite da rispettare: 4096 byte per messaggio.** Oggi il più grande misura
~1 KB, ma se aggiungi campi allo stato controlla che il test lo stampi ancora
sotto soglia. `Net.send` rifiuta i messaggi oltre 3900 byte.

Lo stato locale sta in `localStorage` (`uno_me`, `uno_game`), così si riprende
una partita riaprendo il sito.

## Pubblicare

Si pubblica con un `git push` sul ramo `main`: GitHub Pages serve il repo così
com'è, non c'è niente da compilare. La pagina è
<https://mosk0vich314.github.io/Peachuno/>.

**Il problema non è pubblicare, è la cache.** GitHub Pages manda l'HTML con
`Cache-Control: max-age=600`, quindi per una decina di minuti il vecchio file
resta valido; e se il sito è stato aggiunto alla schermata Home dell'iPhone
(`apple-mobile-web-app-capable` è acceso) può restarci molto più a lungo. Siccome
il gioco è un unico file, "vecchio file" vuol dire *tutto* vecchio: regole,
carte, interfaccia.

Per questo c'è `const VERSION` in cima allo script, che si legge nel menu della
partita: **va cambiata a ogni pubblicazione**, ed è il modo per capire al volo se
i due telefoni stanno girando la stessa versione. Il pulsante **Aggiorna il
gioco** nel menu ricarica con una query sempre diversa
(`?r=<timestamp>`), che è un indirizzo che la cache non ha mai visto: è la via
sicura per farsi ridare il file per intero senza svuotare la cache a mano.
L'hash `#g=…` viene mantenuto, quindi non si perde la partita in corso.

## Struttura del codice in index.html

Nell'ordine, dentro l'unico `<script>`:

1. `RELAY`, `ASSETS_RAW`/`ART` (le immagini), costanti dei colori e dei nomi
2. `CARDS` — la lista fissa del mazzo
3. utility, `store` (localStorage)
4. `Net` — WebSocket + pubblicazione
5. stato: `ME`, `S`, `myIdx()`, `isMine()`
6. **motore**: `playable`, `playFromHand`, `applyCard`, `doDraw`, `passDraw`,
   `endTurn`, `settleCancel`, `resolveCancel/ArmaPlace/Arma/ArmaColor/Reveal`
7. `commit(fn)` — applica la mossa allo stato locale, incrementa `S.v`, salva e
   pubblica. **Ogni modifica di stato passa da qui.** Se `fn` ritorna `false` la
   mossa è rifiutata e non si pubblica niente.
8. `onRemote` — stato in arrivo, confronto versioni, ricucitura
9. render: `cardHTML`, `render`, `renderPhase`, `renderLobby`, `renderRules`
10. handler dei click, `boot()`

Le mosse che richiedono più passaggi (annullare con il NO!, posare i due
segnalini dell'Armageddon e poi sceglierne uno, scegliere il colore con
l'Angioletto, scegliere quale carta rivelare) sono modellate come **fasi**:
`S.phase = {t:'cancel'|'armaPlace'|'arma'|'armaColor'|'reveal', …}`.
La fase `cancel` si porta dietro `orig`/`origBy`/`choice` (la carta contestata) e
`depth` (quanti NO! sono stati giocati finora), perché la catena di NO! si
risolve alla fine guardando la parità di `depth`.
`S.drawn` è la carta appena pescata, e vuol dire "in questo turno ho già
pescato": finché non è `null` il turno non è finito e `doDraw` rifiuta una
seconda pescata, ma **non limita più cosa puoi giocare**. Finché c'è una fase attiva il turno non avanza e
`playable()` ritorna sempre `false`. Chi deve agire è indicato dentro la fase,
non da `S.turn`.

## Test

```
cd tools && python3 test_game.py       # richiede playwright + chromium
cd tools && python3 test_rules.py
```

`test_game.py` guarda la **sincronizzazione**: apre due browser separati (due
telefoni), sostituisce WebSocket e `fetch` con un relay finto in memoria
(`fake_relay.py`), e verifica:

- ingresso digitando il codice, avvio, **partita intera** giocata a mosse casuali
- che i due stati restino identici fino alla fine
- **caduta di connessione**: si stacca la socket di uno, l'altro continua, alla
  riconnessione deve riallinearsi
- **mossa persa**: si butta via un messaggio in volo e si controlla che il
  battito ricuci da solo
- **traffico da fermi**: sessanta secondi senza toccare niente, partendo dal caso
  peggiore (battito appena azzerato), contando quanti messaggi partono. Il tetto
  è 8: col vecchio battito fisso erano una quindicina. È la prova che tiene
  lontana la quota di ntfy, quindi se la tocchi sappi cosa stai facendo.
- **relay pieno**: il relay finto risponde 429 (`FULL['on']`) e il gioco deve
  diventare rosso e dirlo, poi tornare verde da solo quando il relay riparte

Stampa anche la dimensione del messaggio più grande. Va fatto girare dopo ogni
modifica al motore, allo stato o al battito.

`test_rules.py` guarda invece le **regole**, ed è lì che va aggiunta una prova
quando si tocca il motore. Una partita a mosse casuali non garantisce niente su
una regola precisa (magari quella carta non è mai uscita), quindi ogni prova si
costruisce lo stato che le serve con `commit(s => { ... })` da `page.evaluate`,
fa la mossa e controlla il risultato. Oggi copre: pescare col mazzo e giocare la
carta pescata (o passare), la catena di NO! a uno e a due, e l'Armageddon con
tutte e due le scelte di posa.

Quello che il test **non** copre: la connessione vera a ntfy.sh. Quella si
verifica solo aprendo il sito in due; se il pallino in alto resta rosso, il
problema è lì.

## Convenzioni

- Interfaccia e commenti **in italiano**, tono discorsivo, dando del tu.
- L'avversaria è "lei" nei testi: il gioco è pensato per loro due.
- Palette: viola notturno di fondo, rosa cipria per i pulsanti, le carte fanno
  il colore. I quattro colori del mazzo sono verde / rosa / arancione / blu
  (non c'è il giallo).
- `.pad` usa `justify-content: safe center`: con `center` normale, quando il
  contenuto è più alto dello schermo la parte in cima diventa irraggiungibile.

## Idee non ancora fatte

- Suoni e vibrazione a ogni mossa
- Punteggio cumulativo fra una partita e l'altra
- Notifica push quando tocca a te (ntfy le supporta, ma vuole il permesso del
  browser e su iOS funziona solo se il sito è aggiunto alla schermata Home)
- Un modo per rigiocare la mano precedente / annullare l'ultima mossa
