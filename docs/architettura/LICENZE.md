# Licenze, fasce e prova gratuita

Compito T-202. Codice: `src/impaginatore/licenze/` e `src/impaginatore/ed25519.py`. Formato della chiave e strumento che
la emette: `marketing/negozio/chiavi/FORMATO-CHIAVE.md` e `chiavi.py`. Fasce e funzioni: `docs/mercato/tier.json`.

## Le decisioni da cui parte

Decisioni del titolare, riportate dal piano di T-202:

- nessun server di attivazione, nessun account, nessun cookie;
- la chiave si verifica sul computer dell'utente, con la firma Ed25519;
- per la licenza il programma non «telefona a casa»: non scarica niente e non manda niente, mai;
- l'elenco delle chiavi revocate arriva con gli aggiornamenti del programma, firmato.

Ne segue che il numero di computer di una licenza non si conta: è un limite del contratto (EULA), reso visibile dal nome
dell'intestatario che il programma mostra. Ne segue anche che tutto il controllo è locale, con i limiti detti in
«Che cosa non protegge».

## Come è fatto

| File | Cosa fa |
|---|---|
| `ed25519.py` | Ed25519 della RFC 8032 con la sola libreria standard (verifica in pochi millisecondi). Servirà anche ai manifesti firmati degli aggiornamenti (T-207) |
| `licenze/chiave.py` | testo `IMP1-…` → contenuto verificato (`decodifica`); elenco firmato delle revoche (`revoche`); chiavi pubbliche del programma (`CHIAVI_PUBBLICHE`) |
| `licenze/__init__.py` | stato del programma (`stato`), prova gratuita, attivazione e rimozione della chiave, domande sulle funzioni (`consentita`, `limite`) e cancelli dell'editor |
| `licenze/filigrana.py` | filigrana delle esportazioni JPG e PDF durante la prova |
| `licenze/tier.json` | copia di `docs/mercato/tier.json` dentro il pacchetto; un test controlla che siano uguali |
| `licenze/revoche.json` | elenco firmato delle revoche. Non sta nel repository: lo aggiunge il rilascio. Se manca non è revocato niente |

File sul computer dell'utente, in `<dati dell'utente>/licenza/` (cartella 0700, file 0600 su macOS e Linux):

- `chiave.txt`: il testo della chiave attivata. Resta anche se si reinstalla il programma;
- `prova.json`: `{"formato": 1, "inizio": …, "visto": …}`, inizio della prova e ultima ora vista, in secondi.

Nient'altro: nessun identificativo del computer, nessuna impronta dell'hardware, nessun dato che esca.

## Stati

`licenze.stato()` si calcola a ogni domanda: rilegge i due file (pochi byte), la firma si verifica una volta sola per
testo. Così un editor aperto vede subito una chiave attivata dalla schermata dei progetti.

| Stato | Quando | Funzioni |
|---|---|---|
| `prova` | nessuna chiave; meno di 30 giorni dalla prima apertura | quelle di `prova` in `tier.json`: il Pro senza PSD a livelli; JPG e PDF con la filigrana |
| `attiva` | chiave valida per questa versione maggiore, non revocata, non scaduta | quelle della sua fascia (`essenziale`, `pro`, `studio`, `laboratorio`) |
| `scaduta` | prova finita, oppure chiave a scadenza oltre l'ultimo giorno | sola lettura |
| `revocata` | il seriale della chiave è nell'elenco delle revoche del programma | sola lettura |
| `non valida` | chiave salvata che non si verifica, o di un'altra versione maggiore | come senza chiave: prova se c'è ancora, altrimenti sola lettura |

**Sola lettura** (LICENZA-USO 5.3, TERMINI-VENDITA 3, sito, email di fine prova): i progetti si aprono e si guardano;
si salvano (il lavoro fatto prima non si perde), si esportano come progetto (cartella o ZIP) e si ripristinano le
versioni (`import_export_progetto` e `versioni_backup` restano sempre); non si modificano, non si aggiungono foto e non
si esportano JPG, PDF o PSD.

Ogni stato ha un messaggio per l'utente in `stato()["messaggio"]`, e i rifiuti dicono perché e dove si trova la funzione
(«Il PSD a livelli non fa parte della prova gratuita: c'è nelle licenze Pro e Studio.»).

## Dove si controlla

Una sola domanda per il resto del programma: `licenze.consentita(funzione)`, con le chiavi di `funzioni` di `tier.json`.
I cancelli sollevano `licenze.NonConsentita` (un `ValueError` con il messaggio per l'utente); l'editor risponde 403 con
`{"errore": …, "licenza": true}`, così l'interfaccia può distinguere un limite della licenza da un errore.

| Dove | Cancello | Funzione |
|---|---|---|
| `editor/server.py`, `do_op` | `controlla_operazione` | `editor_completo` per ogni operazione tranne `copia` (appunti); `uniformita_tono` per `tono_fix`, `tono_L`, `tono_escl` |
| `editor/server.py`, `do_import` | `controlla_modifica` | `editor_completo` |
| `editor/server.py`, `run_export` | `controlla_esportazione` | `export_jpg`, `export_pdf`, `export_psd_livelli`, `export_jpg` anche per la consegna al laboratorio (T-208); nella prova restituisce «con filigrana» |
| `laboratori/__init__.py` (album nuovo, importazione, operazione `prodotto`, consegna, assistente) | `controlla_licenza` | `preset_laboratori` per i cataloghi non generici; il Generico è di tutti (CATALOGHI.md) |
| `editor/server.py`, `modelli` | `controlla_modelli` | `modelli_personali`: salvare o importare oltre il limite della fascia (Essenziale: 5) |
| `editor/server.py`, GET `/api/tono`, `/api/tono_all` | `controlla_lettura` | `uniformita_tono` (pannello Tono) |
| `home/server.py` | — | GET `/api/licenza` (stato, mai il testo della chiave), POST `/api/licenza/attiva` `{chiave}`, POST `/api/licenza/rimuovi` |

Non hanno cancelli, di proposito: salvataggio e autosalvataggio, esportazione del progetto, ripristino delle versioni,
ricollegamento delle foto spostate, aggiornamento delle foto cambiate, apertura e creazione dei progetti nella schermata.

La schermata dei progetti ha un pulsante «Licenza» con lo stato (prova e giorni rimasti, fascia, sola lettura) e una
finestra dove si incolla la chiave o la si toglie da questo computer.

## Prova gratuita

- Parte alla prima apertura del programma (la prima domanda sullo stato, di solito la schermata dei progetti), dura
  `prova.giorni` di `tier.json` (30), non chiede la carta, non ha limite di spread.
- L'ora che conta non torna indietro: è la più recente tra l'orologio e l'ultima ora vista (`visto`, riscritta al massimo
  ogni 10 minuti). Spostare indietro la data non allunga la prova né la riapre; se l'orologio è indietro di più di
  6 ore il messaggio lo dice.
- La scadenza delle chiavi a tempo (formato 2) usa invece l'orologio così com'è: un cliente pagante non deve restare
  bloccato perché l'orologio una volta è andato avanti per sbaglio.
- File della prova illeggibile o con valori impossibili: la prova riparte, con un avviso nel registro.
- Proroga della prova decisa dal supporto: una chiave Pro a scadenza (`chiavi.py emetti --tier pro --prezzo omaggio
  --scadenza …`).

## Revoche

`chiavi.py revoca` e `togli-revoca` aggiornano il registro del negozio; `chiavi.py revoche --uscita
src/impaginatore/licenze/revoche.json` scrive l'elenco firmato nella copia del rilascio. L'elenco vale da quando
l'utente installa quell'aggiornamento. File assente, rovinato o con la firma sbagliata: nessuna revoca, avviso nel
registro. Dettagli in `FORMATO-CHIAVE.md`, § 4.

## Prima del rilascio

1. Mettere la chiave pubblica di produzione al posto del segnaposto in `licenze/chiave.py`
   (`CHIAVI_PUBBLICHE = {1: Pubblica("…")}`, la riga la stampa `chiavi.py genera-coppia`). La chiave privata non
   entra mai nel repository.
2. Rigenerare `licenze/revoche.json` con `chiavi.py revoche --uscita …`.
3. Controllare che `licenze/tier.json` sia uguale a `docs/mercato/tier.json` (lo fa un test).

Il punto 1 è protetto da `tests/test_licenze.py::test_un_rilascio_non_parte_con_il_segnaposto`: con una versione finale
(`2.0.0`, senza `.dev`, `a`, `b`, `rc`) e il segnaposto, la suite fallisce, quindi la CI e il rilascio si fermano. Quando
ci sarà la pipeline di rilascio (T-303) conviene ripetere il controllo come passo esplicito prima della costruzione:
`python -c "from impaginatore.licenze import chiave as K; assert not K.problemi_per_il_rilascio()"`.
Con il segnaposto nessuna chiave è valida: una copia di sviluppo vive di prova gratuita.

Nei test la coppia di firma nasce a ogni sessione (`tests/conftest.py`, fixture `licenza`): ogni test gira con una
licenza Studio, salvo quelli che provano gli altri stati. Gli editor lanciati come processi a parte non vedono quella
coppia e lavorano in prova gratuita.

## Che cosa non protegge

Il controllo è tutto sul computer dell'utente: chi ha accesso al computer e un po' di competenza lo aggira. È una scelta
accettata con le decisioni sopra; la tabella dice quanto costa ogni aggiramento.

| Aggiramento | Effetto | Difesa |
|---|---|---|
| Fabbricare o modificare una chiave | impossibile senza la chiave privata | firma Ed25519 |
| Copiare una chiave valida su altri computer | funziona | contratto (EULA); il nome dell'intestatario compare nel programma |
| Cancellare `prova.json` (o rovinarlo) | la prova riparte da capo | nessuna tecnica; EULA 5.4 lo vieta |
| Mettere l'orologio avanti alla prima apertura e poi riportarlo indietro | la prova dura fino alla data finta più 30 giorni | nessuna; serve farlo prima del primo avvio |
| Orologio avanti per sbaglio durante la prova | la prova finisce prima | il messaggio lo dice; il supporto dà una chiave di proroga |
| Non installare più gli aggiornamenti | una chiave revocata continua a funzionare | nessuna: è il prezzo di «nessuna rete» |
| Modificare il programma (Python, o il binario Nuitka di T-302) | tutto sbloccato | nessuna; la compilazione alza il costo, non lo azzera |
| Lanciare a mano gli script del motore (`python -m impaginatore.motore.genera_psd_angolo`, `esporta_pdf`, `anteprima`) | esportazioni senza cancello | oggi nessuna; i cancelli stanno nell'editor e nelle sue API |

## Cosa manca

- **Interfaccia dell'editor** (T-205): l'editor non mostra lo stato della licenza e non nasconde i comandi che la fascia
  non comprende; oggi l'utente li vede e riceve il messaggio d'errore quando li usa. `index.html` non è stato toccato.
- **Funzioni di `tier.json` senza cancello**: `modelli_autore` (Essenziale 30: non è deciso quali 30 tra i moduli e i
  modelli a spread); `correzione_spaziature_album` (la correzione di tutto l'album è un giro della pagina sulle
  operazioni dei singoli spread: il server non la distingue); `impaginazione_automatica_album` e `server_mcp` (oggi
  esistono solo con Claude e la skill; il server MCP di T-203 deve chiedere `licenze.consentita("server_mcp")` e
  `consentita("impaginazione_automatica_album")`); `computer` (non si conta). `preset_laboratori` ha il suo cancello
  (T-208), ma oggi tutte le fasce lo comprendono.
- **Chiave copiata negli appunti** e **link `impaginatore://`** (FLUSSO-ACQUISTO, § 3): il programma accetta il link
  incollato, ma non legge gli appunti da solo e il link non apre il programma finché l'installatore non lo registra (T-302).
- **Chiavi Polar** (`IMP-` + UUID): non accettate; servirebbero solo se si passasse a Polar con le sue attivazioni,
  che le decisioni sopra escludono.
- **Testi**: italiano, scritti nel codice di `licenze/`; passeranno dal sistema di traduzione con T-206.
