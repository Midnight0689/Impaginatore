# Aggiornamenti del programma (T-207)

Stato al 16/11/2026: il giro completo (controllo, scaricamento, verifica, installazione, riavvio nella versione nuova,
ritorno alla precedente) funziona per il programma installato come pacchetto Python ed è provato su Linux con processi
veri e una release in una cartella. **Non è ancora acceso per gli utenti**: mancano la chiave pubblica vera dei rilasci e
il repository delle release (vedi «Prima del primo rilascio»). Il programma compilato (T-302) controlla e avvisa allo
stesso modo, ma si aggiorna a mano con il suo pacchetto (sotto, «Programma compilato»).

Regole di sicurezza e dove sono nel codice: `SICUREZZA.md`, «Aggiornamenti».

## Cosa vede l'utente

- All'avvio (dopo 5 secondi, per non rallentare la partenza) e poi al massimo una volta al giorno il programma controlla se
  c'è una versione nuova. Nella finestra «Versione del programma» l'interruttore «Controlla da solo se ci sono versioni
  nuove» lo spegne (`<dati>/aggiornamenti.json`); «Controlla aggiornamenti» resta sempre.
- Se c'è, in cima alla schermata Album compare un avviso discreto: «È disponibile Impaginatore 2.0.1», le prime novità,
  «Aggiorna e riavvia» e «Più tardi» (vale fino alla chiusura della finestra o della scheda). Niente si scarica da solo.
- «Aggiorna e riavvia»: il programma scarica e verifica, gli editor aperti salvano e si chiudono, il programma si riavvia
  nella versione nuova sulla stessa porta e la pagina si riapre da sola. Una volta compare «Impaginatore aggiornato alla
  versione 2.0.1.». Durante un'esportazione l'aggiornamento aspetta.
- «Versioni precedenti» nella stessa finestra: si torna alla versione usata prima dell'ultimo aggiornamento («Impaginatore
  è tornato alla versione …»). Una versione lasciata così non ricompare nell'avviso (resta «Aggiorna ora» nella finestra).
- Se una versione nuova non riesce a partire per 3 volte, alla quarta il programma torna da solo alla precedente.
- I progetti non cambiano: un aggiornamento sostituisce solo il codice del programma.
- Programma compilato: lo stesso avviso, con «Scarica la versione nuova» al posto di «Aggiorna e riavvia» e la nota «Si apre
  la pagina dei download: si installa come la prima volta, album e impostazioni restano.». Il pulsante apre nel browser la
  pagina della release; niente si scarica né si sostituisce dal programma. «Versioni precedenti» elenca solo la versione
  in uso: per tornare indietro si reinstalla il pacchetto della versione voluta.

## Come funziona

```
cli.main(argv)
 └─ lanciatore.avvia(argv)          quale copia avviare? <dati>/programma/attuale.json
      ├─ la base (il pacchetto installato con pip/uv, o il checkout)              → si continua qui
      └─ versioni/<v>/ se completa e più nuova della base                         → os.execv: python -c CODICE <copia> <argomenti>
home.server.main
 ├─ AGGIORNAMENTI = aggiornamenti.predefiniti(riavvia_programma)
 │    PacchettiFirmati(SorgenteGitHub(REPOSITORY), InstallazionePython())
 ├─ crea_server → lanciatore.conferma()   la versione nuova è partita: non si conta più
 └─ ciclo: controlla() all'avvio e ogni giorno (se acceso)
      SorgenteGitHub.ultimo()  GET https://api.github.com/repos/<repository>/releases/latest
      leggi manifesto.json e manifesto.json.sig → firmati.verifica (Ed25519, CHIAVI_FIDATE) → controlla_campi
POST /api/aggiorna (dalla pagina, con il gettone)
 └─ PacchettiFirmati.aggiorna
      scarica il pacchetto (al massimo la misura firmata) → misura e sha256 del manifesto
      InstallazionePython.installa
        estrai in versioni/.prepara-<v>-… solo i file del manifesto (sha256 di ognuno)
        controlla_revoche (licenze/revoche.json) → prova_avvio (processo a parte: importa schermata, editor, motore)
        .completa → rename in versioni/<v> → puntatore {versione: <v>, precedente: <in uso>, confermata: false}
        tiene solo la versione nuova e la precedente
      annuncio.json → riavvia_programma(): editor salvati e chiusi, rilancio sulla stessa porta, uscita
```

File nella cartella dei dati dell'utente (macOS `~/Library/Application Support/Impaginatore`, Windows
`%APPDATA%\Impaginatore`, Linux `~/.local/share/impaginatore`):

```
programma/attuale.json      {"formato": 1, "versione", "precedente", "confermata", "tentativi", "scartata"}
programma/versioni/<v>/     impaginatore/… e .completa
programma/scarichi/         pacchetto in arrivo (si cancella sempre)
programma/annuncio.json     «aggiornato» / «tornato» per il primo avvio dopo il riavvio
aggiornamenti.json          {"automatico": true | false}
```

Per ripartire da zero basta cancellare `programma/`: parte la versione installata.

Contratto del lanciatore (ogni versione installata fa da base alle successive, quindi non cambia senza una migrazione):
la base installata più nuova vince sempre sulle copie (reinstallare con pip o con l'installatore riporta tutto pulito);
`IMPAGINATORE_VERSIONE_SCELTA` impedisce un secondo salto; `IMPAGINATORE_BASE` dice alla copia dove sta la base.
Da un checkout git le copie si usano solo con `IMPAGINATORE_AGGIORNAMENTI_FINTI` (il codice su cui si lavora non resta
nascosto); il programma compilato non usa copie.

## Una release

Una release su GitHub (tag `v2.0.1`, **pubblicata**, non bozza e non «pre-release»: l'API `releases/latest` restituisce
solo l'ultima release pubblicata che non è né l'una né l'altra). Gli asset che il programma legge sono tre:

| Asset | Contenuto |
|---|---|
| `impaginatore-2.0.1-py3-none-any.whl` | la wheel del programma (`uv build --wheel`) |
| `manifesto.json` | descrizione firmata della versione (sotto) |
| `manifesto.json.sig` | firma Ed25519, 128 cifre esadecimali, di `IMPAGINATORE-AGGIORNAMENTO-v1\0` + i byte esatti di `manifesto.json` |

Accanto ci sono i pacchetti del programma compilato per chi installa (`Impaginatore-2.0.1-<chiave>.<dmg|exe|deb>`, con
`.sha256` e `.componenti.json`), `SHA256SUMS` e `verifiche.json` (esito della prova di ogni pacchetto nella pipeline).
Una pre-release (versione `a`, `b` o `rc`, per esempio una beta `v2.0.0b1`) ha gli stessi file ma non arriva ai
programmi installati: serve a dare i pacchetti a chi prova la beta.

```json
{
 "formato": 1, "prodotto": "impaginatore", "id_firma": 1, "versione": "2.0.1", "data": "2026-12-01",
 "novita": {"it": ["Esportazione più veloce"], "en": ["Faster export"]},
 "python_minimo": "3.11",
 "pacchetti": {"python": {"nome": "impaginatore-2.0.1-py3-none-any.whl", "dimensione": 2101129, "sha256": "…"}},
 "file": {"impaginatore/__init__.py": "<sha256>", "…": "…"}
}
```

Nome, testo e misure della release su GitHub non contano: tutto ciò che il programma usa sta nel manifesto firmato. Le
novità si mostrano nella lingua in uso (altrimenti in inglese, poi in italiano), al massimo 30 righe di 300 caratteri.
`pacchetti` può avere anche un pacchetto per sistema (`mac-arm64`, `mac-x86_64`, `windows`, `linux`, `linux-arm64`: le
chiavi di `installazione.chiave_pacchetto()`; Windows su ARM usa `windows`, il pacchetto x64 che esegue in emulazione)
per il programma compilato, con misura e sha256 come la wheel. Li aggiunge `aggiornamento.py firma … --compilato
chiave=file` (una volta per pacchetto), di solito attraverso `strumenti/rilascio.py pubblica` (o `prepara`), che fa
anche `SHA256SUMS` e le note (`DISTRIBUZIONE.md`, «Rilascio»).

## Come si pubblica

Dal 16/11/2026 la release si fa in due tempi: la pipeline crea la release **in bozza** con i pacchetti, sul computer di
chi pubblica `strumenti/rilascio.py pubblica` firma il manifesto e la pubblica. La procedura passo per passo è in
`DISTRIBUZIONE.md`, «Rilascio»; qui sotto la parte della chiave e, per chi pubblica solo la wheel, il giro a mano.

Una volta sola:

1. `uv run python strumenti/aggiornamento.py genera-coppia` crea la chiave privata dei rilasci in
   `~/.impaginatore-negozio/aggiornamenti-privata-1.hex` (o `--dir`, o `IMPAGINATORE_NEGOZIO_DIR`; mai dentro il
   repository) e stampa la pubblica. **Farne subito una copia offline**: senza, le copie installate non accettano più
   aggiornamenti e serve una reinstallazione.
2. Mettere la pubblica in `src/impaginatore/aggiornamenti/firmati.py`: `CHIAVI_FIDATE = {1: "<64 cifre>"}`.
3. Mettere il repository delle release in `src/impaginatore/aggiornamenti/sorgenti.py`: `REPOSITORY = "proprietario/nome"`
   (pubblico: il programma lo legge senza autenticazione; 60 richieste all'ora per indirizzo IP, ne basta una al giorno).

A ogni versione, a mano (solo la wheel, senza pacchetti compilati; con i pacchetti si usa la pipeline e `rilascio.py
pubblica`, `DISTRIBUZIONE.md`):

1. Versione in `src/impaginatore/__init__.py` (unico posto), `CHANGELOG.md`, test (`ruff check`, `pytest`).
2. Elenco delle revoche, se ci sono licenze revocate: `python3 marketing/negozio/chiavi/chiavi.py revoche --uscita
   src/impaginatore/licenze/revoche.json` (finisce nel pacchetto e quindi nel manifesto).
3. `uv build --wheel` → `dist/impaginatore-<v>-py3-none-any.whl`.
4. `uv run python strumenti/aggiornamento.py firma dist/impaginatore-<v>-py3-none-any.whl --novita-it "…" --novita-en "…"`
   (una opzione per riga) → `dist/manifesto.json` e `dist/manifesto.json.sig`.
5. `uv run python strumenti/aggiornamento.py verifica dist --pubblica <64 cifre>`.
6. Su GitHub: nuova release con tag `v<v>`, non pre-release; caricare i tre file di `dist/` (wheel, manifesto, firma).
   Pubblicarla: da quel momento i programmi la trovano al controllo successivo.

Una release sbagliata si toglie da GitHub (o se ne pubblica una più nuova): chi l'ha già installata torna indietro dalla
finestra «Versioni precedenti». Una versione non torna mai a una più vecchia da sola, se non perché non parte.

Rotazione della chiave (persa o rubata): nuova coppia con `genera-coppia --id 2`, la versione successiva firmata con la
vecchia chiave porta `CHIAVI_FIDATE = {1: …, 2: …}`; da quella in poi si firma con `--id 2` e la 1 si toglie. Se la chiave
è rubata, chi l'ha può firmare aggiornamenti accettati dalle copie che hanno solo la 1: serve una versione nuova
(reinstallazione) e un avviso agli utenti.

### Prima del primo rilascio

- `tests/test_aggiornamenti_firmati.py::test_un_rilascio_non_parte_con_il_segnaposto` fallisce se una versione finale ha
  ancora il segnaposto della chiave (come `test_licenze.py` per le licenze).
- `REPOSITORY` vuoto vuol dire nessuna richiesta di rete: la finestra della versione dice «Aggiornamenti non ancora
  attivi: il canale delle versioni nuove non è configurato in questa versione».

## Prove a mano

```
uv run python strumenti/aggiornamento.py finta /tmp/release-finta --versione 2.0.1.dev1 --novita-it "Prova"
IMPAGINATORE_AGGIORNAMENTI_FINTI=/tmp/release-finta uv run impaginatore
```

`finta` fa una wheel dal codice di `src` con la versione indicata, la firma con una chiave di prova e prepara la cartella
come la risposta dell'API (`releases/latest.json`) con gli asset accanto. La chiave di prova (`chiave-prova.txt`) vale solo
se la versione **in uso** è di sviluppo (`.dev`, `a`, `b`, `rc`) e il programma non è compilato: per fare più giri di
fila conviene pubblicare versioni `.devN` (dalla 2.0.1 finale la chiave di prova non vale più e il controllo dice «firma
non valida»). Per ripartire: cancellare `<dati>/programma/`.

## Cosa è vero e cosa è finto

| Parte | Stato |
|---|---|
| Manifesto, firma, controlli, estrazione, prova di avvio, puntatore, ritorno indietro, ritorno da solo dopo 3 avvii falliti | vero, provato (test unitari e `test_aggiornamenti_programma.py` con processi veri) |
| Avviso nella schermata Album, annuncio, interruttore, ricarica della pagina dopo il riavvio | vero, provato in Chrome (`test_ux_aggiornamenti.py`) |
| Sorgente GitHub | scritta sull'API documentata (`X-GitHub-Api-Version: 2026-03-10`), provata con una rete finta: **mai una richiesta vera** |
| Release | finte, in una cartella (`SorgenteFinta`) |
| Chiave pubblica dei rilasci | vera, id 1 (sotto, «Stato delle chiavi»); `strumenti/rilascio.py prepara` controlla che la privata usata sia la sua |
| Repository delle release | vuoto |
| Programma compilato (`InstallazioneCompilata`) | aggiornamento a mano: controllo e avviso veri, il pulsante apre la pagina della release (provato con test e nel programma compilato su Linux) |

## Programma compilato (T-302)

Il programma compilato con Nuitka (`DISTRIBUZIONE.md`) **non si sostituisce da solo**. `predefiniti()` gli dà
`PacchettiFirmati(SorgenteGitHub(), InstallazioneCompilata(), …)`: il controllo legge e verifica il manifesto firmato
come per il pacchetto Python (con `IMPAGINATORE_AGGIORNAMENTI_FINTI` legge la cartella finta, ma sempre con le chiavi
vere: la chiave di prova non vale nel compilato), e lo stato dice `manuale: true`. `aggiorna` non scarica niente: chiama
`InstallazioneCompilata.a_mano`, che apre nel browser `PAGINA_SCARICAMENTO` (con `{versione}`) o, se vuota, la pagina
della release `https://github.com/<REPOSITORY>/releases/tag/v<versione>`, e risponde `{pagina, versione}`. Se il browser
non si apre, l'errore dice l'indirizzo («Il browser non si è aperto: scarica la versione nuova da …»). `installa` e
`torna` rifiutano: in un programma compilato non ci sono copie da installare né da cui tornare, e il lanciatore non
avvia mai copie dalla cartella dei dati.

Perché a mano, su tutti e tre i sistemi: senza firma Authenticode e senza ID sviluppatore Apple, sostituire il
programma da dentro il programma vorrebbe dire eseguire un installatore non firmato scaricato in silenzio (Windows) o
riscrivere un bundle che Gatekeeper rimette in quarantena (macOS), senza un modo sicuro di tornare indietro se si ferma
a metà. Installato a mano, l'aggiornamento passa dagli stessi controlli del sistema della prima installazione e
dall'impronta pubblicata. Con i certificati si cambierà solo `InstallazioneCompilata` (Windows: installatore firmato in
modo silenzioso e chiusura del programma; macOS: sostituzione del bundle notarizzato con un piccolo aiutante; poi
`torna` sul pacchetto precedente tenuto da parte), da provare su macchine vere.

## Limiti

- Un aggiornamento cambia solo il codice del pacchetto `impaginatore`, non le librerie (numpy, OpenCV, Pillow, pywebview)
  né Python: una versione che ne vuole di nuove si ferma alla prova di avvio («non si avvia su questo computer») e va
  installata da capo. `python_minimo` lo dice prima di scaricare.
- Si torna indietro di una versione sola (quella usata prima dell'ultimo aggiornamento), più la base installata.
- Tornando a una versione precedente torna anche il suo elenco delle revoche (più vecchio).
- La copia aggiornata sta nella cartella dei dati dell'utente: chi può scriverci può cambiare il programma. È lo stesso
  utente che lo esegue (lo stesso vale per la base installata con `pip --user` o `uv`).
- Solo la stessa versione maggiore (2.x → 2.y): il passaggio alla 3 è un acquisto nuovo (licenze per versione maggiore).
- Non provati: rete vera (GitHub, la CDN degli asset, proxy con ispezione TLS), `os.execv` e riavvio su Windows (dove
  `os.execv` crea un processo nuovo) e su macOS, lanciatori della 1.x (`legacy/`).

## Decisioni per il titolare

- Il repository delle release (pubblico) e chi tiene la chiave privata dei rilasci.
- Solo stessa versione maggiore (proposto) o anche le successive.
- Un canale «beta» per chi ha la licenza beta (release marcate «pre-release», lette da `/releases` invece che da
  `/releases/latest`): oggi le pre-release non arrivano a nessuno. `rilascio.py pubblica` pubblica le versioni a/b/rc
  come pre-release proprio per questo: si scaricano dalla pagina della release, ma i programmi installati non le vedono.
- Controllo automatico acceso di serie (proposto) e una volta al giorno.

## Stato delle chiavi al 16/11/2026

Nel codice (`aggiornamenti/firmati.py`, `CHIAVI_FIDATE`) c'è la chiave pubblica vera dei rilasci (id 1). La chiave
privata è stata generata con `strumenti/aggiornamento.py genera-coppia` e sta fuori dal repository, in
`~/.impaginatore-negozio/aggiornamenti-privata-1.hex` sul computer del titolare: va copiata subito anche offline.
Resta vuoto `sorgenti.REPOSITORY`: finché non c'è il repository pubblico delle release, nessuna richiesta parte.
