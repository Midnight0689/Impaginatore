# Formato dei progetti (2.0)

Un progetto dell'Impaginatore è una cartella. Dalla 2.0 l'impaginazione si salva in `album.json`: **solo dati, mai codice**.
Le versioni 1.x salvavano `spec.py`, un file Python che veniva eseguito all'apertura (audit SEC-001, SEC-003, SEC-009):
la 2.0 non esegue mai niente di quello che sta in un progetto, lo legge come testo e lo controlla.

Codice: `src/impaginatore/formato.py` (lettura e scrittura), `validazione.py` (controlli), `formato_1x.py` (spec.py delle
1.x), `archivio.py` (Importa ZIP), `nomi.py` (nome del progetto e della cartella). Test: `tests/test_formato.py`,
`tests/test_sicurezza.py`.

## La cartella

| File | Contenuto | Se manca o non è valido |
|---|---|---|
| `progetto.json` | impostazioni: formato, foto, correzioni, testi, stili, guide | il progetto non si apre (messaggio chiaro) |
| `album.json` | impaginazione (formato 2, sotto) | manca: album vuoto; non valido: il progetto non si apre |
| `spec.py` | impaginazione di un progetto 1.x non ancora aperto con la 2.0 | si converte alla prima apertura (sotto) |
| `spec.py.1x` | lo `spec.py` originale dopo la conversione (`.1x.2`, `.1x.3`... se c'è già) | copia di sicurezza: il programma non la legge più |
| `modelli_utente.json` | modelli arrivati con un progetto esportato da altri | si ignorano le voci non valide |
| `Foto/` | foto del progetto (o di un pacchetto esportato) | — |
| `_cache/meta.json`, `faces.json`, `origine.json`, `thumbs/` | elenco delle foto con le misure, volti, cartella d'origine, miniature | si rifanno dalle foto |
| `_backup_editor/` | copie fatte a ogni salvataggio: `AAAAMMGG-hhmmss_album.json` e `_progetto.json` (le 1.x: `_spec.py`) | — |
| `PSD/`, `Esportazioni/` | uscite | — |

Ogni file del programma si scrive in modo **atomico** (`formato.scrivi_atomico`, `scrivi_json`, `copia_atomica`): un file
temporaneo con nome unico nella stessa cartella, `fsync`, `os.replace` al posto di quello vero, `fsync` della cartella
(dove il sistema lo permette). Un'interruzione a metà (programma chiuso, batteria, disco pieno) lascia il file di prima,
mai uno troncato (BUG-005). Vale per `album.json`, `progetto.json`, `_cache/*.json`, il registro dei progetti, i modelli
dell'utente, le copie di `_backup_editor` e `origine.json` scritto da `abbina`.

## album.json (formato 2)

JSON in UTF-8, al massimo 10 MB. Un elemento per riga, così si legge e si confronta anche a occhio.

```json
{
  "formato": 2,
  "programma": "Impaginatore 2.0.0",
  "spread": [
    {
      "sinistra": {"modo": "W", "elementi": [
        {"k": "t", "kind": "title", "c": 0, "r": 0, "w": 12, "h": 8}
      ]},
      "destra": {"modo": "I", "elementi": [
        {"k": "full", "foto": "_DSC4287"}
      ]}
    }
  ]
}
```

| Chiave | Tipo | Note |
|---|---|---|
| `formato` | intero, obbligatorio | `2`. Un numero più alto: «salvato da una versione più recente: aggiorna il programma». Altro: formato sconosciuto |
| `programma` | testo, facoltativo | chi l'ha scritto (solo informazione, al massimo 200 caratteri) |
| `spread` | elenco, obbligatorio | al massimo 2000 spread; ognuno ha esattamente `sinistra` e `destra` |
| `sinistra` / `destra` | oggetto | `modo`: `"I"` (immersiva, la griglia arriva al bordo) o `"W"` (bianca, con margine); `elementi`: al massimo 500 |

Le foto si indicano con il **nome del file senza estensione** (`"_DSC4287"`), mai con il numero: all'apertura si controlla
che ogni foto sia nel progetto (`_cache/meta.json`).

### Elementi

Ogni elemento è un oggetto con `k` (tipo). Le chiavi obbligatorie devono esserci tutte; una chiave non prevista è un errore
(«chiave sconosciuta»): un file scritto da altri non può far arrivare al motore valori che il programma non conosce.

| Tipo | Obbligatorie | Facoltative |
|---|---|---|
| foto nella griglia | `k: "p"`, `foto`, `c`, `r`, `w`, `h` | `bw`, `z`, `a`, `bd`, `sh`, `oc`, `zo` |
| foto a tutta pagina | `k: "full"`, `foto` | come sopra |
| foto in cornice libera | `k: "f"`, `foto`, `x`, `y`, `w`, `h` | come sopra |
| titolo / firma nella griglia | `k: "t"`, `kind: "title"` o `"end"`, `c`, `r`, `w`, `h` | `ts`, `zo` |
| titolo / firma liberi | `k: "t"`, `kind: "title"` o `"end"`, `fx`, `fy`, `fw`, `fh` | `ts`, `zo` |
| livello di testo | `k: "t"`, `kind: "txt"`, `tx`, `fx`, `fy`, `fw`, `fh`, `font`, `size`, `col`, `al`, `tr` | `auto`, `lh`, `caps`, `zo`, `stile` |

| Chiave | Valori ammessi |
|---|---|
| `c`, `r`, `w`, `h` (griglia) | interi; la pagina è 12 colonne × 8 righe: `c` 0–11, `r` 0–7, `w` 1–12, `h` 1–8, e la cornice non esce dalla griglia |
| `x`, `y`, `w`, `h` (cornice libera) | frazioni della pagina: posizione da −10 a 10, misura maggiore di 0 e fino a 10 |
| `fx`, `fy`, `fw`, `fh` (testi liberi) | come sopra, misura da 0 a 10 |
| `foto` | testo (al massimo 255 caratteri), nome di una foto del progetto |
| `bw` | `true` / `false` (bianco e nero) |
| `z` | numero da −100 a 100 (ingrandimento; 1 = nessuno) |
| `a` | angolo in gradi, da −360 a 360 |
| `bd` | `[millimetri da 0 a 100, "#rrggbb"]` (bordo) |
| `sh`, `oc` | interi da 0 a 100 (ombra, opacità) |
| `zo` | intero da −1 000 000 a 1 000 000 (ordine dei livelli) |
| `ts` | numero da 0,05 a 20 (scala dei caratteri di titolo e firma) |
| `tx` | testo fino a 100 000 caratteri (a capo ammessi) |
| `font`, `stile` | testo fino a 200 caratteri |
| `size` | numero maggiore di 0 e fino a 5000 (punti) |
| `col` | `[r, g, b]`, interi da 0 a 255 |
| `al` | `"left"`, `"center"`, `"right"` |
| `tr` | numero da −1000 a 5000 (spaziatura) |
| `auto`, `caps` | `true` / `false` |
| `lh` | numero da 0,1 a 10 (interlinea) |

Regole comuni a tutti i file JSON che arrivano da fuori (`formato.leggi_json_rigoroso`): niente chiavi doppie, niente
`NaN` o `Infinity`, numeri finiti e non booleani dove serve un numero, testi senza surrogati e (per i nomi) senza caratteri
invisibili o di controllo. Ogni problema è un `ErroreProgetto` con il punto esatto, per esempio
«spread 3, pagina sinistra, elemento 2, z: deve essere un numero da -100 a 100»: mai un'eccezione qualsiasi più avanti.

`formato.salva` controlla `album.json` anche **prima di scriverlo**: il programma non può salvare un file che poi non
riaprirebbe.

### Versioni future del formato

Una versione che cambia `album.json` aumenta `formato` e aggiunge in `formato.py` la conversione dal formato precedente,
con un test che apre un progetto salvato con la versione di prima (come `tests/dati/progetto_152` per la 1.5.2). Il
formato 2 va letto da tutte le 2.x.

## progetto.json

Si controllano le chiavi che il programma usa (tipi, e intervalli dove un valore sbagliato bloccherebbe il programma o il
computer); **le chiavi che il programma non conosce restano com'erano**, perché possono venire da altre versioni.
Obbligatoria solo `formato_cm` ([larghezza, altezza] da 1 a 1000 cm). Controllate: `ppi` (30–2400), `abbondanza_mm`,
`spazio_mm`, `margine_mm`, `dimensioni_esatte`, `nome`, `foto`, `foto_extra`, `uscita_psd`, `tolte`, `stelle`, `tono_escl`,
`testo`, `esposizione`, `centri_volto`, `bilanciamento_bianco`, `tono`, `tono_L`, `tono_Z`, `ritocco`, `colori`, `stili`, `guide`.
Formato e risoluzione insieme non possono superare 4 miliardi di pixel per spread.

`prodotto` (facoltativa, T-208): il prodotto del laboratorio scelto per l'album, copiato dal catalogo
(`formato_catalogo`, `catalogo`, `nome_catalogo`, `laboratorio`, `data`, `stato`, `prodotto`), così il progetto resta giusto
anche se il catalogo cambia o sparisce. All'apertura si controlla con le regole dei cataloghi
([`CATALOGHI.md`](CATALOGHI.md)); se non va o viene da una versione più recente, l'album si apre senza prodotto e il file la
tiene com'era. I progetti senza questa chiave si aprono come prima: nessuna migrazione.

Il **nome del progetto** è un dato: sta in `progetto.json` e nell'interfaccia, mai dentro un file di codice (SEC-003).
Si accetta un testo di una riga, al massimo 120 caratteri, senza caratteri invisibili o che cambiano il verso del testo.

## Cache delle foto

`_cache/meta.json` (elenco delle foto: `n` nome del file, `dt`, `src`, `w`, `h`, `ar`), `faces.json` (volti),
`origine.json` (cartella d'origine di ogni foto). Se un file è rovinato o non valido (anche un `n` con `../` o un
percorso assoluto), il motore lo tralascia e lo ricostruisce dalle foto: il progetto si apre lo stesso.

## Modelli dell'utente

`modelli_utente.json` nella cartella dei dati dell'utente (macOS `~/Library/Application Support/Impaginatore`, Windows
`%APPDATA%\Impaginatore`, Linux `$XDG_DATA_HOME/impaginatore`): un elenco di modelli
`{"id", "nome", "n", "lato", "pages": [{"mode", "items": [...]}, {...}]}`; ogni cornice ha solo geometria
(`k` `p`/`f`/`full`, `c r w h` o `x y w h`, `a`, `zo`). Ogni modello si controlla come dato (`validazione.modello`):
quelli non validi si tralasciano e **restano nel file** com'erano (il prossimo salvataggio non li cancella); un file
illeggibile si copia in `modelli_utente.json.illeggibile` prima di essere riscritto.

I modelli che arrivano **con un progetto** (`<progetto>/modelli_utente.json`, li mette l'esportazione) non entrano mai da
soli nei tuoi (SEC-009): l'editor li mostra solo in quel progetto, segnati «del progetto», e li aggiunge ai tuoi solo se
premi «Aggiungi ai miei» (`POST /api/modelli {"azione": "importa", "id": ...}`).

## Progetti delle versioni 1.x (spec.py)

Alla prima apertura con la 2.0 (`formato.carica`), uno `spec.py` si **legge senza eseguirlo** (`formato_1x.leggi`): il
testo si analizza con `ast` e si accetta solo la grammatica che scrivevano l'editor 1.x e l'assistente con la skill:

- la riga di descrizione in alto (un testo) e i commenti;
- `from album import *` e `from album_libere import *` (o solo alcuni dei loro nomi, anche con `as`);
- `NOME = espressione`, `NOME += espressione`, `NOME.append(espressione)`, `NOME.extend(espressione)`;
- espressioni: testi, numeri, `True`/`False`/`None`, `+`/`-` davanti ai numeri, `+ - * /` tra numeri, `+` tra elenchi o tra
  testi, elenchi e tuple (anche con `*elenco`), nomi già assegnati, chiamate ai costruttori del motore
  (`P FULL TXT I W DUO VLL V4 G4 CV SV PP COL2 BAND2 STRIP3`, `FREE TXTF TEXT ROT STY`) con argomenti di questa grammatica.

Tutto il resto (import di altri moduli o di file del progetto, funzioni, cicli, condizioni, attributi, indici, dizionari,
`lambda`, chiamate a qualsiasi altra funzione, `**argomenti`...) produce l'errore
«Questo progetto contiene istruzioni non riconosciute (spec.py, riga N: motivo). Per sicurezza l'Impaginatore non esegue il
contenuto dei progetti: il progetto non è stato aperto né modificato.» Ci sono limiti contro i file costruiti per bloccare
il programma: 4 MB, 400 000 nodi, 60 livelli di annidamento, elenchi fino a 200 000 elementi, testi fino a 1 milione di
caratteri, numeri fino a 10¹².

I costruttori chiamati sono quelli veri del motore (stessi elementi delle 1.x), solo dopo aver confrontato gli argomenti
con la loro firma. Poi la conversione: lo stato si controlla come un `album.json` (stesse regole), si scrive `album.json`,
e `spec.py` diventa `spec.py.1x` (non si cancella niente). Un progetto che non si converte resta com'era.

La schermata dei progetti controlla `spec.py` senza caricare il progetto (`formato.controlla`, con costruttori finti
della stessa firma): un progetto non valido mostra l'errore e non avvia l'editor.

## Esportare per la versione 1.x

La 2.0 **non scrive più `spec.py`** durante il lavoro. Chi deve riaprire un progetto con la 1.x spunta «Aggiungi spec.py
per la versione 1.x» in Progetto → Esporta progetto: il pacchetto esportato contiene anche `spec.py` e le copie del motore
che gli script 1.x leggono (`album_libere.py`, `testo.py`, `vib_lut.npz`). Ogni valore è scritto con `repr` e la riga di
descrizione con tutte le virgolette e i caratteri di controllo protetti: nessun dato dell'utente diventa istruzione.

Quando un pacchetto così torna nella 2.0 la cartella ha sia `album.json` sia `spec.py`. Alla prima apertura
(`formato.carica`) `spec.py` si confronta, riga di descrizione esclusa, con quello che la 2.0 scriverebbe per `album.json`:
se è uguale vale `album.json` (che conserva anche quello che la 1.x non sa scrivere, come l'ordine dei livelli dei
titoli); se è diverso l'ha cambiato la 1.x, quindi si converte `spec.py` (sempre senza eseguirlo) e l'`album.json` di prima
va in `_backup_editor/` (si ritrova in «Versioni precedenti»). In tutti e due i casi `spec.py` diventa `spec.py.1x`. La
schermata dei progetti controlla anche uno `spec.py` che sta accanto ad `album.json`: con istruzioni non riconosciute il
progetto non si apre.

Scartato: scrivere sempre anche `spec.py` accanto ad `album.json` (due file da tenere allineati, e un file di codice nei
progetti che si scambiano); non offrire l'esportazione (la conversione inversa costa poche righe ed è provata da un test
con l'`album.py` della 1.5.2).

## Importa ZIP

`archivio.estrai` controlla **tutto l'elenco prima di scrivere qualsiasi file**:

- percorsi assoluti, lettere di unità (`C:`), `..` (anche con `\`), collegamenti simbolici: lo ZIP si rifiuta tutto;
- al massimo 20 000 voci, 50 GB estratti, spazio libero sul disco (con 1 GB di riserva), rapporto di compressione oltre
  100 (sopra i 100 MB) o oltre 200 per un file sopra 1 MB (bombe ZIP): rifiutato;
- si estraggono solo i tipi di file di un progetto (`.json`, foto `.jpg .jpeg .png .tif .tiff .heic .heif .webp`, `.txt`, e
  `spec.py` solo nella cartella del progetto, che si legge come dato); programmi, script `.py`, file nascosti, voci cifrate,
  dispositivi e nomi non validi su uno dei tre sistemi si tralasciano e si dice quanti;
- ogni file si scrive in modalità esclusiva, senza seguire collegamenti; `zipfile` controlla il CRC e non dà più byte di
  quelli dichiarati: uno ZIP rovinato interrompe l'importazione e non lascia niente.

Dopo l'estrazione `formato.prepara_importato` controlla `progetto.json` e l'impaginazione, toglie i percorsi del computer
di chi ha esportato (`foto`, `foto_extra`, `uscita_psd`) e fa puntare `_cache/meta.json` solo alla cartella `Foto` del
progetto. Un progetto non valido non entra nell'elenco.

L'esportazione (`editor.server.esporta_progetto`) scrive `album.json`, `progetto.json` senza percorsi, la cache, i modelli
(nel file del progetto, che dall'altra parte non entrano da soli nei modelli di chi lo riceve), `font_usati.txt`,
`LEGGIMI.txt`, le foto se richieste, `spec.py` se richiesto, e volendo lo ZIP.

## Nomi delle cartelle

`nomi.nome_cartella` ricava dal nome del progetto un nome di cartella valido su macOS, Windows e Linux: i caratteri vietati
da Windows (`< > : " / \ | ? *`) e quelli invisibili diventano `-`; niente punti all'inizio (cartella nascosta) né punti o
spazi in fondo; i nomi riservati di Windows (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, anche con
estensione) prendono un `_` davanti; Unicode in forma composta (NFC); al massimo 80 caratteri. Vale per i progetti nuovi,
per Importa ZIP e per Esporta progetto.
