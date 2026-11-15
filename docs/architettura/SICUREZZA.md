# Sicurezza dei server locali

Stato: compiti T-102 e T-103 (rilievi SEC-002, SEC-004, SEC-005, SEC-006, SEC-007, SEC-008, SEC-010, BUG-001…007 di
`docs/audit/AUDIT-2026-11.md`). Codice: `sicurezza.py`, `servizio.py` (classe `Gestore`), `percorsi.py`, `giornale.py`;
prove: `tests/test_sicurezza_server.py`, `tests/test_editor_richieste.py`, `tests/test_foto.py`, `tests/test_interfaccia.py`.

## Da cosa ci si difende

L'Impaginatore apre due server HTTP su `127.0.0.1`: la schermata dei progetti (porta 8765) e un editor per ogni progetto
aperto (8801–8899). Fino alla 2.0 rispondevano a chiunque, con `Access-Control-Allow-Origin: *`. Le minacce considerate:

| Chi | Cosa potrebbe fare | Difesa |
|---|---|---|
| Una pagina web qualsiasi aperta nel browser dell'utente | leggere progetti e percorsi, creare/cancellare progetti, aggiornare il programma, chiuderlo | gettone di sessione, `Origin`/`Sec-Fetch-Site`, niente CORS, solo JSON in POST |
| Un sito che usa il DNS rebinding (un suo nome che risolve in `127.0.0.1`) | tutto quanto sopra, come «stessa origine» | controllo di `Host` |
| Un altro utente dello stesso computer | leggere il gettone da una riga di comando o da un file | gettone mai sulla riga di comando, file di sessione 0600 |
| Dati preparati ad arte: nomi di file, EXIF, nomi di progetti, progetti condivisi | eseguire script nella pagina (XSS), comandi nel sistema (AppleScript, PowerShell) | escaping unico nella pagina, CSP, argomenti al posto del testo degli script |
| Una richiesta con un percorso qualsiasi | elencare `/etc`, mostrare o cestinare file fuori dal progetto, lanciare app con `open -a` | radici consentite |
| File o richieste enormi | esaurire memoria o thread | limiti di corpo, di pixel, di tempo |

## Gettone di sessione (SEC-002)

Ogni server, all'avvio, crea il suo gettone con `secrets.token_urlsafe(32)` (`sicurezza.Sessione`). Schermata ed editor
hanno gettoni diversi. Il confronto è sempre a tempo costante (`hmac.compare_digest`, `sicurezza.uguali`).

Il gettone si presenta in due modi:

1. **Intestazione `X-Impaginatore-Gettone`**: la usano tutte le `fetch` della pagina (funzione `rq` in `index.html` e
   `home.html`) e i client locali. Tutte le API la vogliono.
2. **Cookie `impaginatore_<porta>`** (`HttpOnly; SameSite=Strict; Path=/`): vale solo per le richieste GET della pagina
   (`/`), delle immagini (`/img/…`, `/api/fthumb`, `/api/cover`) e dei rimandi (`/vai/…`), cioè per ciò che il browser
   carica da solo (`<img>`, sfondi CSS, navigazione) e non può portare un'intestazione. Il nome contiene la porta perché i
   cookie non distinguono le porte.

Il cookie si ottiene una volta sola dall'**URL di avvio** `http://127.0.0.1:<porta>/avvio?c=<codice>`: il codice è casuale,
vale una volta e per `DURATA_CODICE` (120 s); il server risponde con il cookie e un rimando 303 a `/`. La pagina servita
contiene il gettone in `<meta name="gettone">` (risposta `no-store`, leggibile solo dalla stessa origine). Chi apre
l'indirizzo nudo senza cookie vede una pagina che spiega come aprire il programma (401), mai i dati.

Chi crea gli URL di avvio: la schermata quando apre il browser (`main`), la schermata per l'editor (`/api/pronto` →
`indirizzo`, a cui la pagina naviga), l'editor per il pulsante «Progetti» (`/vai/progetti` → 303 a un URL di avvio della
schermata), e qualunque client con il gettone (`POST /api/avvio`).

### Perché cookie con URL monouso e non un parametro firmato

- **Parametro firmato** in ogni indirizzo di immagine (`?g=HMAC(...)`): scartato. Va aggiunto a decine di punti del JS
  (anche dentro `url(...)` dei CSS), finisce nella cronologia e nella cache del browser, e basta dimenticarne uno per un
  errore silenzioso. Il cookie viaggia da solo su `<img>` e sfondi.
- **Gettone nell'URL di apertura** (`/?g=<gettone>`): scartato. `webbrowser.open` passa l'URL al browser sulla riga di
  comando (visibile agli altri utenti con `ps`) e l'URL resta nella cronologia. Il codice di avvio invece vale una volta e
  scade: dopo il primo uso non serve più a niente.
- **Cookie senza `SameSite=Strict`**: scartato. Con `Strict` una pagina di un altro sito non può far partire una richiesta
  che porti il cookie, nemmeno con un link o un modulo; in più le API non accettano il cookie, solo l'intestazione.
- **Finestra incorporata (pywebview, T-201)**: funziona allo stesso modo (la finestra apre l'URL di avvio e tiene il
  cookie nel suo archivio); in più può aggiungere l'intestazione da sola. Il motore della finestra (WebKit su macOS,
  WebView2 su Windows) gestisce `SameSite=Strict` e `HttpOnly` come un browser.

Rischio residuo noto: su Linux (e dove `ps` mostra gli argomenti degli altri utenti) il **codice** di avvio compare per un
attimo sulla riga di comando del browser lanciato da `webbrowser.open`. Un altro utente che lo legge e lo usa prima del
browser ottiene il cookie; il browser dell'utente vedrebbe allora «Questa scheda non è collegata». Passo successivo:
aprire il browser su un file HTML temporaneo 0600 che rimanda all'URL di avvio (il codice non tocca più la riga di
comando), oppure la finestra incorporata, dove l'URL non passa da nessun processo esterno.

### Controlli su ogni richiesta (`servizio.Gestore.controlla`)

Prima di arrivare a `do_GET`/`do_POST`, nell'ordine:

1. `Host` deve essere `127.0.0.1:<porta>` o `localhost:<porta>` → 403 (difesa dal DNS rebinding).
2. `Sec-Fetch-Site`, se c'è: per le navigazioni GET si accettano `same-origin`, `same-site`, `none`; per tutto il resto solo
   `same-origin` e `none` → 403. Le due porte di `127.0.0.1` sono «same-site» ma origini diverse: la pagina dell'editor
   non chiama le API della schermata, le chiede al suo server (che usa il gettone della schermata, vedi sotto).
3. `Origin`, se c'è, deve essere l'origine del server stesso → 403.
4. Gettone nell'intestazione, oppure cookie per le GET elencate sopra → 401. Uniche eccezioni: `GET /avvio` (controlla il
   codice) e `GET /favicon.ico` (204 vuoto).
5. Solo POST: `Content-Type: application/json` (415), `Content-Length` presente e senza `Transfer-Encoding` (411), al
   massimo `MAX_CORPO` = 4 MB (413, rifiutato dalla sola intestazione, senza leggere il corpo). Il corpo deve essere un
   oggetto JSON (400).

Nessuna richiesta GET cambia progetti, impostazioni o programma (al più cache in memoria e l'ultima cartella vista). Ogni connessione si chiude dopo 60 s di silenzio
(`Gestore.timeout`). I rifiuti vanno nel registro a livello INFO (metodo, percorso senza la query, motivo).

### Intestazioni di sicurezza

Su tutte le risposte: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
`Cross-Origin-Resource-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin`, `X-Frame-Options: DENY`,
`Permissions-Policy` (niente fotocamera, microfono, posizione). Nessun `Access-Control-Allow-Origin`.

`Content-Security-Policy` delle pagine:

```
default-src 'none'; script-src 'nonce-<nuovo a ogni risposta>'; style-src 'self' 'unsafe-inline'; img-src 'self';
connect-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'
```

Le risposte che non sono pagine hanno `script-src 'none'`. Ogni pagina ha un solo `<script nonce>`; i gestori in linea
(`onclick="…"`) sono stati tolti (la prova `test_intestazioni_di_sicurezza_e_csp` lo controlla).

**`'unsafe-inline'` negli stili** resta perché l'interfaccia usa centinaia di attributi `style="…"` nei modelli HTML.
Rischio: iniezione di CSS (niente script; con `img-src 'self'` e `connect-src 'self'` nessuna uscita verso altri siti).
Passo successivo: spostare gli stili dei modelli in classi o in `elemento.style` (che la CSP non blocca), poi
`style-src 'self' 'nonce-…'` e `style-src-attr 'none'`.

## Gettone tra processi e client locali fidati

- **Mai sulla riga di comando.** La schermata lancia l'editor con `--progetto`, `--porta`, `--home http://127.0.0.1:<porta>`
  e basta. Ogni server si prende il gettone con `sicurezza.gettone_del_processo()`: quello della variabile d'ambiente
  `IMPAGINATORE_GETTONE` se c'è (riavvio con `os.execv` dopo un'importazione: la pagina aperta resta collegata), altrimenti
  uno nuovo, che scrive nella variabile. `piattaforma.processi.ambiente_figli` toglie la variabile ai processi figli (l'editor
  ha il suo gettone); `rilancia_dopo(..., gettone=)` la rimette solo per il rilancio della schermata dopo un aggiornamento.
- **File di sessione.** Ogni server in funzione scrive `<dati dell'utente>/sessioni/<tipo>-<porta>.json` (cartella 0700, file
  creato 0600 e sostituito in modo atomico) con `tipo`, `porta`, `gettone`, `pid`, `creato` e `progetti` (schermata) o
  `progetto` (editor); lo toglie alla chiusura, solo se contiene ancora il suo gettone. Cartella dei dati: macOS
  `~/Library/Application Support/Impaginatore`, Windows `%APPDATA%\Impaginatore`, Linux `$XDG_DATA_HOME/impaginatore`.
- **Schermata → editor**: `gia_attivo` e `/api/pronto` leggono `editor-<porta>.json`, interrogano l'editor con il suo gettone
  e gli chiedono un URL di avvio, che la pagina apre.
- **Editor → schermata**: `/api/aggiornamento` e `/vai/progetti` dell'editor leggono `home-<porta>.json` (porta presa da
  `--home`). Prima la pagina dell'editor chiamava la schermata direttamente grazie a `Access-Control-Allow-Origin: *`.
- **Un'istanza sola**: `impaginatore` con la porta occupata usa `home-<porta>.json` per riconoscere la propria schermata e
  apre un URL di avvio nuovo.

### Come un client locale fidato (server MCP, T-203) ottiene il gettone

Stessa macchina, stesso utente: legge il file di sessione e manda il gettone nell'intestazione.

```python
from impaginatore import sicurezza
for s in sicurezza.sessioni("editor"):                       # [{tipo, porta, gettone, pid, creato, progetto}], per porta
    try: stato = sicurezza.chiedi(s["porta"], "/api/state", s["gettone"])          # GET; con corpo= diventa POST JSON
    except OSError: continue                                 # file rimasto da un server che non c'è più
    url = sicurezza.chiedi(s["porta"], "/api/avvio", s["gettone"], {})["indirizzo"]   # per aprire la pagina all'utente
```

Regole per il client: `Host: 127.0.0.1:<porta>`, nessun `Origin`, `Content-Type: application/json` nelle POST. Un file
può essere vecchio (server chiuso male): se il server non risponde si ignora. Il gettone non va scritto in altri file,
registri o argomenti. Gli altri utenti del computer non leggono i file (0600 in una cartella 0700); su Windows la
protezione è quella della cartella `%APPDATA%` dell'utente (i permessi POSIX non valgono).

## Percorsi: radici consentite (SEC-005, SEC-010)

Le richieste che portano un percorso (`/api/ls`, `/api/fthumb`, `/api/import`, `/api/ricollega`, `/api/prj_esporta`,
`/api/export` con `dest`, `/api/reveal` con `path` nell'editor; `/api/finder`, `/api/cestino`, la cartella delle foto di
`/api/nuovo` nella schermata) passano da `percorsi.Radici.controlla`: fuori dalle radici rispondono 403 con un messaggio
che invita a usare «Scegli…».

Radici (`percorsi.Radici`):

- **scelte dall'utente in questa sessione** con una finestra di sistema (`/api/pick`, `/api/scegli-foto`, ricollega ed
  esporta senza percorso): la cartella scelta, o quella del file scelto;
- **schermata**: la cartella dei progetti e i progetti aggiunti all'elenco;
- **editor**: la cartella del progetto, quella delle foto e la cartella che la contiene (le altre cartelle del cliente),
  l'uscita dei PSD, le cartelle delle foto aggiunte e di tutte le foto in elenco.

Le radici dedotte da un progetto che sono troppo ampie (la radice del disco, la casa dell'utente o una cartella che la
contiene) si scartano: un `progetto.json` con `"foto": "/"` non apre tutto il disco. Quelle scelte con la finestra di
sistema valgono anche se ampie: le ha scelte l'utente.

Contenimento (`percorsi.dentro`): `realpath` (collegamenti simbolici e `..` risolti), confronto con `normcase` e separatore
finale (`/a/radice2` non sta in `/a/radice`); se non basta, si risale confrontando le cartelle vere (`samestat`), che
regge i dischi che non distinguono le maiuscole (macOS, Windows). Unità diverse di Windows non si contengono mai.

Altri vincoli: il Cestino accetta solo una cartella di progetto vera (con `progetto.json`) dentro la cartella dei progetti,
mai la cartella dei progetti stessa; «Mostra nel Finder» riceve sempre un percorso assoluto (niente `-a` per lanciare
applicazioni); le immagini dell'editor (`/img/thumb/<nome>`, `/api/info/<nome>`) accettano solo nomi di foto del progetto.

**`/api/ls` (selettore di foto del programma): limitato alle radici**, con «Altra cartella…» che apre la finestra di
sistema e aggiunge la cartella scelta. Alternative scartate: sostituirlo del tutto con la finestra di sistema (si perdono
le miniature e la scelta visiva delle foto, usate ogni giorno) e lasciarlo libero (era il rilievo). Sopra una radice non
si sale; i «luoghi» mostrati sono le radici.

## Testo degli script esterni (SEC-004)

Nessun dato (percorso, messaggio, codice) entra nel testo di uno script:

- AppleScript: lo script legge i dati da `on run argv` (`osascript -e … <argomento>`): Cestino (`azioni.cestina`), finestre
  di scelta (`dialoghi.Mac`), Photoshop (`photoshop._do_javascript`). Il nome dell'applicazione Photoshop (letto dal disco)
  è quotato con `photoshop.quota_applescript`.
- PowerShell: il percorso passa dalla variabile d'ambiente `IMPAGINATORE_PERCORSO` (con `-Command` gli argomenti
  diventerebbero testo dello script).
- JavaScript di Photoshop (ExtendScript): ogni dato entra come letterale JSON (`json.dumps`), compresi i percorsi.
- VBS (Windows): il percorso del `.jsx` arriva come `WScript.Arguments(0)`.
- Nessun `shell=True`; percorsi sempre assoluti, così non sembrano opzioni.

Le prove usano percorsi con virgolette, apici, barre rovesciate, `$`, accenti e a capo, e un `osascript` finto che registra
gli argomenti (`tests/test_sicurezza_server.py`, `tests/test_piattaforma.py`).

## Pagine senza XSS (SEC-006)

Ogni dato inserito con `innerHTML`/`insertAdjacentHTML` passa da una sola funzione di escaping per pagina (`escH` in
`index.html`, `esc` in `home.html`: `& < > " ' \``); i nomi negli indirizzi passano da `encU` (`encodeURIComponent` più
`! ' ( ) *`, sicuro anche dentro `url("…")` dei CSS). Il censimento di tutti i punti è nel resoconto di T-102. La CSP con
nonce è la seconda difesa: anche un'iniezione sfuggita non esegue script. La prova `test_xss_da_nomi_ed_exif` apre
schermata ed editor in Chrome senza schermo con nome del progetto, nome di file, data EXIF e nome di carattere malevoli.

## Limiti (SEC-008)

| Cosa | Limite | Dove |
|---|---|---|
| Corpo di una richiesta | 4 MB | `sicurezza.MAX_CORPO` |
| Pixel di una foto | 160 milioni (`IMPAGINATORE_MAX_MPIXEL`) | `album.limite_pixel`, `album.apri_foto` (controllo prima di decodificare) |
| Silenzio su una connessione | 60 s | `servizio.Gestore.timeout` |
| Validità di un URL di avvio | 120 s, un uso | `sicurezza.DURATA_CODICE` |

Una foto oltre il limite non entra nel progetto: va in `album.SCARTATE` con il motivo e l'editor lo mostra.

## Aggiornamenti (SEC-007)

L'aggiornamento con git vale solo per chi lavora da un checkout (`aggiornamenti.predefiniti`). Le richieste che cambiano
il programma (`/api/aggiorna`, `/api/ripristina`, `/api/controlla`, `/api/esci`) passano dai controlli di sopra come tutte
le altre. Il contratto per le installazioni da pacchetto (manifesto firmato Ed25519, chiave pubblica nel programma,
sha256 del pacchetto, niente ritorni a versioni vecchie, installazione solo su richiesta dell'utente) è in
`aggiornamenti/firmati.py` (`PacchettiFirmati`, non ancora attivo).

## Registro

`giornale.configura(processo)` attiva il registratore `impaginatore` su `<dati dell'utente>/registro/impaginatore.log`
(5 file da 1 MB). Regole: mai il contenuto delle foto né il gettone; i percorsi dei file dell'utente solo a livello DEBUG.
`IMPAGINATORE_REGISTRO=DEBUG` alza il dettaglio.

## Compatibilità e cose aperte

- **`Impaginatore.app` della 1.x** (`legacy/macos`): controlla che il programma sia acceso con
  `curl http://127.0.0.1:8765/api/ping | grep -q ok` e poi apre l'indirizzo nudo. Con il gettone `/api/ping` risponde 401:
  l'applet crede che il programma non parta e, dopo l'attesa, mostra «Non riesco ad avviare il programma», anche se la
  schermata è partita e ha aperto da sola il browser con un URL di avvio (anche con `--daemon`). Dedotto dai testi
  dell'applet compilata (`main.scpt`), non provato su un Mac. Correzione proposta:
  ricompilare `main.scpt` (serve un Mac, `osacompile`) perché esegua solo `home.py --porta 8765 --daemon`, che pensa da
  sé a un'istanza sola e all'apertura del browser. Non si è aperta un'eccezione al gettone per `/api/ping`.
- Il codice di avvio sulla riga di comando del browser (vedi sopra).
- `'unsafe-inline'` negli stili (vedi sopra).
- Provato su Linux. Su macOS e Windows le parti di sistema (osascript, PowerShell, permessi dei file) sono provate
  simulando il sistema e intercettando i comandi; vanno provate su macchine reali.
