# Architettura dell'Impaginatore (2.0, fondamenta)

Stato: fine del compito T-006 (fase 0). Il comportamento è quello della 1.5.2: stessa interfaccia, stesso formato dei
progetti, stesse operazioni. Cambia la struttura: un pacchetto Python installabile (`src/impaginatore`), uno strato che
isola le differenze tra macOS, Windows e Linux, nessun effetto all'import, una base di test.
Dopo T-101 il formato dei progetti è `album.json` (solo dati): vedi «Formato dei progetti» e `FORMATO-PROGETTO.md`.

## Mappa dei moduli

```
src/impaginatore/
├── __init__.py          __version__ (unico posto della versione: lo leggono pyproject, home, editor, aggiornamenti)
├── __main__.py, cli.py  comando «impaginatore»: schermata dei progetti, oppure «impaginatore editor ...» o «impaginatore mcp»
├── compilato.py        programma compilato con Nuitka (T-302, DISTRIBUZIONE.md): attivo(), riga di comando dei processi, sottocomandi _psd/_dialogo/_rilancia
├── servizio.py          ServerLocale (ThreadingHTTPServer su 127.0.0.1), Gestore (controlli di sicurezza di ogni richiesta), porta_libera()
├── sicurezza.py         gettone di sessione, URL di avvio monouso, file di sessione per i client locali (docs/architettura/SICUREZZA.md)
├── percorsi.py          radici consentite: i percorsi che arrivano dalla pagina restano nelle cartelle del progetto o scelte dall'utente
├── giornale.py          registro «impaginatore» su file a rotazione nella cartella dei dati
├── lingua.py            testi per l'utente in italiano e inglese (T-206): t()/tn() dalla tabella, numeri e date per lingua, lingua in uso
├── formato.py           l'unico modulo che legge e scrive l'impaginazione (album.json) e i JSON del progetto; scritture atomiche
├── formato_1x.py        spec.py delle 1.x: lettura con ast senza eseguirlo (migrazione) e scrittura per «Esporta per la 1.x»
├── validazione.py      controllo dei dati letti da un progetto (album.json, progetto.json, modelli, cache): ErroreProgetto
├── archivio.py         estrazione sicura di uno ZIP di progetto (percorsi, limiti, tipi di file)
├── nomi.py             nome del progetto (un dato) e nome di cartella valido su macOS, Windows e Linux
├── ed25519.py          firme Ed25519 (RFC 8032) con la sola libreria standard: chiavi di licenza, elenco delle revoche
├── licenze/            licenze, fasce di tier.json, prova gratuita, sola lettura, filigrana; tutto in locale (LICENZE.md)
├── statistiche/        statistiche d'uso della beta privata (T-204): spente di serie, solo dopo il «sì»; registro locale,
│                       schema chiuso degli eventi (schema.py), invio (invio.py, oggi nessuno) (STATISTICHE.md)
├── laboratori/         cataloghi dei laboratori (T-208): formato e firma (catalogo.py), installati e importati, prodotto
│                       dell'album, file della consegna (consegna.py); cataloghi/generico.json (CATALOGHI.md)
├── home/server.py       schermata dei progetti: elenco, nuovo, apri (lancia l'editor), ZIP, cestino, aggiornamenti, licenza
├── editor/server.py     editor di un album: stato in memoria, operazioni, annulla/ripeti, anteprime, Tono, esportazioni (esito in /api/esito)
├── motore/              motore di impaginazione (viene dalla skill «impaginazione-album-stefano»)
│   ├── album.py         progetto caricato, geometria, foto (metadati, miniature, volti con OpenCV), moduli P/FULL/DUO..., render
│   ├── album_libere.py  cornici libere, angoli, stili, testi liberi, tono/ritocco: si «installa» dentro album all'import
│   ├── spazi.py         stacchi fra le foto: stato e correzione («Correggi spazi», «Sistema»), gli stessi della pagina
│   ├── bozza.py         bozza dell'album: capitoli, gruppi, ritmo, scelta delle disposizioni (UX-018)
│   ├── testo.py         testi liberi: font installati (nomi letti dai file), misura e disegno
│   ├── photoshop.py     funzioni per gli script (app_name, run_jsx, open_documents) + libreria ExtendScript JS_LIB
│   ├── genera_psd_angolo.py  genera_psd con le parti JavaScript estese (angoli, testi, tono, sRGB): niente exec
│   └── abbina, analizza, anteprima, esporta_pdf, genera_psd, modifica_psd, verifica_psd   script: python -m impaginatore.motore.<nome>
├── piattaforma/         TUTTO ciò che cambia tra sistemi (il resto del codice non controlla sys.platform)
│   ├── __init__.py      sistema() -> "mac" | "windows" | "linux", letto a ogni chiamata (i test lo simulano)
│   ├── cartelle.py      dati dell'utente, cache, documenti, Scrivania, dischi, cartella dei progetti, migrazione da ~/.album-tools
│   ├── dialoghi.py      finestre di scelta: osascript (Mac), tkinter in un processo figlio (Windows/Linux), zenity/kdialog, nessuna
│   ├── azioni.py        mostra nel Finder/Esplora risorse/file manager; Cestino (Finder, PowerShell, gio, freedesktop a mano)
│   ├── font.py          cartelle dei font, font di ripiego, font dei vecchi titoli, profilo sRGB
│   ├── photoshop.py     dove sta Photoshop e come eseguire un .jsx (osascript sul Mac, COM via cscript su Windows; su Linux no)
│   ├── lingua.py        lingua del sistema per il primo avvio (AppleLanguages, GetUserDefaultUILanguage, LANG e simili)
│   └── processi.py      ambiente dei figli (UTF-8), riavvio con gli stessi argomenti, rilancio ritardato, distacco dal terminale
├── aggiornamenti/       aggiornamenti (T-207, AGGIORNAMENTI.md): interfaccia Aggiornamenti, NonDisponibili, impostazione del controllo automatico
│   ├── lanciatore.py    prima cosa di cli.main: quale copia avviare (base installata o versione aggiornata), puntatore, ritorno da solo
│   ├── firmati.py       PacchettiFirmati: manifesto firmato Ed25519, controllo, scaricamento, installazione, ritorno indietro, annuncio
│   ├── sorgenti.py      SorgenteGitHub (API delle release, solo https, limiti) e SorgenteFinta (una cartella, per le prove)
│   ├── installazione.py InstallazionePython (estrazione sicura, prova di avvio, puntatore) e InstallazioneCompilata (a mano: apre la pagina della release)
│   ├── rilascio.py      manifesto, firma e release finta per chi pubblica e per i test (strumenti/aggiornamento.py)
│   └── git.py           Git: aggiornamenti da un checkout (sviluppo, Mac dell'ideatore)
├── desktop/             finestra del programma con pywebview (T-201; extra «desktop»): pywebview si carica solo in motore()
│   ├── finestra.py      motore() (finestra o browser), esegui() (finestra della schermata, chiusura ordinata), ospite()
│   ├── avvio.py         schermata di avvio (T-207): logotipo, versione, licenza; la finestra si mostra quando la schermata Album è pronta
│   ├── navigazione.py   la finestra apre solo le pagine del programma; i siti vanno nel browser di sistema
│   ├── geometria.py     misura e posizione ricordate in <dati>/finestra.json
│   └── dialoghi.py      finestre di scelta di pywebview (schermata) e Ponte (editor → schermata, POST /api/dialogo)
├── mcp/                 server MCP per gli assistenti AI (T-203; extra «mcp», SDK ufficiale): client locale del programma in funzione (MCP.md)
│   ├── collegamento.py  trova schermata ed editor dai file di sessione, richieste con il gettone senza proxy, avvio del programma
│   ├── strumenti.py     gli strumenti (Assistente): argomenti controllati, licenza, testi come dati, limiti; senza SDK
│   ├── consenso.py      immagini all'assistente: spente di serie, --consenti-immagini o <dati>/assistente.json
│   └── server.py        registrazione con l'SDK (schemi, annotazioni, risposte) e avvio su stdio
└── risorse/             home.html, index.html (interfaccia), avvio.html (schermata di avvio), testi/<lingua>/<area>.json (tabella dei testi), vib_lut.npz (vibranza misurata in Photoshop), icona.png (da brand/icona)
tests/                   pytest; dati/progetto_152 = progetto salvato dalla 1.5.2 (riferimento di parità)
legacy/macos/            Impaginatore.app (applet compilata), .command, setup.sh; «Editor Album/home.py» è un ponte per l'applet
skill/impaginatore-stefano/  istruzioni per Claude (SKILL.md, references, assets)
```

## Processi e porte

```
impaginatore [--porta 8765] [--browser | --no-browser] [--progetti DIR] [--daemon]
 └─ lanciatore (cli.main)            dopo un aggiornamento: os.execv nella copia <dati>/programma/versioni/<v> (AGGIORNAMENTI.md)
 └─ home (processo 1) 127.0.0.1:8765  ── apre la finestra del programma (o il browser) su un URL di avvio monouso (http://127.0.0.1:8765/avvio?c=…)
      POST /api/apri {path}
       ├─ editor già in ascolto per quel progetto? (porta stabile, poi 8801–8899: file di sessione + /api/ping con "path") -> si riusa
       └─ altrimenti: python -m impaginatore.editor --progetto P --porta N --home http://127.0.0.1:8765
            N = porta_stabile(P) = 8801 + crc32(P) % 99 se libera, altrimenti la prima libera 8801–8899
            cwd = cartella che contiene il pacchetto, ambiente con PYTHONUTF8=1, uscita in <progetti>/editor.log
            └─ editor (processo 2, uno per progetto) 127.0.0.1:N
                 ├─ /api/import, /api/ripristina -> salva e riparte con gli stessi argomenti (processi.riesegui = os.execv);
                 │    /api/import con a_caldo: true aggiunge le foto senza ripartire (UX-012)
                 └─ export PSD -> python -m impaginatore.motore.genera_psd_angolo --progetto P --spread ...
                       └─ Photoshop: osascript «do javascript» (Mac) / cscript + COM (Windows); su Linux si ferma prima
```

- Programma compilato (T-302): al posto di `python -m <modulo>` il programma lancia se stesso con un sottocomando
  (`impaginatore editor …`, `impaginatore _psd …`, `impaginatore _rilancia …`): `compilato.comando`, `DISTRIBUZIONE.md`.
- Porta libera: si prova ad aprirla davvero (bind); su macOS e Linux si controlla anche che nessuno risponda. Niente
  `lsof`, niente `connect_ex` su 99 porte (su Windows costava secondi per porta).
- Un'istanza sola: se la porta della home risponde a `/api/ping` (con il gettone del suo file di sessione), il comando apre
  solo la pagina, con un URL di avvio nuovo: in un'altra finestra del programma (`desktop.ospite`, che chiudendosi non
  ferma niente) o, senza finestra, nel browser.
- `--porta 0`: porta libera qualsiasi (test); l'indirizzo vero è nella prima riga stampata.
- Ogni richiesta vuole il gettone del suo server (intestazione o, per pagina e immagini, cookie derivato dato dall'URL di
  avvio, che lascia il gettone nella `sessionStorage` della scheda): `docs/architettura/SICUREZZA.md`. La pagina dell'editor
  chiede aggiornamenti (`/api/aggiornamento`) e ritorno ai progetti (`/api/vai_progetti`) al suo server, che li chiede alla
  home con il gettone della home (niente più CORS `*`).
- Uscita: `/api/esci` termina gli editor lanciati da quella home e chiude il processo (`home.server.esci`).
- Dopo un aggiornamento: la home fa salvare e chiudere gli editor (`desktop.finestra.chiudi_editor`), rilancia
  `python -m impaginatore --porta <stessa> --no-browser` dopo 1,5 s (processo staccato) ed esce; il lanciatore del
  programma rilanciato avvia la versione nuova e la pagina si ricarica quando risponde di nuovo (`/api/ping`). Con la
  finestra il rilancio è senza `--no-browser`: la finestra vecchia si chiude con il suo processo e il programma
  rilanciato ne apre una nuova (stesso gettone). Durante un'esportazione aggiorna e ripristina si rifiutano.

## Finestra desktop (T-201)

```
impaginatore                         (senza --browser, --no-browser, --daemon)
 └─ desktop.motore()                 pywebview + motore del sistema, oppure None → browser come prima (motivo nel registro e su stderr)
 └─ home (processo 1, thread)        crea_server(porta, desktop.gettone()): il gettone non resta nell'ambiente
 └─ desktop.esegui()                 thread principale: finestra pywebview sull'URL di avvio monouso (dentro il processo)
      ├─ avvio.py (T-207)            prima la schermata di avvio (480 × 300, senza bordi, al centro, pagina senza script:
      │                              logotipo in negativo, versione, licenza); la finestra nasce nascosta e si mostra quando
      │                              la pagina chiede /api/progetti (home.server.PRONTA), dopo almeno 1 s e al massimo 20 s
      ├─ schermata ⇄ editor          stessa finestra, come nella scheda del browser: /api/pronto e /api/vai_progetti danno
      │                              un URL di avvio monouso del server di arrivo; ogni origine ha la sua sessionStorage
      ├─ navigazione.py              filtro del motore (WebKitGTK «decide-policy», WebView2 NavigationStarting) + controllo
      │                              dopo ogni caricamento (l'unico su macOS): solo http://127.0.0.1:<schermata o editor>
      ├─ dialoghi.py                 GTK e macOS: finestre di scelta di pywebview; l'editor le chiede alla schermata
      │                              (IMPAGINATORE_DIALOGHI=finestra:<porta> → POST /api/dialogo). Windows: tkinter come prima
      └─ chiusura della finestra     se un editor esporta (/api/ping «esporta») chiede conferma in una finestra del sistema
                                     (desktop.esporta_titolo/testo, da un thread a parte: il gestore «closing» gira nel thread
                                     dell'interfaccia); poi misura salvata, ogni editor salva (POST /api/save) e si chiude
                                     (5 s, poi kill), la schermata si ferma, main() restituisce 0. «Esci» nella pagina chiude la finestra
```

- Motori ammessi: WebKitGTK (`gtkwebkit2`, Linux: PyGObject e WebKit2GTK 4.1 o 4.0 del sistema, non installabili da
  PyPI), WebView2 (`edgechromium`, Windows), WKWebView (`wkwebview`, macOS). Mai Internet Explorer (`mshtml`, il ripiego di
  pywebview su Windows senza WebView2) né Qt: con questi si apre il browser.
- Impostazioni: `ALLOW_FILE_URLS`, `ALLOW_DOWNLOADS`, `IGNORE_SSL_ERRORS` spenti, nessuna porta di debug remoto, strumenti
  di sviluppo solo con `IMPAGINATORE_FINESTRA_SVILUPPO=1` fuori da un programma impacchettato, nessuna `js_api` né
  funzione esposta. `private_mode=False` con `storage_path=<dati>/finestra`: l'editor usa `localStorage` (righelli,
  preferenze) senza try/catch e WebKitGTK in modo privato lo toglie. `text_select` e `draggable` accesi (l'editor
  trascina foto e testi), `zoomable` spento.
- Misura e posizione: `<dati>/finestra.json`, minimo 1024 × 700; una posizione fuori da tutti gli schermi si scarta.
- Trascinare una cartella sulla finestra (UX-015): **non fatto**. pywebview passa i percorsi dei file trascinati solo
  agli eventi DOM registrati da Python (`window.dom...on("drop")`), che usano `evaluate_js` → `eval`, bloccato dalla CSP
  delle nostre pagine (provato con WebKitGTK: EvalError). Inoltre il campo `pywebviewFullPath` lo può scrivere la pagina
  quando pywebview non ha un percorso suo, su GTK il percorso arriva da `get_text()` del trascinamento (da provare con
  `text/uri-list`), e su WebView2 le cartelle non sono provate. Servirebbe: `'unsafe-eval'` nella CSP solo nella finestra
  (da evitare) oppure un gestore nativo per ogni motore (GTK `drag-data-received`, WebView2 `WebMessageReceived` con
  `postMessageWithAdditionalObjects`, Cocoa `performDragOperation`) che passi alla schermata solo cartelle esistenti, poi
  `RADICI.aggiungi` e il flusso «Nuovo progetto» con quella cartella, provato su tre sistemi veri.
- Prova vera: `tests/test_desktop.py::test_finestra_vera` (marcatore `finestra`) lancia `tests/prova_finestra.py` sotto
  `xvfb-run` con WebKitGTK; saltata senza Linux, xvfb-run, pywebview o PyGObject. Il resto usa un pywebview finto.
- macOS, versione 1.x: `Impaginatore.app` esegue `cd "<cartella dell'app>/Editor Album" && ~/.album-tools/venv/bin/python home.py --porta 8765 --daemon`;
  `legacy/macos/Editor Album/home.py` passa gli argomenti a `impaginatore.cli.main`. `--daemon` (doppio fork) c'è solo su POSIX.

## Formato dei progetti

Dalla 2.0 (T-101) l'impaginazione si salva in `album.json` (formato 2, solo dati): schema, limiti, regole di controllo,
migrazione dei progetti 1.x, esportazione per la 1.x e Importa ZIP sono in `FORMATO-PROGETTO.md`. Nessun file di un
progetto viene eseguito: `spec.py` delle 1.x si legge con `ast` (`formato_1x`), si converte una volta in `album.json` e
resta come `spec.py.1x`. `tests/test_formato.py` prova che il progetto salvato dalla 1.5.2 (`tests/dati/progetto_152`)
convertito dà lo stesso stato dell'editor e le stesse anteprime di `spec.py` eseguito come faceva la 1.5.2, e che un
progetto esportato per la 1.x si apre con l'`album.py` della 1.5.2. `tests/test_sicurezza.py` rifà i payload dell'audit
e controlla che nel pacchetto non ci siano `exec`, `eval`, `compile`, `__import__`, `importlib`, `runpy`, `pickle`.

## Stato globale che resta (un progetto per processo)

| Dove | Cosa | Chi lo azzera |
|---|---|---|
| `motore/album.py` | PROJ, CFG, M (foto), F (volti), IDX, CW/CH/G..., TITLE, INK, font dei titoli | `carica_progetto(cartella, sottofondo)` |
| `motore/album_libere.py` | sostituisce funzioni di `album` (`_place`, `zcrop.__code__`, `_photo`, `render`, `_text`, `apply_ev`, `layout.__code__`) la prima volta che viene importato; cache `_VIB` | mai (è voluto: vale per tutto il processo) |
| `motore/testo.py` | `_FONTS` (elenco dei font, una volta per processo), `DIRS`/`CACHE` sovrascrivibili | riavvio |
| `editor/server.py` | PROJ, HOME, CFG (= `album.CFG`), SP, GD, UNDO/REDO, CLIP, LOG, SAVED, REV, LASTC, BOOT, BL/VW/VH, NPH, UT_FILE, cache (CACHE, TH, INFO, PV, FT, TONO_*), LAST, SAVE_ERR, LASTDIR, AGG, `_ICC`, ESITO, DISP, BOZZA (ultima bozza proposta), PREP e PREP_FILO (preparazione in sottofondo) | `inizializza(progetto, home, sottofondo)` (ferma la preparazione in corso) |
| `home/server.py` | PROGETTI, REG, PORTA, AGGIORNAMENTI, EDITORS (processi figli), SERVER, RADICI (cartelle scelte) | `configura(...)`, `crea_server(...)`; `RADICI.scelte` vale per la sessione |
| `piattaforma/dialoghi.py` | implementazione scelta con `imposta()` | `imposta(None)` |
| `home/server.py` (T-201) | FINESTRA (la schermata è nella finestra), `esci` sostituita dalla chiusura della finestra | `desktop.esegui` alla fine |
| `desktop/finestra.py` | ATTUALE (la finestra di questo processo, per le prove) | `desktop.esegui` / `ospite` alla fine |
| `piattaforma/font.py` | `_cerca_linux` in `lru_cache` | riavvio |
| `lingua.py` | `_TABELLE` (tabella di ogni lingua, letta una volta), `_SCELTA` (lingua salvata: si rilegge quando `preferenze.json` cambia) | riavvio / da sola |
| PIL | `Image.MAX_IMAGE_PIXELS` = `album.limite_pixel()` (160 MP, `IMPAGINATORE_MAX_MPIXEL`), impostato da `carica_progetto` e `apri_foto` | — |

Conseguenza: in un processo c'è un solo editor «vivo». I test usano l'editor nello stesso processo, uno alla volta.

## Punti di estensione

- **Formato di salvataggio**: `formato.py` e `validazione.py`. Un formato 3 aumenta `validazione.FORMATO`, aggiunge in
  `formato.carica` la conversione dal 2 e un test con un progetto salvato nel formato 2 (vedi `FORMATO-PROGETTO.md`).
- **Finestre di scelta**: `piattaforma.dialoghi.imposta(oggetto con _scegli(tipo, messaggio))` per tutto il processo;
  `IMPAGINATORE_DIALOGHI=mac|tk|zenity|kdialog|nessuno|finestra:<porta>` per sceglierle per nome (vale anche per i
  processi figli).
- **Finestra desktop** (T-201, fatto): `desktop.esegui(motore, server, fermo)`. Un altro motore si aggiunge in
  `finestra.GUI`/`MOTORI` e, se ha un filtro di navigazione, in `navigazione.FILTRI`; le finestre di scelta di pywebview si
  accendono per motore in `finestra.DIALOGHI_PROPRI` (Windows: da accendere dopo una prova vera).
- **Aggiornamenti** (T-207, fatto per il pacchetto Python): `aggiornamenti.Aggiornamenti` (stato, controlla, versioni,
  aggiorna, ripristina, ciclo) passato a `home.server.configura(aggiorna=...)` o scelto da `aggiornamenti.predefiniti()`.
  `PacchettiFirmati` prende una `Sorgente` (da dove: GitHub o una cartella) e una `Installazione` (come si sostituisce il
  codice): il programma compilato (T-302) usa `InstallazioneCompilata`, che oggi apre solo la pagina della release. Come
  si pubblica una release: `AGGIORNAMENTI.md`; come si costruiscono i pacchetti: `DISTRIBUZIONE.md`.
- **Licenze** (T-202): il punto d'ingresso unico è `cli.main` (e `home.server.main` / `editor.server.main`); le funzioni a
  pagamento passano tutte dalle richieste HTTP (`H.do_POST` di home ed editor) e dalle funzioni `run_export`, `esporta_progetto`:
  lì va il controllo della fascia (`docs/mercato/tier.json`).
- **MCP** (T-203, fatto): `impaginatore mcp` usa l'API HTTP della schermata e degli editor in funzione, come la pagina
  (scelta e motivi in `MCP.md`). Uno strumento nuovo è un metodo di `mcp.strumenti.Assistente` con `@strumento` più la sua
  registrazione in `mcp.server.crea`; le operazioni dell'editor che può chiamare sono quelle di `OPERAZIONI.md`.
  Le operazioni aggiunte per l'interfaccia nuova e per l'assistente (altra disposizione, sostituisci, controllo,
  «Sistema», bozza, annulla con nome, ricollega con prova, import a caldo) sono descritte in `OPERAZIONI.md`.
- **Lingua** (T-206): ogni testo per l'utente sta in `risorse/testi/<lingua>/<area>.json` (`it` ed `en`, stesse chiavi e
  stessi parametri `{nome}`, niente HTML). Le pagine ricevono `TESTI`, `LINGUA` e `LOCALE` dal server (`servizio.pagina`)
  e usano `t()`, `tn()`, `tH()` (per `innerHTML`, con l'escape) e `fN()`; i moduli Python `lingua.t("area.chiave", nome=…)`
  al momento del messaggio. La lingua in uso è quella scelta nella schermata Album (`<dati>/preferenze.json`), altrimenti
  quella del sistema salvata al primo avvio. Una lingua nuova è una cartella `testi/<codice>/` più una voce in
  `lingua.LINGUE` e `LOCALI`; `tests/test_lingua.py` controlla chiavi, parametri e testi rimasti fuori dalla tabella.
  Termini inglesi in `docs/prodotto/ux/GLOSSARIO.md`.
- **Riavvio dell'editor**: `editor.server.riavvia_processo` (di serie `os.execv` con gli stessi argomenti) si può sostituire
  quando l'editor gira dentro un altro processo.
- **Photoshop**: `piattaforma.photoshop.trova / esegui_jsx / esegui_js`; i test li sostituiscono con un Photoshop finto.
  Lo script JavaScript dei PSD ha parti con nome (`genera_psd.PARTI`: `TESTO`, `INIZIO`, `NUOVO_DOC`, `ANGOLO`, `STILE`,
  `TONO`, `AGGIUNGI_TESTO`) che una variante sostituisce passando `parti=` a `genera_psd.main`.

## Variabili d'ambiente

| Variabile | Effetto |
|---|---|
| `IMPAGINATORE_PROGETTI` | cartella dei progetti (prima di `<checkout>/Progetti` e `Documenti/Impaginatore/Progetti`) |
| `IMPAGINATORE_DATI`, `IMPAGINATORE_CACHE` | cartelle dei dati dell'utente (modelli salvati) e della cache (font) |
| `IMPAGINATORE_DIALOGHI` | finestre di scelta per nome (`nessuno` nei test; `finestra:<porta>` la mette la finestra per gli editor) |
| `IMPAGINATORE_FINESTRA=no` | niente finestra del programma: si apre il browser (anche `0`, `browser`; i test la spengono) |
| `IMPAGINATORE_FINESTRA_SVILUPPO=1` | strumenti di sviluppo della vista web nella finestra (mai in un programma impacchettato) |
| `IMPAGINATORE_AGGIORNAMENTI=no` | aggiornamenti spenti |
| `IMPAGINATORE_AGGIORNAMENTI_FINTI=<cartella>` | le release da una cartella locale (prove a mano, `AGGIORNAMENTI.md`); vale anche da un checkout |
| `IMPAGINATORE_VERSIONE_SCELTA`, `IMPAGINATORE_BASE` | le mette il lanciatore: copia già scelta (niente secondo salto) e dove sta la base installata |
| `IMPAGINATORE_SENZA_RIAVVIO` | dopo un aggiornamento non riavvia (prove) |
| `IMPAGINATORE_GETTONE` | gettone di sessione del server di questo processo (lo scrive il server; resta dopo un riavvio, non passa ai figli) |
| `IMPAGINATORE_LINGUA` | lingua «del sistema» (`it`, `en`, `it_IT`…): vale finché l'utente non ne sceglie una; i test la mettono a `it` |
| `IMPAGINATORE_MAX_MPIXEL` | milioni di pixel al massimo per foto (predefinito 160) |
| `IMPAGINATORE_REGISTRO` | livello del registro (`DEBUG`, `INFO`…; predefinito `INFO`) |
| `ALBUM_PROGETTO` | cartella del progetto per gli script del motore (come nelle 1.x) |

Cartelle dei dati: macOS `~/Library/Application Support/Impaginatore` (cache `~/Library/Caches/Impaginatore`), Windows
`%APPDATA%\Impaginatore` (cache `%LOCALAPPDATA%\Impaginatore\Cache`), Linux `$XDG_DATA_HOME/impaginatore` (cache
`$XDG_CACHE_HOME/impaginatore`). Un file che manca viene copiato da `~/.album-tools` (l'originale resta).

## Test

`pytest` dalla radice; `pytest --cov` per la copertura (anche dei processi figli: `[tool.coverage.run] patch`).
La copertura si misura con il motore `ctrace` su ogni versione di Python (`[tool.coverage.run] core`): con Python 3.14
il predefinito `sysmon` segna come parziali dei rami percorsi (`if ...: raise ...` su una riga). La soglia è 100 % di
righe e rami (`[tool.coverage.report] fail_under`, l'unico posto): una riga esclusa ha il motivo accanto al `pragma`. Gli
script del motore senza `main()` si eseguono nello stesso processo con `aiuti.come_script`; runpy su un modulo già
importato è un errore. `tests/test_script_motore.py` li prova con un Photoshop finto (registra gli script `.jsx` e
risponde come lui) e con PSD finti che hanno la forma di quelli di psd-tools (gruppi, maschere vettoriali, regolazioni
agganciate).
Marcatori: `photoshop` (saltati se Photoshop manca), `browser` (Chrome/Chromium senza schermo), `finestra` (finestra
vera con WebKitGTK sotto Xvfb), `lento`.
Ogni test ha una casa finta (`HOME`, `APPDATA`, `XDG_*`), `IMPAGINATORE_DIALOGHI=nessuno`, `IMPAGINATORE_FINESTRA=no` e
aggiornamenti spenti. Gli aggiornamenti si provano con release finte firmate con una chiave dei test
(`tests/aiuti_aggiornamenti.py`); `tests/test_aggiornamenti_programma.py` fa il giro vero con processi veri (installa,
riavvia nella versione nuova, torna indietro). I processi che eseguono copie del programma fuori da `src` girano senza
coverage (sarebbero file estranei al rapporto).

## Cosa non è verificato

Pacchetti di installazione (T-302): programma compilato, `.deb`, installazione e prova del programma installato
provati solo su Linux; macOS e Windows scritti e affidati alla pipeline `pacchetti.yml`, mai eseguita
(`DISTRIBUZIONE.md`, «Cosa è provato»).

Tutto è stato provato su Linux (Python 3.12). Su macOS e Windows i rami del codice sono provati simulando il sistema
(`sys.platform`) e intercettando i comandi; l'esecuzione vera (osascript, COM di Photoshop, PowerShell, tkinter su Windows,
`Impaginatore.app` con il ponte) va provata su una macchina reale.

Aggiornamenti (T-207): il giro completo è provato su Linux con processi veri e una release in una cartella; la rete
vera (api.github.com, la CDN degli asset, un proxy) non è provata, né il salto `os.execv` e il riavvio su Windows e macOS
(dettagli in `AGGIORNAMENTI.md`, «Cosa non è provato»). Schermata di avvio: vista davvero solo con WebKitGTK sotto Xvfb
(`docs/prodotto/ux/schermate/2.0/avvio-*.png`).

Finestra desktop: provata davvero solo con WebKitGTK 2.52 (WebKit2 4.1) sotto Xvfb, Python 3.12, pywebview 6.2.1
(schermata, editor nella stessa finestra, finestre di scelta GTK della schermata e dell'editor, navigazioni fuori dal
programma fermate, gettone assente dall'ambiente dei processi di WebKit, chiusura ordinata). Non provati: WKWebView su
macOS (solo il controllo dopo il caricamento: la pagina esterna può partire prima di essere lasciata), WebView2 su
Windows (filtro NavigationStarting scritto sui nomi di pywebview 6.2, mai eseguito), le finestre di scelta di pywebview
su macOS, `alert`/`confirm`/`prompt` nella finestra, un `target=_blank` cliccato dall'utente (WebKit blocca i
`window.open` senza gesto dell'utente), Wayland vero, schermi multipli veri, finestra massimizzata su un desktop vero.
