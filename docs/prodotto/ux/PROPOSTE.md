# Proposte UX per la 2.0 (T-209)

Proposte numerate `UX-001…`, ordinate per rapporto fra beneficio e costo. Ogni proposta rimanda ai punti d'attrito di [`ANALISI.md`](ANALISI.md) (`A-xx`) e dice cosa il motore sa già fare, verificato nel codice.

**Come leggere le schede**

- **Beneficio** da 1 a 5: tempo risparmiato nel flusso tipico, errori evitati, fiducia. **Sforzo** S (fino a 2 giorni), M (fino a 2 settimane), L (oltre). Il rapporto è beneficio diviso per 1 (S), 2 (M) o 3 (L).
- **Motore**: «pronto» = le funzioni ci sono, manca solo l'interfaccia; «quasi» = ci sono i pezzi, manca un'operazione che li unisca; «no» = da scrivere.
- **Fascia**: secondo `docs/mercato/tier.json` (chiavi fra parentesi). Dove la scelta spetta al titolare è scritto.
- **Nomi**: tutti nostri, presi dal lessico del manuale (`brand/STYLEBOOK.md` §5: bozza, consegnare, laboratorio, piega, abbondanza). Niente «Auto…», «Smart…», «Rearrange», «Designer View», «Drop Zones», «Un'altra», «Variante». Niente «magico», «in un clic», emoji.
- Nessuna proposta manda foto in rete. Tutto quello che segue lavora sui file del computer dell'utente.

## Riepilogo

| ID | Proposta | Attriti | Benef. | Sforzo | Motore | Fascia | Gruppo |
|---|---|---|---|---|---|---|---|
| UX-001 | «Altra disposizione» con un tasto | A-08 | 4 | S | pronto | tutte | 2.0 |
| UX-002 | Sostituisci e riadatta | A-09, A-10, A-11 | 4 | S | quasi | tutte | 2.0 |
| UX-003 | Annulla che dice cosa annulla, niente conferme inutili | A-15, A-17 | 4 | S | quasi | tutte | 2.0 |
| UX-004 | Ricollega sicuro | A-23 | 3 | S | quasi | tutte | 2.0 |
| UX-005 | Recupero di un album danneggiato | A-24 | 3 | S | quasi | tutte | 2.0 |
| UX-006 | Menu contestuale per compiti, sempre uguale | A-09 | 3 | S | pronto | tutte | 2.0 |
| UX-007 | Messaggi riscritti | A-24, A-26 e altri | 3 | S | pronto | tutte | 2.0 |
| UX-008 | Stati vuoti che portano avanti | A-04, A-05, A-28 | 3 | S | pronto | tutte | 2.0 |
| UX-009 | La pagina si aggiorna quando lavora l'assistente | A-32 | 3 | S | quasi | tutte | 2.0 con T-203 |
| UX-010 | Tono in parole del fotografo e «Uniforma» | A-13 | 4 | S–M | pronto | spread: tutte; album: Pro, Studio | 2.0 |
| UX-011 | Stampa dagli originali, con abbondanza | A-18, A-19 | 5 | M | quasi | tutte | 2.0 |
| UX-012 | Editor subito, foto preparate in sottofondo | A-03, A-16 | 5 | M | quasi | tutte | 2.0 |
| UX-013 | «Consegna» al posto di «Esporta…» | A-18…A-22 | 5 | M | quasi | tutte; PSD Pro, Studio | 2.0 |
| UX-014 | «Controlla» sempre visibile e «Sistema» | A-10, A-12, A-20 | 5 | M–L | quasi | Controlla: tutte; Sistema album: Pro, Studio | 2.0 |
| UX-015 | Trascina la cartella | A-01, A-02 | 4 | M | quasi | tutte | 2.0 con T-201 |
| UX-016 | Tela grande e barra della selezione | A-07, A-33 | 4 | M | pronto | tutte | 2.0 |
| UX-017 | Primo avvio: prova senza moduli, chiave incollata | — | 4 | M | no | — | 2.0 con T-202 |
| UX-018 | «Prepara la bozza» dell'album | A-06, flusso 2 | 5 | L | quasi | Pro, Studio, prova | 2.0 |
| UX-019 | Tastiera e accessibilità | A-27, A-33, A-34 | 3 | M | pronto | tutte | 2.0 (minimo), 2.1 |
| UX-020 | Salvataggio visibile e versioni con nome | A-25, A-26 | 3 | M | quasi | tutte | 2.1 |
| UX-021 | «Altre disposizioni» come provini numerati | A-08, LEG-004 | 3 | M | pronto | tutte | 2.0 |
| UX-022 | Schermata «Album» a scaffale | LEG-004 | 3 | M | pronto | tutte | 2.0 |
| UX-023 | Testo: caratteri della marca e un solo pannello | A-14, LEG-003 | 2 | M | pronto | tutte | 2.0 |
| UX-024 | Copertina | A-29 | 4 | L | no | tutte | 2.1 |
| UX-025 | Revisione col cliente: versioni a confronto | flusso 4 | 3 | L | quasi | tutte | più avanti |
| UX-026 | Tema chiaro | — | 2 | S dopo i token | pronto | tutte | 2.1 |

---

## Le azioni «un pulsante»: cosa c'è già nel motore

| Azione | Il motore oggi | Verifica |
|---|---|---|
| **Prepara la bozza** (UX-018) | **Quasi.** `tpl_options()` propone e assegna le disposizioni per 1–10 foto in 0,00–0,07 s; `newspread` crea lo spread; `newspreadsel` sceglie già da solo la migliore per un gruppo. Lo script `marketing/sito/strumenti/schermate.py` (`bozza()`, `scegli()`) costruisce un album intero con queste funzioni. **Manca**: dividere le foto in gruppi (capitoli dagli orari EXIF, densità), il ritmo (pagine piene e bianche, niente tre moduli uguali di fila), un'operazione unica con un solo annulla, l'anteprima senza scrivere l'album | prova: 35 spread in meno di 3 s via API; il primo modello lascia una pagina vuota in 9 spread su 35 |
| **Controlla e Sistema** (UX-014) | **Quasi.** Spazi: `gapPairs`/`gapFix`/`gapAll` esistono ma in JavaScript nella pagina. Piega, ritagli oltre ×1,25, spazi diversi, fuori pagina, doppie, non usate: in `motore/anteprima.py`, solo riga di comando. Tono: `tono_spread()` calcola per ogni foto la correzione (`compl`), `tono_fix` la applica con un solo annulla. PPI: `photo_info()`. Volti: `_cache/faces.json` (riquadri normalizzati) e `crop()`. **Manca**: un'operazione `controlla` che restituisca un elenco strutturato, un'operazione `sistema` con un solo annulla, i controlli volto-ritaglio e volto-piega | prova: `tono_spread` × 35 = 17,9 s; il riconoscimento volti trova «volti» anche nei dettagli di fiori (DEMO_0001): i controlli sui volti vanno proposti, mai applicati da soli |
| **Consegna al laboratorio** (UX-013) | **Quasi.** `run_export()` fa JPG, PDF e PSD; `preflight()` controlla spazio, permessi, foto mancanti, Photoshop. **Manca**: stampa dagli originali e abbondanza (UX-011), il catalogo del laboratorio (T-208), un avanzamento numerico al posto del registro | prova: 22 s per 35 JPG, 3,9 s per il PDF |
| **Altra disposizione** (UX-001) | **Pronto.** `GET /api/templates?s=` restituisce le disposizioni per le foto dello spread, l'operazione `template` le applica | — |
| **Sostituisci e riadatta** (UX-002) | **Quasi.** `replace` (che scambia se la foto è già usata) più `tpl_options` più `template`: manca solo farle in una volta con un solo annulla | prova: verticale in cornice orizzontale tagliata ×2,28 |
| **Uniforma il tono** (UX-010) | **Pronto.** `tono_fix` accetta più foto in un'operazione; il pulsante non viene disegnato (`index.html`, commento «la correzione si fa a mano») | — |
| **Trascina la cartella** (UX-015) | **Quasi.** `home.nuovo()` crea l'album accanto alla cartella del cliente, `RADICI.scelta()` autorizza la cartella. **Manca**: ricevere il percorso dal trascinamento (finestra desktop, T-201) | — |
| **Nessun dialogo per i predefiniti** | **Quasi.** Formato, spazio e margine hanno già valori predefiniti in `nuovo()`; manca ricordare l'ultimo formato e i formati del laboratorio | — |

---

## Schede

### UX-001 — «Altra disposizione» con un tasto

- **Problema osservato.** Cambiare la disposizione di uno spread costa 3–5 azioni per prova: «Modelli», scorrere, clic. La finestra copre lo spread e si chiude a ogni scelta; a 1280 × 800 si vede un modello e mezzo (A-08, [12](schermate/12-modelli.jpg)). È la correzione più frequente nel lavoro descritto in `stile.md` («solo correzioni puntuali»).
- **Proposta.** Il tasto **D** (e il pulsante «Altra disposizione» nella barra dello spread e in quella della selezione) mette sullo spread la disposizione successiva per le stesse foto, sul posto.
- **Comportamento.** Ogni pressione cambia lo spread in meno di 0,1 s. Sotto lo spread compare una pillola: «Disposizione 3 di 12 · D avanti · Maiusc+D indietro · Esc torna a com'era». L'ordine è quello del motore (dal costo minore); dopo le 12 «buone» vengono quelle che tagliano di più, con il segno «taglia ×1,4» nella pillola. Se è selezionata una sola pagina, cambia solo quella: il parametro `side` di `tpl_options` lo fa già, oggi solo quando l'altra pagina è di testo. Le pressioni consecutive diventano un solo passo d'annulla («Annulla Altra disposizione»). Se l'utente aveva spostato a mano le cornici, la prima pressione lo avvisa nella pillola: «Le modifiche a mano di questo spread si perdono. D di nuovo per continuare».
- **Motore.** Riuso: `templates(s)` (`GET /api/templates?s=`), op `template`. Da aggiungere: unire in un solo passo d'annulla le operazioni consecutive dello stesso tipo sullo stesso spread (un campo `gruppo` in `do_op`).
- **Fascia.** Tutte. **Rischio.** Basso; perdita di ritocchi a mano, coperta da Esc e annulla. **Sforzo.** S.
- **Metrica.** Azioni per cambio di disposizione: da 3–5 a 1. Quota delle disposizioni cambiate con D rispetto al pannello (misura solo con consenso, T-204).

### UX-002 — Sostituisci e riadatta

- **Problema osservato.** «Sostituisci» è nel sottomenu «Tutti i comandi» (4 clic). Una verticale messa in una cornice orizzontale resta tagliata ×2,28, si vede il 44 % dell'altezza, senza avviso (A-10). Se tutte le foto sono usate la finestra di scelta è vuota e non dice perché (A-11).
- **Proposta.** Sostituire una foto riadatta lo spread quando la nuova foto non entra bene nella cornice.
- **Comportamento.** Si sostituisce trascinando una foto della striscia su una cornice, oppure con «Sostituisci» nella barra della selezione. Se il ritaglio supera ×1,25 (la stessa soglia di `anteprima.py`), lo spread prende la disposizione migliore per le foto nuove, tenendo l'ordine di lettura e, se possibile, la stessa disposizione sull'altra pagina. Per 6 secondi compare la pillola «Disposizione adattata alla nuova foto · Tieni la cornice di prima». Un solo passo d'annulla per tutto. Se la foto scelta è già in un altro spread, si scambiano come oggi e la pillola lo dice: «Scambiata con lo spread 12–13». La finestra di scelta mostra prima le foto da usare, poi «Già nell'album» con il numero dello spread: non è mai vuota.
- **Motore.** Riuso: op `replace` (`server.py:315`, scambia se la foto è usata altrove), `tpl_options`, op `template`. Da aggiungere: un'operazione `sostituisci` che faccia le due cose con un solo annulla.
- **Fascia.** Tutte. **Rischio.** L'utente voleva proprio quel taglio: «Tieni la cornice di prima» lo risolve con un clic. **Sforzo.** S.
- **Metrica.** Sostituzioni che finiscono con un ritaglio oltre ×1,25 non scelto: 0.

### UX-003 — Annulla che dice cosa annulla, niente conferme inutili

- **Problema osservato.** Il secondo ⌘Z della prova ha tolto lo spread 35 mentre si guardava lo spread 4, senza un messaggio (A-15). «Elimina» chiede conferma e intanto dice «puoi annullare» (A-17).
- **Proposta.** Ogni operazione ha un nome; annullare mostra cosa e dove.
- **Comportamento.** Il menu Modifica e il suggerimento del pulsante dicono «Annulla Elimina spread 07–08». Dopo l'annulla la tela va allo spread toccato e contorna per 400 ms le cornici cambiate (con movimento ridotto: solo il contorno). Un avviso breve: «Annullato: Nuovo spread 35–36 · Ripeti». Nessuna conferma per le azioni che si possono annullare: eliminare uno spread dà «Spread 07–08 eliminato · Annulla». Restano le conferme solo per ciò che non si annulla (eliminare un modello personale dalla libreria, chiudere il programma durante una consegna), in un foglio dentro la finestra, non con `confirm()`.
- **Motore.** Riuso: `UNDO`/`REDO` con istantanee in `do_op` (`server.py:792`). Da aggiungere: nome e indice dello spread per ogni istantanea (il tipo dell'operazione e lo spread `s` sono già nell'operazione). La cronologia che si perde all'import si risolve con UX-012.
- **Fascia.** Tutte. **Rischio.** Basso. **Sforzo.** S.
- **Metrica.** Coppie annulla→ripeti entro 5 s (segno di disorientamento): in calo.

### UX-004 — Ricollega sicuro

- **Problema osservato.** «Ricollega foto…» cerca per nome in tutte le sottocartelle e ha collegato la foto mancante alla sua miniatura nella cache del progetto: «tutte trovate», ma il file è da 1200 px (A-23).
- **Proposta.** Ricollegare solo a file veri, e mostrare cosa si sta per fare.
- **Comportamento.** La ricerca salta le cartelle del progetto (`_cache`, `_backup_editor`, `Esportazioni`, `PSD`, `PSD_vecchi`). Un file trovato va bene solo se misure in pixel e data di scatto coincidono con quelle registrate (`meta.json` ha `w`, `h`, `dt`). Prima di applicare, un foglio: «Trovata 1 su 2: DEMO_0020 in Lavoro. Non trovata: DEMO_0007. Forse è «DEMO_0007 rinominata.jpg»: stessa data di scatto e stesse misure · Usa questa». Il controllo della consegna blocca le foto collegate a un file più piccolo dell'originale registrato.
- **Motore.** Riuso: `ricollega()` (`server.py:1590`), `meta.json`. Da aggiungere: esclusioni, confronto, risposta in due tempi (proposta e conferma).
- **Fascia.** Tutte. **Rischio.** Basso. **Sforzo.** S. È anche un difetto da correggere subito.
- **Metrica.** Nessun collegamento dentro le cartelle del progetto (test automatico).

### UX-005 — Recupero di un album danneggiato

- **Problema osservato.** Con `album.json` rovinato la scheda mostra «album.json non è un JSON valido (riga 9, colonna 28…)» e il clic ripete il testo in un `alert()`. Le copie buone sono in `_backup_editor/`, ma nessuno lo dice (A-24).
- **Proposta.** La schermata «Album» offre il ripristino.
- **Comportamento.** La riga dell'album dice «Non si apre: il file dell'impaginazione è danneggiato» e ha il pulsante «Ripristina la copia di oggi alle 10:02 (35 spread)». Il clic mette da parte il file rotto come `album.json.danneggiato-AAAAMMGG-hhmm`, copia la versione buona più recente e apre l'album. Se non ci sono copie: «Nessuna copia di sicurezza. Mostra la cartella» e un rimando all'assistenza.
- **Motore.** Riuso: i file `_backup_editor/AAAAMMGG-hhmmss_album.json`, `formato.leggi_progetto()` e `formato.controlla()` per validarli. Da aggiungere: l'elenco delle copie dal lato della schermata dei progetti (oggi `versioni()` vive solo nell'editor).
- **Fascia.** Tutte (`versioni_backup`). **Rischio.** Basso. **Sforzo.** S.
- **Metrica.** Ogni album danneggiato con almeno una copia si recupera senza aprire una cartella (test).

### UX-006 — Menu contestuale per compiti, sempre uguale

- **Problema osservato.** Il primo gruppo del menu destro su una foto, «Suggeriti», è fatto di comandi di livello (Porta avanti, Porta indietro, In cima, In fondo, Centra); Sostituisci, Bianco e nero, Sposta nella cornice stanno in «Tutti i comandi ▸». Con l'uso le voci cambiano posto (`ctxMenu`, `index.html:1744`) (A-09, [11](schermate/11-menu-contestuale.jpg)).
- **Proposta.** Un ordine fisso, dal compito più frequente.
- **Comportamento.** Su una foto: Sostituisci…, Altra disposizione (D), Sposta nella cornice (doppio clic), Bianco e nero, Primo piano; poi Preferita (P), Togli dallo spread (⌫); poi i sottomenu «Disponi ▸» (livelli, centra, stessa misura, proporzioni, tutta pagina) e «Ritocco ▸» (copia, incolla, azzera, applica alle foto con la stessa etichetta); in fondo Mostra nella cartella, Copia il nome. Etichette colore in una riga in cima, come oggi. Niente classifica per uso.
- **Motore.** Nessun cambio. **Fascia.** Tutte. **Rischio.** Nessuno. **Sforzo.** S.
- **Metrica.** Clic per sostituire una foto: da 4 a 2.

### UX-007 — Messaggi riscritti

- **Problema osservato.** Messaggi tecnici o sbagliati: riga e colonna del JSON, `spec.py`, `editor.log`, «guarda il riquadro» (A-24, A-26, A-21, A-22).
- **Proposta.** Ogni messaggio dice cosa è successo, cosa resta salvo e cosa fare, con i numeri. Tabella completa in «Riscontro e fiducia», più sotto.
- **Comportamento.** Gli errori restano visibili finché non si leggono (non 4,5 s); quelli che bloccano una consegna stanno nel pannello del controllo, non in un avviso che sparisce. I testi passano dal sistema di traduzione (T-206).
- **Motore.** `_spiega()` in `server.py` traduce già alcuni errori: va esteso. **Fascia.** Tutte. **Sforzo.** S.
- **Metrica.** Richieste d'assistenza per messaggi non capiti.

### UX-008 — Stati vuoti che portano avanti

- **Problema osservato.** Album senza foto: filtri, ordinamento, zoom ed «Esporta…» (unico pulsante primario) attivi con 0 foto (A-28, [28](schermate/28-progetto-vuoto.jpg)). Con le foto e senza spread, metà finestra vuota con istruzioni (A-04). Dopo il primo spread si resta in Foto e lo spread non si vede (A-05).
- **Proposta.** Ogni stato vuoto ha una sola azione principale.
- **Comportamento.** Vedi la tabella in «Primo avvio e stati vuoti». In breve: senza foto, tutta la finestra è l'area per la cartella; con le foto e senza spread, «Prepara la bozza» o «Comincia a mano»; dopo aver creato uno spread dalle foto, la tela lo mostra subito e la striscia delle foto resta sotto.
- **Motore.** Nessun cambio. **Fascia.** Tutte. **Sforzo.** S.
- **Metrica.** Utenti nuovi che arrivano al primo spread senza aiuto (prova con 5 fotografi).

### UX-009 — La pagina si aggiorna quando lavora l'assistente

- **Problema osservato.** Dopo 34 spread creati via API la pagina ne mostrava ancora uno, fino al ricaricamento (A-32). Con il server MCP (T-203, decisione D3) l'utente guarderà l'editor mentre Claude impagina.
- **Proposta.** La pagina segue i cambiamenti fatti da fuori.
- **Comportamento.** Quando l'album cambia da un'altra finestra o dall'assistente, la pagina si aggiorna da sola entro un secondo e mostra una pillola discreta con l'icona «bozza» del manuale: «L'assistente ha aggiunto 12 spread · Mostra». Le operazioni dell'assistente entrano nella stessa cronologia d'annulla, con il nome «Assistente: Nuovo spread 14–15». Se l'utente sta trascinando, l'aggiornamento aspetta che lasci.
- **Motore.** Riuso: `REV` e `LASTC` (chi ha fatto l'ultima operazione) in `do_op`; `/api/ping`. Da aggiungere: `rev` nella risposta di `/api/ping` (o un flusso di eventi locale).
- **Fascia.** Tutte (il server MCP è Pro e Studio, ma l'aggiornamento serve anche con due finestre). **Sforzo.** S. **Dipende da** T-203.
- **Metrica.** Nessun ricaricamento manuale nelle prove con l'MCP.

### UX-010 — Tono in parole del fotografo e «Uniforma»

- **Problema osservato.** Il pannello Tono parla di Scarto, Luci, Ombre, Bruc., L*; suggerisce «Esposizione −0,5» ma non ha un pulsante per applicarlo; misurare tutto l'album richiede 17,9 s senza avanzamento; il pannello taglia lo spread (A-13, [14](schermate/14-tono.jpg)). `stile.md` dice che uniformare la luminosità è parte di ogni album.
- **Proposta.** Il tono entra nel controllo (UX-014) e nell'ispettore della foto, con parole e un pulsante.
- **Comportamento.** Ogni foto fuori tono ha una frase: «più chiara del resto dello spread», «più scura», «bianchi bruciati sul 5 %». Due pulsanti: «Uniforma lo spread» e «Uniforma l'album». Il secondo mostra l'avanzamento («Spread 12 di 35») e un riepilogo: «Corrette 23 foto in 14 spread. Lasciate com'erano le 2 che hai escluso». Un pulsante «Prima / Dopo» tenuto premuto mostra lo spread senza correzioni. Un solo passo d'annulla. I numeri (L*, scarto) restano sotto «Dettagli» per chi li vuole. L'esposizione per la stampa di tutto l'album (+0,25 EV in `stile.md`) diventa un'impostazione dell'album nella consegna al laboratorio, non un campo da ricordare a ogni esportazione.
- **Motore.** Pronto: `tono_spread()` restituisce per ogni foto la correzione completa (`compl`: EV e ritocco), op `tono_fix` la applica a più foto con un solo annulla (`server.py:337`). Da aggiungere: una funzione che raccolga le correzioni di tutto l'album con l'avanzamento.
- **Fascia.** «Uniforma lo spread»: tutte. «Uniforma l'album»: Pro e Studio (`uniformita_tono`). Il titolare decide se anche lo spread singolo va in Pro: oggi il suggerimento per spread è già nell'editor per tutti.
- **Rischio.** Foto volutamente scure o chiare: si escludono con un clic e restano escluse. **Sforzo.** S–M.
- **Metrica.** Album consegnati con almeno una correzione di tono; tempo passato nel pannello.

### UX-011 — Stampa dagli originali, con abbondanza

- **Problema osservato.** «Stampa · 300 dpi, a grandezza reale» produce file a 300 dpi ricavati dalle miniature da 1200 px: con originali da 3000 px le foto sono ingrandite ×2,2, con originali da 6000 px la perdita è ancora maggiore, perché la miniatura resta da 1200. Nella prova la varianza dei bordi è 346 contro 1406 dell'originale ([29](schermate/29-stampa-da-miniatura.jpg)). JPG e PDF tagliano via l'abbondanza (A-18, A-19). È il difetto più grave per un prodotto da vendere: il laboratorio stampa file sfocati.
- **Proposta.** I file per la stampa vengono dagli originali alla misura vera; l'abbondanza resta dove serve.
- **Comportamento.** Nella consegna «Al laboratorio» ogni foto si legge dal file originale, si decodifica alla misura più piccola sufficiente (per i JPEG con la riduzione in decodifica di Pillow), si ritaglia e si ricampiona una volta sola. L'abbondanza resta nel file se è impostata, con segni di taglio a scelta del laboratorio. L'etichetta dice il vero: «Stampa · 300 ppi dagli originali». Il PDF per il cliente resta leggero e può continuare a usare le miniature (per uno spread largo 2000 px bastano). Se un originale manca o è più piccolo del necessario (meno di 200 ppi effettivi) il controllo lo dice prima di cominciare.
- **Motore.** Riuso: `album.render()`, `_photo()` (`album.py:339`) e `album_libere._photo_rot()`, che oggi aprono `THUMBS`; le correzioni di tono e ritocco sono le stesse funzioni. Da aggiungere: una sorgente «originale» per la resa a grandezza reale, il mantenimento dell'abbondanza, un test che confronti resa ridotta e resa piena.
- **Fascia.** Tutte (`export_jpg`). **Rischio.** Tempo di consegna più lungo (stima: 30–60 s per 35 spread, da misurare), da mostrare con l'avanzamento; differenze di colore fra miniatura e originale, da coprire con un test. **Sforzo.** M.
- **Metrica.** Nitidezza del file consegnato rispetto all'originale alla stessa scala: almeno 90 % (oggi 25 %).

### UX-012 — Editor subito, foto preparate in sottofondo

- **Problema osservato.** 90 s di rotellina per 100 foto prima di vedere l'editor, 0,65 s per foto in un solo thread, 73 % per i volti (A-03). Importare 3 foto riavvia l'editor (4,3 s) e cancella la cronologia d'annulla (A-16).
- **Proposta.** L'editor si apre subito; miniature e volti si preparano mentre si lavora; l'import non riavvia.
- **Comportamento.** Dopo «Crea» (o il trascinamento della cartella) l'editor è in uso in meno di 2 s. Le foto compaiono nella griglia con un segnaposto grigio e il nome, poi con la miniatura appena è pronta, in ordine di scatto. Nella barra in alto: «Preparo le foto · 34 di 100 · circa 40 s», con una barra sottile; si può scegliere, ordinare e preparare la bozza intanto (servono solo proporzioni e date, che si leggono in millisecondi). Il riconoscimento dei volti gira dopo, su tutti i core meno uno; quando arriva, centra i ritagli delle sole foto che l'utente non ha già sistemato. Importare foto le aggiunge allo stesso modo, senza riavvio: la cronologia d'annulla resta.
- **Motore.** Riuso: `_raccogli_foto`, `carica_progetto`, `_build_thumbs`, `_build_faces` (`album.py:217`, `:224`). Da aggiungere: un lavoratore in sottofondo con avanzamento in `/api/state`, l'aggiunta di foto a caldo al posto di `restart()`, la lettura veloce di proporzioni e date dall'intestazione dei file.
- **Fascia.** Tutte. **Rischio.** Concorrenza sui dati del motore (c'è già `LOCK`); ritagli che cambiano quando arrivano i volti, limitato alle foto non toccate. **Sforzo.** M (L se il motore va ristrutturato più del previsto).
- **Metrica.** Da «Crea» all'editor in uso: meno di 3 s per 400 foto. Miniature pronte: misurare per sistema operativo. Contribuisce al KPI «primo spread in meno di 5 minuti».

### UX-013 — «Consegna» al posto di «Esporta…»

- **Problema osservato.** La finestra d'esportazione parla di formati di file, non di destinazioni; il registro è grezzo; i PSD sono offerti dove non si possono fare; nessun formato di laboratorio (A-18…A-22, [15](schermate/15-esporta.jpg), [16](schermate/16-esporta-registro.jpg), [17](schermate/17-esporta-psd-linux.jpg)).
- **Proposta.** Una finestra «Consegna» con tre destinazioni.
- **Comportamento.**
  - Tre scelte grandi: **Al laboratorio** (stampa dagli originali, abbondanza e profilo dal pacchetto del laboratorio, nomi dei file come li vuole), **Al cliente** (PDF leggero con copertina, numeri degli spread e, durante la prova, la filigrana), **A Photoshop** (PSD a livelli; su Linux la scelta è spenta con la frase «Non disponibile su Linux: Photoshop non c'è»).
  - A sinistra lo stato del controllo (UX-014): «Pronto · nessun problema» oppure «2 da controllare», ognuno con «Vai».
  - Predefiniti: l'ultima destinazione usata per quell'album; il laboratorio scelto alla creazione; la cartella `Esportazioni/<destinazione>` dentro l'album.
  - Un solo pulsante primario con il numero: «Consegna 35 spread». Nessuna conferma.
  - Durante: «Spread 12 di 35 · circa 20 s» con «Ferma»; si può continuare a lavorare.
  - Dopo: «35 spread pronti in Esportazioni/Laboratorio (54 MB) · Mostra nella cartella». Si salva da sola una versione con nome «Consegnata al laboratorio, 16/11» (UX-020).
- **Motore.** Riuso: `run_export()`, `preflight()`, `parse_range()`, `write_pdf()`, `srgb_icc()`, `LOG`. Da aggiungere: avanzamento strutturato (numero e totale) al posto delle righe di testo, i pacchetti dei laboratori (T-208), la stampa dagli originali (UX-011), la pagina di copertina nel PDF (oggi solo in `esporta_pdf.py`, via Photoshop).
- **Fascia.** Tutte (`preset_laboratori` è in tutte le fasce); A Photoshop solo Pro e Studio (`export_psd_livelli`). **Rischio.** Medio: è la fine del flusso, va provata con i laboratori pilota. **Sforzo.** M.
- **Metrica.** Riesportazioni dovute a errori; file rifiutati dai laboratori pilota: 0.

### UX-014 — «Controlla» sempre visibile e «Sistema»

- **Problema osservato.** «Controlla album» controlla solo le spaziature, con tre nomi diversi per la stessa cosa (A-12). Nessun controllo su volti, piega, PPI, testi prima della consegna (A-20). L'avviso di ritaglio è spento di serie (A-10).
- **Proposta.** Un indicatore nella barra in alto e un pannello di controllo con le correzioni sicure in un gesto.
- **Comportamento.**
  - **Indicatore** accanto al nome dell'album: grigio «Controllo…» mentre lavora, verde «Pronto», ambra «3 da controllare», rosso «1 blocca la stampa». Il controllo gira da solo un secondo dopo ogni modifica, solo sugli spread cambiati; tutto l'album all'apertura.
  - **Pannello** (a destra, al clic sull'indicatore), raggruppato per spread con la miniatura e una frase:
    - *Blocca la stampa*: foto mancante; foto sotto i 150 ppi effettivi; testo o foto fuori dalla pagina.
    - *Da controllare*: foto fra 150 e 200 ppi; volto vicino alla piega (a meno di 1 cm) o tagliato dal ritaglio; ritaglio oltre ×1,25; spazi diversi dallo standard; pagina vuota; foto fuori tono; foto ripetuta.
    - *Per sapere*: foto non usate, foto ★ non usate.
    - Ogni riga ha «Vai» (apre lo spread e seleziona la cornice) e, dove la correzione è sicura, «Sistema».
  - **Sistema** in cima al pannello: un foglio dice cosa farà, con i numeri: «Sistemo 9 cose: spazi in 4 spread, tono di 5 foto. Restano 3 da guardare tu». Al clic applica tutto, con un solo passo d'annulla, e chiude con «Sistemato · Annulla» ([schema](schemi/editor-sistema.svg)). Non cambia mai disposizioni né foto scelte; i volti non li corregge da solo (il riconoscimento sbaglia, come dice `stile.md`), li propone.
- **Motore.** Riuso: logica degli spazi oggi in JavaScript (`gapPairs`, `gapFix`, `gapAll`); controlli di `anteprima.py` (fuori pagina, piega `FOLD`, ritaglio oltre 1,25, spazi diversi da `G`, doppie, non usate); `photo_info()` per i PPI; `_cache/faces.json` e `crop()`; `tono_spread()` e `tono_fix`; `preflight()`. Da aggiungere: operazioni `controlla` (elenco strutturato) e `sistema` (un annulla); controlli volto-ritaglio e volto-piega; spostare nel motore il calcolo degli spazi, così lo usa anche l'MCP.
- **Fascia.** Controlla: tutte (prevenire un errore di stampa non è un extra). Sistema su tutto l'album: Pro e Studio (`correzione_spaziature_album`, `uniformita_tono`); in Essenziale «Sistema questo spread».
- **Rischio.** Falsi allarmi sui volti (DEMO_0001, una foto di fiori, ha due «volti»): vanno in «Da controllare» con un «Non è un volto» che li zittisce per sempre. **Sforzo.** M–L.
- **Metrica.** Album consegnati con l'indicatore rosso: 0. Problemi trovati dal laboratorio dopo la consegna: in calo.

### UX-015 — Trascina la cartella

- **Problema osservato.** Per creare un album servono quattro passaggi e una finestra di sistema; il nome proposto è vuoto se la cartella si chiama «JPG» (A-01); il formato del laboratorio non c'è e l'abbondanza è nascosta (A-02).
- **Proposta.** Trascinare la cartella delle foto sulla finestra crea l'album e lo apre.
- **Comportamento.** Una cartella lasciata in qualunque punto della schermata «Album» (o di un album vuoto) crea l'album accanto alle foto, come oggi. Il nome viene dalla cartella; se il nome è generico (JPG, Export, Selezione, Foto, Alta) si usa quello della cartella sopra: «Matrimonio Giulia e Marco». Il formato è l'ultimo usato o quello del laboratorio predefinito, e resta visibile in una pillola «60 × 22,5 cm · abbondanza 3 mm · Cambia». Solo al primissimo album compare un foglio con i formati del laboratorio scelto (tre più «Altro…»). Lasciare dei file (non una cartella) aggiunge quelle foto all'album aperto. Lasciare una cartella sulla riga di un album esistente aggiunge le foto a quell'album.
- **Motore.** Riuso: `home.nuovo()` con la cartella, `RADICI.scelta()` (la cartella trascinata vale come scelta dall'utente), `do_import()`. Da aggiungere: ricevere il percorso dal trascinamento nella finestra desktop (T-201: pywebview fornisce il percorso completo dei file trascinati; da verificare in T-201, non provato qui), l'elenco dei nomi generici.
- **Fascia.** Tutte. **Rischio.** Nel browser il percorso non si può leggere: la funzione esiste solo nella finestra desktop. **Sforzo.** M.
- **Metrica.** Gesti per creare un album: da 4 clic più la finestra di sistema a 1 trascinamento.

### UX-016 — Tela grande e barra della selezione

- **Problema osservato.** Lo spread occupa il 15 % della finestra a 1280 × 800 e l'8 % a 1024 × 700; due file di 16 pulsanti da 66 × 58 px, metà disattivati; al 200 % la tela sparisce (A-07, A-33, [07](schermate/07-album-1280x800.jpg), [09](schermate/09-album-1024x700.jpg), [23](schermate/23-zoom-200.jpg)).
- **Proposta.** Via le due file di pulsanti; una barra sottile dello spread e una barra che compare sotto la selezione.
- **Comportamento.** Sopra la tela, una riga alta 36 px: numero dello spread in mono «07–08», tipo di pagina per lato (Piena / Bianca), «Altra disposizione», «Testo», zoom. Con una foto selezionata, sotto la foto compare una barra: Sostituisci, Altra disposizione, Ritaglia, B/N, «⋯» (Disponi, Ritocco). L'ispettore a destra si apre solo quando serve e mette in cima quello che conta: misura in cm e ppi effettivi, Scala, Esposizione; Luce e Colore chiusi. Sotto i 1280 px di larghezza il pannello di destra diventa un foglio sovrapposto e la colonna degli spread mostra solo i numeri; al 200 % i pannelli si impilano. Dettagli in [`ARCHITETTURA-INTERFACCIA.md`](ARCHITETTURA-INTERFACCIA.md).
- **Motore.** Nessun cambio. **Fascia.** Tutte. **Rischio.** Gli utenti abituati alle icone grandi: tutte le funzioni restano nei menu e con le stesse scorciatoie. **Sforzo.** M.
- **Metrica.** Quota della finestra occupata dallo spread 60 × 22,5, misurata con lo stesso script di questa analisi: a 1280 × 800 almeno 24 % con tutti i pannelli aperti (oggi 15,3 %) e almeno 50 % con la tela piena (F); a 1024 × 700 almeno 30 % con il pannello di destra chiuso (oggi 7,9 %). Lo schema [`editor.svg`](schemi/editor.svg) arriva a 24,9 %. Lo spread è largo 2,67 volte l'altezza: lo spazio che conta è quello orizzontale, quindi i pannelli laterali sono stretti e le foto vanno in basso.

### UX-017 — Primo avvio: prova senza moduli, chiave incollata

- **Problema osservato.** Non c'è ancora (T-202). Il KPI «dal pagamento al primo spread in meno di 5 minuti» e quello «1 installer, 1 chiave» dipendono da come è fatto.
- **Proposta.** Il primo avvio è una schermata sola con la prova già attiva.
- **Comportamento.** Al primo avvio: il logo, la frase «Prova completa per 30 giorni, senza carta» e l'area «Trascina qui la cartella di un album». In basso, piccolo: «Ho una chiave». Nessun modulo, nessuna email. La chiave si incolla in qualunque punto della schermata (⌘V con una chiave nel formato giusto) o da Impaginatore › Licenza: «Chiave Pro valida. Attivata su questo computer». I giorni rimasti si vedono solo negli ultimi 7, nella schermata «Album», mai in una finestra a ogni apertura. La filigrana della prova è detta nella consegna, prima del clic. Dopo la scadenza gli album si aprono e si guardano (sola lettura, come da `tier.json`); la consegna è spenta con «Compra una chiave».
- **Motore.** Nessuno: dipende da T-202. **Fascia.** —. **Rischio.** Medio (licenze). **Sforzo.** M.
- **Metrica.** KPI D6 cronometrato su macchina pulita; errori d'attivazione.

### UX-018 — «Prepara la bozza» dell'album

- **Problema osservato.** Comporre a mano 35 spread costa almeno 105 clic più lo scorrimento; il primo modello proposto lascia una pagina vuota in 26 % dei casi (A-06). Oggi l'impaginazione di tutto l'album la fa solo Claude, via API. `tier.json` vende `impaginazione_automatica_album` in Pro e Studio: la funzione deve esistere.
- **Proposta.** Un comando che prepara la bozza di tutto l'album, la mostra e la applica solo se l'utente la vuole.
- **Comportamento.**
  - Si trova nello stato vuoto dell'album, in cima alla vista Foto e nel menu Album. Serve un album con almeno 10 foto da usare.
  - Il clic apre il foglio «Bozza dell'album» con tre scelte e l'anteprima che si aggiorna:
    - *Densità*: cursore «più spread ↔ meno spread» con il numero «circa 30 spread · 3,3 foto per spread»; il predefinito tiene conto del massimo di spread del laboratorio, se c'è.
    - *Ritmo*: «Pagine piene e bianche alternate» (predefinito, da `stile.md`), «Solo pagine piene», «Solo pagine bianche».
    - *Preferite*: «Le ★ da sole su una pagina» (acceso).
  - L'anteprima è un foglio di provini con tutti gli spread numerati «01–02, 03–04…», 3 per riga, e i capitoli segnati dove fra due scatti passano più di 30 minuti («11:20 · cerimonia» se l'orario c'è). Si prepara in pochi secondi con l'avanzamento «Spread 12 di 30».
  - «Usa questa bozza» (primario) aggiunge gli spread dopo quelli già fatti; «Rifalla» propone un'altra combinazione; «Chiudi» non cambia niente. Le foto «Tolte» non entrano; gli spread esistenti non si toccano.
  - Dopo: la tela mostra il primo spread nuovo e l'indicatore del controllo lavora. Un solo passo d'annulla: «Annulla Bozza dell'album (30 spread)». Si salva da sola una versione «Prima bozza» (UX-020).
- **Motore.** Quasi: `tpl_options()` (0,00–0,07 s per gruppo), op `newspread`, `newspreadsel`; `A.render()` può già disegnare uno spread non ancora salvato (riceve una tupla), quindi l'anteprima non tocca l'album; `schermate.py` dimostra che l'album intero si costruisce in meno di 3 s. Da aggiungere: raggruppamento per orario e densità, scelta delle disposizioni che riempiono le due pagine salvo pausa voluta, alternanza piena/bianca, nessun modulo uguale tre volte di fila, panoramiche da sole (come `schermate.py`, rapporto ≥ 1,8), penalità ai ritagli oltre ×1,25; operazione `bozza` con un solo annulla; la stessa funzione esposta all'MCP (T-203), così Claude e il pulsante danno risultati coerenti.
- **Fascia.** Pro, Studio e prova (`impaginazione_automatica_album`). In Essenziale la voce è nel menu con il lucchetto e una riga di spiegazione; nessuna finestra che insiste.
- **Rischio.** Una bozza che sembra «il compitino» (`stile.md`, v2) delude: va presentata come bozza, sempre con anteprima, e si rifà con un clic. **Sforzo.** L.
- **Metrica.** Bozze accettate; modifiche per spread dopo la bozza; dall'import alla bozza completa in meno di 2 minuti per 100 foto.

### UX-019 — Tastiera e accessibilità

- **Problema osservato.** Tab non sposta il fuoco (A-34); scorciatoie con i simboli Mac anche su Linux (A-27); bersagli da 18 px; testi da 9–11 px; nessun `prefers-reduced-motion`; al 200 % l'editor non si usa (A-33).
- **Proposta.** Il minimo per la 2.0: Tab libero, nomi accessibili, bersagli e testi della marca, movimento ridotto, scorciatoie per sistema. Il resto in 2.1.
- **Comportamento.** Tab e Maiusc+Tab spostano il fuoco; nascondere i pannelli passa a F (tela piena). Dentro la tela Tab passa da una cornice all'altra, Invio seleziona, le frecce spostano. Contorno del fuoco 2 px in Verde Bottega. Ogni icona ha un nome accessibile. Bersagli di almeno 24 × 24 px; testo dell'interfaccia 13 px, etichette mai sotto 12 px (stylebook §10). Con movimento ridotto le durate vanno a 0 (stylebook §15). Le scorciatoie mostrano Ctrl su Windows e Linux (lo stato dell'editor ha già il campo `sistema`).
- **Motore.** Nessun cambio. **Fascia.** Tutte. **Sforzo.** M (il minimo è S dentro UX-016).
- **Metrica.** Flusso 1 completato solo da tastiera; nessun errore grave con uno strumento automatico di verifica dell'accessibilità.

### UX-020 — Salvataggio visibile e versioni con nome

- **Problema osservato.** «Salva» annuncia file che non esistono più (A-26); le versioni hanno solo data e numero di spread, una ogni 10 minuti al massimo, e il ripristino riavvia (A-25).
- **Proposta.** Niente pulsante «Salva»; versioni con un nome quando contano.
- **Comportamento.** In alto: «Salvato alle 10:42». ⌘S resta e risponde «Salvato». Le versioni si salvano da sole con nome nei momenti che contano: «Prima bozza», «Inviata al cliente» (dopo la consegna al cliente), «Consegnata al laboratorio». «Salva questa versione…» con un campo per il nome nella finestra. L'elenco mostra la miniatura del primo spread e «12 spread diversi da ora». «Torna a questa» non riavvia (UX-012) e si annulla.
- **Motore.** Riuso: `save()`, `versioni()`, `ripristina()`, `spread_hash()` (serve a contare gli spread cambiati). Da aggiungere: nome nella copia, ripristino a caldo.
- **Fascia.** Tutte (`versioni_backup`). **Sforzo.** M.
- **Metrica.** Ripristini riusciti al primo tentativo.

### UX-021 — «Altre disposizioni» come provini numerati

- **Problema osservato.** La galleria dei modelli copre la tela, mostra un modello e mezzo per schermata, ha come azione più evidente «💾 Salva questo spread come modello…» ed è uno dei tratti riconoscibili indicati da LEG-004 ([12](schermate/12-modelli.jpg)).
- **Proposta.** Le disposizioni stanno nel pannello di destra, come provini piccoli numerati, accanto allo spread.
- **Comportamento.** Con nessuna cornice selezionata, il pannello di destra mostra «Altre disposizioni · 12 per queste 4 foto», due colonne di provini con il numero e, se tagliano, il fattore «×1,4»; quella attuale è contornata. Un clic la applica e il pannello resta aperto: si confronta guardando la tela. D scorre le stesse disposizioni (UX-001). «Salva come modello» è nel menu «⋯» del pannello e chiede il nome in un campo, non con `prompt()`.
- **Motore.** Pronto. **Fascia.** Tutte (limite dei `modelli_personali` per Essenziale: 5). **Sforzo.** M. Fa parte di T-205.
- **Metrica.** Prove di disposizione per spread (più prove, meno tempo).

### UX-022 — Schermata «Album» a scaffale

- **Problema osservato.** La schermata dei progetti a schede grandi ricalca un concorrente (LEG-004) e non dice in che stato è ogni album ([01](schermate/01-home-vuota.jpg)).
- **Proposta.** La schermata si chiama «Album» ed è un elenco, come uno scaffale.
- **Comportamento.** Una riga per album: miniatura del primo spread, nome, «60 × 22,5 cm · 35 spread · 100 foto», stato («In lavorazione», «Inviato al cliente il 12/11», «Consegnato il 16/11», presi dalle versioni con nome), ultima modifica. Al passaggio del mouse: Apri, Mostra nella cartella, «⋯». In cima la riga per creare: «Trascina qui la cartella di un album nuovo · Nuovo album…». Ricerca quando gli album sono più di 12. Gli album danneggiati hanno il ripristino (UX-005).
- **Motore.** Riuso: `progetti()` della schermata. **Fascia.** Tutte. **Sforzo.** M. Fa parte di T-205.
- **Metrica.** Tempo per riaprire l'album giusto.

### UX-023 — Testo: caratteri della marca e un solo pannello

- **Problema osservato.** Carattere predefinito Avenir Next (Apple, non incorporabile e assente su Linux); la barra dice «AvenirNext-Regular» e il pannello «aakar»; elenco di tutti i caratteri del sistema; testo nuovo di 22,3 pt, quasi invisibile a vista intera (A-14, LEG-003, [24](schermate/24-testo.jpg)).
- **Proposta.** Caratteri predefiniti della marca, un elenco corto, un solo posto per i comandi.
- **Comportamento.** Predefiniti Newsreader per i titoli e Instrument Sans per i testi (SIL OFL, incorporabili). In cima all'elenco una scelta breve di caratteri OFL; sotto, «Altri caratteri del sistema…» con la nota sulla licenza. Il corpo iniziale è proporzionato alla pagina. Uno stile pronto «Titolo dell'album» (nome in corsivo, sottotitolo e data in maiuscoletto spaziato, inchiostro caldo, come in `stile.md`). I comandi di testo stanno solo nella barra che compare sul testo selezionato.
- **Motore.** Riuso: `TX.fonts()`, stili di testo (`stile_salva`, `stile_applica`). **Fascia.** Tutte. **Sforzo.** M.
- **Metrica.** Album consegnati con caratteri non incorporabili: 0.

### UX-024 — Copertina

- **Problema osservato.** La copertina non esiste nell'editor (A-29); oggi c'è solo una pagina di copertina nel PDF fatto da `esporta_pdf.py`, via Photoshop. Per i laboratori è un prodotto a sé (REQUISITI-VOCALI, punto 3).
- **Proposta.** La copertina è il primo elemento della colonna degli spread.
- **Comportamento.** «Copertina» sta sopra «01–02», con i formati del pacchetto del laboratorio (T-208). «Usa come copertina» nel menu della foto. Se la foto è già in uno spread, la riga chiede: «È anche nello spread 07–08: lasciala · toglila e riadatta lo spread» (la regola di `stile.md`). Si consegna come file a parte.
- **Motore.** No. **Fascia.** Tutte. **Sforzo.** L. **Dipende da** T-208.
- **Metrica.** Album consegnati con la copertina fatta in Impaginatore.

### UX-025 — Revisione col cliente: versioni a confronto

- **Problema osservato.** Le correzioni dei clienti arrivano come schermate con segni colorati (skill, §4); oggi non si vede cosa è cambiato fra la versione inviata e quella attuale.
- **Proposta.** Confrontare con la versione inviata e mandare solo gli spread cambiati, senza rete.
- **Comportamento.** Nelle versioni, «Confronta con Inviata al cliente» affianca gli spread cambiati. Nella consegna al cliente, «Solo gli spread cambiati» produce un PDF «Modifiche spread 7, 12» (come fa oggi `anteprima.py --spread`). Nessun caricamento online.
- **Motore.** Quasi: `spread_hash()`, `anteprima.py`. **Fascia.** Tutte. **Sforzo.** L.
- **Metrica.** Giri di revisione per album.

### UX-026 — Tema chiaro

- **Problema osservato.** Solo il tema scuro (stylebook §17: «scuro predefinito, chiaro disponibile»).
- **Proposta.** Vista › Tema: Sistema, Scuro, Chiaro; i grigi attorno alla foto restano neutri (C = 0) in tutti e due.
- **Motore.** Nessuno. **Fascia.** Tutte. **Sforzo.** S una volta adottati i token di `brand/tokens.css`.

---

## Cosa togliere, nascondere o unire

| Oggi | Proposta | Perché |
|---|---|---|
| Pulsante «Salva» | Togliere; resta ⌘S | il salvataggio è automatico dopo 2 s; il pulsante annuncia file sbagliati (A-26) |
| «Spaziature», «Correggi spazi», «Controlla album» | Unire in «Controlla» (UX-014) | tre pulsanti e tre nomi per un controllo |
| Scheda «Tono» nella striscia | Unire nel controllo e nell'ispettore (UX-010) | il tono è un controllo, non una galleria |
| Barra «Selezione» (In cima, Avanti, Indietro, In fondo, Stessa misura, Proporzioni, Tutta pagina, Verticali, Orizzontali) | Menu «Disponi» nella barra della selezione | 9 pulsanti sempre visibili, usati di rado |
| Pulsanti Copia, Incolla | Togliere; restano ⌘C, ⌘V e il menu | doppioni |
| Inverti pagine | Menu «⋯» della barra dello spread | raro |
| Riquadro «Vista» (Magnete, Righelli, Guide, Blocca guide, Avviso ritaglio, Cancella) | Menu Vista e tasti; l'avviso di ritaglio diventa un controllo sempre acceso | sei pulsanti grandi per impostazioni che si toccano una volta |
| Quattro pallini per lo sfondo della tela | Vista › Sfondo | senza etichetta, raro |
| Tre icone per i pannelli, Tab | Vista e tasto F | Tab serve alla tastiera (A-34) |
| «Modelli» nella barra in alto e finestra sovrapposta | «Altre disposizioni» nel pannello di destra e tasto D (UX-001, UX-021) | copre la tela, si chiude a ogni prova |
| Tre righe di filtri nella vista Foto | Una riga: «Da usare · Tutte · ★ · Colore ▾»; ordinamento in «⋯»; «Da usare» predefinito | meno spazio, il filtro utile è già scelto |
| «Seleziona tutte», «Deseleziona» | ⌘A, Esc e il menu | doppioni |
| «+ Importa cartella…», «+ Importa foto…» | «Aggiungi foto…» e trascinamento | una sola azione |
| Sfoglia file interno (`#fbd`) | Finestre di sistema della finestra desktop (T-201) | doppione meno familiare (A-31) |
| Bordo, Ombra, Opacità, Angolo in vista nell'ispettore | Sezione «Altro» chiusa | `stile.md`: niente cornici né ombre |
| «I tuoi comandi più usati» nel menu destro | Ordine fisso (UX-006) | le voci cambiano posto |
| `confirm()`, `prompt()`, `alert()` (21 punti) | Niente per le azioni annullabili; fogli nella finestra per le altre | bloccano la pagina, non sono nello stile |
| «Aggiungi spec.py per la versione 1.x» in Esporta progetto | Sotto «Avanzate» | serve a pochissimi |
| Pillola «Versione…» e «Chiudi programma» nella schermata dei progetti | Menu Impaginatore (T-201, T-207) | spazio a ciò che si usa |
| Oro `#e0b23c`, rosa `#ff3d7f`, blu di sistema, vetro smerigliato | Token della marca (stylebook §17) | due colori d'azione oggi; somiglianza col concorrente giallo |

---

## Primo avvio e stati vuoti

**Obiettivo.** Dal doppio clic al primo spread sullo schermo in **meno di 60 secondi** per un album da 100 foto, con 1 trascinamento e 2 clic. Questo lascia circa 4 minuti per scaricare, installare e attivare dentro il KPI D6 («dal pagamento al primo spread in meno di 5 minuti»). Oggi, su questa macchina: circa 2 minuti e mezzo dalla schermata dei progetti, di cui 90 s di attesa cieca, più finestra di sistema e nome digitato; installazione e attivazione non misurabili (non esistono ancora).

| Tempo | Cosa vede l'utente | Gesto |
|---|---|---|
| 0 s | Doppio clic. Schermata «Album» vuota: «Prova completa per 30 giorni, senza carta», area «Trascina qui la cartella di un album», «Ho una chiave» ([schema](schemi/primo-avvio.svg)) | doppio clic |
| ~5 s | Cartella trascinata. Si apre l'album «Matrimonio Giulia e Marco», le foto compaiono man mano, «Preparo le foto · 12 di 100» | 1 trascinamento |
| ~10 s | Stato «foto senza spread»: «Prepara la bozza» (primario) e «Comincia a mano» | 1 clic |
| ~15 s | Foglio della bozza con l'anteprima di circa 30 spread | — |
| ~20 s | «Usa questa bozza». Primo spread sulla tela; l'indicatore del controllo diventa verde o ambra quando i volti sono pronti | 1 clic |

In Essenziale, al posto della bozza: «Comincia a mano», con le foto già in ordine di scatto e il filtro «Da usare»; il primo spread arriva con 3 clic (prima foto, Maiusc+clic, disposizione).

**Prova e chiave.** Vedi UX-017: nessun modulo, nessuna email, chiave incollabile ovunque, giorni rimasti solo negli ultimi 7, filigrana detta prima della consegna, album sempre apribili dopo la scadenza.

**Stati vuoti.**

| Stato | Oggi | Proposta |
|---|---|---|
| Nessun album | scheda «+ Nuovo progetto» e percorso della cartella ([01](schermate/01-home-vuota.jpg)) | area «Trascina qui la cartella di un album», «Nuovo album…», una riga «Le foto restano sul tuo computer: Impaginatore non le copia e non le carica in rete» |
| Album senza foto | filtri, ordinamento, zoom ed «Esporta…» attivi; frase piccola al centro ([28](schermate/28-progetto-vuoto.jpg)) | tutta la finestra è l'area per la cartella; «Scegli la cartella…»; «Consegna» spenta con «Prima impagina almeno uno spread» |
| Foto senza spread | metà destra vuota: «Seleziona le foto per uno spread…» ([04](schermate/04-foto-vista-iniziale.jpg)) | «Prepara la bozza» e «Comincia a mano: scegli le foto qui sotto» |
| Primo spread creato dalle foto | si resta in Foto, avviso «Spread 1 aggiunto» ([06](schermate/06-dopo-primo-spread.jpg)) | la tela mostra lo spread, la striscia delle foto resta sotto con il filtro «Da usare» |
| Filtro «Da usare» senza risultati | griglia vuota | «Tutte le foto sono nell'album · Mostra tutte» |
| Sostituisci quando tutte le foto sono usate | finestra vuota ([18](schermate/18-sostituisci-vuoto.jpg)) | sezione «Già nell'album» con il numero dello spread; scegliere significa scambiare |
| Controllo senza problemi | — | «Pronto. Nessun problema in 35 spread» |
| Versioni ancora vuote | elenco vuoto | «La prima copia si salva da sola fra poco. Puoi anche salvarne una con un nome» |
| Consegna con 0 spread | apre la finestra e poi dice «Non c'è nessuno spread da esportare» | pulsante spento con la spiegazione al passaggio del mouse |

---

## Riscontro e fiducia

### Avanzamento delle operazioni lunghe

Regola: sotto 0,4 s niente; fra 0,4 e 2 s un indicatore sul posto; oltre 2 s una barra con i numeri e il tempo che resta; oltre 10 s si può continuare a lavorare oppure fermare.

| Operazione | Oggi (misurato) | Proposta |
|---|---|---|
| Aprire un album nuovo | 0,65 s per foto (90 s per 100), rotellina «Apro «…»…» | editor subito; «Preparo le foto · 34 di 100 · circa 40 s» nella barra; foto usabili appena pronte (UX-012) |
| Importare foto | 4,3 s per 3 foto con riavvio; «ci vuole un po'» | stesso indicatore, nessun riavvio, annulla salvo |
| Misurare il tono dell'album | 17,9 s, «Misuro il tono…» | avanzamento per spread nel controllo, risultati che compaiono man mano |
| Bozza dell'album | — | «Preparo la bozza · spread 12 di 30» nel foglio |
| JPG per la stampa | 22 s per 35 spread, registro di testo | «Spread 12 di 35 · circa 14 s», «Ferma»; registro solo in «Dettagli» |
| PDF per il cliente | 3,9 s, registro | barra breve, poi «Pronto · Mostra nella cartella» |
| Ripristinare una versione | riavvio dell'editor | meno di 1 s, si annulla |

### Salvataggio visibile

- Testo fisso in alto: «Salvato alle 10:42»; mentre salva, «Salvo…» solo se dura più di 0,4 s.
- Se il salvataggio non riesce, una riga rossa che resta finché il problema c'è: «Non riesco a salvare: il disco è pieno. Le modifiche restano qui; riprovo da solo ogni 10 secondi». Oggi c'è «⚠ SALVATAGGIO NON RIUSCITO», che è giusto ma non dice cosa fare.

### Annulla dappertutto

Cose che oggi sfuggono all'annulla, e proposta:

| Azione | Oggi | Proposta |
|---|---|---|
| Importare foto | riavvio, cronologia persa | si annulla come le altre (UX-012) |
| Tornare a una versione | riavvio, cronologia persa | si annulla |
| Ricollegare foto | cambia `meta.json`, non si annulla | si annulla |
| Salvare, rinominare, eliminare un modello personale | file globale, `confirm()` | avviso «Modello eliminato · Annulla» per 30 s |
| Annulla in generale | muto | nome dell'azione e ritorno al punto (UX-003) |

### Messaggi: prima e dopo

| Dove | Oggi | Proposta |
|---|---|---|
| Album danneggiato | «album.json non è un JSON valido (riga 9, colonna 28: Unterminated string starting at)» | «Questo album non si apre: il file dell'impaginazione è danneggiato. C'è una copia buona di oggi alle 10:02 (35 spread). · Ripristina · Mostra la cartella» |
| Editor che non parte | «L'editor non si è avviato (guarda Progetti/editor.log)» | «L'album non si è aperto. Riprova; se succede ancora, Aiuto › Salva la diagnostica crea un file da mandarci (senza foto)» |
| Salvataggio a mano | «Salvato spec.py e progetto.json (copie in _backup_editor)» | «Salvato alle 10:42» |
| Foto mancanti | «2 foto su 101 non si trovano (spostate, rinominate o disco scollegato): DEMO_0007.jpg, DEMO_0020.jpg. Premi «Ricollega foto…» e scegli la cartella dove sono ora.» | «2 foto non si trovano più: DEMO_0007 (spread 03–04) e DEMO_0020 (spread 11–12). Gli spread restano come sono. · Cerca in una cartella…» |
| Ricollega | «101 foto · tutte trovate» (anche quando ha trovato la miniatura) | «Trovata 1 su 2: DEMO_0020 in Lavoro. DEMO_0007 non c'è; forse è «DEMO_0007 rinominata.jpg» (stessa data e misure) · Usa questa» |
| Cartella scritta a mano | «Non posso usare quella cartella delle foto: sta fuori dalle cartelle del progetto e da quelle che hai scelto. Sceglilo con «Scegli…»» | con la finestra di sistema il caso sparisce; se resta: «Scegli la cartella con «Scegli…»: per sicurezza Impaginatore apre solo le cartelle che indichi tu» |
| Altra finestra | «Questo progetto è stato modificato da un'altra scheda: ho ricaricato lo stato, riprova.» | «L'album è cambiato in un'altra finestra o dall'assistente. Ti mostro la versione aggiornata: rifai l'ultima modifica» |
| PSD su Linux | dopo una conferma: «I PSD si creano con Photoshop, che non esiste per Linux: esporta in JPG o PDF (oppure apri il progetto su un Mac o un PC Windows con Photoshop)» | scelta spenta prima del clic: «A Photoshop: non disponibile su Linux. Puoi consegnare in JPG o PDF, oppure aprire l'album su un Mac o un PC con Photoshop» |
| Conferma PSD | «Genero i PSD in Photoshop (i PSD modificati a mano non vengono toccati, salvo la spunta). Continuo?» | nessuna conferma; il pulsante dice «Crea 35 PSD (salto i 3 ritoccati a mano)» |
| PSD saltati | «3 spread NON generati: …» | «3 PSD non rifatti perché li hai ritoccati a mano: 05–06, 12–13, 18–19. Per rifarli spunta «Sostituisci anche i PSD ritoccati»» |
| Errore generico | «Qualcosa non è andato: guarda il riquadro» | «2 spread non consegnati (07–08, 21–22): [motivo in parole]. Gli altri 33 sono nella cartella · Mostra» |
| Elimina spread | `confirm`: «Eliminare lo spread 7? Le foto tornano libere (puoi annullare).» | nessuna conferma; «Spread 07–08 eliminato, le foto tornano da usare · Annulla» |
| Spazi | «Nessuna coppia di foto vicine da controllare» | «In questo spread le foto non si toccano: niente spazi da controllare» |
| Spazi dell'album | «Tutti gli stacchi dell'album sono uguali al riferimento scelto.» | «Spazi uguali in tutto l'album (2,5 mm)» |
| Tono | «La 3 è un po' chiara, la 4 è un po' chiara. … Scarto +18 · Bruc. 5,0%» | «La 3 e la 4 sono più chiare del resto dello spread, con i bianchi bruciati sul 5 %. · Uniforma» |
| Tono, suggerimento | «luce media L* 62 (standard 52) · alte luci L* 86 · ombre L* 28 · clic: seleziona · clic destro: escludi dal calcolo (scura o chiara di proposito)» | «Più chiara del riferimento dell'album (62 contro 52). Tasto destro: è chiara di proposito» |
| Import | «Importo 3 foto… preparo miniature e riconoscimento volti: ci vuole un po'» | «Preparo 3 foto · 1 di 3 · puoi continuare a lavorare» |
| Apertura | «Apro «Giulia e Marco»…» per 90 s | «Preparo le foto · 34 di 100 · circa 40 s» con l'editor già in uso |
| Consegna vuota | «Non c'è nessuno spread da esportare» (dopo il clic) | pulsante spento: «Prima impagina almeno uno spread» |
| Spazio su disco | «Spazio insufficiente: servono circa 1,2 GB e ne restano 0,8 GB. Libera spazio o scegli un altro disco» | resta, con i numeri in mono e «Scegli un'altra cartella…» come pulsante |
