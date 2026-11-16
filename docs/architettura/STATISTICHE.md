# Statistiche d'uso facoltative

Compito T-204, per la beta privata. Codice: `src/impaginatore/statistiche/` (`__init__.py` consenso, registro e
funzioni chiamate dal programma; `schema.py` gli eventi ammessi; `invio.py` la destinazione dei dati). Strumento del
titolare per leggere i file dei tester: `strumenti/statistiche_beta.py`. Prove: `tests/test_statistiche.py`,
`tests/test_statistiche_beta.py`, `tests/test_ux_statistiche.py`.

## Principi

- **Spente di serie, per tutti.** Senza la scelta «sì» salvata il programma non scrive niente e non manda niente: con le
  statistiche spente una funzione delle statistiche costa un `os.stat` ed esce.
- **Consenso esplicito.** La domanda compare solo a chi ha una licenza beta privata attiva, al primo avvio della
  schermata Album (e subito dopo aver attivato la chiave beta), con due pulsanti di uguale peso: «No, grazie» e
  «Sì, condividi». Esc rimanda la domanda all'avvio successivo. La scelta si cambia quando si vuole dal menu ⋯ ›
  «Statistiche d'uso…».
- **Mai contenuti.** Nessun campo di testo libero: solo numeri, vero/falso e parole di elenchi chiusi (`schema.py`).
  Foto, immagini, nomi di file, cartelle, album e clienti, percorsi, testi dell'album, EXIF e volti non hanno un posto
  dove stare. Degli errori si tengono il tipo e il punto del codice, mai il messaggio.
- **Prima sul computer, leggibile.** Ogni evento si scrive prima in un registro locale (JSON, una riga per evento) che
  l'utente legge così com'è («Cosa condivido»), esporta a mano («Esporta le statistiche…») e cancella («Cancella i dati
  raccolti»).
- **Mai d'intralcio.** Le funzioni pubbliche non sollevano eccezioni (`@sicura`): un disco pieno o un file rovinato non
  fermano un'operazione. Le operazioni dell'editor si contano in memoria e si scrivono a gruppi, ogni 30 secondi.
- **Nessuna richiesta di rete finché non c'è il server.** `invio.INDIRIZZO` è vuoto: nessun thread d'invio, nessuna coda,
  nessuna connessione (provato da `test_nessuna_richiesta_di_rete_senza_indirizzo`). I tester mandano il file esportato.

## Consenso

Il file `consenso.json` tiene la scelta e la versione del testo a cui si riferisce. Due versioni:

| Costante | Valore | Testo mostrato |
|---|---|---|
| `TESTO_CONSENSO` | 1 | i dati restano sul computer; li manda l'utente con «Esporta le statistiche…» (oggi) |
| `TESTO_CONSENSO_INVIO` | 2 | i dati si scrivono nel registro e poi partono da soli verso il server (con un `INDIRIZZO`) |

Quando si mette l'indirizzo del server, il «sì» dato al testo 1 non vale più: la domanda si rifà. Se il testo cambia in
modo sostanziale, si alza la costante. `SOLO_BETA = True`: l'interruttore compare solo con una licenza beta, o se c'è già
una scelta o un registro da vedere (decisione aperta: `docs/legale/DA-DECIDERE.md`).

## File sul computer

In `<dati dell'utente>/statistiche/` (cartella 0700, file 0600 su macOS e Linux). Importare il modulo non crea niente.

| File | Contenuto |
|---|---|
| `consenso.json` | `{"formato": 1, "scelta": "si"\|"no", "testo": 1, "quando": "…"}` |
| `installazione.json` | `{"formato": 1, "id": "<32 cifre esadecimali>"}`: codice casuale nato al primo «sì», nuovo a richiesta («Nuovo codice») |
| `eventi.jsonl` | il registro, un evento per riga; oltre 4 MB passa a `eventi.1.jsonl` (ne restano due: al massimo 8 MB) |
| `traguardi.json` | quali «prime volte» sono già state annotate |
| `coda.jsonl`, `coda-invio.jsonl`, `coda-invio.json` | solo con un server: eventi da mandare (al massimo 2 MB), lotto in corso e quanti ne sono partiti |

«Cancella i dati raccolti» toglie registro, traguardi e code; restano la scelta e il codice. «Esporta le statistiche…»
copia il registro in `impaginatore-statistiche-<8 cifre del codice>-<data>-<ora>.jsonl` (0600) nella cartella scelta.

## Gli eventi

Ogni riga è un oggetto JSON con la **busta** e i campi dell'evento. Un evento o un campo che non è nello schema non si
scrive (`schema.pulisci`); un valore `None` si toglie. `schema.controlla_riga` controlla una riga intera.

| Busta | Tipo | Cosa |
|---|---|---|
| `v` | intero | versione dello schema (1) |
| `t` | istante | UTC al secondo, `2026-11-16T10:00:00Z` |
| `id` | 32 esadecimali | codice casuale dell'installazione |
| `sessione` | 12 esadecimali | casuale per processo: lega gli eventi di una stessa apertura |
| `proc` | elenco | `home` (schermata Album), `editor`, `altro` |
| `ver` | versione | versione del programma |
| `serie` | intero | numero di serie della licenza, **solo con una licenza beta**: lega i dati al tester (dato personale) |
| `ev` | nome | nome dell'evento |

Tipi dei campi: *intero* (0 … 10⁹, arrotondato), *decimale* (0 … 10⁶, un decimale), *vero* (true/false), *elenco* (una
parola dell'elenco), *conteggi* (`{parola dell'elenco: intero}`), *codice* (lettere, cifre e `_ . : < >`, senza spazi né
barre, al massimo 100 caratteri), *versione* (`14.6.1`).

| Evento | Quando | Campi |
|---|---|---|
| `consenso` | al «sì» | `scelta` (si), `testo` (versione del testo) |
| `avvio` | avvio della schermata Album, e al «sì» | `sistema` (mac, windows, linux), `sistema_versione`, `architettura` (x86_64, arm64, x86, altra), `python`, `lingua`, `memoria_gb`, `core`, `finestra_programma` (finestra del programma o browser), `licenza` (prova, attiva, scaduta, revocata, non_valida), `fascia`, `beta`, `giorni_dal_primo_avvio` |
| `chiusura` | uscita dal programma | `durata_s` della sessione |
| `finestra` | apertura della schermata o dell'editor | `pagina` (album, editor), `larghezza`, `altezza`, `scala`, `schermo_larghezza`, `schermo_altezza` |
| `licenza` | chiave attivata o tolta | `azione` (attivata, tolta), `stato`, `fascia`, `beta`, `a_scadenza` |
| `album_nuovo` | album creato | `larghezza_cm`, `altezza_cm`, `cartella_foto` (nato da una cartella di foto), `catalogo` (con il prodotto di un laboratorio) |
| `album_aperto` | l'editor apre un album | `foto`, `spread`, `larghezza_cm`, `altezza_cm`, `ppi`, `ms` (tempo di apertura), `sola_lettura` |
| `operazioni` | ogni 30 s e alla chiusura dell'editor, una riga per operazione usata | `op` (nome dell'operazione o «altro»), `n`, `rifiutate`, `licenza` (fermate dalla licenza), `errori`, `assistente` (chieste dall'assistente AI), `ms_tot`, `ms_max` |
| `primo_spread` | il primo spread di un album nato vuoto | `secondi` dall'apertura, `modo` (bozza, manuale, assistente), `foto` |
| `bozza_proposta` | proposta di bozza calcolata | `foto`, `spread`, `ritmo`, `ms` |
| `bozza_accettata` | bozza messa nell'album | `spread`, `foto`, `assistente` |
| `controllo` | «Controlla l'album» | `spread` controllati, `blocca`, `guarda`, `info`, `tipi` (conteggi per tipo di problema), `pronto`, `ms` |
| `esportazione` | esportazione finita | `formato` (jpg, pdf, psd, consegna, progetto, altro), `totale`, `fatti`, `saltati`, `errori`, `ms`, `secondi_dall_apertura`, `filigrana` |
| `importazione` | foto aggiunte, progetto ZIP o catalogo importato | `tipo` (foto, progetto_zip, catalogo), `foto`, `saltate`, `ms` |
| `preparazione` | miniature e volti preparati in sottofondo | `miniature`, `volti`, `ms`, `interrotta` |
| `traguardo` | la prima volta, una sola per installazione | `nome`, `secondi_dal_primo_avvio` |
| `errore` | errore imprevisto di una richiesta o di un'esportazione | `tipo` (classe dell'eccezione), `dove` (`modulo:funzione` più interno del programma), `riga`, `origine` (pacchetto più interno, per esempio `PIL`), `errno` (per esempio `ENOSPC`) |

Traguardi: `primo_album`, `prime_foto`, `primo_spread`, `prima_bozza`, `primo_controllo`, `prima_esportazione`,
`prima_consegna`. I secondi «dal primo avvio» partono dalla prima apertura del programma (inizio della prova gratuita).

Le richieste rifiutate con un messaggio per l'utente (`ValueError`) non sono errori: si contano come `rifiutate`.

### A cosa servono (KPI di `docs/prodotto/REQUISITI-VOCALI.md`)

| Domanda | Dove si legge |
|---|---|
| Quanto ci vuole dal primo avvio al primo spread (obiettivo: meno di 5 minuti) | `traguardo` `primo_spread`, `primo_spread.secondi` |
| Il percorso primo avvio → primo album → foto → spread → controllo → esportazione | i `traguardo` in ordine |
| Quanto si usano bozza e assistente AI | `bozza_proposta`, `bozza_accettata`, `operazioni.assistente`, `primo_spread.modo` |
| Funzioni usate e lente | `operazioni` (`n`, `ms_tot`, `ms_max`), `bozza_proposta.ms`, `controllo.ms`, `esportazione.ms` |
| Dove si rompe | `errore` (tipo, punto, `errno`), `operazioni.errori`, `esportazione.saltati` |
| Su che computer | `avvio`, `finestra` |

## L'invio (quando ci sarà il server)

Oggi spento. Con `invio.INDIRIZZO = "https://…"` (e il testo del consenso 2):

- gli eventi vanno anche in `coda.jsonl` (al massimo 2 MB; oltre restano solo nel registro);
- ogni 15 minuti un thread della schermata manda la coda a lotti di al massimo 50 eventi e 64 KB, con 3 tentativi per lotto
  (pause di 5 e 30 secondi); il progresso si salva lotto per lotto, così un lotto arrivato non si rimanda; quello che
  non parte resta per il giro dopo;
- «Cancella i dati raccolti» chiede anche al server di cancellare i dati dei codici del registro (in sottofondo; se il
  server non risponde la richiesta si perde, e va ripetuta scrivendo al titolare).

Richiesta: `POST` all'indirizzo, `Content-Type: application/json`, `User-Agent: Impaginatore/<versione>`. Nessun cookie,
nessun gettone della sessione locale, nessuna intestazione d'identità. Corpo:

```json
{"formato": 1, "azione": "eventi", "eventi": [{"v": 1, "t": "…", "id": "…", "ev": "avvio", "…": "…"}]}
{"formato": 1, "azione": "cancella", "ids": ["<32 esadecimali>", "…"]}
```

Il client: solo `https://`, certificato e nome del server verificati (`ssl.create_default_context`), nessun
reindirizzamento seguito, proxy del sistema per un server vero e nessun proxy per un indirizzo di questo computer
(`127.0.0.1`, `localhost`). Ogni errore diventa `ErroreInvio` con il solo tipo.

### Il server (da costruire: requisiti)

1. HTTPS con un certificato valido, in UE; risponde `2xx` solo dopo aver salvato il lotto in modo durevole.
2. Controlla ogni evento con le regole di `schema.controlla_riga` (stesso schema, versione `v`) e scarta il resto.
3. Toglie i doppioni: un lotto può arrivare due volte se la risposta si perde (chiave: l'intera riga).
4. Non tiene gli indirizzi IP (o li tronca subito); nessun registro d'accesso con l'IP oltre quanto serve alla sicurezza.
5. `cancella`: toglie tutti gli eventi di quei codici entro 30 giorni e risponde `2xx` anche se non ne ha.
6. Limiti: corpo al massimo 128 KB, poche richieste al minuto per indirizzo; nessuna autenticazione dei client (un
   gettone nel programma sarebbe pubblico comunque): i dati si trattano come non fidati.
7. Conservazione e accesso come deciso in `DA-DECIDERE.md`; la tabella seriale → tester resta solo nel registro del
   negozio (`marketing/negozio/chiavi/`), fuori dal server.

### Accendere l'invio

1. decisione del titolare (server, conservazione, informativa: `DA-DECIDERE.md`);
2. server pronto e provato con `invio.HTTPS` su un indirizzo di prova;
3. `INDIRIZZO` in `invio.py`, testi `statistiche.dove_invio` e informativa aggiornati;
4. aggiornare `test_nessuna_richiesta_di_rete_senza_indirizzo`, che oggi pretende l'indirizzo vuoto.

## Lo strumento del titolare

```
python3 strumenti/statistiche_beta.py <cartella con i file .jsonl dei tester> [--uscita <cartella>] [--registro <registro.csv>]
```

Legge i file esportati, anche in sottocartelle (righe fuori schema scartate e contate, doppioni tolti), scrive
`riepilogo.md` e `riepilogo.csv`: per tester (seriale o codice) e in tutto, funzioni più usate, tempi mediani, percorso
dal primo avvio alla prima esportazione, errori più frequenti, KPI. Con `--registro` (il `registro.csv` del negozio)
accanto al seriale compare l'intestatario: il riepilogo diventa un documento con dati personali e resta sul computer del
titolare, fuori dal repository, come i file dei tester.

Per i tester: manuale, capitolo 14 (`docs/manuale/14-beta-e-statistiche.md`). Accordo con i tester, in bozza:
`docs/legale/ACCORDO-BETA.md`.

## Limiti noti

- L'editor non annota la propria chiusura: lo chiude la schermata (i conteggi si scrivono ogni 30 secondi e a `ferma()`;
  se il processo viene terminato si perdono al massimo gli ultimi 30 secondi).
- I secondi «dal primo avvio» si basano sull'inizio della prova: se l'utente cancella `prova.json` ripartono.
- Il codice d'installazione si azzera a richiesta, ma con la licenza beta il numero di serie resta: i dati restano
  legati al tester finché ha la licenza beta (lo dice il testo del consenso).
- Nessuna firma sui file esportati: un tester può modificarli prima di mandarli.
