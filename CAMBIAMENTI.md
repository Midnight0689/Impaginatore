# Registro delle modifiche

Scritto per Claude (e per Stefano): cosa è stato cambiato, perché, in quali file.
**Regola:** prima di toccare il programma si legge questo file; dopo ogni modifica si aggiunge una voce in cima (numero di versione = numero del commit, vedi riquadro Versione), poi commit + push. Le versioni si possono ripristinare dal riquadro Versione → "Versioni precedenti".

## Versione 83 — Pannello Tono ridisegnato: una riga per foto con scala
Le barre verticali si schiacciavano con il pannello basso. Ora ogni foto ha una riga: numero, miniatura, scala della luce (L* 20–90) con la fascia verde della zona giusta e il pallino della foto, valore, e un consiglio scritto («Esposizione +0,5 · Ombre +20»). In Completa un pallino tratteggiato mostra dove arriva la foto dopo la correzione. La colonna dei comandi scorre se il pannello è basso. — `index.html`.

## Versione 82 — Tono più intelligente: scene volute, centro e pelle, correzione leggera, vista album
- **Scene chiare o scure di proposito** (abito bianco, interno con luci accese): la tolleranza per quella foto sale di 1,5 volte e sotto la miniatura compare «ok · scena chiara/scura». Nella vista album sono segnate con un contorno blu.
- **Misura dove conta**: nella luce media il centro pesa più dei bordi e la pelle il doppio, quindi uno sfondo scuro non fa sembrare sottoesposto un viso giusto.
- **Correzione più leggera**: Semplice e Completa portano la foto solo dentro il bordo della zona (non fino al centro), con il cursore **Intensità** (0–100%) per dosarla.
- **Vista album**: tasto «Vista album» nella scheda Tono, con tutti gli spread, punteggio e un quadratino per foto; «Peggiori prima» li ordina, clic per andare allo spread.
— `editor.py` (`_tono_pesi`, `_tono_scena`, `tono_all`, `/api/tono_all`), `index.html` (`albumHtml`, `tonoF`).

## Versione 81 — Tono: riferimento standard fisso (L* 52 ±12), uguale per tutto l'album
Il Tono non dipende più dalle altre foto né dallo spread: ogni foto è confrontata con un **valore standard** di luce media (L* 52, regolabile nella scheda Tono insieme all'ampiezza della zona, ±12). Oltre ±12 la foto è «da guardare», oltre ±18 «da correggere». Alte luci (p95 tra 82 e 97) e ombre (solo informative) hanno zone fisse. Semplice e Completa portano la foto verso lo standard senza bruciare le alte luci. Sull'album di Serena segnala 24 foto su 92 (con ±8 erano 40, troppe: scene chiare e interni sono naturalmente diversi). Valori salvati nel progetto: `tono_L`, `tono_Z` (solo se cambiati). — `editor.py` (`_tono_L0`, `_tono_Z`, `_tono_sim`, op `tono_L`), `index.html` (`drawTono`).

## Versione 79 — Il riquadro «Design» mostra le correzioni
Il riquadro a destra (la foto con il ritaglio) mostrava sempre l'originale: ora mostra la foto con esposizione e ritocchi, e si aggiorna in tempo reale mentre trascini i cursori. — `editor.py` (`corr_thumb`, `/img/corr`), `index.html` (`corrUrl`).

## Versione 78 — Anteprima live mentre si trascinano i cursori
- Trascinando Esposizione, Contrasto, Alteluci, Ombre, Bianchi, Neri, Temperatura, Tinta, Vibranza, Saturazione, Angolo o Bordo, la foto nella cornice (anche se la stessa foto è usata più volte nello spread) si aggiorna subito, con lo stesso calcolo dell'anteprima e del PSD (≈40 ms a foto). Al rilascio il valore si salva e l'immagine definitiva sostituisce quella veloce senza lampeggi.
- Con la scheda «Tono» aperta, anche colonne, numeri, colori e pillole sulle cornici si muovono in tempo reale.
- — `editor.py` (`live_photo`, `/img/live`, `tono_spread(over=…)`), `index.html` (`liveSend`, `livePump`, `updPills`).
- Non è live (si aggiornano al rilascio): Ombra, Opacità, Scala, Livelli/Curva e gli ingrandimenti della galleria.

## Versione 77 — Correzione Completa più prudente
Sullo spread 3 la Completa aveva corretto una foto già a posto (esposizione −0,6 e alteluci +40) perché le sue ombre erano diverse dalle altre: troppo aggressiva. Ora:
- Le **ombre** non fanno più scattare nessuna correzione (restano solo il puntino informativo): dipendono troppo dalla scena. Le alte luci diverse al massimo mettono «da guardare».
- La correzione parte solo dalle foto fuori tono (stessi casi di «Semplice»), e luce media pesa molto di più di alte luci e ombre; alteluci/ombre ±20, bianchi ±15.
- Sul progetto di Serena i casi da correggere passano da 48 a 12, tutti con la luce media davvero fuori; le correzioni non bruciano le luci (la Completa si ferma prima della Semplice se per arrivare alla mediana dovesse bruciarle). — `editor.py` (`_tono_ottimizza`, soglie).

## Versione 76 — Scheda Tono: correzione «Completa» (esposizione + alteluci, ombre, bianchi) e bianco e nero
- **Interruttore Semplice / Completa** nella scheda Tono. «Semplice» = solo Esposizione (come prima). «Completa» misura per ogni foto luce media, alte luci (95° percentile) e ombre (10°) e prova esposizione, Alteluci, Ombre e Bianchi con la stessa pipeline dell'anteprima e del PSD, scegliendo i valori che avvicinano la foto alla mediana dello spread. Tetti prudenti (esposizione ±1 EV, alteluci/ombre ±40, bianchi ±30), zona di tolleranza attorno alla mediana (non porta la foto al valore esatto, solo dentro la fascia giusta) e penalità sulle correzioni grandi; non accetta correzioni che bruciano le luci.
- Sotto ogni miniatura, in Completa, due puntini (luci e ombre) e l'elenco di cosa cambierebbe («esp. +0,1 · luci −10 · ombre +25»).
- **«Correggi»** è un'unica operazione con un solo annulla per tutte le foto (`tono_fix`).
- **Bianco e nero:** la misura ora considera la foto come appare in B/N (prima la misurava a colori). Un eventuale bordo bianco o nero della foto stessa non conta come tono.
- — `editor.py` (`_tono_sim`, `_tono_ottimizza`, `tono_spread`, op `tono_fix`), `index.html`.

## Versione 75 — Scheda Tono: misura più giusta sulle foto con sfondo scuro
Una foto con sfondo scuro e soggetto chiaro (es. fiocco bianco su legno) veniva proposta di +1 EV perché la mediana guardava solo lo sfondo, e la correzione la rovinava. Ora il tono è la media tra la luce media e le alte luci (90° percentile): le foto di quello spread risultano allo stesso tono (scarti ≤ 0,2). La correzione automatica è limitata a ±1 EV per volta. — `editor.py` (`_tono_misure`, `TONO_MAX`).

## Versione 74 — Scheda «Tono»: misura se le foto di uno spread hanno la stessa luminosità
- **Pannello in basso a due schede:** «Galleria» e «Tono» (la scelta si ricorda; ognuna ha la sua altezza regolabile). — `index.html`.
- **Scheda Tono:** frase di sintesi («2 foto da sistemare: la 2 è troppo scura…»), voto di uniformità su 100, una colonna per foto (più alta = più chiara) con la fascia verde «zona giusta» (±0,3 EV dalla mediana dello spread), miniatura e istruzione («schiarisci di 0,8», «ok»); riga con il tono degli spread vicini; «⚠ luci» se schiarire farebbe bruciare le alte luci.
- **Sulle cornici:** pillole con numero e scarto in EV (verde, giallo ≤ ±0,6, rosso oltre) e contorno colorato per le foto fuori; interruttore «Numeri sulle foto».
- **«Correggi le N foto»:** porta l'Esposizione di ogni foto rossa alla mediana (un solo annulla per foto con ⌘Z); «Correggi anche le da guardare» include le gialle. Clic su una colonna: seleziona la foto; clic destro: la esclude dal calcolo (scura o chiara di proposito), salvato nel progetto.
- Misura: luminanza mediana della foto come appare (ritocchi compresi), in luce lineare gamma 2.2 come il livello Esposizione di Photoshop. — `editor.py` (`tono_spread`, op `tono_escl`, `/api/tono`).
- Il cursore Esposizione per foto ora va da −2 a +2 EV (prima ±1).

## Versione 73 — Geometria, bordo, ombra e testi coincidono con Photoshop
Nuovo test `tests/fedelta_geometria.py` (15 cornici + 9 testi, PSD appiattito in Photoshop vs anteprima).
- **Ritaglio, zoom, angolo, bordo, ombra, bianco e nero:** già coincidenti (scarto medio ≤ 1.2/255, nessuno spostamento, bordi nello stesso punto). Nessuna modifica.
- **Opacità + ombra:** nel PSD l'ombra sta dietro un rettangolo bianco, quindi attraverso una foto semitrasparente non si vede; l'anteprima la mostrava (scarto 6.7, 12% di pixel). Ora coincide (0.6). — `album_libere.py` (`_render_ombre`).
- **Testi, posizione:** il testo nel PSD partiva 9–20 px (a 8268 px di pagina) più a sinistra dell'anteprima, perché Pillow non conta lo spazio a sinistra della lettera e Photoshop dà come ingombro il riquadro. Ora il margine si misura sull'inchiostro vero e il livello si allinea sull'inchiostro rasterizzato di una copia temporanea. — `testo.py` (`_ink_left`), `genera_psd_angolo.py`.
- **Testi, larghezza:** il PSD era più stretto dell'1.7% per la crenatura (kerning) automatica di Photoshop che l'anteprima non ha; ora il PSD usa crenatura manuale e lo scarto scende a 0.1–0.3% (≤ 7 px su 8268). Se vuoi la crenatura di Photoshop nei PSD, va tolta questa riga e il test mostrerà di nuovo la differenza.
- I PSD già esportati con testi vanno rifatti.

## Versione 72 — Curva e bianco e nero coincidono con Photoshop
Test completo `tests/fedelta_psd.py` (51 casi, PSD appiattito in Photoshop vs anteprima): scarto medio ≤ 1.4/255 su tutti i parametri, max pixel ≤ 9/255 solo agli estremi ±100.
- **Curva (panello Tono):** Photoshop usa una spline cubica naturale; l'anteprima usava un'interpolazione monotona diversa (scarto fino a 50/255). Ora è la stessa (scarto 0.7). La curva parte sempre da (0,0) e arriva a (255,255) come nel PSD. — `album_libere.py` (`tono_lut`).
- **Bianco e nero:** il livello B/N del PSD aveva i pesi predefiniti di Photoshop (scarto medio fino a 19/255); ora ha pesi di luminanza (R30 Y89 G59 C70 B11 M41), uguali all'anteprima (scarto 0.2). Resta un livello modificabile. — `motore/scripts/photoshop.py`.
- Nuovo `tests/fedelta_psd.py`: da rilanciare dopo ogni modifica a regolazioni/PSD.
- I PSD già esportati vanno rifatti per avere il B/N nuovo.

## Versione 71 — Anteprima e PSD ora coincidono (controllo matematico con Photoshop)
Misurato su 27 foto uguali, ognuna con un parametro diverso: PSD aperto in Photoshop, appiattito e confrontato con l'anteprima.
- **Curve di contrasto/alteluci/ombre/bianchi/neri:** il livello Curve del PSD ora ha 16 punti (più fitti vicino a neri e bianchi) e comprende gli estremi veri (prima i neri alzati venivano persi, errore fino a 21/255). — `album_libere.py` (`rit_curva`), `genera_psd_angolo.py`.
- **Saturazione:** ora è una matrice (Miscelatore canale in Photoshop), identica all'anteprima (errore 0.2/255; prima fino a 6/255 di scarto).
- **Vibranza:** l'anteprima usa una tabella misurata sul livello Vibranza di Photoshop (`vib_lut.npz`, da -100 a 100), non più una formula approssimata.
- **Esposizione:** l'anteprima segue il livello Esposizione di Photoshop (gamma 2.2, senza la spalla morbida sulle alte luci che nel PSD non c'era): +1 ora combacia (prima +1.5/255 di scarto e luci diverse). — `motore/scripts/album.py`.
- Esportando i PSD, i file del programma si prendono sempre dalla versione attuale. — `editor.py`.
- Risultato: differenza media anteprima↔PSD ≈ 2.4–4.2/255 su tutti i parametri, quanto il solo ricampionamento delle immagini (foto senza correzioni: 2.44); scarto medio di colore ≈ 0.

## Versione 70 — Blocca guide
- Nuovo pulsante «Blocca» accanto a Guide: le guide restano visibili e agganciano ancora, ma non si spostano né si tolgono, non se ne creano di nuove dai righelli e «Cancella» è spento. Si ricorda tra una sessione e l'altra. — `index.html`.

## Versione 69 — Scala, Angolo, Esposizione, Opacità come gli altri
- Stesso layout di Luce/Colore: nome e valore sopra (con ⊗ per ripristinare), cursore grande a tutta larghezza sotto. — `index.html`.

## Versione 68 — Sezione Cornice più chiara
- Bordo e Ombra con nome e valore sopra e cursore sotto; i colori del bordo hanno un'etichetta («Colore del bordo»), pallini più grandi con anello chiaro sul selezionato, e restano attenuati finché il bordo è «no». — `index.html`.

## Versione 67 — Cursori colorati come Temperatura/Tinta
- Tutti i cursori del pannello foto hanno la barra con sfumatura (Contrasto, Alteluci, Ombre, Bianchi, Neri in toni di grigio; Scala, Angolo, Esposizione, Opacità, Bordo, Ombra con la loro sfumatura) e un sottile contorno per vederli sul fondo scuro. — `index.html`.

## Versione 66 — Le foto arrivano fino al bordo della pagina anche con il margine bianco
- Nelle pagine con margine bianco la foto non poteva superare il margine: ora si può allargare/spostare fino al bordo vero della pagina (il margine resta come punto di aggancio). «Tutta pagina» ora riempie davvero la pagina, bordo compreso. — `editor.py` (`fullpage`, limiti verticali, `grid.full`), `index.html` (`startFree`).

## Versione 65 — Regolazioni più leggibili
- Nel pannello della foto, Luce e Colore (Contrasto … Saturazione): nome e valore stanno sopra, lo slider sotto a tutta larghezza, così «Temperatura» e «Saturazione» non si sovrappongono più. Colonna delle etichette degli altri cursori un po' più larga. — `index.html`.

## Versione 64 — Menu «Nuovo» di nuovo cliccabile
- Il menu di Nuovo (spread vuoto, prossime foto, scegli le foto) finiva sotto la barra strumenti e non si poteva cliccare: ora sta sopra. — `index.html`.

## Versione 63 — Inverti pagine
- Nuovo pulsante «Inverti pagine» nel riquadro Spread: scambia le due pagine (le foto a sinistra vanno a destra e viceversa, stesse posizioni dentro la pagina; anche le guide verticali si specchiano). Annulla rimette tutto. — `editor.py` (op `swappages`), `index.html`.

## Versione 62 — Comando Taglia
- Tasto destro → «Taglia» (e ⌘X): copia gli elementi scelti e li toglie dallo spread; si incolla con ⌘V anche in un altro spread. Annulla rimette tutto. — `index.html` (`cutSel`).

## Versione 61 — Riparata la pagina che non si apriva
- La versione 60 aveva un errore di sintassi (un commento a metà riga) e l'editor non si apriva. Corretto; il test automatico ora controlla anche la sintassi del codice della pagina, così non può ricapitare. — `index.html`, `tests/smoke.py`.

## Versione 60 — Allargamento di gruppo libero, Maiusc = in proporzione
- Le maniglie d'angolo del riquadro di gruppo ora ridimensionano liberamente (larghezza e altezza indipendenti); tenendo premuto Maiusc mentre trascini restano in proporzione, come in Photoshop. — `index.html` (`startGroup`).

## Versione 59 — Doppio clic su una foto della galleria
- Doppio clic su una foto libera in basso: viene messa al centro dello spread aperto (come trascinarla). — `index.html` (`renderPool`).

## Versione 58 — Opacità della foto
- Nuovo cursore «Opacità» (0–100%) sotto Esposizione nel pannello della foto: la foto diventa trasparente sullo spread (anteprima, JPG, PDF). Salvata nello spec (`STY(..., oc=)`), mantenuta nei modelli. Nel PSD il livello riceve la stessa opacità (da verificare in Photoshop). — `album_libere.py`, `editor.py`, `genera_psd_angolo.py`, `index.html`.

## Versione 57 — Allarga più foto insieme
- Con due o più foto selezionate compare un riquadro tratteggiato unico con le maniglie: trascinandole le foto si allargano/rimpiccioliscono tutte insieme (angoli = in proporzione, lati = solo in quella direzione), con distanze tra le foto che si scalano uguali. Un solo passo di annulla. — `editor.py` (op `gscale`), `index.html` (`groupBox`, `startGroup`).

## Versione 56 — Più modelli di impaginazione
- 11 nuove disposizioni (con versioni specchiate e a margine bianco): fascia panoramica, foto spostata di lato, due foto una sopra l'altra, una grande + una stretta, una larga + due, una grande + due piccole, tre colonne, quattro colonne, una larga + tre, cinque foto, griglia da sei. Nell'elenco Modelli si vedono fino a 90 proposte. — `editor.py` (`NPH`, `BUILD`, `LAYS`).

## Versione 55 — Galleria foto con righe allineate
- Le foto libere in basso riempiono ogni riga fino al bordo destro (prima restava uno spazio diverso a ogni riga); le foto si adattano di pochissimo. — `index.html` (`renderPool`).

## Versione 54 — Modelli: un solo pulsante apre e chiude
- Il pulsante Modelli in alto apre e richiude la schermata (resta acceso quando è aperta); tolto il tasto Chiudi separato. — `index.html`.

## Versione 53 — Con i Modelli aperti spariscono i pulsanti degli strumenti
- Aprendo la schermata Modelli la barra strumenti non si vede più attraverso. — `index.html` (`body.tplopen`).

## Versione 52 — La foto lascia davvero il suo posto mentre la trascini
- Trascinando una foto libera, nell'immagine dello spread il suo posto di partenza resta vuoto (prima rimaneva una copia della foto sotto). Per le foto ancora nelle celle dei modelli resta il segnaposto scuro tratteggiato. — `editor.py` (`spread_jpg(..., hide)`, `/img/spread/N?hide=L:3`), `index.html` (`startFree`).

## Versione 51 — Trascinamento: la foto con la sua inquadratura
- La foto che trascini mostra il ritaglio vero della cornice (non più una versione centrata), è più nitida e resta in bianco e nero se lo è. — `index.html`.

## Versione 50 — Trascinamento fluido delle foto
(da qui il numero è quello che vedi nell'elenco Versioni del programma; la 46 è il punto sicuro `v45-riferimento`)
- Mentre trascini, la foto vera segue il mouse (prima si vedeva solo un rettangolo semitrasparente) e il posto di partenza resta come segnaposto scuro tratteggiato. — `index.html`.
- Il movimento è agganciato alla scheda grafica (un solo aggiornamento per schermata invece di uno per ogni evento del mouse); guide e misure si ridisegnano solo quando cambiano.
- Al rilascio la foto resta dove l'hai lasciata finché l'immagine nuova non è pronta: non torna più per un attimo al posto vecchio.

## Versione 45 — PSD: maiuscolo vero di Photoshop
- Verificato aprendo il PSD in Photoshop: corpo, interlinea (corpo × valore scelto) e spaziatura corrispondono all'editor. — `testo.py`, `genera_psd_angolo.py`.
- «TT tutto maiuscolo» ora diventa l'attributo «Tutto maiuscolo» di Photoshop: il testo resta com'è scritto e puoi toglierlo dal pannello Carattere (prima nel PSD finivano lettere maiuscole vere).

## Versione 44 — Esportazione più solida (JPG, PDF, PSD)
- **Correzione importante:** dalla versione 40 l'esportazione PSD si fermava se nello spread c'era un testo (errore interno nel calcolo dell'interlinea). Trovato dalla nuova prova automatica e risolto. — `testo.py`.
- Controlli prima di esportare, con messaggio chiaro: spread inesistenti, foto non più trovate (dice quali), cartella non scrivibile, spazio sul disco insufficiente, Photoshop non installato (solo PSD). — `editor.py`.
- I JPG e il PDF si scrivono in un file temporaneo e poi si spostano: un'esportazione interrotta non lascia file a metà né sostituisce quelli buoni.
- Se un solo spread JPG fallisce gli altri vengono esportati lo stesso e il riepilogo dice quali sono saltati e perché.
- PSD: dopo Photoshop si controlla che ogni file esista davvero; errori di Photoshop spiegati («aperto? finestre in attesa?») e riepilogo «PSD creati: N su M».
- `tests/smoke.py` prova anche JPG, PDF, i casi di errore e, con `--psd`, un PSD vero (23 controlli).

## Versione 43 — Installazione e aggiornamento più robusti
- `setup.sh`: cerca un Python 3.9+ che funzioni davvero (il «python3» finto di macOS non conta), rifà da solo l'ambiente se è rovinato, usa versioni compatibili delle librerie ed esce con errore chiaro (senza internet, senza Python, librerie che non si caricano). Prima l'errore veniva nascosto. — `motore/scripts/setup.sh`.
- `Installa.command`: si ferma con un messaggio se qualcosa non va (prima diceva «Fatto» comunque), rifiuta cartelle su dischi esterni, mostra la versione installata.
- `Aggiorna.command`: salva i progetti aperti prima di riavviare, avvisa se la cartella non è collegata a GitHub, non dice «Aggiornato» se l'ambiente non è pronto.
- Aggiornamento dentro il programma: se l'ambiente non è pronto non riavvia e spiega perché. — `home.py`.
- `Impaginatore.app`: se il programma non è installato mostra un avviso invece di un errore incomprensibile. — `Impaginatore.app`.

## Versione 42 — Più solidità: salvataggio sicuro e prova automatica
- Il salvataggio scrive prima in un file temporaneo e poi lo sostituisce: un blocco del Mac a metà scrittura non rovina più `spec.py` e `progetto.json`. — `editor.py`.
- Le copie di sicurezza (`_backup_editor`) si limitano alle ultime 200, senza crescere all'infinito. — `editor.py`.
- Se l'autosalvataggio non riesce compare in alto «⚠ SALVATAGGIO NON RIUSCITO» (prima lo sapeva solo il registro). — `editor.py`, `index.html`.
- Nuova prova automatica `tests/smoke.py`: crea un progetto temporaneo, fa le operazioni principali, salva, riapre e confronta (14 controlli). Si lancia prima di ogni rilascio. — `tests/smoke.py`.

## Versione 41 — Testo: doppio clic per modificare
- Doppio clic su un testo lo riapre per scrivere, con il cursore in fondo (prima il doppio clic poteva perdersi perché il primo clic ricostruiva gli elementi). Il testo appena creato resta tutto selezionato, così scrivi sopra. — `index.html`.

## Versione 40 — Testo: barra del carattere stile Photoshop
- Selezionando un testo compare sopra di lui una barra con: elenco dei caratteri con anteprima e ricerca, stile (Regular/Bold/Italic…), corpo con corpi comuni, interlinea, spaziatura, allineamento, TT tutto maiuscolo, colore. — `index.html`.
- Nuovi: interlinea e maiuscolo, salvati nel progetto, nell'anteprima e nei PSD. — `testo.py`, `editor.py`, `album_libere.py`, `genera_psd_angolo.py`.
- Tolta l'etichetta «Testo» che copriva le prime lettere del testo.

## Versione 39 — Nomi dei comandi nella fascia, più grande e più in alto
- I comandi della fascia hanno di nuovo il nome sotto l'icona, pulsanti più grandi (66×58). — `index.html`.
- La fascia sta più in alto e c'è più spazio tra la fascia e lo spread.

## Versione 38 — Tolto il pannello Allinea
- Il pannello Allinea è stato tolto dalla fascia strumenti (per ora). Il codice dei comandi di allineamento resta nel programma. — `index.html`.

## Versione 37 — Fascia strumenti sempre completa e più grande
- Allinea e i comandi della selezione (livelli, proporzioni, tutta pagina…) sono sempre presenti nella fascia: spenti finché non selezioni qualcosa, non compaiono più al clic sulla foto. — `index.html`.
- Pulsanti più grandi; su finestre strette si rimpiccioliscono e vanno a capo.

## Versione 36 — Fascia strumenti fissa, una riga, più grande
- Tolta la fascia a scomparsa e il tasto «Strumenti»: la fascia è sempre fissa sopra lo spread, centrata, su una sola riga (a capo solo se la finestra è stretta), con pulsanti più grandi e meno spazio sprecato in alto. — `index.html`.

## Versione 35 — Fascia strumenti: tasto al centro, di default visibile
- La fascia parte visibile; il tasto «▾ Strumenti» (al centro in alto, sempre visibile) la nasconde, e passandoci sopra si riapre. — `index.html`.

## Versione 34 — Fascia strumenti a scomparsa
- La fascia strumenti ora galleggia sopra lo spread e compare passando il mouse in alto (o sul tasto «Strumenti»); non sposta più lo spread, che diventa più grande. — `index.html`.
- Il tasto «Strumenti» la fissa sempre visibile (azzurro = fissa).

## Versione 33 — Fascia solo icone e tema chiaro dello sfondo
- I pulsanti della fascia strumenti mostrano solo l'icona (il nome è nel tooltip): più compatta. — `index.html`.
- Con lo sfondo bianco: fascia, righelli e ombra dello spread si adattano per restare leggibili.

## Versione 32 — Sfondo dello spread e grafica più pulita
- Quattro pallini in alto (nero, grigio scuro, grigio chiaro, bianco) cambiano lo sfondo dietro lo spread; si ricorda la scelta. — `index.html`.
- Fascia strumenti più piccola (frecce avanti/indietro compatte) e più staccata dallo spread.
- Miniature degli spread e gallerie foto più calme: una sola tinta (blu) per le selezioni, niente giallo, bordi tolti, etichette discrete.

## Versione 31 — Zoom con il pizzico del trackpad
- Il pizzico a due dita sul trackpad (Mac) ingrandisce lo spread come Alt + rotella (Chrome lo manda come Ctrl + rotella, Safari come eventi di gesto). — `index.html`.

## Versione 30 — Zoom dello spread con Alt + rotella
- Alt + rotella (o trackpad) ingrandisce lo spread fino al 500%, centrato sul puntatore; si scorre con rotella/trackpad normali; il pulsante «NNN% · Adatta» in basso a destra torna alla vista intera. A zoom alto l'anteprima viene richiesta più nitida (fino a k=1). Righelli, cornici e guide seguono lo zoom. — `index.html` (`applyZoom`, `ZM`).

## Versione 29 — Menu del tasto destro a due livelli
- Il menu mostra in alto i colori e le 5 voci più usate (se non hai ancora usato nulla: «Suggeriti», le prime 5); le altre stanno nel sottomenu «Tutti i comandi ▸». I clic si contano per tipo di menu (foto dello spread, galleria/striscia, sfondo, miniatura) in `localStorage` «ctxUso»; le voci che cambiano nome (es. Bianco e nero / Togli…) hanno un `id` fisso. — `index.html` (`ctxMenu`).

## Versione 28 — Tolta la riga di istruzioni sotto lo spread
- Via la frase «Foto: trascina per spostare…» sotto lo spread; resta solo il messaggio che compare quando si usa il ritaglio. — `index.html`.

## Versione 27 — Sostituisci, preferite, bordo e ombra, proporzioni, menu sfondo e miniature
- Tasto destro su foto dello spread: «Sostituisci con un'altra foto…» (elenco delle libere, o anche già usate = scambio), «Proporzioni» 1:1, 3:2, 2:3, 4:5, 5:4, 16:9 (stessa area e centro), bordo bianco e ombra al volo. Pannello foto: nuova sezione «Cornice» con bordo (0–20 mm, bianco/crema/grigio/nero) e ombra (0–100). Nello spec.py: `STY(FREE(...), bd=(mm, '#hex'), sh=N)` (prima di ROT). Anteprima/JPG/PDF: bordo disegnato dentro la cornice, ombra sfumata sotto (`_photo_bordo`, `_render_ombre` in `album_libere.py`). PSD: livello «Ombra …» sotto la cornice e «Bordo …» sopra (rettangoli con effetto Contorno interno/Ombra esterna, a zero riempimento per il bordo), provato in Photoshop; gli effetti sulla cornice stessa non funzionano (vengono ritagliati), per questo livelli separati.
- Preferite ★: tasto P (o menu), stella sulla miniatura, filtro ★ nella barra (galleria e striscia). Dati `stelle` in progetto.json, annullabile.
- «Applica questo ritocco a tutte le foto dello stesso colore» nel menu delle foto.
- Tasto destro sullo sfondo dello spread: aggiungi foto qui, aggiungi testo qui, incolla, righelli, guide, duplica, esporta questo spread. Tasto destro sulla miniatura di uno spread (a sinistra): vai, nuovo vuoto dopo, duplica, sposta prima/dopo, esporta JPG, elimina. «Esporta come JPG…» apre la finestra Esporta già impostata su quel solo spread.
— `index.html`, `editor.py`, `album_libere.py`, `genera_psd_angolo.py`.

## Versione 26 — Menu del tasto destro completo
- Tasto destro su una foto o un testo dello spread: colori, avanti/indietro/cima/fondo, centra, tutta pagina, proporzioni, stessa misura, bianco e nero, sposta nella cornice, copia/incolla/azzera ritocco, Finder, copia nome, copia/incolla, «togli dallo spread», «mostra nella galleria». Tasto destro nella galleria/striscia: colori, «usa in un nuovo spread», vai allo spread, togli/ripristina, «seleziona tutte del colore», ritocco, Finder. Menu unico `ctxMenu` (voci con scorciatoie). `/api/reveal` accetta anche `{foto}`. Le foto ora hanno `rit` nello stato. — `index.html`, `editor.py`.

## Versione 25 — Galleria ridimensionabile, colori col tasto destro, titoli subito, + e − per i livelli
- Striscia «foto libere» dell'album: ora le foto vanno a capo su più file e si alza/abbassa trascinando la maniglia sul bordo alto (doppio clic = altezza automatica, ricordata in `localStorage` «poolH»). Prima era una sola fila orizzontale.
- Colori: tasto destro su una foto (galleria o striscia) apre il menu dei colori; nel pannello della foto c'è «Etichetta colore»; restano i tasti 1–7/0 e i pallini «Colora:».
- Titoli dei pulsanti (Allinea, Avanti/Indietro…) compaiono dopo 0,1 s invece di aspettare quelli del sistema.
- Tasti + (o =) e − portano la selezione avanti/indietro di un livello, come ] e [.
— `index.html`.

## Versione 24 — Ritocco stile Lightroom al posto di livelli e curva
- Pannello foto: via Neri/Mezzitoni/Bianchi e la curva. Ora «Luce»: Contrasto, Alteluci, Ombre, Bianchi, Neri; «Colore»: Temperatura, Tinta, Vibranza, Saturazione (−100…+100, doppio clic su un cursore lo azzera, «⊗ azzera» toglie tutto). L'Esposizione resta nel blocco Design. Vale per anteprima, JPG/PDF e PSD: nel PSD diventano livelli di regolazione (Bilanciamento bianco per temperatura/tinta, «Ritocco: tono» = Curve con max 11 punti perché Photoshop ne ammette 16, «Vibranza e saturazione»), provato con un PSD vero. Dati in `progetto.json` → `ritocco` (annullabile). I vecchi `tono` già salvati continuano ad essere applicati (nessuna foto di Stefano li usa tranne `_DSC7517` in Serena) e si tolgono con «azzera». Matematica in `album_libere.py` (`rit_lut`, `rit_gains`, `_apply_rit`), PSD in `genera_psd_angolo.py`, UI `wireRit`. — `album_libere.py`, `editor.py`, `genera_psd_angolo.py`, `index.html`.

## Versione 23 — Fascia strumenti chiudibile, adattamento automatico
- Pulsante «▾ Strumenti» sopra lo spread: chiude/apre tutta la fascia (scelta ricordata in `localStorage` «tbar»). Alla prima apertura, se la finestra è piccola (meno di 900 px di altezza o 1250 di larghezza) la fascia parte chiusa e l'elenco spread a sinistra è nascosto, senza memorizzarlo. — `index.html` (`setTools`).

## Versione 22 — Allinea compatto e strumenti che si adattano alla larghezza
- «Allinea alla pagina» è una sola riga bassa, senza titolo. La fascia strumenti reagisce alla larghezza dello spazio dello spread (container query `stg` su `#stage`, non della finestra): sotto 1250 px pulsanti più piccoli, sotto 980 ancora di più. Con finestre piccole la fascia resta alta: si guadagna spazio chiudendo i pannelli laterali. — `index.html`.

## Versione 21 — Pannelli a destra incolonnati
- «Allinea alla pagina» e «Foto selezionata» ora sono uno sopra l'altro, stessa larghezza e stesso bordo, con i pulsanti che riempiono la riga (prima erano sfalsati e di larghezze diverse). — `index.html` (`#sbarR`).

## Versione 20 — Rotella del mouse sulla striscia foto libere
- Nella striscia «foto libere» dell'album la rotella (e il trackpad in verticale) ora scorre in orizzontale; prima non faceva nulla. — `index.html`.

## Versione 19 — Filtri, colori e ordinamento anche in Album; colori stile Lightroom
- La striscia «foto libere» dell'album ha la stessa barra della galleria Foto: filtri, Verticali/Orizzontali, colori, ordinamento, ricerca e zoom (la striscia si alza/abbassa con lo zoom). Etichette colore (rosso, arancio, giallo, verde, azzurro, viola, rosa): si assegnano con i pallini «Colora:» alle foto selezionate, o coi tasti 1–7 (0 toglie) sulla selezione, o sulla foto sotto il mouse (anche nella striscia dell'album). Pallino sulla miniatura e filtro per colore (anche «senza colore»). Ordinamento: import, nome A→Z/Z→A, data di scatto ↑/↓, colore. Server: `CFG["colori"]` (progetto.json, annullabile), op `colore`, campo `col` nelle foto. — `editor.py`, `index.html` (`mkBar`, `filterList`, `renderPool`).

## Versione 18 — Galleria foto: scorrimento, filtri, ricerca, zoom miniature
- Barra di scorrimento della galleria larga e ben visibile (sempre presente). Nuova riga sotto i pulsanti: filtri Tutte / Da usare / Già usate / Tolte / Mancanti (con conteggi), Tutte / Verticali / Orizzontali, ricerca per nome, e zoom miniature con − / cursore / + (80–360 px). Scelte ricordate (`localStorage` «galleriaFoto»). «Seleziona tutte» (e ⌘A) e Maiusc-clic agiscono solo sulle foto visibili e ancora da usare. Rimossa la casella «nascondi le già usate» (ora è il filtro «Da usare»). La posizione di scorrimento resta quando si seleziona. — `index.html` (`renderLib`, `visPhotos`, `GF`).

## Versione 17 — Selettore di foto tutto nostro
- «Importa foto…» e «Importa cartella…» non aprono più la finestra di macOS (osascript, dove ⌘A e ⌘-clic non andavano) ma un selettore dentro il programma: miniature, sidebar (Scrivania, Documenti, Immagini, Download, Home, dischi), ⌘A, ⌘-clic, Maiusc-clic, Invio/Esc. Server: `ls_dir` e `file_thumb` in `editor.py` (`/api/ls`, `/api/fthumb`, solo lettura, solo JPEG e cartelle); interfaccia: blocco «selettore di foto» e `doImport` in `index.html`. `pick()` e `/api/pick` restano nel codice ma non sono più usati dai pulsanti. — `editor.py`, `index.html`.

## Versione 16 — Selezione foto nella galleria
- ⌘A nella galleria Foto seleziona tutte le foto ancora da usare. Clic semplice = solo quella foto; ⌘-clic (o Ctrl) aggiunge/toglie; Maiusc-clic = intervallo. Prima il clic semplice aggiungeva sempre e ⌘A non faceva nulla. Non riguarda la finestra di scelta file di macOS (`pick()` in `editor.py`, che ha già la selezione multipla). — `index.html`.

## Versione 15 — Strumenti nella fascia sopra la pagina, divisi a sinistra e a destra
- Come da disegno di Stefano: nella fascia sopra lo spread (`#tools`), a SINISTRA Spread + Strumenti + Vista (`#sbarL`), a DESTRA Allinea alla pagina + Foto selezionata (`#sbarR`, allineata a destra). Pulsanti grandi (66×58 px). Colonne laterali di nuovo strette (230 / 310 px), elenco spread a tutta altezza. — `index.html`. Sostituisce il posizionamento della v14.

## Versione 14 — Strumenti divisi: sinistra e destra
- A SINISTRA (sopra l'elenco degli spread, `#sbarL`): Spread, Strumenti, Vista. A DESTRA (sopra l'ispettore, `#sbarR`): Allinea alla pagina e Foto selezionata (compaiono solo con una selezione), pulsanti grandi come nella v12. `#list` è ora un contenitore con `#sbarL` + `#thumbs` (l'elenco: `renderList` scrive in `#thumbs`); `#side` contiene `#sbarR` + `#insp`. I selettori dei pulsanti sono `.sb [data-al]`. Colonne: sinistra 288 px, destra 330 px. — `index.html`.

## Versione 13 — Strumenti di nuovo SOPRA la pagina
- Il pannello della v12 (a destra) non andava bene: `#sbar` è tornato sopra la pagina, dentro `#stage`; a destra resta solo l'ispettore (`#insp` dentro `#side`). Restano i pulsanti grandi a icona, ma più compatti (56×50 px, etichette corte: Prima/Dopo, Uguali, Originale, Pagina, Vertic., Orizz.; distribuisci solo icona) per stare su 2-3 righe. — `index.html`.

## Versione 12 — Pannello strumenti a destra, pulsanti grandi
- Spread / Allinea / selezione (livelli e misure) / Strumenti / Vista non stanno più sopra la pagina ma in cima al pannello di DESTRA (`#sbar` dentro `#side`; l'ispettore della foto è sotto, in `#insp`). Pulsanti grandi a icona + etichetta (`ICP`/`IC` in `index.html`), numero dello spread grande con frecce. Pannello largo 330 px (`--rc`). Gli id dei pulsanti e i `data-al`/`data-mode` sono rimasti uguali: i gestori non sono cambiati. — `index.html`.

## Versione 11 — Livelli delle foto
- Davanti/dietro non funzionava sulle foto che sono ancora «cornici del modello»: restavano sempre SOTTO le cornici libere. Ora, prima di spostare i livelli, le foto scelte e quelle che le toccano diventano cornici libere (stessa posizione) e partono dal fondo. — `editor.py` (`_zprep`, op `zorder`).

## Versione 10 — Correzioni pannello Modelli
- Con il pannello Modelli aperto, cambiando spread i modelli si ricaricano per lo spread nuovo (prima restavano quelli del precedente). `tplFor` + controllo in fondo a `render()`; le richieste in ritardo vengono scartate. — `index.html`.
- Sparita la striscia verticale sopra i modelli: le guide dello spread stavano SOPRA il pannello (z-index). `#tpl` ora z-index 20, `#toast` 60; il pannello nasconde le barre di scorrimento dello stage. — `index.html`.

## Versione 9 — Nuova interfaccia in stile Apple (solo scuro)
- Tema scuro neutro (`--bg #1b1b1d`, blu di sistema `--blue` per i comandi; il GIALLO resta solo per la selezione delle cornici sulla pagina). Font di sistema, pulsanti arrotondati senza bordo, controlli segmentati, finestre sfocate, scrollbar sottili.
- Barra in alto con icone SVG (annulla/ripeti, modelli, progetto, versioni, pannelli, esporta); sotto 1180 px di larghezza restano solo le icone. «Salva» diventa blu quando c'è qualcosa da salvare. Tolte le emoji dai pulsanti dello spread.
- Tutto il tema è in fondo al blocco `<style>` di `index.html` e `home.html` (sezione «Tema scuro in stile Apple»): per tornare indietro basta il ripristino di versione. Nessuna funzione cambiata.

## Versione 8 — Torna indietro e registro modifiche
- Riquadro Versione: elenco delle ultime 20 versioni con «Torna a questa». Il ripristino crea una NUOVA versione (la storia resta intatta, gli altri Mac la ricevono come aggiornamento). — `Editor Album/home.py` (`elenco_versioni`, `ripristina_versione`), `home.html`.
- Questo file `CAMBIAMENTI.md`.

## Versione 7 — Pulsante versione
- Pillola «Versione N · aggiornata / disponibile la N+1 / non riesco a controllare» con pallino verde/giallo/rosso. — `home.html`, `index.html`.

## Versione 6 — Riquadro versione
- Versione in uso, ultima su GitHub, novità, «Controlla aggiornamenti». — `home.py` (`info_versione`), `home.html`.

## Versione 5 — Avviso di aggiornamento
- Il programma fa `git fetch` all'avvio e ogni 3 ore; mostra l'avviso e «Aggiorna ora» (pull --ff-only, setup.sh, riavvio). Nell'editor compare «⬆ Aggiornamento». — `home.py`, `home.html`, `index.html`.

## Versione 4 — Galleria: foto mancanti
- Foto mancante: bordo rosso + etichetta «⚠ MANCANTE», la miniatura resta (galleria e striscia foto libere). Attenzione: `S.photos[].n` è senza estensione, `S.mancanti` con estensione. — `index.html`.

## Versione 3 — Importa foto senza copie
- `do_import` non crea più link/copie in `<progetto>/Foto`: aggiunge i percorsi degli originali a `foto_extra`. — `editor.py`.

## Versione 2 — Nuovo progetto accanto alle foto
- Campo facoltativo «Cartella delle foto»: il progetto nasce in `<cartella cliente>/Impaginatore`, le foto restano dove sono. — `home.py` (`nuovo`, `/api/scegli-foto`), `home.html`.

## Versione 1 — Prima versione su GitHub
- Programma completo (home + editor), motore incluso in `motore/`, `Installa.command`, `Aggiorna.command`, skill `impaginatore-stefano`.
- Funzioni già presenti: modelli utente, duplica/copia/incolla spread, allinea, versioni e backup del progetto, ricollegamento foto, esporta/importa progetto (ZIP), rilevamento foto modificate da Lightroom, PDF/JPG con profilo sRGB, magnete al centro.
