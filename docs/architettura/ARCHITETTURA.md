# Architettura dell'Impaginatore (2.0, fondamenta)

Stato: fine del compito T-006 (fase 0). Il comportamento è quello della 1.5.2: stessa interfaccia, stesso formato dei
progetti, stesse operazioni. Cambia la struttura: un pacchetto Python installabile (`src/impaginatore`), uno strato che
isola le differenze tra macOS, Windows e Linux, nessun effetto all'import, una base di test.
Dopo T-101 il formato dei progetti è `album.json` (solo dati): vedi «Formato dei progetti» e `FORMATO-PROGETTO.md`.

## Mappa dei moduli

```
src/impaginatore/
├── __init__.py          __version__ (unico posto della versione: lo leggono pyproject, home, editor, aggiornamenti)
├── __main__.py, cli.py  comando «impaginatore»: schermata dei progetti, oppure «impaginatore editor ...»
├── servizio.py          ServerLocale (ThreadingHTTPServer su 127.0.0.1), Gestore (controlli di sicurezza di ogni richiesta), porta_libera()
├── sicurezza.py         gettone di sessione, URL di avvio monouso, file di sessione per i client locali (docs/architettura/SICUREZZA.md)
├── percorsi.py          radici consentite: i percorsi che arrivano dalla pagina restano nelle cartelle del progetto o scelte dall'utente
├── giornale.py          registro «impaginatore» su file a rotazione nella cartella dei dati
├── formato.py           l'unico modulo che legge e scrive l'impaginazione (album.json) e i JSON del progetto; scritture atomiche
├── formato_1x.py        spec.py delle 1.x: lettura con ast senza eseguirlo (migrazione) e scrittura per «Esporta per la 1.x»
├── validazione.py      controllo dei dati letti da un progetto (album.json, progetto.json, modelli, cache): ErroreProgetto
├── archivio.py         estrazione sicura di uno ZIP di progetto (percorsi, limiti, tipi di file)
├── nomi.py             nome del progetto (un dato) e nome di cartella valido su macOS, Windows e Linux
├── ed25519.py          firme Ed25519 (RFC 8032) con la sola libreria standard: chiavi di licenza, elenco delle revoche
├── licenze/            licenze, fasce di tier.json, prova gratuita, sola lettura, filigrana; tutto in locale (LICENZE.md)
├── home/server.py       schermata dei progetti: elenco, nuovo, apri (lancia l'editor), ZIP, cestino, aggiornamenti, licenza
├── editor/server.py     editor di un album: stato in memoria, operazioni, annulla/ripeti, anteprime, Tono, esportazioni
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
│   └── processi.py      ambiente dei figli (UTF-8), riavvio con gli stessi argomenti, rilancio ritardato, distacco dal terminale
├── aggiornamenti/       interfaccia Aggiornamenti; git.py (checkout git), NonDisponibili (installato o spento), firmati.py (contratto dei pacchetti firmati)
└── risorse/             home.html, index.html (interfaccia), vib_lut.npz (vibranza misurata in Photoshop)
tests/                   pytest; dati/progetto_152 = progetto salvato dalla 1.5.2 (riferimento di parità)
legacy/macos/            Impaginatore.app (applet compilata), .command, setup.sh; «Editor Album/home.py» è un ponte per l'applet
skill/impaginatore-stefano/  istruzioni per Claude (SKILL.md, references, assets)
```

## Processi e porte

```
impaginatore [--porta 8765] [--no-browser] [--progetti DIR] [--daemon]
 └─ home (processo 1) 127.0.0.1:8765  ── apre il browser su un URL di avvio monouso (http://127.0.0.1:8765/avvio?c=…)
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

- Porta libera: si prova ad aprirla davvero (bind); su macOS e Linux si controlla anche che nessuno risponda. Niente
  `lsof`, niente `connect_ex` su 99 porte (su Windows costava secondi per porta).
- Un'istanza sola: se la porta della home risponde a `/api/ping` (con il gettone del suo file di sessione), il comando apre
  solo la pagina, con un URL di avvio nuovo.
- `--porta 0`: porta libera qualsiasi (test, finestra desktop futura); l'indirizzo vero è nella prima riga stampata.
- Ogni richiesta vuole il gettone del suo server (intestazione o, per pagina e immagini, cookie derivato dato dall'URL di
  avvio, che lascia il gettone nella `sessionStorage` della scheda): `docs/architettura/SICUREZZA.md`. La pagina dell'editor
  chiede aggiornamenti (`/api/aggiornamento`) e ritorno ai progetti (`/api/vai_progetti`) al suo server, che li chiede alla
  home con il gettone della home (niente più CORS `*`).
- Uscita: `/api/esci` termina gli editor lanciati da quella home e chiude il processo (`home.server.esci`).
- Dopo un aggiornamento: la home chiude gli editor, rilancia `python -m impaginatore --porta <stessa> --no-browser` dopo 1,5 s
  (processo staccato) ed esce; la pagina si ricarica da sola.
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
| `piattaforma/font.py` | `_cerca_linux` in `lru_cache` | riavvio |
| PIL | `Image.MAX_IMAGE_PIXELS` = `album.limite_pixel()` (160 MP, `IMPAGINATORE_MAX_MPIXEL`), impostato da `carica_progetto` e `apri_foto` | — |

Conseguenza: in un processo c'è un solo editor «vivo». I test usano l'editor nello stesso processo, uno alla volta.

## Punti di estensione

- **Formato di salvataggio**: `formato.py` e `validazione.py`. Un formato 3 aumenta `validazione.FORMATO`, aggiunge in
  `formato.carica` la conversione dal 2 e un test con un progetto salvato nel formato 2 (vedi `FORMATO-PROGETTO.md`).
- **Finestre di scelta**: `piattaforma.dialoghi.imposta(oggetto con _scegli(tipo, messaggio))` per tutto il processo;
  `IMPAGINATORE_DIALOGHI=mac|tk|zenity|kdialog|nessuno` per sceglierle per nome (vale anche per i processi figli).
- **Finestra desktop** (T-201): `home.server.configura(...)` + `crea_server(0)` in un thread + finestra pywebview sull'indirizzo;
  dialoghi di pywebview con `dialoghi.imposta`; l'editor si può tenere in processo separato come ora.
- **Aggiornamenti** (T-207): implementare `aggiornamenti.Aggiornamenti` (stato, controlla, versioni, aggiorna, ripristina,
  ciclo) e passarlo a `home.server.configura(aggiorna=...)` o farlo scegliere da `aggiornamenti.predefiniti()`.
- **Licenze** (T-202): il punto d'ingresso unico è `cli.main` (e `home.server.main` / `editor.server.main`); le funzioni a
  pagamento passano tutte dalle richieste HTTP (`H.do_POST` di home ed editor) e dalle funzioni `run_export`, `esporta_progetto`:
  lì va il controllo della fascia (`docs/mercato/tier.json`).
- **MCP** (T-203): le azioni esistono già come funzioni senza interfaccia: `home.server.nuovo`, `editor.server.inizializza`,
  `do_import`, `do_op` (tutte le operazioni dell'editor, stesso formato JSON della pagina), `templates_for`, `save`,
  `run_export`. Un server MCP può chiamarle nello stesso processo (un progetto per volta) oppure usare l'API HTTP dell'editor.
  Le operazioni aggiunte per l'interfaccia nuova e per l'assistente (altra disposizione, sostituisci, controllo,
  «Sistema», bozza, annulla con nome, ricollega con prova, import a caldo) sono descritte in `OPERAZIONI.md`.
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
| `IMPAGINATORE_DIALOGHI` | finestre di scelta per nome (`nessuno` nei test) |
| `IMPAGINATORE_AGGIORNAMENTI=no` | aggiornamenti spenti |
| `IMPAGINATORE_SENZA_RIAVVIO` | dopo un aggiornamento non riavvia (prove) |
| `IMPAGINATORE_GETTONE` | gettone di sessione del server di questo processo (lo scrive il server; resta dopo un riavvio, non passa ai figli) |
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
Marcatori: `photoshop` (saltati se Photoshop manca), `browser` (Chrome/Chromium senza schermo), `lento`.
Ogni test ha una casa finta (`HOME`, `APPDATA`, `XDG_*`), `IMPAGINATORE_DIALOGHI=nessuno` e aggiornamenti spenti.

## Cosa non è verificato

Tutto è stato provato su Linux (Python 3.12). Su macOS e Windows i rami del codice sono provati simulando il sistema
(`sys.platform`) e intercettando i comandi; l'esecuzione vera (osascript, COM di Photoshop, PowerShell, tkinter su Windows,
`Impaginatore.app` con il ponte) va provata su una macchina reale.
