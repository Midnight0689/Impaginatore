# Cataloghi dei laboratori (T-208)

Un **catalogo** è un file JSON che descrive i prodotti album di un laboratorio: formato della pagina, spread ammessi,
abbondanza, zona di sicurezza, piega, risoluzione, profilo colore, nomi dei file di consegna, copertina. Il fotografo
sceglie «Laboratorio X · Album 30 × 30» e ottiene un album con il formato giusto, un controllo che segue le regole del
laboratorio e una **consegna** già pronta (file e riepilogo in una cartella nuova).

Guida per chi scrive un catalogo: [`docs/laboratori/SCRIVERE-UN-CATALOGO.md`](../laboratori/SCRIVERE-UN-CATALOGO.md).

## Dove sta nel codice

| File | Cosa fa |
|---|---|
| `laboratori/catalogo.py` | formato, controllo rigoroso (`valida`, `prodotto`), firma (`firma`, `verifica`) |
| `laboratori/__init__.py` | cataloghi installati (`cataloghi`, `elenco`), scelta di un prodotto (`trova`, `scelta`), licenza, prodotto in `progetto.json` (`per_progetto`, `dal_progetto`, `stato`), formato dell'album (`geometria`, `incompatibile`), importazione (`importa`) |
| `laboratori/consegna.py` | file della consegna: nomi, misure, abbondanza, divisione in pagine, cartella nuova, riepilogo |
| `laboratori/cataloghi/generico.json` | l'unico catalogo che viene con il programma: formati comuni, **non** di un laboratorio |
| `home/server.py` | `GET /api/cataloghi`, `POST /api/importa-catalogo` (finestra del sistema), `POST /api/nuovo` con `prodotto` |
| `editor/server.py` | operazione `prodotto` (con annulla), `GET /api/prodotti`, controllo e bozza con le regole del prodotto, esportazione `consegna` |
| `mcp/strumenti.py` | `elenca_prodotti`, `imposta_prodotto`, `crea_progetto(prodotto=…)`, `esporta(formato="consegna")` |
| `marketing/negozio/chiavi/chiavi.py` | `firma-catalogo`: la firma del produttore (fuori dal programma, con la chiave privata) |

## Dove stanno i cataloghi

- **Del programma**: `src/impaginatore/laboratori/cataloghi/*.json`. Oggi solo `generico.json` («Generico»,
  `generico: true`). Solo questi possono dirsi generici; il Generico è di tutte le fasce.
- **Dell'utente**: `<dati dell'utente>/cataloghi/` (`piattaforma.cartelle.dati_utente()`: su macOS
  `~/Library/Application Support/Impaginatore/cataloghi`, su Windows `%APPDATA%\Impaginatore\cataloghi`, su Linux
  `~/.local/share/impaginatore/cataloghi`). Ci finiscono con «Importa il catalogo di un laboratorio…» nella finestra
  «Nuovo album» (finestra del sistema, tipo `catalogo`), salvati come `<id>.json`. Si possono anche copiare a mano.

Si leggono a ogni richiesta (sono pochi e piccoli); un file che non va finisce tra i `problemi` e non ferma gli altri;
due cataloghi con lo stesso `id`: vince il primo (prima quelli del programma, poi in ordine di nome di file).

## Formato (versione 1)

```json
{
  "formato_catalogo": 1,
  "id": "lab-rossi-2027",
  "nome": "Album fine art 2027",
  "laboratorio": "Laboratorio Rossi",
  "data": "2027-01-15",
  "stato": "confermato",
  "fonte": "Specifiche tecniche del laboratorio, edizione gennaio 2027",
  "note": "Testo libero per il fotografo.",
  "prodotti": [
    {
      "id": "flush-30x30",
      "nome": "Flush mount 30 × 30",
      "descrizione": "Pagine rigide, apertura piatta",
      "pagina_cm": [30, 30],
      "spread_min": 10,
      "spread_max": 40,
      "abbondanza_mm": 5,
      "sicurezza_mm": 8,
      "piega_mm": 10,
      "ppi": 300,
      "ppi_minimi": 180,
      "ppi_consigliati": 250,
      "profilo_colore": "sRGB",
      "consegna": {"formato": "jpg", "qualita": 95, "file": "spread", "nome": "{album}_{n}", "cifre": 2},
      "copertina": "Rigida in lino, da ordinare a parte"
    }
  ],
  "id_firma": 1,
  "firma": "<128 cifre esadecimali>"
}
```

| Chiave | Obbligatoria | Valori | Uso |
|---|---|---|---|
| `formato_catalogo` | sì | `1` | un numero più alto: «aggiorna il programma» |
| `id` | sì | `[a-z0-9][a-z0-9-]{0,39}` | identifica il catalogo (nome del file importato, `progetto.json`) |
| `nome`, `laboratorio` | sì | testo, ≤ 80 caratteri, una riga | mostrati nelle pagine e nel riepilogo |
| `data` | sì | `AAAA-MM-GG` | edizione; serve anche per le chiavi di firma ritirate |
| `generico` | no | `true`/`false` | solo i cataloghi del programma |
| `stato` | no | `confermato` (di serie), `da_confermare` | «da confermare» si vede nelle pagine, nel riepilogo e per l'assistente |
| `fonte` | no | testo, ≤ 300 | da dove vengono le specifiche |
| `note` | no | testo, ≤ 1000, anche su più righe | per il fotografo |
| `prodotti` | sì | da 1 a 200 | `id` diversi |
| `id_firma`, `firma` | no (insieme) | numero; 128 cifre esadecimali minuscole | firma del produttore |

Prodotto:

| Chiave | Obbligatoria | Valori | Uso |
|---|---|---|---|
| `id`, `nome` | sì | come sopra | `id` nel catalogo; `nome` nelle pagine e nei nomi dei file |
| `descrizione` | no | testo, ≤ 300 | |
| `pagina_cm` | sì | `[larghezza 5–150, altezza 5–200]` | **una pagina**: lo spread aperto è largo il doppio |
| `spread_min`, `spread_max` | no | 1–500, min ≤ max | controllo («blocca»), bozza entro `spread_max` |
| `abbondanza_mm` | sì | 0–20 | album nuovi; consegna (compresa nei file) |
| `sicurezza_mm` | no (0) | 0–50, meno di metà del lato corto | testi più vicini al bordo: «guarda» |
| `piega_mm` | no (0) | 0–50 | per lato della piega: volti (al posto di 1 cm) e testi nella zona: «guarda» |
| `ppi` | sì | 150–600 interi | risoluzione degli album nuovi e dei file di consegna |
| `ppi_minimi` | no (150) | 72–`ppi` | foto sotto: «blocca» |
| `ppi_consigliati` | no (200, al massimo `ppi`) | `ppi_minimi`–1200 | foto sotto: «guarda» |
| `profilo_colore` | no | `sRGB` | incorporato nei file (vedi limiti) |
| `consegna.formato` | no | `jpg` | |
| `consegna.qualita` | no (95) | 80–100 | qualità JPEG |
| `consegna.file` | no (`spread`) | `spread`, `pagine` | un file per spread o uno per pagina |
| `consegna.nome` | sì | ≤ 80 caratteri, senza `< > : " / \ \| ? *`, al massimo 4 segnaposti | nome dei file senza estensione |
| `consegna.cifre` | no (2) | 1–4 | zeri davanti ai numeri |
| `copertina` | no | testo, ≤ 500 | solo descrizione: nel riepilogo, «da preparare a parte» |

Segnaposti di `consegna.nome`: `{album}` (nome dell'album), `{prodotto}` (nome del prodotto), `{n}` (numero dello
spread), `{pagina}` (numero della pagina: con `file: "spread"` è la prima pagina dello spread). Deve esserci `{n}`, o
`{pagina}` con `file: "pagine"`: ogni file ha un nome diverso. Si sostituiscono uno per uno: il modello **non** passa da
`str.format` (niente `{0}`, `{x.attr}`, `{__class__}`). I valori si ripuliscono (`nomi.nome_cartella`: caratteri
vietati, nomi riservati di Windows, al massimo 40 caratteri per segnaposto): il nome finale sta sotto i 255 caratteri.

Ogni altra chiave è un errore (anche dentro `consegna`). Controlli in più: niente chiavi doppie, niente `NaN`/`Infinity`,
file al massimo 1 MB, UTF-8, niente caratteri invisibili nei testi di una riga (`validazione.testo`).

## Dato non fidato

Il catalogo arriva da altri. Per questo:

- **Niente percorsi, niente codice**: nessuna chiave è un percorso o un'espressione; il modello dei nomi è testo con
  segnaposti fissi; `id` è un identificativo ristretto (non può contenere `/`, `..`).
- **Testi sempre come testo**: le pagine li mettono con `textContent`, `new Option(...)`, `optgroup.label` (mai
  `innerHTML`); l'assistente li riceve ripuliti con `dato()` e l'istruzione di trattarli come dati.
- **Misure limitate**: ogni numero ha un intervallo; i file della consegna non superano le misure di un album
  (pagina ≤ 150 × 200 cm, 600 ppi) e passano dallo stesso motore delle esportazioni JPG.
- **Importazione**: i byte si leggono una volta sola (al massimo 1 MB), si scrivono in un file temporaneo nella cartella
  dei cataloghi, si controllano (formato, firma, licenza) e solo allora diventano `<id>.json`; un errore non lascia niente.
  Il file lo sceglie l'utente nella finestra del sistema: la richiesta HTTP non porta percorsi.
- **Sostituzioni**: un catalogo del programma non si sostituisce (stesso `id`: rifiutato); uno **verificato** non si
  sostituisce con uno non verificato.

## Firma

Facoltativa, con lo stesso meccanismo delle licenze: Ed25519 (`impaginatore.ed25519`, solo libreria standard) e le
chiavi pubbliche compilate nel programma (`licenze.chiave.CHIAVI_PUBBLICHE`).

- Byte firmati: `b"IMPAGINATORE-CATALOGO-v1\x00"` + JSON canonico del catalogo senza `firma` (chiavi ordinate, separatori
  `,` e `:` senza spazi, `ensure_ascii`): `catalogo.canonico` = `licenze.chiave.canonico`. Il dominio separa le firme dei
  cataloghi da quelle delle licenze e delle revoche.
- Chi firma: il produttore del programma, con `python3 marketing/negozio/chiavi/chiavi.py firma-catalogo <file>`
  (chiave privata fuori dal repository, come per le licenze). Il produttore firma dopo aver ricevuto le specifiche dal
  laboratorio e averle provate nel programma (lo strumento non controlla lo schema).

| Caso | Esito |
|---|---|
| Firma valida | **verificato** («firmato dal produttore di Impaginatore») |
| Nessuna firma | si usa, **non verificato** («il catalogo non è firmato») |
| Chiave che questa versione non conosce | si usa, non verificato, con il motivo |
| Copia di sviluppo (chiave pubblica segnaposto) | si usa, non verificato («versione di sviluppo») |
| Firma presente ma sbagliata (contenuto cambiato) | **rifiutato** |
| Firmato con una chiave ritirata (`data` dopo `emesse_fino`) | **rifiutato** |
| Solo uno tra `id_firma` e `firma`, o firma non esadecimale | rifiutato |

«Non verificato» si vede nella finestra «Nuovo album», nella consegna dell'editor, nel riepilogo della consegna e
per l'assistente. Il catalogo del programma è verificato per costruzione (viene con il pacchetto firmato).

## Licenza

`preset_laboratori` di `tier.json`: oggi è in tutte le fasce (Essenziale, Pro, Studio, Laboratorio e prova). Il cancello
c'è lo stesso, per le fasce che verranno: i cataloghi **non generici** si importano, si scelgono (album nuovo, editor,
assistente) e si consegnano solo se la licenza comprende `preset_laboratori` (`laboratori.controlla_licenza`, messaggio
di `licenze.motivo`). Il Generico è di tutti. La consegna è un'esportazione JPG: cancello `export_jpg`; nella prova i
file hanno la filigrana e il riepilogo lo dice.

Un prodotto è «generico» solo se il catalogo installato con lo stesso `id` è generico **e** ha lo stesso identico
prodotto: un `progetto.json` ricevuto non può dichiararsi generico (né verificato) da solo.

## Il prodotto nel progetto

`progetto.json` ha la chiave facoltativa `prodotto` (vedi [`FORMATO-PROGETTO.md`](FORMATO-PROGETTO.md)): una **copia**
del prodotto e dei dati del catalogo (`per_progetto`), così il progetto resta giusto anche se il catalogo cambia o
sparisce. All'apertura si controlla come un catalogo (`dal_progetto`); se manca o questa versione non la capisce (un
formato più recente), il progetto si apre come sempre, senza prodotto, e il file la tiene com'era
(`editor.PRODOTTO_FILE`). Nessuna migrazione: la chiave è nuova e facoltativa.

- **Album nuovo** (schermata dei progetti, `POST /api/nuovo` con `prodotto`: `"catalogo/prodotto"` o
  `{catalogo, prodotto}`): formato dello spread = `[2 × larghezza, altezza]`, abbondanza e ppi del prodotto; spazio e
  margine restano quelli scelti. Le misure scritte a mano si ignorano.
- **Album esistente** (editor, operazione `{"op": "prodotto", "prodotto": "catalogo/prodotto"}`, `null` per toglierlo):
  un passo d'annulla («Prodotto del laboratorio»), salvato con l'album. **Il formato di un album fatto non cambia**: un
  prodotto con un'altra pagina (oltre mezzo millimetro) o con più abbondanza di quella dell'album si rifiuta con il
  motivo («crea un album nuovo con questo prodotto»). Cambiare il formato vorrebbe dire ricalcolare geometria, guide e
  cache dell'editor in un passo d'annulla: non è stato fatto (vedi «Limiti»).
- **Stato per la pagina** (`/api/state` → `prodotto`): la copia, `verificato`, `generico`, `installato`, `verifica`
  e `avviso` (il motivo, se l'album non ha più il formato del prodotto: progetto ricevuto o modificato a mano).

## Controllo e bozza

Con un prodotto, `/api/controlla` (e `controlla_album` dell'assistente):

| Regola | Livello | Tipo |
|---|---|---|
| spread fuori da `spread_min`–`spread_max` (solo controllo di tutto l'album) | blocca | `prodotto` |
| formato o abbondanza dell'album diversi da quelli del prodotto (solo tutto l'album) | blocca | `prodotto` |
| foto sotto `ppi_minimi` / sotto `ppi_consigliati` | blocca / guarda | `risoluzione` |
| testo a meno di `sicurezza_mm` dal bordo | guarda | `sicurezza` |
| testo nella zona `piega_mm` per lato | guarda | `piega` |
| volto a meno di `piega_mm` dalla piega (1 cm se il prodotto non lo dice) | guarda | `volto_piega` |

Senza prodotto il controllo è quello di prima. La bozza (`/api/bozza`, operazione `bozza`) resta entro `spread_max`:
alza le foto per spread quanto basta, e se gli spread sono ancora troppi tiene i primi e lo dice (`limite_prodotto`:
`spread_max`, `foto_escluse`); applicare più spread di quelli ammessi si rifiuta.

## Consegna (UX-013)

Editor, Esporta → **Consegna** (`/api/export` con `fmt: "consegna"`), o l'assistente con `esporta(formato="consegna")`:

1. Controlli prima di cominciare: c'è il prodotto, l'album ha il suo formato e almeno la sua abbondanza, licenza.
2. Cartella **nuova**: di serie `Esportazioni/Consegna/<prodotto> <data ora>`; una cartella scelta si usa se non esiste
   o è vuota, altrimenti se ne crea una nuova dentro. Non si sovrascrive mai niente.
3. Per ogni spread: il motore disegna dagli originali, con l'abbondanza dell'album (come i JPG «stampa»); si toglie
   l'abbondanza in più, si porta alla risoluzione del prodotto (`ppi`, LANCZOS) e, con `file: "pagine"`, si divide sulla
   piega (ogni pagina tiene la sua abbondanza anche dal lato della piega, presa dall'altra pagina). JPEG con la qualità
   del prodotto, `dpi` del prodotto e profilo sRGB incorporato (`srgb_icc`, lo stesso delle altre esportazioni).
4. `Riepilogo consegna.txt`: album, laboratorio, catalogo e firma, prodotto, «da confermare», misure, abbondanza, zone,
   risoluzione, profilo, file e pixel, spread rispetto ai limiti, esito del controllo, filigrana della prova, copertina
   «da preparare a parte», elenco dei file. Da mandare al laboratorio insieme ai file.

Il registro (`/api/log`) ha le stesse righe dei JPG, nella lingua dell'utente (in italiano: `Esporto N spread in CONSEGNA →
<cartella>`, `  spread k: <file>`, `SALTATO spread k -> <motivo>`, `ESPORTATI`), più le due righe fisse `RISULTATO:<cartella>`
e `[finito]`. Chi deve sapere com'è andata (pagina, assistente) legge `/api/esito`, che è uguale in ogni lingua. Nessuna rete: la consegna è una
cartella sul computer; il caricamento sul sito del laboratorio lo fa il fotografo.

## Assistente AI (MCP)

Nessun argomento nuovo è un percorso: i prodotti si nominano con `"catalogo/prodotto"` (solo identificativi).
`elenca_prodotti` (lettura), `imposta_prodotto` (modifica, un passo d'annulla dell'editor), `crea_progetto` con
`prodotto` (le misure non servono), `esporta` con `formato: "consegna"` (cartella nuova costruita dal server). Il
riassunto di `apri_progetto` dice il prodotto dell'album. I cataloghi non si importano dall'assistente: li sceglie
l'utente nella finestra del sistema.

## Limiti

- **Profilo colore**: solo sRGB, quello che il programma incorpora già (profilo di sistema o quello interno di Pillow).
  Nessun profilo ICC di laboratorio (licenze dei file da chiarire con ogni laboratorio; conversione con
  `ImageCms.profileToProfile` possibile in una versione futura con `profilo_colore` diverso da `sRGB`).
- **Formato dei file**: solo JPEG. TIFF e PDF di consegna no.
- **Copertina**: solo descritta nel riepilogo; Impaginatore non prepara il file della copertina (dorso, risvolti).
- **Formato di un album fatto**: non si cambia scegliendo un prodotto (si crea un album nuovo).
- **Nessun catalogo di laboratori veri** nel programma: vedi «Decisioni» nel rapporto di T-208. Il Generico è fatto di
  formati comuni ed è segnato come tale.
- **Testi**: i messaggi del server sono in italiano nel codice, come il resto del server; quelli delle pagine passano da
  `risorse/testi/it.json`.
