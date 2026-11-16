# Costruire i pacchetti di Impaginatore

Qui ci sono gli script che costruiscono il programma compilato e il suo pacchetto di installazione, uno per sistema.
Sono gli stessi che usa la pipeline di GitHub (`.github/workflows/pacchetti.yml`): servono quando un pacchetto va fatto
su un computer, per esempio quello per i Mac con chip Apple quando GitHub non ha macchine libere.

Ogni pacchetto si costruisce **solo sul suo sistema e sulla sua architettura**: non si può fare il pacchetto del Mac
con chip Apple da un Mac Intel, né quello di Windows da Linux.

| Pacchetto | Script | Dove va lanciato | Risultato |
|---|---|---|---|
| Mac con chip Apple (M1 e successivi) | `costruzione/mac-arm64/costruisci.sh` | Mac con chip Apple, macOS 13 o successivo | `Impaginatore-<versione>-mac-arm64.dmg` |
| Mac Intel | `costruzione/mac-x86_64/costruisci.sh` | Mac Intel, macOS 14 o successivo | `Impaginatore-<versione>-mac-x86_64.dmg` |
| Windows 10 e 11 (anche Windows 11 su ARM) | `costruzione\windows\costruisci.ps1` | PC Windows x64 | `Impaginatore-<versione>-windows.exe` |
| Linux x86_64 | `costruzione/linux/costruisci.sh` | Ubuntu 24.04 x86_64 | `Impaginatore-<versione>-linux.deb` |
| Linux arm64 | `costruzione/linux-arm64/costruisci.sh` | Ubuntu 24.04 arm64 | `Impaginatore-<versione>-linux-arm64.deb` |

`costruzione/comune.sh` è la parte comune degli script per macOS e Linux: non si lancia da sola.

## Che cosa fa uno script

1. Controlla il computer: sistema, architettura, strumenti. Se manca qualcosa lo elenca e si ferma. **Non installa
   niente e non chiede la password.**
2. Dice che cosa sta per costruire: versione, commit. Si ferma se il codice ha modifiche non salvate in un commit.
3. Prepara l'ambiente di compilazione in `.venv-compilazione` (Python 3.12 e librerie alle versioni fissate in `uv.lock`).
4. Compila il programma e fa il pacchetto (`strumenti/compila.py`).
5. Prova il programma (`strumenti/verifica_pacchetto.py`): tutti i controlli e la finestra vera, che si apre per circa
   un minuto e si chiude da sola.
6. Lascia tutto in `dist/pacchetti`:
   - il pacchetto;
   - `<pacchetto>.sha256`, la sua impronta;
   - `<pacchetto>.componenti.json`, l'elenco dei componenti e delle loro licenze;
   - `verifica-<sistema>.json`, il rapporto della prova.

Opzioni: `--controlla` (solo il punto 1), `--pulisci` (ricompila da capo), `--senza-prova` (salta il punto 5; un
pacchetto senza prova non entra in una release). Su Windows: `-Controlla`, `-Pulisci`, `-SenzaProva`.

La prima compilazione dura da 15 a 45 minuti secondo il computer. Servono circa 6 GB liberi sul disco.

## Mac con chip Apple, passo per passo

Per chi lo fa la prima volta. Tutto si scrive nel Terminale (Applicazioni › Utility › Terminale), una riga alla volta.

**Una volta sola**

1. Strumenti di Apple per compilare (si apre una finestra: «Installa»; qualche minuto):

   ```
   xcode-select --install
   ```

2. `uv`, che scarica Python e le librerie. Le istruzioni sono sulla pagina ufficiale:
   <https://docs.astral.sh/uv/getting-started/installation/>. Dopo l'installazione chiudere e riaprire il Terminale.

3. Il codice, in una cartella nuova (non quella dove si lavora di solito):

   ```
   cd ~
   git clone https://github.com/Midnight0689/Impaginatore.git Impaginatore-costruzione
   cd Impaginatore-costruzione
   ```

**A ogni versione**

1. Portarsi sulla versione da costruire. Il titolare dice quale tag usare, per esempio `v2.0.0b1`:

   ```
   cd ~/Impaginatore-costruzione
   git fetch --tags --force
   git checkout v2.0.0b1
   ```

2. Controllare che il Mac abbia tutto:

   ```
   costruzione/mac-arm64/costruisci.sh --controlla
   ```

   Deve finire con «Tutto quello che serve c'è.» Altrimenti dice che cosa manca e come metterlo.

3. Costruire e provare:

   ```
   costruzione/mac-arm64/costruisci.sh
   ```

   Verso la fine si apre da sola una finestra di Impaginatore per circa un minuto: non toccarla, è la prova. Lo script
   finisce con «Pronto», l'elenco dei file e l'impronta. Se finisce con «ERRORE», mandare al titolare le ultime righe.

4. Mandare al titolare **tutta la cartella** `dist/pacchetti` (quattro file), per esempio compressa:

   ```
   cd dist && zip -r ~/Desktop/pacchetti-mac-arm64.zip pacchetti
   ```

Se il Terminale risponde «il Terminale gira con Rosetta», è impostato per fingersi un Mac Intel: Finder › Applicazioni
› Utility › Terminale › Ottieni informazioni › togliere «Apri con Rosetta», poi riaprirlo.

## Che cosa fa il titolare con la cartella ricevuta

Il pacchetto costruito su un computer entra nella release in bozza che la pipeline ha già creato per lo stesso tag:

```
python strumenti/rilascio.py aggiungi v2.0.0b1 <cartella ricevuta> --prova     # controlla e basta
python strumenti/rilascio.py aggiungi v2.0.0b1 <cartella ricevuta>             # carica nella bozza
```

`aggiungi` ricontrolla l'impronta e il rapporto della prova (esito e architettura), non sostituisce un pacchetto che la
bozza ha già, carica pacchetto, impronta e componenti e aggiorna `SHA256SUMS` e `verifiche.json`, dove resta scritto che
quel pacchetto viene da un computer e non dalla pipeline. Poi si pubblica come sempre (`rilascio.py pubblica`,
`docs/architettura/DISTRIBUZIONE.md`). Dopo `aggiungi` il giro del tag non va rilanciato: il job della bozza
riscriverebbe `SHA256SUMS` e `verifiche.json` senza il pacchetto aggiunto.

Un pacchetto fatto su un computer vale quanto la fiducia in quel computer: la pipeline parte da una macchina pulita, un
computer personale no. Per questo il pacchetto va costruito da un tag, in una cartella clonata apposta, e l'origine
resta scritta nella release.

## Differenze dalla pipeline

- Su Linux e Windows lo script prova il programma compilato nella cartella di costruzione, senza installare il
  pacchetto: così non tocca un Impaginatore già installato su quel computer. La pipeline, su macchine usa e getta,
  installa il pacchetto e prova quello. Sui Mac la prova è la stessa: dal DMG montato.
- La pipeline controlla prima anche le licenze delle dipendenze del sistema (`strumenti/controlli.py licenze`) e, sui
  tag, fa passare tutti i test.
- Su Windows la pipeline compila con Visual Studio (MSVC). Senza, Nuitka usa MinGW64 e lo script lo dice.
