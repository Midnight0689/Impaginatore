# Photoshop da script: cosa funziona e cosa no (macOS, Photoshop 2026)

## Struttura dei PSD che Stefano ha scelto
- Ogni foto in una **Cornice di Photoshop** (strumento Cornice, K) con dentro l'originale **incorporato** come oggetto
  avanzato. Per cambiare foto: trascinare un file dal Finder sulla cornice. Non vuole cornici vettoriali + maschere di ritaglio
  (provato e scartato: "non mi piace molto questa struttura per le modifiche").
- Incorporati e non collegati: file autonomi (150–250 MB l'uno), nessun collegamento rotto.
- Cartelle "Pagina sinistra" / "Pagina destra"; sopra ogni cornice, agganciati: Esposizione, Bilanciamento bianco
  (Miscelatore canale), Bianco e nero. Testi veri modificabili. Una guida sulla piega.

## Chiamare Photoshop
- `osascript -e 'tell application "Adobe Photoshop 2026" to do javascript "$.evalFile(new File(\'/percorso/script.jsx\'))"'`
- NON `do javascript (POSIX file ...)`: dà "errore generale 8800".
- Lo .jsx deve essere ASCII puro: i caratteri come "·" vanno come escape (`\xb7`), altrimenti diventano "¬∑".
- Costruire i documenti a 72 ppi (così px = pt per i testi) e alla fine `resizeImage(undefined, undefined, ppi, ResampleMethod.NONE)`.
- Errore di una pagina: chiudere il documento senza salvare, così il file su disco non cambia.

## Action Manager (vedi scripts/photoshop.py, JS_LIB)
- Cornice: `make` di `framedGroupSection` con `framedGroupRect` (classFloatRect top/left/bottom/right).
- Foto nella cornice: con la cornice selezionata, `placeEvent` (linked=false). Poi ridimensionare e spostare il livello
  oggetto avanzato: la cornice (gruppo) resta ferma, il contenuto si muove dentro.
- Sostituire la foto: `placedLayerReplaceContents` sul livello oggetto avanzato, poi riposizionare.
- Esposizione: livello di regolazione `Exps` (chiave `Exps`, `Ofst`, `gammaCorrection`); per cambiarla `setd` con `T   `.
- Bilanciamento bianco: Miscelatore canale (`ChnM`, `Mnch`=false, ogni canale = sé stesso x guadagno in percentuale;
  percentuale = 100 x guadagno_lineare^(1/2,2)).
- Raggruppare: selezionare i livelli per ID (`slct` + addToSelection) e `make layerSection from target`.
  Spostare un livello dentro un gruppo vuoto con `move(INSIDE)` fallisce: "Argomento non valido".

## Trappole incontrate
- **Ordine dei livelli**: nel DOM i livelli vanno dall'alto in basso; le regolazioni agganciate a una cornice stanno
  SOPRA la cornice (indice minore). psd-tools invece li elenca dal basso all'alto. Sbagliare direzione ha cambiato le
  esposizioni della foto vicina: controllare sempre dopo (verifica_psd.py) e correggere.
- **opencv 5** non ha più `CascadeClassifier`: usare `opencv-python-headless<5`.
- **psd-tools e PIL Lab**: in PIL a* e b* sono int8 (complemento a due), non uint8 con offset 128.
- **Nomi file doppi** tra cartelle diverse (es. _DSC4141 in Porticciolo e in Battesimo): le correzioni "per cartella"
  vanno decise sull'origine vera del file (origine.json), non sul nome.
- **Nomi variabili Python con lettere uguali ai campi JS**: un campo `t` (ritaglio in alto) è stato scambiato per "testo".
  Usare nomi espliciti (`txt`).
- **"%" nel codice JS** rompe la formattazione Python con %: concatenare le stringhe.
- Le foto di grandi dimensioni (130 Mpx) fanno scattare l'avviso "decompression bomb" di PIL: `Image.MAX_IMAGE_PIXELS = None`.

## Verifiche da fare sempre
- Rileggere i PSD salvati (psd-tools): misura px e cm, cornici, spazi, esposizioni, foto doppie/mancanti.
- Esportare da Photoshop un JPG e guardarlo: è l'unica prova di cosa vedrà il cliente.
- Prima di aprire un PSD controllare i documenti aperti: mai toccare documenti con modifiche non salvate di Stefano.
