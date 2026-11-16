# Distribuzione: programma compilato e pacchetti di installazione (T-302)

Stato al 16/11/2026: costruzione, pacchetto e prova scritti per i tre sistemi; **provati davvero solo su Linux** (sotto,
«Cosa è provato»). Per la beta privata, senza certificati Apple e Microsoft, per scelta del titolare.

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
  un eseguibile senza nessuna firma non parte, quella ad hoc basta. Non è un'identità: Gatekeeper al primo avvio blocca
  il programma scaricato e l'utente lo apre da Impostazioni › Privacy e sicurezza › «Apri comunque» (macOS 15 ha tolto
  la scorciatoia Ctrl-clic › Apri). La guida lo spiega passo per passo.
- Un DMG per architettura (`mac-arm64` su `macos-26`, `mac-x86_64` su `macos-15-intel`): Nuitka non fa binari universali
  da un solo ambiente e le ruote di numpy/OpenCV sono per architettura. Il manifesto degli aggiornamenti ha una chiave
  per ognuna.
- Versione minima di macOS: la decide la libreria che chiede la versione più alta; `compila.macos_minimo` la legge da
  tutti i binari del bundle (`otool -l`) e la scrive in `componenti.json` e nel registro della costruzione. Va riportata
  nella guida alla prima costruzione vera (oggi la guida dice «macOS 14, da confermare»).
- Finestre di scelta: quelle del Finder (osascript), come nel pacchetto Python.

### Windows

- Installatore Inno Setup 6 (`strumenti/compilazione/impaginatore.iss`), **per l'utente** (`PrivilegesRequired=lowest`):
  non chiede la password di amministratore e non scrive in `Program Files`. Italiano e inglese. `AppId` fisso: una
  versione nuova si installa sopra la vecchia (la cartella del programma si svuota prima, `InstallDelete`).
- Non firmato: SmartScreen mostra «Windows ha protetto il PC» la prima volta e l'utente sceglie «Ulteriori
  informazioni» › «Esegui comunque». La reputazione di SmartScreen per un file non firmato si azzera a ogni versione.
- WebView2: l'installatore controlla nel registro se c'è e, se manca, lo dice (non lo scarica). Senza WebView2 il
  programma si apre nel browser; le finestre di scelta usano tkinter (incluso solo su Windows, `--enable-plugin=tk-inter`).
- Eseguibile con console «attach» (`--windows-console-mode=attach`): aperto da Start non mostra una console, da un
  terminale scrive lì (serve a `impaginatore mcp` su stdio). **Da provare su Windows vero.**
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

- Parte a mano o con un tag `v*`. Permessi in sola lettura, nessun segreto, nessuna release: i pacchetti restano come
  artefatti dell'esecuzione per 30 giorni. Azioni fissate per hash come in `ci.yml`.
- Prima i test (`strumenti/controlli.py`: lint e copertura su Linux, test su macOS e Windows), poi un job per pacchetto
  (`linux`, `mac-arm64`, `mac-x86_64`, `windows`) e la wheel.
- Ogni job di pacchetto: licenze delle dipendenze di quel sistema (macOS e Windows ne hanno di proprie: pyobjc,
  pythonnet…; `sicurezza.yml` controlla quelle di Linux), ambiente di compilazione, `compila.py`, installazione come la
  farebbe un utente (`apt install ./….deb`; installatore silenzioso, che si installa per l'utente; DMG montato in sola
  lettura con `codesign --verify`), `verifica_pacchetto.py` sul programma installato, disinstallazione (Windows).
- La schermata di avvio si prova su tutti i sistemi con `impaginatore _avvio` (la stessa pagina della finestra): versione,
  «Prova gratuita · 30 giorni», «Free trial · 30 days left» e «Sola lettura» dopo una prova finita. «Beta privata» vuole
  una chiave firmata con la chiave vera e si prova nei test (`tests/test_avvio.py`).
- La prova della finestra blocca solo su Linux (xvfb). Lì fotografa la schermata di avvio (`avvio-finestra.png`
  nell'artefatto, non bloccante: dura un secondo) e poi la finestra del programma (`finestra-programma.png`), che deve
  vedersi. Su macOS e Windows dipende dalla sessione grafica del runner e non blocca: il risultato è nel suo rapporto
  JSON.
- Il controllo dei PSD lancia il sottocomando `_psd` su un album vero: carica l'album (volti compresi, con OpenCV) e,
  senza Photoshop, deve fermarsi con il suo messaggio e non con un errore.
- Costo: stima nella testa del workflow (circa 8 $ a esecuzione, quasi tutto macOS; il Mac Intel è il job più caro). Da
  rifare con i tempi della prima esecuzione.

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

| | Linux | macOS | Windows |
|---|---|---|---|
| Compilazione e pacchetto | provati su questo computer (Ubuntu 24.04, Python 3.12.9 di python-build-standalone) | solo scritti | solo scritti |
| Installazione come un utente | `.deb` estratto (`dpkg-deb -x`, senza amministratore non si installa) e lanciato da un collegamento come `/usr/bin/impaginatore` | solo scritto (DMG montato nella pipeline) | solo scritto (installatore silenzioso nella pipeline) |
| Programma installato: schermata di avvio (prova, inglese, sola lettura), schermata, editor, JPG e PDF, progetto 1.x, PSD fino a Photoshop, MCP, chiusura | provato | da provare nella pipeline | da provare nella pipeline |
| Finestra: schermata di avvio con versione e licenza, poi la finestra del programma | provata e fotografata sotto Xvfb (WebKitGTK del sistema) | non provata | non provata |
| Avvisi del sistema (Gatekeeper, SmartScreen) e testi della guida | — | da provare su un Mac vero | da provare su un PC vero |
| Pipeline su GitHub | mai eseguita | mai eseguita | mai eseguita |

Misure su Linux (16/11/2026, Ubuntu 24.04.5, 12 core, gcc 13 senza ccache, Nuitka 4.3.5, Python 3.12.9):

| | |
|---|---|
| Compilazione e pacchetto | 15 min 43 s (114 min di CPU); i file più lunghi sono `editor/server.c` (circa 12 min) e `bottle.c` |
| Pacchetto `.deb` | 93,2 MB |
| Programma installato | 382,4 MB su disco, 196 file, eseguibile 96,3 MB, 34 componenti di terze parti |
| Prova completa con la finestra | 14 s |
| Versione / porta della schermata / editor pronto | 0,17 s / 0,13 s / 0,52 s |
| Esportazione JPG / PDF di uno spread | 0,27 s / 0,27 s |

Dalla prima esecuzione della pipeline le misure dei tre sistemi sono nel suo riepilogo (`verifica-<chiave>.json`).

Problemi che la prova del programma compilato ha trovato, e che i test sul sorgente non vedevano:

- l'eseguibile non può chiamarsi come la cartella dei dati del pacchetto (`impaginatore`): Nuitka si ferma (sopra);
- Nuitka 4 mette in `sys.executable` un `python` che non esiste: l'editor non partiva (`compilato.prepara` lo corregge);
- i modelli di OpenCV per i volti e `optparse` per il `gi` del sistema mancavano (sopra, «Cosa c'è»);
- su Linux la finestra del programma, creata nascosta per la schermata di avvio, non si mostrava mai: pywebview 6 su
  GTK la rinasconde se resta segnata come nascosta (anche dal sorgente; `desktop/avvio.py`). La prova della finestra
  vera (`tests/prova_finestra.py`) ora lo controlla, ma gira solo con un Python che vede il PyGObject del sistema.

## Decisioni per il titolare

- Nuitka 4.x (AGPL con eccezione) o l'ultima 2.x (Apache-2.0).
- Offerta del sorgente di FFmpeg (LGPL) nella release.
- HEIC escluso dal programma compilato (o una libreria HEIC con licenza compatibile).
- Identificativo del bundle macOS `it.impaginatore.Impaginatore` e indirizzo del sito nel pacchetto `.deb`
  (`impaginatore.example`, segnaposto): definitivi prima del primo rilascio.
- Il Mac Intel nella pipeline (costo) e la versione minima di macOS.
- Elenco delle revoche nel repository sul tag del rilascio.
- AppImage per le distribuzioni che non sono Ubuntu 24.04.
