# Architettura dell'Impaginatore (2.0, fondamenta)

Stato: fine del compito T-006 (fase 0). Il comportamento è quello della 1.5.2: stessa interfaccia, stesso formato dei
progetti, stesse operazioni. Cambia la struttura: un pacchetto Python installabile (`src/impaginatore`), uno strato che
isola le differenze tra macOS, Windows e Linux, nessun effetto all'import, una base di test.

## Mappa dei moduli

```
src/impaginatore/
├── __init__.py          __version__ (unico posto della versione: lo leggono pyproject, home, editor, aggiornamenti)
├── __main__.py, cli.py  comando «impaginatore»: schermata dei progetti, oppure «impaginatore editor ...»
├── servizio.py          ServerLocale (ThreadingHTTPServer su 127.0.0.1), Gestore (controlli di sicurezza di ogni richiesta), porta_libera()
├── sicurezza.py         gettone di sessione, URL di avvio monouso, file di sessione per i client locali (docs/architettura/SICUREZZA.md)
├── percorsi.py          radici consentite: i percorsi che arrivano dalla pagina restano nelle cartelle del progetto o scelte dall'utente
├── giornale.py          registro «impaginatore» su file a rotazione nella cartella dei dati
├── formato.py           l'unico modulo che legge e scrive spec.py / progetto.json (carica, salva, testo_spec, conta_spread...)
├── home/server.py       schermata dei progetti: elenco, nuovo, apri (lancia l'editor), ZIP, cestino, aggiornamenti
├── editor/server.py     editor di un album: stato in memoria, operazioni, annulla/ripeti, anteprime, Tono, esportazioni
├── motore/              motore di impaginazione (viene dalla skill «impaginazione-album-stefano»)
│   ├── album.py         progetto caricato, geometria, foto (metadati, miniature, volti con OpenCV), moduli P/FULL/DUO..., render
│   ├── album_libere.py  cornici libere, angoli, stili, testi liberi, tono/ritocco: si «installa» dentro album all'import
│   ├── testo.py         testi liberi: font installati (nomi letti dai file), misura e disegno
│   ├── compat.py        nomi 1.x «album», «album_libere», «testo» come moduli di primo livello (per spec.py e i PSD)
│   ├── photoshop.py     funzioni per gli script (app_name, run_jsx, open_documents) + libreria ExtendScript JS_LIB
│   ├── genera_psd_angolo.py  esegue genera_psd.py con le aggiunte per angoli, testi, tono, sRGB (sostituzioni sul testo)
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
                 ├─ /api/import, /api/ripristina -> salva e riparte con gli stessi argomenti (processi.riesegui = os.execv)
                 └─ export PSD -> python -m impaginatore.motore.genera_psd_angolo --progetto P --spread ...
                       └─ Photoshop: osascript «do javascript» (Mac) / cscript + COM (Windows); su Linux si ferma prima
```

- Porta libera: si prova ad aprirla davvero (bind); su macOS e Linux si controlla anche che nessuno risponda. Niente
  `lsof`, niente `connect_ex` su 99 porte (su Windows costava secondi per porta).
- Un'istanza sola: se la porta della home risponde a `/api/ping` (con il gettone del suo file di sessione), il comando apre
  solo la pagina, con un URL di avvio nuovo.
- `--porta 0`: porta libera qualsiasi (test, finestra desktop futura); l'indirizzo vero è nella prima riga stampata.
- Ogni richiesta vuole il gettone del suo server (intestazione o, per pagina e immagini, cookie dato dall'URL di avvio):
  `docs/architettura/SICUREZZA.md`. La pagina dell'editor chiede aggiornamenti (`/api/aggiornamento`) e ritorno ai progetti
  (`/vai/progetti`) al suo server, che li chiede alla home con il gettone della home (niente più CORS `*`).
- Uscita: `/api/esci` termina gli editor lanciati da quella home e chiude il processo (`home.server.esci`).
- Dopo un aggiornamento: la home chiude gli editor, rilancia `python -m impaginatore --porta <stessa> --no-browser` dopo 1,5 s
  (processo staccato) ed esce; la pagina si ricarica da sola.
- macOS, versione 1.x: `Impaginatore.app` esegue `cd "<cartella dell'app>/Editor Album" && ~/.album-tools/venv/bin/python home.py --porta 8765 --daemon`;
  `legacy/macos/Editor Album/home.py` passa gli argomenti a `impaginatore.cli.main`. `--daemon` (doppio fork) c'è solo su POSIX.

## Formato dei progetti

Invariato rispetto alla 1.5.2 (cartella con `progetto.json` + `spec.py`, vedi `formato.py`). `spec.py` è codice Python
(`from album import *`, `SPREADS = [...]`): `formato.carica` lo compila dal testo e lo esegue con i nomi 1.x resi
disponibili da `motore/compat.py` (un cercatore in `sys.meta_path` che restituisce i moduli del pacchetto), senza lasciare
`__pycache__` nel progetto. Quando ci sono cornici libere/angoli/testi, `formato.salva` copia ancora `album_libere.py`,
`testo.py`, `vib_lut.npz` accanto a `spec.py` (le leggono gli script 1.x; il programma usa sempre le sue): per questo quei
due moduli funzionano anche da soli (`try: from . import album / except ImportError: import album`).
I test `tests/test_formato.py` provano: progetto salvato dalla 1.5.2 riaperto e risalvato identico; stesse operazioni
della 1.5.2 -> stesso `spec.py` (misure dei testi a parte, dipendono dai font), stesso `progetto.json`, stesso stato;
progetto salvato dalla 2.0 aperto con l'`album.py` della 1.5.2.

## Stato globale che resta (un progetto per processo)

| Dove | Cosa | Chi lo azzera |
|---|---|---|
| `motore/album.py` | PROJ, CFG, M (foto), F (volti), IDX, CW/CH/G..., TITLE, INK, font dei titoli | `carica_progetto(cartella)` |
| `motore/album_libere.py` | sostituisce funzioni di `album` (`_place`, `zcrop.__code__`, `_photo`, `render`, `_text`, `apply_ev`, `layout.__code__`) la prima volta che viene importato; cache `_VIB` | mai (è voluto: vale per tutto il processo) |
| `motore/testo.py` | `_FONTS` (elenco dei font, una volta per processo), `DIRS`/`CACHE` sovrascrivibili | riavvio |
| `editor/server.py` | PROJ, HOME, CFG (= `album.CFG`), SP, GD, UNDO/REDO, CLIP, LOG, SAVED, REV, LASTC, BOOT, BL/VW/VH, NPH, UT_FILE, cache (CACHE, TH, INFO, PV, FT, TONO_*), LAST, SAVE_ERR, LASTDIR, AGG, `_ICC` | `inizializza(progetto, home)` |
| `home/server.py` | PROGETTI, REG, PORTA, AGGIORNAMENTI, EDITORS (processi figli), SERVER, RADICI (cartelle scelte) | `configura(...)`, `crea_server(...)`; `RADICI.scelte` vale per la sessione |
| `piattaforma/dialoghi.py` | implementazione scelta con `imposta()` | `imposta(None)` |
| `piattaforma/font.py` | `_cerca_linux` in `lru_cache` | riavvio |
| `motore/compat.py` | cercatore in `sys.meta_path` (installato alla prima lettura di uno spec) | `disinstalla()` |
| PIL | `Image.MAX_IMAGE_PIXELS` = `album.limite_pixel()` (160 MP, `IMPAGINATORE_MAX_MPIXEL`), impostato da `carica_progetto` e `apri_foto` | — |
| `formato.carica` | aggiunge per un attimo la cartella del progetto a `sys.path` e spegne la scrittura dei .pyc | lo rimette com'era |

Conseguenza: in un processo c'è un solo editor «vivo». I test usano l'editor nello stesso processo, uno alla volta.

## Punti di estensione

- **Formato di salvataggio** (T-101): `formato.py`. Un formato nuovo (JSON) va aggiunto lì: `carica` sceglie il lettore,
  `salva` scrive il nuovo; spec.py resta leggibile (migrazione) e va tolto l'`exec` sui dati dell'utente.
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
- **Riavvio dell'editor**: `editor.server.riavvia_processo` (di serie `os.execv` con gli stessi argomenti) si può sostituire
  quando l'editor gira dentro un altro processo.
- **Photoshop**: `piattaforma.photoshop.trova / esegui_jsx / esegui_js`; i test li sostituiscono con un Photoshop finto.

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
Marcatori: `photoshop` (saltati se Photoshop manca), `browser` (Chrome/Chromium senza schermo), `lento`.
Ogni test ha una casa finta (`HOME`, `APPDATA`, `XDG_*`), `IMPAGINATORE_DIALOGHI=nessuno` e aggiornamenti spenti.

## Cosa non è verificato

Tutto è stato provato su Linux (Python 3.12). Su macOS e Windows i rami del codice sono provati simulando il sistema
(`sys.platform`) e intercettando i comandi; l'esecuzione vera (osascript, COM di Photoshop, PowerShell, tkinter su Windows,
`Impaginatore.app` con il ponte) va provata su una macchina reale.
