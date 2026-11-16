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
   (`/`) e delle immagini (`/img/…`, `/api/fthumb`, `/api/cover`), cioè per ciò che il browser carica da solo (`<img>`,
   sfondi CSS, navigazione) e non può portare un'intestazione. Il nome contiene la porta perché i cookie non distinguono
   le porte. **Il valore non è il gettone** (VER-006): è `HMAC-SHA256(gettone, "impaginatore-pagina:<porta>")`
   (`sicurezza.valore_cookie`). Il browser manda i cookie di `127.0.0.1` a ogni porta, quindi anche al server di un altro
   programma che l'utente visita: chi lo riceve non ne ricava il gettone, e con il cookie le API rispondono 401.

Il cookie e il gettone si ottengono una volta sola dall'**URL di avvio** `http://127.0.0.1:<porta>/avvio?c=<codice>`: il
codice è casuale, vale una volta e per `DURATA_CODICE` (120 s). Il server risponde con il cookie e una piccola pagina
(`sicurezza.pagina_avvio`, `no-store`, script con nonce) che lascia il gettone nella `sessionStorage` della scheda (chiave
`impaginatore_gettone`) e apre `/` con `location.replace`. La pagina `/` **non contiene il gettone**: lo legge dalla
`sessionStorage`, che nessun server riceve. Chi apre l'indirizzo nudo senza cookie vede una pagina che spiega come aprire
il programma (401); una scheda con il cookie ma senza gettone (indirizzo scritto a mano in una scheda nuova) mostra lo
stesso messaggio, mai i dati. Ricaricare la scheda la tiene collegata.

Chi crea gli URL di avvio: la schermata quando apre il browser (`main`), la schermata per l'editor (`/api/pronto` →
`indirizzo`, a cui la pagina naviga), l'editor per il pulsante «Progetti» (`GET /api/vai_progetti`, con il gettone
nell'intestazione → `indirizzo`, a cui la pagina naviga; prima era `/vai/progetti`, aperto anche dal cookie), e qualunque
client con il gettone (`POST /api/avvio`). Nessun percorso aperto dal cookie restituisce il gettone o un URL di avvio.

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
  cookie nel suo archivio, la pagina tiene il gettone nella `sessionStorage`). Il motore della finestra (WebKit su macOS e
  Linux, WebView2 su Windows) gestisce `SameSite=Strict` e `HttpOnly` come un browser. Vedi «Finestra del programma».

Rischio residuo noto (VER-006): il cookie che arriva al server di un altro programma su `127.0.0.1` gli apre ancora la
pagina (che non contiene segreti) e **le immagini** (miniature, spread, copertine, `/api/fthumb` dentro le radici) finché
la sessione è viva. Le API, i file e le esportazioni no. Toglierlo del tutto vuol dire il parametro firmato in ogni
indirizzo di immagine (vedi sopra, scartato per ora): decisione aperta.

Rischio residuo noto: su Linux (e dove `ps` mostra gli argomenti degli altri utenti) il **codice** di avvio compare per un
attimo sulla riga di comando del browser lanciato da `webbrowser.open`. Un altro utente che lo legge e lo usa prima del
browser ottiene il cookie; il browser dell'utente vedrebbe allora «Questa scheda non è collegata». Con la finestra del
programma (T-201) il rischio non c'è più: l'URL di avvio passa a WebKit/WebView2 dentro il processo, non su una riga di
comando. Resta per chi usa `--browser` o non ha la finestra; lì il passo successivo è aprire il browser su un file HTML
temporaneo 0600 che rimanda all'URL di avvio.

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

Le immagini dei fogli di stile (per esempio il lucchetto dei comandi che la licenza non comprende) sono file statici del
programma, `/risorse/<nome>.svg`: un indirizzo `data:` lo bloccherebbe `img-src 'self'`, che non si allarga. Nessuna
pagina o foglio di stile usa `data:` (`test_niente_indirizzi_data_nelle_pagine`); i test che aprono le pagine in Chrome
falliscono a ogni violazione della CSP, anche se il test non la cerca (`tests/cdp.py`, `Browser.__exit__`).

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
  L'ambiente di un processo lo legge solo lo stesso utente (`/proc/<pid>/environ` su Linux), la riga di comando chiunque.
- **File di sessione.** Ogni server in funzione scrive `<dati dell'utente>/sessioni/<tipo>-<porta>.json` (cartella 0700, file
  creato 0600 e sostituito in modo atomico) con `tipo`, `porta`, `gettone`, `pid`, `creato` e `progetti` (schermata) o
  `progetto` (editor); lo toglie alla chiusura, solo se contiene ancora il suo gettone. Cartella dei dati: macOS
  `~/Library/Application Support/Impaginatore`, Windows `%APPDATA%\Impaginatore`, Linux `$XDG_DATA_HOME/impaginatore`.
- **Schermata → editor**: `gia_attivo` e `/api/pronto` leggono `editor-<porta>.json`, interrogano l'editor con il suo gettone
  e gli chiedono un URL di avvio, che la pagina apre.
- **Editor → schermata**: `/api/aggiornamento` e `/api/vai_progetti` dell'editor leggono `home-<porta>.json` (porta presa da
  `--home`). Prima la pagina dell'editor chiamava la schermata direttamente grazie a `Access-Control-Allow-Origin: *`.
- **Un'istanza sola**: `impaginatore` con la porta occupata usa `home-<porta>.json` per riconoscere la propria schermata e
  apre un URL di avvio nuovo.

## Finestra del programma (T-201)

Codice: `desktop/`; prove: `tests/test_desktop.py` (pywebview finto) e `test_finestra_vera` (WebKitGTK sotto Xvfb).

- **URL di avvio dentro il processo.** La finestra apre `srv.indirizzo_avvio()` con `create_window(url=...)`: nessuna
  riga di comando, nessun browser. Il secondo avvio del comando apre un'altra finestra con un URL di avvio nuovo.
- **Gettone fuori dall'ambiente.** Con la finestra la schermata prende il gettone con `desktop.gettone()`, che lo toglie
  da `os.environ` (se arriva da un rilancio) invece di scriverlo: i processi del motore (WebKitWebProcess, msedgewebview2)
  e il browser aperto per i link esterni non lo ereditano (provato con WebKitGTK leggendo `/proc/<pid>/environ`). La
  schermata non si riavvia con `os.execv`; il rilancio dopo un aggiornamento passa il gettone in modo esplicito come prima.
- **Solo le pagine del programma.** La finestra apre solo `http://127.0.0.1:<porta della schermata o di un editor in
  funzione>` (porte dai file di sessione, rilette a ogni navigazione), più `about:blank`. Un sito `http`/`https` si apre
  nel browser di sistema (`processi.apri_browser`, senza gettone); `file:`, `data:`, `javascript:`, `blob:`, indirizzi
  con utente e password e gli altri servizi di questo computer (`localhost`, `127.x`, `::1`, `0.0.0.0` su altre porte)
  non si aprono da nessuna parte. Due difese: il filtro del motore prima della navigazione (WebKitGTK «decide-policy»,
  WebView2 `NavigationStarting`; finestre nuove sempre rifiutate) e il controllo dopo ogni caricamento, che lascia una
  pagina fuori dal programma e torna all'ultima del programma. Su macOS pywebview non permette un filtro: c'è solo il
  controllo dopo il caricamento, quindi la richiesta della pagina esterna parte prima di essere lasciata. Le nostre
  pagine non hanno link esterni né `window.open`: il filtro è una difesa in più contro una pagina compromessa (che
  potrebbe comunque usare `fetch`, limitato dalla CSP a `connect-src 'self'`).
- **Nessuna API JavaScript → Python.** pywebview parte senza `js_api` e senza `expose`. Resta il ponte interno di
  pywebview, caricato in ogni pagina (`window.pywebview`): muovere la finestra senza bordi, eventi DOM registrati da
  Python (nessuno), stato condiviso (vuoto), `alert` di pywebview. Rischio residuo: una pagina compromessa può chiamare
  queste funzioni interne (non leggono né scrivono file, non lanciano processi); va rivisto a ogni versione di pywebview
  (fissata `>=6.2,<7`).
- **Impostazioni.** `ALLOW_FILE_URLS`, `ALLOW_DOWNLOADS`, `IGNORE_SSL_ERRORS` spenti, `REMOTE_DEBUGGING_PORT` nessuna,
  strumenti di sviluppo solo con `IMPAGINATORE_FINESTRA_SVILUPPO=1` e mai in un programma impacchettato (`sys.frozen`).
  Motori ammessi: WebKitGTK, WebView2, WKWebView; mai Internet Explorer (`mshtml`), con cui si apre il browser.
- **Archivio della finestra.** `private_mode=False`, `storage_path=<dati dell'utente>/finestra`: cookie (valgono la
  sessione: il server ne cambia il valore a ogni avvio), `localStorage` dell'editor (preferenze), cache. Le immagini che
  il server lascia tenere in cache (copertine della schermata `max-age=600`, immagini dell'editor `no-cache` con ETag o
  `max-age=3600`) finiscono nella cache del motore come oggi in quella del browser: restano su questo computer, nella
  cartella dei dati dell'utente.
- **Finestre di scelta.** Nella finestra (GTK, macOS) le apre pywebview; l'editor, che è un altro processo, le chiede
  alla schermata con `POST /api/dialogo` (gettone della schermata dal file di sessione, come `/api/vai_progetti`), che
  risponde solo se la finestra è aperta e solo per `cartella`, `zip`, `foto`. Il percorso scelto diventa una radice
  consentita come prima, nel processo che l'ha chiesto. Su Windows restano quelle di tkinter (non provate con pywebview).
- **Foto trascinate sulla finestra**: non attivate (ARCHITETTURA.md, «Finestra desktop»); i percorsi che pywebview
  offrirebbe alla pagina sono in parte scrivibili dalla pagina stessa.

### Come un client locale fidato (server MCP, T-203) ottiene il gettone

Stessa macchina, stesso utente: legge il file di sessione e manda il gettone nell'intestazione.

```python
from impaginatore import sicurezza
for s in sicurezza.sessioni("editor"):                       # [{tipo, porta, gettone, pid, creato, progetto}], per porta
    try: stato = sicurezza.chiedi(s["porta"], "/api/state", s["gettone"])          # GET; con corpo= diventa POST JSON
    except OSError: continue                                 # file rimasto da un server che non c'è più
    url = sicurezza.chiedi(s["porta"], "/api/avvio", s["gettone"], {})["indirizzo"]   # per aprire la pagina all'utente
```

Regole per il client: `Host: 127.0.0.1:<porta>`, nessun `Origin`, `Content-Type: application/json` nelle POST, **mai un
proxy** (con `HTTP_PROXY` impostato, o un proxy di sistema, `urllib.request.urlopen` manderebbe anche le richieste a
127.0.0.1, gettone compreso, al proxy: `sicurezza.chiedi` e il server MCP usano `sicurezza.APRI_LOCALE`, senza proxy). Un file
può essere vecchio (server chiuso male): se il server non risponde si ignora. Il gettone non va scritto in altri file,
registri o argomenti. Gli altri utenti del computer non leggono i file (0600 in una cartella 0700); su Windows la
protezione è quella della cartella `%APPDATA%` dell'utente (i permessi POSIX non valgono).

Il server MCP (`mcp/collegamento.py`) segue queste regole e in più non manda il gettone a un file di sessione il cui
processo non c'è più (su macOS e Linux: un altro programma potrebbe aver preso la porta). Non ascolta su nessuna porta:
parla con l'assistente su stdio. Il resto del suo modello di minaccia è in `MCP.md`.

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
  le cartelle delle foto aggiunte (`foto_extra`) e l'uscita dei PSD (`motore.album.luoghi_foto`). Mai le cartelle delle
  foto in elenco (`_cache/meta.json`): un progetto ricevuto come cartella le farebbe puntare ovunque (VER-004).

Le radici dedotte da un progetto che sono troppo ampie (la radice del disco, la casa dell'utente o una cartella che la
contiene) o **riservate** (`percorsi.riservata`: cartelle nascoste della casa come `~/.ssh` e `~/.config`, dati e cache dei
programmi, anche i nostri con i file di sessione, `~/Library` e `AppData`, cartelle di sistema come `/etc`, `/usr`,
`/proc`, `/System`, `%SystemRoot%`) si scartano: un `progetto.json` con `"foto": "/"` non apre tutto il disco. Quelle
scelte con la finestra di sistema valgono anche se ampie o riservate: le ha scelte l'utente.

Foto in elenco (VER-004): all'apertura (`motore.album._src_fidate`) una foto si legge solo se il suo file ha l'estensione
di una foto, sta dentro i luoghi del progetto e non in una cartella riservata (collegamenti risolti); altrimenti risulta
mancante e si ricollega. «Ricollega foto» aggiunge le foto ritrovate a `foto_extra`, così la cartella scelta resta un luogo
del progetto alle aperture successive. `progetto.json` con `foto`, `foto_extra` o `uscita_psd` in una cartella riservata
torna a `Foto`, nessuna, `PSD` del progetto. «Esporta progetto» copia solo foto che passano lo stesso controllo.
Resta aperto: un `progetto.json` ricevuto la cui cartella delle foto è una cartella qualunque (non riservata) dell'utente
la fa ancora diventare radice, come per un progetto proprio.

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
`! ' ( ) *`, sicuro anche dentro `url("…")` dei CSS). I testi della tabella (T-206) non contengono HTML e dentro
`innerHTML` entrano con `tH(chiave, parametri)`, che fa l'escape del testo già completo dei parametri (un nome di file
come parametro resta testo); la tabella arriva nello script come JSON senza `<` (`risorse.testi_pagina`).
`tests/test_lingua.py` fallisce se un testo della tabella contiene `<` o se una riga con `innerHTML` usa `t()` nudo.
Il censimento di tutti i punti è nel resoconto di T-102. La CSP con
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
- Il codice di avvio sulla riga di comando del browser, solo senza la finestra del programma (vedi sopra).
- `'unsafe-inline'` negli stili (vedi sopra).
- Finestra del programma: filtro di navigazione e finestre di scelta provati con WebKitGTK; WebView2 e WKWebView no
  (vedi «Finestra del programma»); ponte interno di pywebview in ogni pagina.
- Provato su Linux. Su macOS e Windows le parti di sistema (osascript, PowerShell, permessi dei file) sono provate
  simulando il sistema e intercettando i comandi; vanno provate su macchine reali.
