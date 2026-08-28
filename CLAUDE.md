# PeachUNO

Uno a due giocatori con il mazzo illustrato Mochi & Peaches e le regole della casa
di Patrizio e della sua ragazza. Serve a giocare a distanza dal telefono.

Sito statico su GitHub Pages. Nessun backend, nessun account, nessun build step
per pubblicare: si carica `index.html` e basta.

## Regola numero uno

**`index.html` deve restare un unico file autosufficiente.** Niente bundler,
niente `node_modules`, niente file esterni: HTML, CSS, JavaScript e tutte le 60
immagini delle carte (base64 inline) stanno lì dentro. È la ragione per cui il
file pesa ~430 KB, ed è voluto: si scarica una volta e resta in cache.

Le uniche risorse esterne sono i font di Google, con fallback di sistema se non
caricano.

## Struttura

```
index.html          il gioco: unico file da pubblicare
sheets/             le quattro foto originali del mazzo (griglie 4×4)
tools/build_cards.py   ritaglia le carte dai fogli e le reinietta in index.html
tools/test_game.py     due browser finti che giocano una partita intera
tools/assets.json      immagini estratte (rigenerabile, non è una sorgente)
```

## Le regole della casa

Non sono l'Uno standard. Vengono dal mazzo di carta che i due giocano dal vivo,
quindi **non "correggerle" verso le regole ufficiali.**

- **NO!** (simbolo divieto, la carta che nell'Uno normale è "salta turno"). Fa
  saltare il turno all'avversaria, come al solito. In più può essere giocata
  **fuori turno** per annullare l'effetto di una carta speciale appena giocata.
  Chi annulla ci rimette il proprio turno: la carta NO! finisce sugli scarti (e
  ne cambia il colore) e rigioca chi aveva lanciato la speciale.
- **Rivela** (i gatti col maglione, che nell'Uno normale sarebbe "cambio giro").
  Non inverte niente. Chi la gioca sceglie **al buio** una posizione nella mano
  avversaria: quella carta resta scoperta per lui da lì in avanti.
- **Armageddon** (angelo e diavolo insieme, sfondo scuro, ×2 nel mazzo). Chi la
  gioca mette Angioletto e Diavoletto coperti, uno davanti a sé e uno davanti
  all'altra. L'altra ne sceglie uno. Chi si ritrova il **Diavoletto pesca 8
  carte**, chi ha l'**Angioletto sceglie il colore**. Poi le due carte tornano da
  parte. **Angioletto e Diavoletto non sono nel mazzo**, sono due segnalini
  riusati a ogni Armageddon.
- **Giullare** (×2 nel mazzo). Vale come qualunque carta numero di qualunque
  colore: chi la gioca dichiara numero e colore.
- **UNO**: 5 secondi per dirlo, poi l'altra può beccarti e ti fa pescare 2.

Mazzo: 108 carte classiche + 2 Armageddon + 2 Giullare = **112**.

Due punti che ho deciso io e che vanno confermati con Patrizio prima di
darli per buoni:

1. Nell'Armageddon lui ha descritto solo il caso in cui l'avversaria pesca il
   Diavoletto. Ho implementato la versione simmetrica (se pesca l'Angioletto,
   sceglie lei il colore e l'altro pesca 8), altrimenti la scelta non sarebbe
   una scommessa.
2. Che annullare con il NO! costi il turno è una mia scelta.

Le regole opzionali (cumulo +2/+4, pesca finché non puoi, 7-0, il NO! che ferma
anche le carte pesca, carte speciali sì/no) si accendono nella lobby e vivono in
`S.opts`.

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

`tools/build_cards.py` fa tutto: ogni foto è una griglia 4×4, ritaglia le 16
celle, toglie il margine bianco e il filetto nero, e riconosce il colore di ogni
carta **contando i pixel** vicini ai quattro colori di riferimento (nei fogli
l'ordine dei colori cambia da riga a riga, quindi non si può scriverlo a mano).
Poi scrive `assets.json` e lo reinietta nella riga `const ASSETS_RAW = …` di
`index.html`.

```
cd tools && python3 build_cards.py     # richiede pillow, numpy, scipy
```

Stampa quante carte ha estratto e quali mancano: devono essere 62 e "mancanti:
nessuna".

## Come si parlano i due telefoni

Non c'è un server. Si usa **ntfy.sh**, un servizio pubblico di messaggistica che
non chiede registrazione. La riga `const RELAY = 'ntfy.sh'` in cima allo script è
l'unico punto da cambiare per usarne un altro.

- **Si pubblica** con `fetch(..., {mode:'no-cors'})`: la risposta non si può
  leggere, ma così i CORS non c'entrano niente.
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
  Mentre si è in lobby in attesa dell'ospite si ripubblica lo stato intero ogni
  12 secondi, così l'invito non scade.

**Limite da rispettare: 4096 byte per messaggio.** Oggi il più grande misura
~950 byte, ma se aggiungi campi allo stato controlla che il test lo stampi ancora
sotto soglia. `Net.send` rifiuta i messaggi oltre 3900 byte.

Lo stato locale sta in `localStorage` (`uno_me`, `uno_game`), così si riprende
una partita riaprendo il sito.

## Struttura del codice in index.html

Nell'ordine, dentro l'unico `<script>`:

1. `RELAY`, `ASSETS_RAW`/`ART` (le immagini), costanti dei colori e dei nomi
2. `CARDS` — la lista fissa del mazzo
3. utility, `store` (localStorage)
4. `Net` — WebSocket + pubblicazione
5. stato: `ME`, `S`, `myIdx()`, `isMine()`
6. **motore**: `playable`, `playFromHand`, `applyCard`, `doDraw`, `endTurn`,
   `resolveCancel/Arma/ArmaColor/Reveal`
7. `commit(fn)` — applica la mossa allo stato locale, incrementa `S.v`, salva e
   pubblica. **Ogni modifica di stato passa da qui.** Se `fn` ritorna `false` la
   mossa è rifiutata e non si pubblica niente.
8. `onRemote` — stato in arrivo, confronto versioni, ricucitura
9. render: `cardHTML`, `render`, `renderPhase`, `renderLobby`, `renderRules`
10. handler dei click, `boot()`

Le mosse che richiedono più passaggi (annullare con il NO!, scegliere una delle
due carte dell'Armageddon, scegliere il colore con l'Angioletto, scegliere quale
carta rivelare) sono modellate come **fasi**: `S.phase = {t:'cancel'|'arma'|
'armaColor'|'reveal', …}`. Finché c'è una fase attiva il turno non avanza e
`playable()` ritorna sempre `false`. Chi deve agire è indicato dentro la fase,
non da `S.turn`.

## Test

```
cd tools && python3 test_game.py       # richiede playwright + chromium
```

Apre due browser separati (due telefoni), sostituisce WebSocket e `fetch` con un
relay finto in memoria, e verifica:

- ingresso digitando il codice, avvio, **partita intera** giocata a mosse casuali
- che i due stati restino identici fino alla fine
- **caduta di connessione**: si stacca la socket di uno, l'altro continua, alla
  riconnessione deve riallinearsi
- **mossa persa**: si butta via un messaggio in volo e si controlla che il
  battito ricuci da solo

Stampa anche la dimensione del messaggio più grande. Va fatto girare dopo ogni
modifica al motore o allo stato.

Per provare rapidamente una regola specifica conviene forzare la mano con
`commit(s => { ... })` da `page.evaluate`, come fa il test per pescare carte
precise dal mazzo.

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
