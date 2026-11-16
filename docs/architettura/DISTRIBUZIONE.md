# Distribuzione: programma compilato e pacchetti di installazione (T-302)

Stato al 16/11/2026: costruzione, pacchetto e prova scritti per i tre sistemi e provati nella pipeline di GitHub su
Linux, Windows e Mac Intel, con il programma installato come lo installerebbe un utente e la sua finestra vera (sotto,
«Cosa è provato»). Il pacchetto per i Mac con chip Apple non è ancora stato costruito: GitHub non ha trovato un runner
macOS arm64 libero (sotto, «Pipeline»). Per la beta privata, senza certificati Apple e Microsoft, per scelta del
titolare.

Guida per chi installa: `docs/manuale/00-installazione.md`. Aggiornamenti: `AGGIORNAMENTI.md`.

## In breve

| Sistema | Pacchetto | Dove si installa | Firma |
|---|---|---|---|
| macOS chip Apple | `Impaginatore-<v>-mac-arm64.dmg` | `/Applications/Impaginatore.app` (trascinandolo) | ad hoc (`codesign --sign -`), senza notarizzazione |
| macOS Intel | `Impaginatore-<v>-mac-x86_64.dmg` | come sopra | come sopra |
| Windows 10/11 x64 | `Impaginatore-<v>-windows.exe` (Inno Setup 6) | `%LOCALAPPDATA%\Programs\Impaginatore`, senza amministratore | nessuna (niente Authenticode) |
| Linux | `Impaginatore-<v>-linux.deb` (Ubuntu 24.04 e derivate) | `/opt/impaginatore`, comando `/usr/bin/impaginatore` | firma della release (sotto) |

L'eseguibile si chiama `impaginatore.exe` su Windows e `impaginatore-app` su macOS e Linux: lì non può chiamarsi
`impaginatore`, perché accanto c'è la cartella dei dati del pacchetto (`impaginatore/risorse/…`); Nuitka lo rifiuta e il
disco del Mac non distingue maiuscole e minuscole. Su Linux il comando resta `impaginatore` (`/usr/bin/impaginatore`).

Accanto a ogni pacchetto la costruzione scrive `<pacchetto>.sha256` e `<pacchetto>.componenti.json` (componenti di terze
parti con versione e licenza). L'integrità per chi scarica è l'impronta SHA-256 pubblicata con la release
(`SHA256SUMS`) e, per gli aggiornamenti, il manifesto firmato Ed25519 che la contiene (`AGGIORNAMENTI.md`).

Cosa non si fa, per decisione del titolare: niente script o comandi che tolgono la quarantena, spengono Gatekeeper o
SmartScreen o cambiano attributi dei file scaricati; niente installatori «di una riga» che lo farebbero. Gli avvisi del
sistema restano e la guida li spiega.

## Come si costruisce

```
UV_PROJECT_ENVIRONMENT=.venv-compilazione uv sync --locked --python 3.12 --extra desktop --extra mcp --extra compilazione
.venv-compilazione/bin/python strumenti/compila.py                 # programma + pacchetto in dist/pacchetti
.venv-compilazione/bin/python strumenti/verifica_pacchetto.py build/compila/linux/Impaginatore/impaginatore-app --finestra
```

- `strumenti/compila.py` (stesso comando sui tre sistemi, costruisce per quello su cui gira): Nuitka in modalità
  standalone (macOS: `--mode=app`), punto d'ingresso `strumenti/compilazione/avvio_impaginatore.py` (= `cli.main`),
  poi il pacchetto del sistema. Opzioni `--solo-programma`, `--solo-pacchetto`, `--uscita`.
- Nuitka gira con `python -X utf8`: il programma compilato prende la modalità UTF-8 da chi lo compila e non legge
  `PYTHONUTF8` (Nuitka ignora le variabili `PYTHON*`). Senza, su Windows il compilato scriverebbe in cp1252 nei tubi e nei
  registri (il messaggio «Photoshop non è stato trovato» del sottocomando `_psd` arriverebbe rovinato all'editor),
  mentre il pacchetto Python dà UTF-8 a ogni processo figlio (`processi.ambiente_figli`). Su Linux e macOS non cambia
  niente di visibile.
- Cache: con `NUITKA_CACHE_DIR` Nuitka tiene lì ccache (Linux, macOS; va installato: `apt install ccache`, `brew
  install ccache`), il suo clcache (Windows con MSVC) e i moduli già analizzati. Una seconda compilazione rifà solo i
  file C cambiati.
- Nuitka è nell'extra `compilazione` di `pyproject.toml` (versione fissata, 4.3.5, con `patchelf` su Linux): entra solo
  nell'ambiente di compilazione `.venv-compilazione`, mai nel programma distribuito né in quello di sviluppo.
- Serve un compilatore C: Linux `gcc` (con `ccache` va più veloce), macOS gli strumenti a riga di comando di Xcode,
  Windows Visual Studio (MSVC, c'è sui runner di GitHub) o, se manca, MinGW64 che Nuitka scarica da solo
  (`--assume-yes-for-downloads`). Su Windows serve anche Inno Setup 6 (`iscc`, nel PATH o nella cartella di serie).
- Linux vuole Python 3.12: la finestra usa il PyGObject del sistema (sotto), che su Ubuntu 24.04 è compilato per la 3.12.
- La pipeline `.github/workflows/pacchetti.yml` fa lo stesso giro sui runner dei tre sistemi (sotto).

### Cosa c'è nel programma compilato

- Il pacchetto `impaginatore` tradotto in C e compilato: **nessun file `.py` né `.pyc` del programma** nel pacchetto
  (`compila.controlla_programma` lo controlla, e la prova lo ricontrolla sul programma installato). Le dipendenze
  (numpy, OpenCV, Pillow, psd-tools, pywebview, SDK MCP…) sono compilate anche loro o copiate come librerie native.
- I dati del pacchetto (`risorse/`: pagine HTML, JavaScript, testi, icone, `avvio.html`) restano file leggibili. La
  prova controlla che ci siano tutti quelli del sorgente (`verifica_pacchetto.dati_mancanti`: testi delle statistiche e
  della licenza beta compresi).
- `risorse/motore_1x/*.txt`: i sorgenti di `album_libere.py` e `testo.py` che «Esporta per la 1.x» copia nel progetto
  accanto allo `spec.py` scritto dall'album, perché la 1.x li esegue (`formato_1x.sorgente_motore`). Sono leggibili: è
  codice che finisce in chiaro in ogni progetto esportato per la 1.x, quindi compilarlo non lo proteggerebbe.
- File che Nuitka non vede da solo e `compila.py` aggiunge: i due modelli di OpenCV per i volti
  (`cv2/data/haarcascade_*.xml`, `compila.CASCATE_OPENCV`: senza, l'apertura di un album nel sottocomando dei PSD si ferma
  con un errore di OpenCV e l'editor non trova volti senza dirlo), il modulo che l'SDK MCP carica per nome
  (`DA_INCLUDERE`) e, su Linux, i moduli della libreria standard che il PyGObject del sistema importa e il programma no
  (`PER_GI_DEL_SISTEMA`: senza `optparse` la finestra non parte e si apre il browser). Un test confronta ciascun elenco
  con il codice (o con il `gi` del sistema, se c'è).
- `licenze-terze-parti/`: il testo di licenza di ogni componente incluso e `componenti.json` (macOS: dentro
  `Impaginatore.app/Contents/Resources`). Lo scrive `compila.scrivi_licenze` dal rapporto di Nuitka
  (`build/compila/<chiave>/compilazione.xml`): solo le distribuzioni davvero incluse, più Python e le librerie native.
- Esclusi apposta (`compila.ESCLUSI_SEMPRE`, `ESCLUSI`): strumenti di sviluppo e prova, `pillow_heif` (sotto), `gi` e
  `cairo` (Linux li prende dal sistema), `tkinter` su macOS e Linux (le finestre di scelta sono quelle del sistema), il
  `.jar` Android di pywebview.

### Quanto protegge la compilazione

Nuitka traduce il codice Python in C: nel programma non c'è il sorgente né il bytecode, e ricostruire il codice
originale da un eseguibile compilato richiede un lavoro di reverse engineering paragonabile a quello di un programma
scritto in C. Non è una cifratura: con la versione gratuita di Nuitka le costanti (testi, nomi di funzioni e di chiavi,
messaggi) restano leggibili nel binario con `strings`, e le pagine dell'interfaccia sono file HTML e JavaScript in
chiaro. Le docstring si tolgono (`--python-flag=no_docstrings`). La protezione delle costanti (`--embed-data`, cifratura)
è della versione commerciale di Nuitka: non serve per la beta.

La licenza non dipende dalla segretezza del codice: le chiavi sono firmate Ed25519 e il programma ha solo la chiave
pubblica (`LICENZE.md`).

### Il programma compilato lancia se stesso

Il pacchetto Python lancia i suoi processi con `python -m impaginatore…` e `python -c …`; il compilato non ha un Python
separato. `compilato.py` decide la riga di comando (`compilato.comando`):

| Processo | Pacchetto Python | Programma compilato |
|---|---|---|
| editor | `python -m impaginatore.editor …` | `impaginatore editor …` |
| schermata (rilancio dopo un aggiornamento) | `python -m impaginatore …` | `impaginatore _rilancia <ritardo> …` |
| server MCP che avvia il programma | `python -m impaginatore …` | `impaginatore …` |
| PSD (Photoshop) | `python -m impaginatore.motore.genera_psd_angolo …` | `impaginatore _psd …` |
| finestra di scelta tkinter (Windows senza WebView2) | `python -c …` | `impaginatore _dialogo …` |
| pagina della schermata di avvio, per la prova del programma installato | `python -m impaginatore _avvio` | `impaginatore _avvio` |

I sottocomandi che iniziano con `_` sono interni (`compilato.INTERNI`): non mostrano la schermata di avvio e non contano
come avvii per il ritorno automatico alla versione precedente.

Il compilato **non avvia mai copie dalla cartella dei dati**: `lanciatore.avvia` esce subito quando `compilato.attivo()`.
Una «versione aggiornata» messa in `<dati>/programma/versioni/` (da un aggiornamento del pacchetto Python, o da chiunque
possa scrivere in quella cartella) resta ignorata. `verifica_pacchetto.py` lo prova con una copia finta e un file spia.

Due adattamenti del codice per Nuitka, provati dai test anche nel pacchetto Python: `motore/album_libere.py` non cambia
più `__code__` alle funzioni del motore se Nuitka non lo permette (usa `functools.partial`), e `formato_1x` legge le
copie del motore dalle risorse quando i `.py` non ci sono.

## Sistema per sistema

### macOS

- `Impaginatore.app` (identificativo `it.impaginatore.Impaginatore`, da non cambiare dopo il primo rilascio: macOS lega
  a quello i permessi dati dall'utente, come l'accesso a Documenti e Scrivania) dentro un DMG compresso (UDZO) con il
  collegamento ad Applicazioni.
- Firma **ad hoc** (`codesign --force --deep --sign -`), poi `codesign --verify --deep --strict`: sui Mac con chip Apple
  il sistema non esegue un binario arm64 senza nessuna firma, quella ad hoc basta. È il comportamento normale degli
  strumenti: Nuitka firma già ad hoc alla fine della compilazione (`--macos-sign-identity`, di serie «ad-hoc») e
  `compila.py` rifirma allo stesso modo dopo aver aggiunto le licenze (che cambiano il contenuto del bundle). Non è
  un'identità e non tocca quarantena né impostazioni del sistema: Gatekeeper al primo avvio blocca il programma
  scaricato e l'utente lo apre da Impostazioni › Privacy e sicurezza › «Apri comunque» (macOS 15 ha tolto la scorciatoia
  Ctrl-clic › Apri). La guida lo spiega passo per passo.
- `hdiutil create` sui Mac di GitHub a volte risponde «Resource busy»: `compila.ripeti` lo riprova fino a 4 volte.
- Un DMG per architettura (`mac-arm64` su `macos-15`, `mac-x86_64` su `macos-15-intel`): Nuitka non fa binari universali
  da un solo ambiente e le ruote di numpy/OpenCV sono per architettura. Il manifesto degli aggiornamenti ha una chiave
  per ognuna.
- Il bundle va nel DMG copiato con `ditto`: `codesign` firma i file di dati in `Contents/MacOS` con la firma negli
  attributi estesi, che `shutil.copytree` su macOS perde (sotto, «Problemi»). La firma si controlla sul bundle e sulla
  copia, e la pipeline la ricontrolla sul DMG montato.
- Mac Intel: **cryptography** (la usa il server MCP: `mcp.server.request_state`, via `pyjwt[crypto]`) non ha più ruote
  per macOS x86_64 dalla 49 (l'ultima con le ruote è la 48.0.1); `uv.lock` ha la 50.0.2. Sul Mac Intel uv la costruisce
  dal sorgente con il Rust del runner e l'OpenSSL 3 di Homebrew collegato in modo statico (`OPENSSL_STATIC=1`).
  Provato nella pipeline: circa 3 minuti, e nell'elenco delle librerie native del programma non c'è nessuna libreria
  OpenSSL (né altre di Homebrew).
- Versione minima di macOS: la decide la libreria che chiede la versione più alta; `compila.macos_minimo` la legge da
  tutti i binari del bundle (`otool -l`) e la scrive in `componenti.json`, nel registro della costruzione e nel rapporto
  della prova (`misure.macos_minimo`). Sul Mac Intel è **14.0** (pipeline, 16/11/2026; Nuitka da solo direbbe 10.15, ma
  numpy e OpenCV vogliono 14). Sul Mac con chip Apple ci si aspetta lo stesso (numpy 2.5.4 `macosx_14_0_arm64`): da
  misurare.
- Finestre di scelta: quelle del Finder (osascript), come nel pacchetto Python.

### Windows

- Installatore Inno Setup 6 (`strumenti/compilazione/impaginatore.iss`), **per l'utente** (`PrivilegesRequired=lowest`):
  non chiede la password di amministratore e non scrive in `Program Files`. Italiano e inglese. `AppId` fisso: una
  versione nuova si installa sopra la vecchia (la cartella del programma si svuota prima, `InstallDelete`). Il file è in
  UTF-8 con BOM, perché Inno Setup legga giusti gli accenti e le «» dei messaggi. Inno Setup 6.7.1 c'è già
  sull'immagine `windows-2025` di GitHub (immagine 20261111); se manca la pipeline lo installa con choco.
- Compilatore: MSVC di Visual Studio 2022 (17.14 sull'immagine `windows-2025`), con il clcache di Nuitka.
- Non firmato: SmartScreen mostra «Windows ha protetto il PC» la prima volta e l'utente sceglie «Ulteriori
  informazioni» › «Esegui comunque». La reputazione di SmartScreen per un file non firmato si azzera a ogni versione.
- WebView2: l'installatore controlla nel registro se c'è e, se manca, lo dice (non lo scarica). Senza WebView2 il
  programma si apre nel browser; le finestre di scelta usano tkinter (incluso solo su Windows, `--enable-plugin=tk-inter`).
- Eseguibile con console «attach» (`--windows-console-mode=attach`): aperto da Start non mostra una console, da un
  terminale scrive lì (serve a `impaginatore mcp` su stdio). Dal codice di Nuitka 4.3.5 (`HelpersConsole.c`): si attacca
  alla console di chi lo lancia e tiene i canali già rediretti (tubi, file), quindi la prova e un assistente AI che
  parlano con lui su stdin/stdout li ricevono. Provato nella pipeline: il controllo «mcp» parla con il programma
  installato su stdin/stdout. Che aperto da Start non mostri una console è da guardare su un PC vero.
- WebView2: c'è sull'immagine `windows-2025` di GitHub (la finestra della prova si apre con WebView2), anche se il suo
  elenco del software non lo nomina.
- L'icona della finestra su Windows è un `.ico` (`risorse/icona.ico`, la stessa di `brand/icona/icona.ico`): con il PNG
  la finestra non si apriva (sotto, «Problemi»).
- Antivirus: i programmi compilati con Nuitka e non firmati a volte vengono segnalati per errore. Se succede, si manda il
  file al produttore dell'antivirus come falso positivo; la guida dice all'utente di non spegnere l'antivirus.

### Linux

- Pacchetto `.deb` per Ubuntu 24.04 e derivate (`dpkg-deb --root-owner-group -Zxz`): `/opt/impaginatore`, collegamento
  `/usr/bin/impaginatore`, voce del menu, icone, `copyright` con le licenze.
- La finestra usa **GTK e WebKitGTK del sistema** attraverso il PyGObject del sistema (`python3-gi`, `gir1.2-gtk-3.0`,
  `gir1.2-webkit2-4.1`, dipendenze del pacchetto: apt le installa). PyGObject non si può includere in modo affidabile
  (le librerie GTK e WebKit e i loro dati sono del sistema), quindi `compilato.SoloGi` carica solo `gi` e `cairo` dalla
  cartella del sistema, e funziona solo se il Python del programma (3.12) è quello per cui il PyGObject del sistema è
  compilato: Ubuntu 24.04, Mint 22, Pop!_OS 24.04. Su altre distribuzioni la finestra non si apre e il programma va nel
  browser, come il pacchetto Python senza l'extra `desktop`.
- AppImage (nel piano) non c'è: per le stesse ragioni dovrebbe includere GTK e WebKit (centinaia di MB, aggiornamenti di
  sicurezza di WebKit a carico nostro). Da decidere se serve davvero per la beta.

## Aggiornamenti del programma compilato

Il programma compilato **non si sostituisce da solo** (`InstallazioneCompilata`, `AGGIORNAMENTI.md`). Controlla il
manifesto firmato come il pacchetto Python e mostra l'avviso con le novità; «Scarica la versione nuova» apre nel browser
la pagina della release (`InstallazioneCompilata.indirizzo`) e l'utente installa il pacchetto come la prima volta.

Perché: senza certificati, sostituire il programma da dentro il programma vorrebbe dire scaricare un `.exe` non firmato
ed eseguirlo, o riscrivere un bundle firmato ad hoc che Gatekeeper rimette in quarantena (macOS) o che il programma in
uso tiene aperto (Windows); un errore a metà lascia un programma che non parte, senza un modo sicuro di tornare indietro.
Installato a mano, l'aggiornamento passa dagli stessi controlli del sistema e dall'impronta. Con un certificato
Authenticode si potrà avviare l'installatore firmato in modo silenzioso (Windows), con l'ID sviluppatore Apple sostituire
il bundle notarizzato (macOS): `InstallazioneCompilata` è il solo punto da cambiare.

## Pipeline (`.github/workflows/pacchetti.yml`)

- Permessi in sola lettura, nessun segreto, nessuna release: i pacchetti restano come artefatti dell'esecuzione (30
  giorni sui tag, 7 negli altri giri). Azioni fissate per hash come in `ci.yml`.
- Il repository è pubblico, e con lui registri e artefatti dei giri: l'artefatto di ogni pacchetto contiene solo il
  pacchetto (con `.sha256` e `.componenti.json`) e il riepilogo della verifica (`verifica-<chiave>.json` e le
  fotografie della finestra). Il rapporto di Nuitka e la diagnosi di un controllo che non va non entrano
  nell'artefatto: la diagnosi è nel registro del job.
- Quali pacchetti, per non spendere minuti che non servono:

  | Come parte | Pacchetti | Test e wheel |
  |---|---|---|
  | tag `v*` (rilascio) | tutti e quattro | sì: test su Linux (copertura), macOS e Windows |
  | avvio manuale (quando il file è sul ramo principale) | scelta: `linux` (di serie), `windows`, `mac-arm64`, `mac-x86_64`, `tre`, `tutti` | sì: Linux, più macOS o Windows se c'è il loro pacchetto |
  | push su `pacchetti/<chiave>` | solo quello (`pacchetti/windows`, `pacchetti/mac-arm64`…); `pacchetti/tre` = Linux, Mac chip Apple, Windows; `pacchetti/tutti` e `pacchetti/prova` = tutti e quattro; ogni altro `pacchetti/**` = solo Linux | no (i test li fa `ci.yml` sui rami `prodotto/**`) |

  Un push nuovo sullo stesso ramo `pacchetti/**` annulla il giro precedente; sui tag no.
- Ogni job di pacchetto: licenze delle dipendenze di quel sistema (macOS e Windows ne hanno di proprie: pyobjc,
  pythonnet…; `sicurezza.yml` controlla quelle di Linux; solo sui tag e con l'avvio manuale), ambiente di compilazione,
  `compila.py`, installazione come la farebbe un utente (`apt install ./….deb`; installatore silenzioso, che si installa
  per l'utente; DMG montato in sola lettura con `codesign --verify`), `verifica_pacchetto.py --finestra` sul programma
  installato, disinstallazione (Windows). Ogni job ha un tempo massimo per sistema (Linux e Mac arm64 120 minuti, Mac
  Intel 150, Windows 180), perché un blocco non tenga occupato un runner per ore.
- Cache: uv (con `enable-cache`; sul Mac Intel tiene anche la cryptography costruita dal sorgente) e Nuitka
  (`NUITKA_CACHE_DIR` in `actions/cache`, una chiave per esecuzione e si riparte dall'ultima). La cache di Nuitka si
  salva subito dopo la compilazione, anche quando dopo qualcosa non va.
- La schermata di avvio si prova su tutti i sistemi con `impaginatore _avvio` (la stessa pagina della finestra): versione,
  «Prova gratuita · 30 giorni», «Free trial · 30 days left» e «Sola lettura» dopo una prova finita. «Beta privata» vuole
  una chiave firmata con la chiave vera e si prova nei test (`tests/test_avvio.py`).
- La finestra vera si prova su tutti e tre i sistemi e blocca: la prova accende le statistiche d'uso nella sua cartella
  dei dati (restano lì: il programma non ha un server a cui mandarle) e aspetta l'evento «finestra» che la schermata
  Album manda quando si carica, con la misura della pagina: così sa che la pagina gira **dentro** la finestra (WebKitGTK,
  WKWebView, WebView2), non in un browser. L'evento «avvio» dice che il motore della finestra è partito. Sotto Xvfb
  (Linux) fotografa e giudica la schermata di avvio (`avvio-finestra.png`) e la finestra del programma
  (`finestra-programma.png`); su macOS e Windows fotografa lo schermo (`screencapture`, PowerShell) come documento e il
  riepilogo dice «NON PROVATO su questa macchina» per il giudizio automatico della fotografia.
- La prova va avanti dopo un controllo che non va (quelli che ne dipendono risultano «saltato») e, se qualcosa non va,
  stampa le ultime righe di uscita, registro ed `editor.log` del programma e le salva nell'artefatto
  (`diagnosi-*.txt`): un giro fallito dice tutto quello che c'è da sapere, senza rifarlo per leggere un altro errore.
- Il controllo dei PSD lancia il sottocomando `_psd` su un album vero: carica l'album (volti compresi, con OpenCV) e,
  senza Photoshop, deve fermarsi con il suo messaggio (senza caratteri rovinati) e non con un errore.

### Consumo

Dal 16/11/2026 il repository è pubblico: i runner standard non si pagano e hanno 4 core su Linux, Windows e Mac Intel,
3 sul Mac arm64. Durata dei job di pacchetto misurata nella pipeline (16/11/2026), dall'inizio alla fine del job:

| Pacchetto | Senza cache di Nuitka | Con la cache del giro prima |
|---|---|---|
| linux | 16 min | 5 min |
| windows | più di 26 min (il primo giro si è fermato dopo la compilazione) | 10 min |
| mac-x86_64 | più di 29 min (il primo giro si è fermato al DMG) | 13–15 min |
| mac-arm64 | non misurata (nessun runner) | non misurata |

I job girano in parallelo: un giro dura quanto il più lento. Se il repository tornasse privato, i runner Linux e
Windows avrebbero 2 core (la compilazione senza cache dura circa il doppio) e GitHub conterebbe i minuti macOS 10 volte
e Windows 2 volte, sul piano da 2.000 minuti al mese: un giro dei quattro pacchetti con la cache costerebbe circa
5 + 2 × 10 + 10 × 15 + 10 × 15 = 325 minuti, senza cache più di 1.000; con i test del job `test` (circa 170 minuti
fatturati) un tag ne costerebbe quindi circa 500 con la cache. I rami `pacchetti/<chiave>` servono a provare un
sistema solo.

## Rilascio (T-303, sul computer di chi pubblica)

```
python strumenti/rilascio.py controlla                       # chiavi vere, repository, versione finale, CHANGELOG
python strumenti/rilascio.py prepara <artefatti scaricati> --novita-it "…" --novita-en "…"
```

`prepara` cerca la wheel e i pacchetti `Impaginatore-<v>-<chiave>.<dmg|exe|deb>` negli artefatti della pipeline, li
copia in `dist/rilascio-<v>`, firma il manifesto con la chiave privata dei rilasci (`strumenti/aggiornamento.py firma
--compilato chiave=file`, la chiave non entra mai nella pipeline), lo verifica, scrive `SHA256SUMS` e `NOTE.md` (dal
registro, con le impronte). Se `controlla` trova problemi, o se la chiave privata usata non è quella di `CHIAVI_FIDATE`
(i programmi installati rifiuterebbero la release), si ferma; con `--prova` va avanti e `NOTE.md` dice in testa
«PROVA: NON PUBBLICARE». Le chiavi pubbliche vere di licenze e aggiornamenti sono nel codice dal 16/11/2026: `controlla`
passa su questo punto e si ferma solo se qualcuno rimette i segnaposto. La release si pubblica a mano su GitHub
(`AGGIORNAMENTI.md`, «Come si pubblica»).

L'elenco delle revoche delle licenze (`licenze/revoche.json`) entra nel pacchetto Python al momento del rilascio
(`LICENZE.md`), ma il programma compilato si costruisce nella pipeline dal repository: per averlo anche nei pacchetti
compilati il file va messo nel repository sul tag del rilascio (è firmato e non contiene segreti). Da decidere.

## Licenze di terze parti

- **Nuitka 4.x**: AGPL-3.0 con la «Nuitka Runtime Library Exception», che esclude dagli obblighi dell'AGPL il programma
  compilato e le parti di Nuitka che finiscono dentro. Fino alla 2.x Nuitka era Apache-2.0. Da far confermare al
  legale (o fissare l'ultima 2.x) prima della vendita.
- **OpenCV** (`opencv-python-headless`): include FFmpeg come librerie condivise, sotto LGPL-2.1. Le librerie restano file
  separati e sostituibili nel pacchetto, come chiede la LGPL; il testo della licenza è in `licenze-terze-parti/`. Va
  aggiunta l'offerta del sorgente di FFmpeg (o il collegamento a quello della versione inclusa) nella documentazione
  della release. Da far confermare al legale.
- **HEIC**: `pillow-heif` non entra nel programma compilato perché le sue ruote includono x265 (GPL). Le foto HEIC si
  riconoscono e il programma dice che non le apre (come il pacchetto Python senza l'extra `heic`).
- Inno Setup e Nuitka sono strumenti di costruzione: non entrano nel programma.
- Le licenze delle dipendenze Python passano da `strumenti/controlli.py licenze` (`LICENZE_AMMESSE`): in `sicurezza.yml`
  per Linux, nella pipeline dei pacchetti per macOS e Windows. `compila.py` non le ricontrolla: copia i testi e scrive la
  licenza dichiarata di ogni distribuzione inclusa, e avvisa se una non ha file di licenza.
- `componenti.json` elenca anche i nomi delle librerie native che Nuitka ha messo nel programma. Quasi tutte vengono
  dalle ruote (e sono coperte dalle loro licenze, per esempio `cv2/LICENSE-3RD-PARTY.txt`); quelle che Nuitka prende dal
  sistema di costruzione vanno guardate a mano nell'elenco a ogni cambio di runner.

## Cosa è provato

Pipeline `pacchetti.yml` sul ramo `pacchetti/prova`, 16/11/2026 (runner standard dei repository pubblici):

| | Linux (`ubuntu-24.04`) | Windows (`windows-2025`) | Mac Intel (`macos-15-intel`) | Mac chip Apple |
|---|---|---|---|---|
| Compilazione e pacchetto | provati | provati | provati | **non costruito**: nessun runner arm64 libero (sotto) |
| Installazione come un utente | `apt install ./….deb` | installatore silenzioso, per l'utente, poi disinstallazione | DMG montato in sola lettura, `codesign --verify --deep --strict` | — |
| Programma installato: schermata di avvio (prova, inglese, sola lettura), schermata, editor, JPG e PDF, progetto 1.x, PSD fino a Photoshop, MCP, chiusura | provato | provato | provato | — |
| Finestra vera con la schermata Album caricata dentro | provata (WebKitGTK, Xvfb), fotografie giudicate | provata (WebView2), fotografia nell'artefatto | provata (WKWebView), fotografia nell'artefatto | — |
| Avvisi del sistema (Gatekeeper, SmartScreen) e testi della guida | — | da provare su un PC vero (il runner non ha SmartScreen sul file scaricato) | da provare su un Mac vero (il DMG non viene da internet: niente quarantena) | da provare su un Mac vero |

Su questo computer (Ubuntu 24.04, 12 core) anche il `.deb` estratto e lanciato da un collegamento come
`/usr/bin/impaginatore`, con la stessa prova.

Misure della pipeline (16/11/2026; «con la cache» = cache di Nuitka del giro prima, solo i file C cambiati da rifare):

| | Linux | Windows | Mac Intel |
|---|---|---|---|
| Core del runner | 4 | 4 | 4 |
| Compilazione e pacchetto, senza cache | 15 min (899 s) | 25 min di Nuitka (1.508 s) più Inno Setup | 25 min (1.497 s) |
| Con la cache | 3 min (186 s) | 8 min (488 s) | 10 min (588 s) |
| Pacchetto | `.deb` 92,0 MB | `.exe` 67,7 MB | `.dmg` 98,9 MB |
| Programma installato | 376,2 MB, 196 file, eseguibile 96,4 MB | 278,3 MB, 1.148 file, eseguibile 80,3 MB | 240,9 MB |
| Componenti di terze parti | 34 | 38 | 38 |
| macOS minimo (dalle librerie) | — | — | 14.0 |
| Prova completa con la finestra | 17 s | circa 30 s | circa 90 s (il primo avvio di un programma nuovo su macOS è lento) |

Python 3.12.16 di python-build-standalone (uv) su tutti e tre. Ogni esecuzione mette le misure nel suo riepilogo e in
`verifica-<chiave>.json`.

Problemi che la prova del programma compilato ha trovato, e che i test sul sorgente non vedevano:

- l'eseguibile non può chiamarsi come la cartella dei dati del pacchetto (`impaginatore`): Nuitka si ferma (sopra);
- Nuitka 4 mette in `sys.executable` un `python` che non esiste: l'editor non partiva (`compilato.prepara` lo corregge);
- i modelli di OpenCV per i volti e `optparse` per il `gi` del sistema mancavano (sopra, «Cosa c'è»);
- su Linux la finestra del programma, creata nascosta per la schermata di avvio, non si mostrava mai: pywebview 6 su
  GTK la rinasconde se resta segnata come nascosta (anche dal sorgente; `desktop/avvio.py`). La prova della finestra
  vera (`tests/prova_finestra.py`) ora lo controlla, ma gira solo con un Python che vede il PyGObject del sistema;
- su Windows la finestra non si apriva e il programma si chiudeva: pywebview (WinForms) passa l'icona a
  `System.Drawing.Icon`, che vuole un `.ico` e con il PNG solleva un'eccezione .NET. Valeva anche per il pacchetto
  Python; ora su Windows la finestra riceve `risorse/icona.ico` (`desktop/finestra.ICONA`);
- su macOS `codesign` firma i file di dati che Nuitka mette in `Contents/MacOS` (i modelli di OpenCV, le risorse) con
  la firma negli attributi estesi; `shutil.copytree` su macOS non li copia e il DMG usciva con il bundle «not signed at
  all». Ora il bundle va nel DMG con `ditto` e la firma si ricontrolla sulla copia;
- Nuitka scrive il suo rapporto in UTF-8 dichiarandolo `encoding='utf8'`, che expat legge come una codifica a un byte:
  su Windows la © di `--copyright` lo rendeva illeggibile e il pacchetto non si costruiva (`compila.leggi_rapporto`);
- senza `-X utf8` a Nuitka il compilato su Windows scriverebbe in cp1252 (sopra, «Come si costruisce»): la prova dei PSD
  ora rifiuta anche i caratteri rovinati, e su Windows passa;
- limiti della prova, non del programma: su Windows la cartella temporanea sta in `AppData`, che il programma considera
  riservata (lì la prova ora usa la cartella dell'utente); sul runner Windows lo schermo è 1024 × 768 e la finestra
  (1440 × 900 di serie) esce dallo schermo.

Da guardare su un Mac vero: al primo avvio sul Mac Intel della pipeline macOS ha mostrato «Allow "Impaginatore" to
find devices on local networks?» (Rete locale, macOS 15). La prova è passata con la domanda ancora aperta, quindi il
programma lavora senza quel permesso (i suoi server ascoltano solo su 127.0.0.1); cosa la fa comparire non è ancora
chiaro (`WKWebView`, o una risoluzione del nome del computer). Va capito prima della beta, e intanto la guida dice di
rispondere «Non consentire».

## Decisioni per il titolare

- Nuitka 4.x (AGPL con eccezione) o l'ultima 2.x (Apache-2.0).
- Offerta del sorgente di FFmpeg (LGPL) nella release.
- HEIC escluso dal programma compilato (o una libreria HEIC con licenza compatibile).
- Identificativo del bundle macOS `it.impaginatore.Impaginatore` e indirizzo del sito nel pacchetto `.deb`
  (`impaginatore.example`, segnaposto): definitivi prima del primo rilascio.
- Il Mac Intel nella pipeline: funziona (cryptography costruita dal sorgente, 3 minuti in più) e con il repository
  pubblico non costa; se il repository tornasse privato è il job più caro. La versione minima di macOS è 14.0 (misurata
  sul Mac Intel; sul Mac con chip Apple da misurare).
- Mac con chip Apple: dal passaggio del repository a pubblico i runner macOS arm64 gratuiti non sono stati disponibili
  (GitHub ha annullato i job dopo 15 minuti in coda, anche quelli di `ci.yml`). Se continua: riprovare in un altro
  orario, o un runner a pagamento (`macos-15-xlarge`), o costruire il pacchetto su un Mac con chip Apple a mano con
  gli stessi due comandi (sopra, «Come si costruisce»).
- Elenco delle revoche nel repository sul tag del rilascio.
- AppImage per le distribuzioni che non sono Ubuntu 24.04.
