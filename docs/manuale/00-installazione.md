# 0. Installare il programma

<!-- Per chi mantiene la guida, stato al 16/11/2026 (dettagli: docs/architettura/DISTRIBUZIONE.md, «Cosa è provato»).
Provato nella pipeline di GitHub, sul programma installato come un utente: Linux («apt install», comando
/usr/bin/impaginatore), Windows (installatore silenzioso per l'utente in %LOCALAPPDATA%\Programs\Impaginatore, poi
disinstallazione) e Mac Intel (DMG montato, firma ad hoc verificata, avvio da Impaginatore.app): schermata di avvio con
la prova gratuita, schermata Album nella finestra del programma, editor, esportazioni, assistente AI con «mcp».
macOS 14 come minimo: misurato sul Mac Intel. Non provato: il Mac con chip Apple (nessun runner libero), gli avvisi di
Gatekeeper e SmartScreen su un file scaricato davvero, i passi a mano dell'installatore e del DMG, i testi esatti degli
avvisi e le schermate «SCHERMATA DA FARE»: vanno rifatti su un Mac e un PC veri con la prima beta. -->

Questa guida è per la **beta privata**: ricevi da noi il collegamento ai file. Ogni passo dice cosa vedi sullo schermo,
compresi gli avvisi del sistema, e perché compaiono.

**In breve.** Il file di installazione non è firmato con un certificato di Apple o di Microsoft. Per questo, la prima
volta, macOS e Windows ti avvisano che non possono verificare chi ha fatto il programma. Non è un errore: è il sistema
che ti chiede di decidere tu. Chi ha fatto il file lo verifichi tu, con l'impronta del file (sotto). Poi segui i passi
per il tuo sistema. Nessun passo ti chiede di spegnere le protezioni del computer: se una guida trovata in rete te lo
chiede, non farlo.

## Cosa serve

| Sistema | Versione | File da scaricare |
|---|---|---|
| Mac con chip Apple (M1, M2, M3, M4 e successivi) | macOS 13 Ventura o successivo | `Impaginatore-<versione>-mac-arm64.dmg` |
| Mac con processore Intel | macOS 14 Sonoma o successivo | `Impaginatore-<versione>-mac-x86_64.dmg` |
| Windows (PC con processore Intel o AMD) | Windows 10 o 11, 64 bit | `Impaginatore-<versione>-windows.exe` |
| Windows su PC con processore ARM (Snapdragon X, Surface Pro con chip ARM…) | Windows 11 | lo stesso `Impaginatore-<versione>-windows.exe` |
| Linux (PC con processore Intel o AMD) | Ubuntu 24.04 o una distribuzione basata su di lei (Linux Mint 22, Pop!_OS 24.04…), 64 bit | `Impaginatore-<versione>-linux.deb` |
| Linux su processore ARM a 64 bit | Ubuntu 24.04 o derivate, arm64 | `Impaginatore-<versione>-linux-arm64.deb` |

Che Mac hai: menu Apple (la mela in alto a sinistra) › «Informazioni su questo Mac». Se c'è la riga «Chip» con
«Apple M…» è un Mac con chip Apple; se c'è «Processore» con «Intel» è un Mac Intel. Ogni Mac con chip Apple può
installare macOS 13 o successivo: se il tuo ha una versione più vecchia, aggiornalo da Impostazioni di Sistema ›
Generali › Aggiornamento Software. Su un macOS troppo vecchio il Mac dice che Impaginatore non è compatibile con
questa versione di macOS e non lo apre.

Che PC hai: Impostazioni › Sistema › Informazioni › «Tipo di sistema». «Processore basato su x64» è un PC Intel o AMD;
«Processore basato su ARM» è un PC ARM. Sui PC ARM Windows 11 esegue Impaginatore in emulazione (lo fa da solo, non
devi fare niente): funziona come sugli altri PC, a volte un po' più lento ad aprirsi.

Spazio su disco: circa 400 MB per il programma, più lo spazio dei tuoi album.

Non serve una connessione a internet per lavorare. Le foto restano sul computer: il programma non le carica in rete.

## Controllare il file scaricato

Insieme ai file ricevi l'elenco delle **impronte SHA-256** (il file `SHA256SUMS`, o le note della versione). L'impronta
è una sequenza di 64 caratteri calcolata dal contenuto del file: se il file è proprio quello che abbiamo pubblicato,
l'impronta che calcoli tu è identica, carattere per carattere. Se anche un solo byte è diverso, l'impronta cambia
del tutto. È il controllo che sostituisce il certificato: fallo prima di installare.

Apri il terminale e scrivi il comando del tuo sistema (cambia il nome del file con quello che hai scaricato):

- **macOS** (Terminale, in Applicazioni › Utility):
  `shasum -a 256 ~/Downloads/Impaginatore-<versione>-mac-arm64.dmg`
- **Windows** (PowerShell, dal menu Start):
  `Get-FileHash "$env:USERPROFILE\Downloads\Impaginatore-<versione>-windows.exe" -Algorithm SHA256`
- **Linux** (Terminale):
  `sha256sum ~/Scaricati/Impaginatore-<versione>-linux.deb`

Accanto a ogni file c'è anche il suo `.sha256` (per esempio `Impaginatore-<versione>-linux.deb.sha256`), con la stessa
impronta.

Confronta il risultato con la riga del file nell'elenco. Se è diversa, non installare: scarica di nuovo il file e, se
resta diversa, scrivici.

## macOS

1. Fai doppio clic sul file `.dmg`. Si apre una finestra con l'icona di Impaginatore e la cartella «Applicazioni».
2. Trascina Impaginatore sulla cartella «Applicazioni». Poi chiudi la finestra ed espelli il disco «Impaginatore»
   (il pulsante ⏏ nel Finder).
3. Apri Impaginatore da Applicazioni (o da Launchpad). La prima volta macOS mostra un avviso simile a:
   «Impossibile aprire "Impaginatore". Apple non può verificare che "Impaginatore" non contenga malware che potrebbe
   danneggiare il Mac o compromettere la privacy.»

   [SCHERMATA DA FARE: avviso di Gatekeeper al primo avvio, macOS 15]

   Perché: il programma non è registrato presso Apple (serve un conto sviluppatore a pagamento). macOS non sa chi l'ha
   fatto e te lo dice. Il controllo dell'impronta (sopra) ti dice che il file è il nostro.

   Premi «Fine» (o «Annulla»), **non** «Sposta nel Cestino».
4. Apri **Impostazioni di Sistema › Privacy e sicurezza** e scorri fino a «Sicurezza». C'è la riga
   «"Impaginatore" è stato bloccato per proteggere il Mac.» con il pulsante **«Apri comunque»**. Premilo e conferma con
   la password del Mac o con Touch ID.

   [SCHERMATA DA FARE: Privacy e sicurezza con «Apri comunque»]

   Su macOS 13 Ventura e 14 Sonoma c'è anche una strada più breve: nel Finder, Ctrl-clic (o clic destro) su
   Impaginatore › «Apri» › «Apri». Da macOS 15 Sequoia questa strada non c'è più: si passa da Impostazioni.
5. Dalla seconda volta Impaginatore si apre con un doppio clic, senza avvisi.

Al primo avvio macOS può chiedere anche **«Consentire a "Impaginatore" di trovare dispositivi sulle reti locali?»**
Rispondi **«Non consentire»**: Impaginatore lavora sul tuo computer e non ha bisogno di cercare altri dispositivi in
rete.

[SCHERMATA DA FARE: domanda «reti locali» di macOS 15]

La prima volta che apri un album o scegli una cartella nella Scrivania, in Documenti o in Download, macOS chiede se
Impaginatore può accedervi: rispondi «Consenti», altrimenti il programma non vede le foto. Dopo un aggiornamento
macOS potrebbe chiederlo di nuovo.

## Windows

1. Scarica `Impaginatore-<versione>-windows.exe`. Il browser può avvisare che il file «non viene scaricato
   comunemente»: in Edge apri il menu «…» accanto al file › «Mantieni» › «Mostra altro» › «Mantieni comunque».

   [SCHERMATA DA FARE: avviso di Edge sul file scaricato]

2. Fai doppio clic sul file. Compare la finestra blu **«Windows ha protetto il PC»** (Microsoft Defender SmartScreen).

   [SCHERMATA DA FARE: SmartScreen, prima e dopo «Ulteriori informazioni»]

   Perché: il file non ha la firma di un certificato a pagamento e Windows non lo conosce ancora. Clicca
   **«Ulteriori informazioni»**: compare l'editore «Sconosciuto» e il pulsante **«Esegui comunque»**. Premilo.
3. Scegli la lingua e segui l'installatore: la cartella proposta è `%LOCALAPPDATA%\Programs\Impaginatore` (la tua
   cartella utente, non serve la password di amministratore); puoi aggiungere un'icona sul desktop. Alla fine puoi
   avviare subito Impaginatore.
4. Il programma è nel menu Start: «Impaginatore».

Su un PC con processore ARM (Windows 11) i passi e gli avvisi sono gli stessi: il file è lo stesso.

La finestra del programma usa **Microsoft Edge WebView2**, che c'è già in Windows 10 e 11 aggiornati. Se manca,
l'installatore lo dice e Impaginatore si apre nel browser: funziona lo stesso. Per avere la finestra, scarica
«WebView2 Runtime» dal sito di Microsoft (pagina «Microsoft Edge WebView2», versione «Evergreen»), installalo e riapri
Impaginatore.

Se l'antivirus blocca il programma, non spegnere l'antivirus: scrivici con il nome dell'antivirus e il messaggio. I
programmi nuovi e senza firma a volte vengono scambiati per sospetti; lo segnaliamo noi al produttore.

## Linux (Ubuntu 24.04 e derivate)

1. Scarica `Impaginatore-<versione>-linux.deb` (su un computer con processore ARM a 64 bit:
   `Impaginatore-<versione>-linux-arm64.deb`; lo dice `dpkg --print-architecture`, che risponde `amd64` o `arm64`).
2. Apri il Terminale nella cartella dove l'hai scaricato e scrivi:
   `sudo apt install ./Impaginatore-<versione>-linux.deb` (o `…-linux-arm64.deb`)
   apt chiede la tua password e installa anche quello che serve alla finestra (GTK e WebKitGTK di Ubuntu).
3. Apri Impaginatore dal menu delle applicazioni, o scrivi `impaginatore` nel Terminale.

Il programma si installa in `/opt/impaginatore`. Su un'altra distribuzione, o su una versione di Ubuntu diversa dalla
24.04, la finestra del programma può non aprirsi: allora Impaginatore si apre nel browser e funziona lo stesso.

## Il primo avvio

- Compare la schermata di avvio, poi la schermata Album.
- Parte la prova gratuita di 30 giorni; la chiave di licenza (anche quella della beta) si inserisce dal pulsante della
  licenza: vedi [Prova gratuita e licenza](11-prova-licenza.md).
- I nuovi album nascono in **Documenti › Impaginatore › Progetti**, oppure accanto alle foto del cliente se scegli la
  sua cartella.
- Le impostazioni del programma stanno qui (non toccarle a mano):
  - macOS: `~/Library/Application Support/Impaginatore`
  - Windows: `%APPDATA%\Impaginatore`
  - Linux: `~/.local/share/impaginatore`

## Aggiornare

Il programma controlla una volta al giorno se c'è una versione nuova (l'interruttore è nella finestra «Versione del
programma», che si apre dal numero di versione nella schermata Album). Se c'è, in cima alla schermata Album compare
«È disponibile Impaginatore …» con le novità e il pulsante **«Scarica la versione nuova»**: si apre nel browser la
pagina della versione. Il programma non si sostituisce da solo: scarichi il file e lo installi come la prima volta
(controllando l'impronta). Album, impostazioni e licenza restano.

Se nella finestra «Versione del programma» leggi «Aggiornamenti non ancora attivi», questa versione non cerca le
versioni nuove e non si collega a internet per farlo: può succedere con le versioni della beta privata.

- **macOS**: trascina il nuovo Impaginatore in Applicazioni e scegli «Sostituisci». Il primo avvio può chiedere di nuovo
  «Apri comunque».
- **Windows**: esegui il nuovo installatore; sostituisce la versione installata.
- **Linux**: `sudo apt install ./Impaginatore-<nuova versione>-linux.deb`.

Per tornare a una versione precedente installa il suo file allo stesso modo (su Linux apt chiede di confermare il
passaggio a una versione più vecchia).

## Disinstallare

- **macOS**: trascina Impaginatore da Applicazioni nel Cestino.
- **Windows**: Impostazioni › App › App installate › Impaginatore › «Disinstalla».
- **Linux**: `sudo apt remove impaginatore`.

Disinstallare toglie il programma, **non** i tuoi album né le impostazioni. Gli album restano nelle loro cartelle. Se
vuoi togliere anche le impostazioni e la licenza da questo computer, cancella la cartella delle impostazioni (elenco
sopra) dopo aver disinstallato.

## Collegare l'assistente AI

Il comando da dare all'assistente (vedi [L'assistente AI](assistente/INDICE.md)) è il programma installato seguito da
`mcp`:

- macOS: `/Applications/Impaginatore.app/Contents/MacOS/impaginatore-app mcp`
- Windows: `%LOCALAPPDATA%\Programs\Impaginatore\impaginatore.exe mcp`
- Linux: `/usr/bin/impaginatore mcp`

## Se qualcosa non va

- **«Il file è danneggiato e non può essere aperto»** (macOS): il file scaricato non è completo. Controlla l'impronta e
  scaricalo di nuovo.
- **La finestra non si apre e si apre il browser**: il programma funziona lo stesso. Su Windows manca WebView2 (sopra);
  su Linux la distribuzione non è Ubuntu 24.04 o simile.
- Per ogni altro problema: [Domande frequenti](13-domande.md), poi scrivici.
