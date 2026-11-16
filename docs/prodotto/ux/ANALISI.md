# Analisi UI/UX dell'editor (T-209)

Analisi dell'interfaccia attuale prima del ridisegno (T-205). Ogni numero viene da una prova fatta sul programma o da una riga di codice citata. Quello che non si è potuto provare è indicato con «non provato».

- **Versione provata:** 2.0.0.dev0, ramo `prodotto/2.0`, commit `e33ffab`, 16/11/2026. I numeri di riga citati valgono per quel commit: durante la stesura il ramo è andato avanti (`c8541e7`, nessun cambio all'interfaccia) e alcune funzioni di `editor/server.py` sono salite di 7 righe.
- **Macchina:** Linux 6.8, 12 core, 62 GB di RAM, Python 3.12.3, OpenCV 4.14, Pillow 13. Durante la prima apertura girava in parallelo la suite di prova di un altro lavoro (carico medio 11), quindi quel tempo è più alto del normale. La misura per foto è stata ripetuta dopo, a carico 2,6.
- **Come:** schermata dei progetti ed editor avviati come li avvia l'utente (`python -m impaginatore`, l'editor come processo figlio con riavvii veri). Chrome 134 senza schermo pilotato col protocollo DevTools: clic e tasti veri (`Input.dispatchMouseEvent`, `Input.dispatchKeyEvent`). Le finestre di sistema per scegliere le cartelle sono state sostituite da un finto `zenity` che restituisce la cartella prevista. Casa finta, nessun dato dell'utente toccato, nessuna rete.
- **Dati:** cartella cliente finta `Matrimonio Giulia e Marco/JPG` con 100 foto: le 62 di `marketing/demo/foto` (lato lungo 3000 px) più 38 copie specchiate per arrivare a un album vero. Formato predefinito 60 × 22,5 cm aperto, spazio 2,5 mm, margine 10 mm, abbondanza 0.
- **Album completo:** 35 spread costruiti con le API dell'editor come farebbe un utente paziente (foto in ordine, gruppi di 1–5, primo modello proposto), poi controllati e corretti a mano dall'interfaccia.
- **Schermate:** `schermate/`, elencate in [`schermate/INDICE.md`](schermate/INDICE.md). Finestra di riferimento 1280 × 800, più 1920 × 1080, 1024 × 700 e zoom al 200 %.

**Non provato:** finestra desktop pywebview (T-201 non c'è ancora: oggi il programma si apre nel browser), installazione e chiave (T-202 non c'è), macOS e Windows, Photoshop e quindi i PSD (su Linux l'editor li rifiuta, vedi A-22), il server MCP (T-203), la resa delle finestre di sistema vere (macOS Finder, tkinter, zenity), un utente vero cronometrato. I tempi di decisione dell'utente non sono misurati: si contano gesti, attese e cambi di contesto.

Scala di gravità usata in tutto il documento: **1** estetico, **2** minore, **3** grave (fa perdere tempo o fiducia), **4** bloccante (risultato sbagliato o attesa che fa abbandonare).

---

## 1. Inventario delle funzioni

Scopribilità: **A** si vede senza cercare; **M** si trova con un passaggio (menu, scheda, scorrimento, suggerimento al passaggio del mouse); **B** bisogna saperla (doppio clic, tasto, tasto destro, sottomenu).
Uso nel flusso tipico: quanto serve per un album da 80–120 foto secondo `docs/prodotto/REQUISITI-VOCALI.md` e le regole di `skill/impaginatore-stefano/references/stile.md` (spazio identico, niente foto sulla piega, mai tagliare le persone, misura esatta, B/N come accento, pagine immersive e bianche alternate, luminosità per la stampa, copertina).

### Schermata dei progetti (`risorse/home.html`, `home/server.py`)

| Funzione | Dove | Come si attiva | Scopr. | Uso |
|---|---|---|---|---|
| Nuovo progetto | scheda «+» | clic | A | una volta per album |
| Cartella delle foto del cliente | finestra Nuovo progetto | «Scegli…» (il campo è di sola lettura) | M | sempre |
| Nome dal nome della cartella | finestra Nuovo progetto | automatico dopo «Scegli…» | B | sempre; non funziona se la cartella si chiama «JPG» (A-01) |
| Formati rapidi 60 × 22,5 · 70 × 25 · 50 × 20 · 40 × 30 | finestra Nuovo progetto | clic | A | spesso |
| Abbondanza, spazio tra le foto, margine | «▸ Avanzate» | clic per aprire | B | l'abbondanza va chiesta ogni volta (stile.md, regola 4) |
| Apri progetto | scheda | clic | A | sempre |
| Apri, Mostra nel gestore file, Togli dall'elenco | «⋯» sulla scheda | clic | M | raro |
| Apri progetto esistente… | barra in alto | clic, finestra di sistema | A | raro |
| Importa ZIP… | barra in alto | clic | A | raro |
| Versione, aggiornamenti, versioni precedenti | pillola «Versione…» | clic | M | raro |
| Chiudi programma | barra in alto | clic + `confirm()` | A | raro |

### Editor, barra superiore (`risorse/index.html`)

| Funzione | Dove | Come si attiva | Scopr. | Uso |
|---|---|---|---|---|
| Torna ai progetti | «‹ Progetti» | clic | A | a volte |
| Vista Foto / Album | selettore | clic | A | sempre |
| Annulla / Ripeti (200 livelli) | icone | clic, ⌘Z / ⇧⌘Z | A | sempre |
| Modelli dello spread | «Modelli» | clic, M | A | sempre |
| Stato del salvataggio, Salva | testo «tutto salvato», «Salva» | automatico dopo 2 s; ⌘S | A | quasi mai (salva da solo) |
| Foto mancanti | «⚠ N foto mancanti» (appare solo se serve) | clic → finestra Progetto | A | raro |
| Progetto: foto modificate, Ricollega, Esporta progetto | «Progetto» | clic | M | raro |
| Versioni salvate | «Versioni» | clic | A | a volte |
| Elenco delle scorciatoie | icona tastiera, ? | clic, ? | M | raro |
| Sfondo della tela (nero, grafite, grigio, bianco) | quattro pallini senza etichetta | clic | B | raro |
| Mostra/nascondi pannelli, schermo pieno | tre icone, Tab | clic, Tab | B | a volte |
| Esporta… | pulsante primario | clic | A | sempre |

### Vista Foto

| Funzione | Dove | Come si attiva | Scopr. | Uso |
|---|---|---|---|---|
| Importa cartella / Importa foto | «+ Importa cartella…», «+ Importa foto…» | sfoglia file interno (`#fbd`), «Altra cartella…» apre quello di sistema | A | a volte |
| Selezione con numero d'ordine | griglia | clic, Maiusc+clic, ⌘+clic, ⌘A | M | sempre |
| Filtri Tutte / Da usare / Già usate / Tolte, Vert. / Orizz., colori, Solo ★ | tre righe sopra la griglia | clic | M | «Da usare» serve sempre, ma il predefinito è «Tutte» |
| Preferita, Tolta | pulsanti, P, X | clic, tasto | M | spesso nella scelta |
| Etichette colore 1–7 | «Colora:» | clic, tasti 1–7, 0 | M | a volte |
| Ordinamento (import, nome, data di scatto, colore) | menu a tendina | clic | M | a volte |
| Cerca per nome, grandezza miniature | campo, − / + | digitare, trascinare | A | raro |
| Modelli per le foto scelte, dove aggiungere | colonna destra | appare dopo la selezione; clic sul modello | A | sempre |
| Anteprima grande | Z, Spazio | tasto | B | spesso |

### Colonna degli spread

| Funzione | Dove | Come si attiva | Scopr. | Uso |
|---|---|---|---|---|
| Spread precedente / successivo, contatore «4 di 35» | riquadro in alto | clic, ↑ ↓ | A | sempre |
| Nuovo, Duplica, Elimina, Sposta prima, Sposta dopo | riquadro in alto | clic (Elimina chiede `confirm()`) | A | a volte |
| Riordina | miniature | trascinare | M (suggerimento) | a volte |
| Nuovo spread dalle foto trascinate tra due miniature | striscia → colonna | trascinare | B | a volte |
| Foto aggiunte a uno spread esistente, «Riorganizza con un altro modello / Lascia così» | striscia → miniatura | trascinare | B | a volte |
| Menu della miniatura (vai, duplica, elimina, sposta, esporta come JPG) | miniatura | tasto destro | B | raro |

### Tela dello spread

| Funzione | Dove | Come si attiva | Scopr. | Uso |
|---|---|---|---|---|
| Selezione e selezione multipla | foto, testi | clic, Maiusc/⌘+clic | A | sempre |
| Scambia due foto | chip «⇄ scambia», trascinare una foto sull'altra | clic, trascinare | M | spesso |
| Sposta l'immagine nella cornice (ritaglio) | foto | doppio clic; menu destro › Tutti i comandi | B | spesso: è la regola «mai tagliare le persone» |
| Ridimensiona, proporzionale, senza magnete | maniglie | trascinare, Maiusc, Alt | M | a volte |
| Sposta di 0,01 / 0,1 cm | foto | frecce, Maiusc+frecce | B | raro |
| Quote dai lati e tra le foto | badge blu sulla selezione | automatiche | A | spesso |
| Righelli, guide, blocca guide, magnete | riquadro «Vista» a destra, R, G | clic, tasto, trascinare dal righello | M | magnete sempre; il resto raro |
| Avviso ritaglio | riquadro «Vista» | clic; **spento di serie** (`showCropWarn = false`, `index.html:1213`) | B | dovrebbe essere sempre acceso |
| Zoom della tela | Alt+rotella, pizzico, «Fit» | gesto | B | a volte |
| Menu dello sfondo (foto libera, testo, incolla, righelli, guide, duplica, esporta JPG) | punto vuoto | tasto destro | B | raro |
| Menu della foto (livelli, centra, tutta pagina, proporzioni, B/N, ritaglio, bordo, ombra, sostituisci, preferita, ritocco, gestore file, taglia/copia/incolla, togli) | foto | tasto destro; 5 voci «Suggeriti» + «Tutti i comandi ▸» | B | spesso; le voci utili sono nel sottomenu (A-09) |

### Barra degli strumenti (16 pulsanti da 66 × 58 px in due righe)

| Funzione | Come si attiva | Scopr. | Uso |
|---|---|---|---|
| Testo | clic, T, poi clic sulla pagina | A | a volte (titolo, firma) |
| Copia, Incolla | clic, ⌘C / ⌘V | A | raro |
| Inverti pagine | clic | A | a volte |
| Spaziature (mostra le misure degli stacchi) | clic | A | spesso (regola 1) |
| Correggi spazi: standard del progetto / il più frequente / valore; questo spread / tutto l'album | clic → menu | M | spesso |
| Controlla album: **solo** il controllo delle spaziature | clic | A, ma il nome promette di più (A-12) | a volte |
| In cima, Avanti, Indietro, In fondo | clic, + − [ ] { } | A | raro |
| Stessa misura, Proporzioni, Tutta pagina, Verticali, Orizzontali | clic con una selezione | A (disattivati senza selezione) | Tutta pagina a volte, il resto raro |

### Pannello di destra (ispettore della foto)

| Funzione | Scopr. | Uso |
|---|---|---|
| Anteprima «Design» con la finestra di ritaglio | A | spesso |
| Scala (primo piano), Angolo, Esposizione, Opacità | A | Scala ed Esposizione spesso (stile.md: z 1,3–1,8; +0,25 EV) |
| Luce: Contrasto, Alteluci, Ombre, Bianchi, Neri | M (scorrere) | a volte |
| Colore: Temperatura, Tinta, Vibranza, Saturazione | M (scorrere) | a volte |
| Cornice: bordo in mm e 4 colori, Ombra | M (scorrere) | raro (stile.md: niente cornici né ombre) |
| Etichetta colore, Sposta nella cornice, Bianco e nero, Alla griglia, Rimuovi | M (scorrere) | B/N spesso |
| Informazioni: misura della cornice, PPI effettivi (rossi sotto 200), pixel, data di scatto | M (in fondo al pannello) | dovrebbe essere sempre sotto gli occhi |
| Copia / incolla il ritocco, applica a tutte le foto con la stessa etichetta | B (menu destro) | a volte |
| Testo: stile salvato, carattere, corpo, spaziatura, allineamento, colore | A quando c'è un testo | a volte |

### Striscia in basso: Galleria e Tono

| Funzione | Scopr. | Uso |
|---|---|---|
| Galleria con filtri (gli stessi della vista Foto) e trascinamento sulla tela | A | sempre |
| Tono dello spread: punteggio /100, per ogni foto Scarto, Luci, Ombre, Bruc., stato, suggerimento d'esposizione | M | spesso (stile.md: in stampa esce più scuro) |
| Vista album, Peggiori prima, Impostazioni (standard L*, zona) | B | raro |
| Escludere una foto dal calcolo | B (tasto destro) | raro |

### Esporta, Progetto, Versioni, Modelli

| Funzione | Dove | Scopr. | Uso |
|---|---|---|---|
| JPG «Stampa · 300 dpi, a grandezza reale» o «Schermo · leggero (¼)», qualità | Esporta | A | sempre |
| PDF 2000 / 3500 / 5000 px con numero dello spread | Esporta | A | sempre (bozza per il cliente) |
| PSD con Photoshop, salta i PSD ritoccati salvo spunta | Esporta | A | sempre per chi lavora in Photoshop |
| Intervallo di spread, Esposizione EV su tutte le foto, cartella | Esporta | A | l'EV globale spesso (stile.md) |
| Controlla foto modificate, Ricollega foto, Esporta progetto (con foto, ZIP, `spec.py` per la 1.x) | Progetto | M | raro |
| Elenco delle versioni con data e numero di spread, «Torna a questa» | Versioni | A | a volte |
| Salva lo spread come modello, Aggiorna, Rinomina, Elimina; «Mostra altri N modelli» | Modelli | A | a volte |

### Funzioni del motore che l'interfaccia non mostra

| Funzione | Dove sta | Stato |
|---|---|---|
| Correzione del tono di più foto con un solo annulla | op `tono_fix` (`editor/server.py:337`); proposte pronte in `tono_spread()` (`compl`: EV e ritocco per foto) | il pulsante non viene più disegnato: il commento dice «la correzione si fa a mano» |
| Controllo dell'album: fuori pagina, foto sulla piega, ritagli oltre ×1,25, spazi diversi, doppie, non usate | `motore/anteprima.py` (riga di comando) | solo riga di comando |
| Foglio con tutti gli spread, prima/dopo delle correzioni | `motore/anteprima.py` | solo riga di comando |
| PDF per il cliente con pagina di copertina (una o più ipotesi A/B) | `motore/esporta_pdf.py --copertina` (passa da Photoshop) | solo riga di comando |
| Modifica dei PSD già ritoccati (scambia, sostituisci, B/N, esposizione, rifai una pagina) | `motore/modifica_psd.py` | solo riga di comando |
| Abbina la selezione del cliente agli originali in alta | `motore/abbina.py` | solo riga di comando |
| Provini numerati, luminosità per cartella, finestre di ritaglio sugli originali, dominanti | `motore/analizza.py` | solo riga di comando |
| Centro del volto fissato a mano | chiave `centri_volto` di `progetto.json` | solo a mano nel file |
| Impaginazione di tutto l'album | nessuna funzione: oggi la fa Claude spread per spread con `/api/templates` e `/api/op` (skill) | assente |

---

## 2. Flussi misurati

Le attese sono cronometrate; i clic sono quelli fatti nella prova. «Cambio di contesto» = cambio di schermata, vista o finestra che nasconde il lavoro.

### Flusso 1 — Primo avvio, nuovo progetto, prime foto, primo spread

| # | Passo | Clic | Attesa | Note |
|---|---|---|---|---|
| 1 | Avvio del programma | — | non provato | oggi si apre una scheda del browser con un indirizzo monouso; la finestra desktop (T-201) non c'è |
| 2 | «Nuovo progetto» | 1 | — | [01](schermate/01-home-vuota.jpg) |
| 3 | «Scegli…» e finestra di sistema fino alla cartella `JPG` | 1 + ≥ 3 | — | finestra di sistema simulata; il campo non accetta un percorso scritto a mano |
| 4 | Nome del progetto | tastiera | — | la cartella si chiama `JPG`: il nome proposto è vuoto (A-01), [02](schermate/02-nuovo-progetto.jpg) |
| 5 | Formato | 0 | — | 60 × 22,5 predefinito; nessun formato di laboratorio |
| 6 | «Crea» | 1 | **89,6 s** | «Apro «Giulia e Marco»…» con la rotellina, nessun avanzamento (A-03), [03](schermate/03-apertura-90s.jpg) |
| 7 | Vista Foto: clic sulla prima foto, Maiusc+clic sulla quarta | 2 | — | a destra compaiono «3 modelli possibili» e «Mostra altri 71», [05](schermate/05-foto-quattro-scelte.jpg) |
| 8 | Clic su «modello 1» | 1 | 0,05 s | lo spread nasce, ma si resta in Foto: lo spread non si vede (A-05), [06](schermate/06-dopo-primo-spread.jpg) |
| 9 | «Album» per vederlo | 1 | — | il modello 1 per 4 foto le mette tutte a sinistra e lascia vuota la pagina destra (A-06) |

**Totale:** 7 clic nell'app più la finestra di sistema, un nome digitato, 90 s di attesa, 3 cambi di contesto (progetti → editor, Foto → Album, finestra di sistema). Un utente che sa già cosa fare arriva al primo spread in circa 2 minuti e mezzo su questa macchina; uno nuovo deve capire da solo che prima si scelgono le foto e poi il modello: la vista iniziale non lo propone ([04](schermate/04-foto-vista-iniziale.jpg)).

**Dove va il tempo dell'attesa.** Misurato a parte con il profilatore su 61 foto da 3000 px, a carico normale: 39,6 s, cioè **0,65 s per foto**, in un solo thread. Il 73 % è il riconoscimento dei volti (`cv2.CascadeClassifier.detectMultiScale`, chiamato 3 volte per foto, `motore/album.py:224`), il 27 % le miniature da 1200 px (`_build_thumbs`, `album.py:217`). L'editor non risponde finché non ha finito tutto. Un matrimonio da 400 foto selezionate vuol dire più di 4 minuti davanti alla rotellina, oltre il KPI «primo spread in meno di 5 minuti» già prima di aver scelto una foto.

### Flusso 2 — Album completo (100 foto, 35 spread)

| Misura | Valore |
|---|---|
| Tempo del motore per proporre i modelli di un gruppo | 0,00–0,07 s (gruppi da 1 a 5 foto) |
| Tempo del motore per creare uno spread | 0,01–0,04 s |
| 35 spread creati via API, scelta inclusa | meno di 3 s in tutto |
| Spread in cui il **primo** modello proposto lascia una pagina vuota | **9 su 35 (26 %)** |
| Gesti a mano per spread nella vista Foto | 3 (clic, Maiusc+clic, modello) se le foto sono vicine; uno in più per ogni foto lontana |
| Gesti a mano per l'album | ≥ 105 clic più lo scorrimento della griglia (12 foto visibili per schermata a 1280 × 800 con il filtro «Tutte» predefinito) |
| Decisioni per spread | quali foto insieme, quale modello fra 3–12 «buoni» e fino a 78 «che tagliano di più», pagina immersiva o bianca (implicita nel modello) |
| Controllo delle spaziature di tutto l'album | 1 clic, risultato immediato: «Tutti gli stacchi dell'album sono uguali al riferimento scelto» ([13](schermate/13-controlla-album.jpg)) |
| Misura del tono di tutti gli spread | `tono_all` 2,3 s; i suggerimenti foto per foto (`tono_spread` × 35) 17,9 s |

Il motore non è il collo di bottiglia: lo sono i gesti e le decisioni. Il motore sa già proporre le disposizioni migliori per qualunque gruppo in un tempo trascurabile; manca il passo che divide le 100 foto in gruppi e sceglie per tutto l'album (oggi lo fa Claude, a mano, via API).

Pannelli toccati in un giro completo: vista Foto (scelta), vista Album (tela, colonna, ispettore), Modelli (sovrapposto alla tela), Galleria, Tono, Spaziature, Esporta. Ogni controllo passa da un posto diverso.

### Flusso 3 — Correzioni tipiche

| Correzione | Gesti oggi | Cosa si vede | Attrito |
|---|---|---|---|
| Cambiare disposizione | M, scorrere (1–3), clic = 3–5 azioni per prova | la finestra dei modelli copre lo spread e si chiude a ogni scelta; a 1280 × 800 si vede un modello e mezzo per schermata ([12](schermate/12-modelli.jpg)) | A-08 |
| Confrontare tre disposizioni | 9–15 azioni | nessun confronto affiancato | A-08 |
| Scambiare due foto | 1 trascinamento | bene: chip «⇄ scambia» | — |
| Sostituire una foto | tasto destro, «Tutti i comandi ▸», «Sostituisci con un'altra foto…», scelta = 4 clic | se tutte le foto sono usate la finestra è vuota e non dice perché ([18](schermate/18-sostituisci-vuoto.jpg)) | A-09, A-11 |
| Sostituire un'orizzontale con una verticale | come sopra | la cornice resta orizzontale: la verticale è tagliata ×2,28 (se ne vede il 44 % dell'altezza), nessun avviso | A-10 |
| Ritagliare / riposizionare | doppio clic sulla foto, trascinare | il modo «sposta nella cornice» si scopre solo dal menu o per caso | A-09 |
| Uniformare gli spazi | «Spaziature», «Correggi spazi», scelta, «Correggi questo spread» = 3–4 clic | tre nomi per la stessa cosa: spaziature, spazi, stacchi ([25](schermate/25-correggi-spazi.jpg)) | A-12 |
| Correggere il tono | scheda Tono, leggere «Esposizione −0,5», selezionare la foto, scorrere l'ispettore, spostare il cursore; per ogni foto | gergo (Scarto, Bruc., L*), nessun pulsante per applicare; il pannello taglia lo spread in basso ([14](schermate/14-tono.jpg)) | A-13 |
| Titolo o testo | Testo, clic sulla pagina = 2 clic | testo di 22,3 pt quasi invisibile a vista intera; carattere predefinito Avenir Next (assente su Linux); la barra dice «AvenirNext-Regular», il pannello «aakar»; elenco di tutti i caratteri di sistema ([24](schermate/24-testo.jpg)) | A-14 |
| Copertina | — | non esiste nell'editor | A-29 |

### Flusso 4 — Revisione col cliente e modifiche dell'ultimo minuto

| Passo | Gesti | Note |
|---|---|---|
| PDF per il cliente | Esporta, PDF, «Leggero · 2000 px», Esporta = 4 clic | 3,9 s per 35 spread, 4,4 MB, nome fisso «… - bozza.pdf» |
| Sostituire una foto | 4 clic (vedi flusso 3) | la disposizione non si adatta |
| Aggiungere uno spread | Foto, scelta, «dopo lo spread attuale», modello | oppure trascinare dalla striscia fra due miniature |
| Togliere uno spread | «Elimina» + conferma = 2 clic | la conferma dice «(puoi annullare)»: allora non serve |
| Tornare indietro | «Versioni»: data, ora, numero di spread ([21](schermate/21-versioni.jpg)) | una copia al massimo ogni 10 minuti; nessun nome («inviata al cliente»), nessuna anteprima, nessun confronto; il ripristino riavvia l'editor |
| Annullare | ⌘Z | funziona, ma non dice cosa annulla né mostra dove (A-15) |

### Flusso 5 — Consegna

| Passo | Gesti | Misura |
|---|---|---|
| JPG per la stampa | Esporta, «Esporta in JPG» = 2 clic | 22 s per 35 spread, 54 MB, 7087 × 2657 px a 300 dpi, profilo sRGB incorporato |
| Nitidezza dei JPG «Stampa · 300 dpi» | — | **ricavati dalle miniature da 1200 px**: le foto sono ingrandite ×2,2 (con originali da 3000 px). Sulla stessa zona, la varianza dei bordi è 346 contro 1406 dell'originale alla stessa scala ([29](schermate/29-stampa-da-miniatura.jpg)). Codice: `motore/album.py:339–340` (`_photo` apre `THUMBS`), `editor/server.py:1466` |
| Abbondanza | — | JPG e PDF la tagliano via (`server.py:1467` e `:1482`): chi l'ha impostata la ritrova solo nei PSD |
| Controlli prima di esportare | automatici | solo tecnici (`preflight`, `server.py:1421`): ci sono spread, foto mancanti, permessi, spazio su disco, Photoshop. Nessun controllo su PPI, volti, piega, testi, pagine vuote |
| Riscontro durante l'esportazione | — | registro grezzo con percorsi completi, nessuna barra ([16](schermate/16-esporta-registro.jpg)) |
| PSD su Linux | PSD, «Esporta in PSD», conferma = 3 clic | solo dopo la conferma: «I PSD si creano con Photoshop, che non esiste per Linux…» ([17](schermate/17-esporta-psd-linux.jpg)) |
| Formati di laboratorio, profili, segni di taglio | — | assenti (T-208) |

### Flusso 6 — Recupero dagli errori

| Caso | Cosa è successo | Gravità |
|---|---|---|
| Foto spostata e foto rinominata | l'editor riaperto in 2,6 s mostra «⚠ 2 foto mancanti»; il clic apre Progetto con i nomi ([19](schermate/19-foto-mancanti.jpg)). Bene | — |
| «Ricollega foto…» scegliendo la cartella che contiene anche il progetto | risultato «101 foto · tutte trovate», ma la foto rinominata è stata collegata a **`_cache/thumbs/DEMO_0007.jpg`**, la miniatura da 1200 px del progetto stesso (`ricollega`, `server.py:1590`, cerca in tutte le sottocartelle). L'esportazione non se ne accorge | 3 (difetto, A-23) |
| Annulla ripetuto | il secondo ⌘Z ha tolto lo spread 35 mentre si guardava lo spread 4: nessun messaggio, nessuno spostamento | 3 (A-15) |
| Importare 3 foto | l'editor si riavvia (4,3 s); dopo, «Annulla» è disattivato: la cronologia è persa (`inizializza` azzera `UNDO`, `server.py:1826`) | 3 (A-16) |
| Progetto con `album.json` danneggiato | la scheda dice «errore: album.json non è un JSON valido (riga 9, colonna 28: Unterminated string starting at)»; il clic ripete lo stesso testo in un `alert()` ([20](schermate/20-progetto-danneggiato.jpg)). In `_backup_editor/` ci sono copie buone, ma l'interfaccia non lo dice e «Versioni» è solo dentro l'editor | 3 (A-24) |
| Operazione rifiutata | il server rifiuta, ripristina lo stato (BUG-001 corretto) e mostra un avviso rosso per 4,5 s | bene |
| Due finestre sullo stesso album | «Questo progetto è stato modificato da un'altra scheda: ho ricaricato lo stato, riprova.» | 2 |
| Modifiche fatte via API (come farà l'MCP) | la pagina aperta non si aggiorna: 35 spread creati via API, la pagina ne mostrava ancora 1 finché non è stata ricaricata | 3 (A-32) |
| Finestre native `confirm()`, `alert()`, `prompt()` | 10 punti nell'editor (7 `confirm`, 3 `prompt`), 11 nella schermata dei progetti (7 `alert`, 4 `confirm`); in Chrome bloccano la pagina finché non si risponde (nella prova la pagina è rimasta ferma e si è dovuta riaprire la scheda) | 2 (A-17) |

### Punti d'attrito

| ID | Attrito | Flusso | Gravità | Schermata |
|---|---|---|---|---|
| A-01 | Nome non proposto se la cartella si chiama «JPG» (`home.html`: `replace(/\s*JPG$/i, "")` lascia una stringa vuota) | 1 | 1 | [02](schermate/02-nuovo-progetto.jpg) |
| A-02 | Primo avvio senza scelta del formato di laboratorio, abbondanza nascosta in «Avanzate» | 1 | 2 | [02](schermate/02-nuovo-progetto.jpg) |
| A-03 | 90 s di rotellina senza avanzamento prima di vedere una foto | 1 | 4 | [03](schermate/03-apertura-90s.jpg) |
| A-04 | Vista iniziale: metà destra vuota, tre righe di filtri, nessuna proposta di partenza | 1 | 2 | [04](schermate/04-foto-vista-iniziale.jpg) |
| A-05 | Dopo il primo spread si resta in Foto e lo spread non si vede | 1 | 2 | [06](schermate/06-dopo-primo-spread.jpg) |
| A-06 | Il primo modello proposto lascia una pagina vuota in 26 % dei casi | 1, 2 | 2 | [05](schermate/05-foto-quattro-scelte.jpg) |
| A-07 | Tela piccola: 15 % della finestra a 1280 × 800, 8 % a 1024 × 700; 16 pulsanti grandi sempre visibili, metà disattivati | tutti | 3 | [07](schermate/07-album-1280x800.jpg), [09](schermate/09-album-1024x700.jpg) |
| A-08 | Cambiare disposizione costa 3–5 azioni per prova, senza confronto | 3 | 3 | [12](schermate/12-modelli.jpg) |
| A-09 | Menu destro: «Suggeriti» = ordine dei livelli; Sostituisci, B/N, ritaglio nel sottomenu; le voci cambiano posto con l'uso (`ctxMenu`, `index.html:1744`) | 3 | 3 | [11](schermate/11-menu-contestuale.jpg) |
| A-10 | Sostituire con un'orientamento diverso taglia la foto ×2,28 senza avviso | 3, 4 | 3 | — |
| A-11 | Finestra «Sostituisci» vuota senza spiegazione quando tutte le foto sono usate; i badge delle misure restano sopra il velo | 3 | 2 | [18](schermate/18-sostituisci-vuoto.jpg) |
| A-12 | «Controlla album» controlla solo le spaziature; tre nomi per la stessa cosa | 2, 3 | 3 | [13](schermate/13-controlla-album.jpg) |
| A-13 | Tono: gergo, suggerimento non applicabile, 18 s di misura senza avanzamento, spread tagliato dal pannello | 3 | 3 | [14](schermate/14-tono.jpg) |
| A-14 | Testo: carattere predefinito assente, nomi diversi nello stesso momento, elenco di tutti i font di sistema | 3 | 2 | [24](schermate/24-testo.jpg) |
| A-15 | Annulla senza nome e senza spostamento | 4, 6 | 3 | — |
| A-16 | Importare foto riavvia l'editor e cancella la cronologia di annulla | 4, 6 | 3 | [27](schermate/27-importa-attesa.jpg) |
| A-17 | Conferme native per azioni che si possono annullare; nomi chiesti con `prompt()` | 3, 4 | 2 | — |
| A-18 | «Stampa · 300 dpi, a grandezza reale» produce file ingranditi dalle miniature | 5 | 4 | [29](schermate/29-stampa-da-miniatura.jpg) |
| A-19 | JPG e PDF tolgono l'abbondanza | 5 | 3 | — |
| A-20 | Nessun controllo di contenuto prima della consegna | 5 | 3 | — |
| A-21 | Registro grezzo, nessuna barra d'avanzamento | 5 | 2 | [16](schermate/16-esporta-registro.jpg) |
| A-22 | PSD proposto su Linux; l'impossibilità si scopre dopo una conferma | 5 | 2 | [17](schermate/17-esporta-psd-linux.jpg) |
| A-23 | Ricollega collega una foto mancante alla sua miniatura nella cache | 6 | 3 | [19](schermate/19-foto-mancanti.jpg) |
| A-24 | Progetto danneggiato senza via d'uscita, con le copie buone già su disco | 6 | 3 | [20](schermate/20-progetto-danneggiato.jpg) |
| A-25 | Versioni senza nome né anteprima, ripristino con riavvio | 4 | 2 | [21](schermate/21-versioni.jpg) |
| A-26 | «Salva» annuncia «Salvato spec.py e progetto.json (copie in _backup_editor)»: file che non esistono più e gergo interno | tutti | 2 | [30](schermate/30-salva.jpg) |
| A-27 | Scorciatoie solo con simboli Mac anche su Linux e Windows | tutti | 2 | [22](schermate/22-scorciatoie.jpg) |
| A-28 | Progetto vuoto: filtri, ordinamento ed «Esporta…» (unico primario) attivi con 0 foto | 1 | 2 | [28](schermate/28-progetto-vuoto.jpg) |
| A-29 | Copertina assente | 4, 5 | 3 | — |
| A-30 | Il menu di «Correggi spazi» resta aperto sopra la finestra di import | 3 | 1 | [26](schermate/26-importa-foto.jpg) |
| A-31 | Il sfoglia file interno mostra tra i «luoghi» le cartelle del progetto e `thumbs`; icone emoji | 1 | 1 | [26](schermate/26-importa-foto.jpg) |
| A-32 | La pagina non si aggiorna quando l'album cambia via API | 6 | 3 | — |
| A-33 | Zoom al 200 %: editor inutilizzabile | — | 3 | [23](schermate/23-zoom-200.jpg) |
| A-34 | Tab non sposta il fuoco: apre e chiude i pannelli | — | 3 | — |

---

## 3. Valutazione euristica

| Principio | Cosa si vede | Grav. |
|---|---|---|
| **Visibilità dello stato** | Bene: «tutto salvato / salvo… / ⚠ SALVATAGGIO NON RIUSCITO», badge delle foto mancanti, quote sulla selezione. Male: 90 s di rotellina all'apertura (A-03); import con riavvio e frase «ci vuole un po'» senza numeri; «Misuro il tono…» senza avanzamento; esportazione come registro grezzo (A-21); annulla muto (A-15) | 4 |
| **Corrispondenza col mondo del fotografo** | «Stampa · 300 dpi» che non è stampa vera (A-18); gergo tecnico: L*, Scarto, Bruc., `spec.py`, `_backup_editor`, «modello 1…12», «stacchi»; il fotografo pensa in «pagina piena / pagina bianca», «primo piano», «copertina», «laboratorio» e l'interfaccia non usa queste parole (le pagine immersive e bianche esistono nel motore ma non hanno nome a schermo) | 4 |
| **Controllo e libertà** | Bene: 200 livelli d'annulla, operazioni rifiutate senza danni. Male: annulla globale senza nome (A-15), perso all'import e al ripristino di una versione (A-16), conferme per azioni annullabili (A-17), la finestra dei modelli si chiude a ogni prova (A-08) | 3 |
| **Coerenza** | Due colori d'azione (blu per i primari, oro per «Correggi questo spread», selezione e maniglie); tre nomi per gli spazi; «Controlla album» = spaziature (A-12); simboli ⌘ su Linux (A-27); voci di menu che cambiano posto con l'uso (A-09); la scheda di un album danneggiato mostra il nome della cartella («Impaginatore») invece di quello dell'album | 3 |
| **Prevenzione degli errori** | Avviso ritaglio spento di serie; sostituzione che taglia ×2,28 senza avviso (A-10); PPI bassi visibili solo in fondo all'ispettore; nessun controllo su volti e piega; PSD proposto dove non si può (A-22); primo modello con pagina vuota (A-06) | 3 |
| **Riconoscere invece di ricordare** | Sostituisci, B/N, ritaglio nascosti (A-09); il ritaglio col doppio clic; Tab che nasconde i pannelli; quattro pallini senza etichetta per lo sfondo | 3 |
| **Efficienza per chi è esperto** | Bene: molte scorciatoie, ordinamento per data, etichette colore, Maiusc+clic. Male: nessun tasto per «prossima disposizione»; 3 gesti per spread anche quando le foto sono già in ordine; nessuna azione su tutto l'album tranne le spaziature | 3 |
| **Estetica e minimalismo** | 16 pulsanti da 66 × 58 px sempre visibili, metà disattivati; tre righe di filtri in Foto; ispettore lungo da scorrere anche per l'esposizione; progetto vuoto con tutti i comandi (A-28) | 3 |
| **Messaggi d'errore** | Il progetto danneggiato mostra riga e colonna del JSON (A-24); «guarda Progetti/editor.log»; «Qualcosa non è andato: guarda il riquadro»; il messaggio sul PSD arriva dopo la conferma | 3 |
| **Aiuto e documentazione** | Solo l'elenco delle scorciatoie e i suggerimenti al passaggio del mouse; nessuna guida al primo avvio; nessun esempio | 2 |

---

## 4. Accessibilità e finestre piccole

| Aspetto | Misura | Riferimento | Grav. |
|---|---|---|---|
| Tastiera | Tab è intercettato (`index.html:2148`: `preventDefault()` e mostra/nasconde i pannelli): con 25 pressioni il fuoco è rimasto sul `BODY`. Le foto sulla tela e le miniature non sono raggiungibili (0 su 39 elementi con `tabindex`) | WCAG 2.2, 2.1.1 Tastiera | 3 |
| Fuoco visibile | `:focus-visible` con contorno blu da 2 px su pulsanti, campi e menu (`index.html:215`): c'è, ma non ci si arriva con Tab | 2.4.7 | 2 |
| Nomi accessibili | 0 attributi `aria-label`, 0 `role` nell'editor; le icone hanno solo `title` | 4.1.2 | 2 |
| Contrasto | testo tenue `#98989f` su `#1b1b1d` 6,0:1, su `#333337` **4,39:1**; bianco sul blu primario `#0a84ff` **3,65:1** (sotto 4,5:1 per testo di 13 px); rosa delle misure `#ff3d7f` sulla pagina bianca **3,37:1**. Il Verde Bottega della marca col bianco fa 6,79:1 | 1.4.3, `brand/STYLEBOOK.md` §9 | 2 |
| Testo piccolo | nel CSS: 9 px ×1, 9,5 px ×3, 10 px ×9, 10,5 px ×8, 11 px ×28; le etichette della barra degli strumenti sono a 10 px | stylebook: 13 px per l'interfaccia | 2 |
| Bersagli | pallini colore 18 × 18 px (sotto il minimo di 24 × 24); 17 comandi fra 24 e 32 px nella vista Album | 2.5.8 | 2 |
| Testo ingrandito al 200 % | la tela sparisce, la pagina scorre in orizzontale (826 px di contenuto in 640), «Esporta…» fuori vista ([23](schermate/23-zoom-200.jpg)) | 1.4.4 | 3 |
| Movimento ridotto | nessuna regola `prefers-reduced-motion` in `index.html` e `home.html`; transizioni e `transform: scale(.97)` sui pulsanti, sfocatura `backdrop-filter` | 2.3.3; stylebook §15 | 1 |
| Lingua | `lang="it"` presente | 3.1.1 | — |

**Finestre piccole.** Quota della finestra occupata dallo spread (60 × 22,5 cm): **30 % a 1920 × 1080, 15,3 % a 1280 × 800, 7,9 % a 1024 × 700**. A 1024 × 700 la barra degli strumenti esce dal riquadro («Controlla album» tagliato) e i pulsanti in alto perdono le etichette (sotto 1180 px). Quando compare «⚠ 2 foto mancanti» il titolo dell'album si tronca in «Giulia …». Le schermate [07](schermate/07-album-1280x800.jpg), [08](schermate/08-album-1920x1080.jpg), [09](schermate/09-album-1024x700.jpg) mostrano le tre misure.

---

## 5. Confronto con gli strumenti creativi

Ricerche del 16/11/2026. Si confrontano categorie di funzioni, non schermate: l'obiettivo è imparare il gesto, non copiare l'aspetto.

| Categoria | Riferimento | Cosa imparare | Cosa evitare |
|---|---|---|---|
| Impaginazione automatica di un libro | Lightroom Classic, modulo Libro: si sceglie una preimpostazione e si preme «Auto Layout»; «Clear Layout» per ricominciare ([help Adobe](https://helpx.adobe.com/uk/lightroom-classic/desktop/photo-books/create-photo-book.html), pagina che risponde 403 allo strumento: testo letto dal risultato di ricerca). Utenti esperti avvertono che i due pulsanti cancellano il lavoro fatto sul libro ([forum Adobe](https://community.adobe.com/t5/lightroom-classic-discussions/lrc-auto-layout-book-module/m-p/12780480)) | una preimpostazione semplice (densità) prima del gesto; un modo esplicito di rifare | il gesto che riscrive tutto senza anteprima e senza un annulla unico. Da noi: anteprima della bozza e «Usa questa bozza» oppure «Rifalla» |
| Spazi uguali con un gesto | Figma, «Tidy up»: per una selezione usa lo spazio più frequente («the most common spacing in the selection», la moda) e lo applica in una o due dimensioni ([help Figma](https://help.figma.com/hc/en-us/articles/360039956914)) | il valore di partenza è la moda, non un numero da scrivere; il comando compare dove c'è la selezione | chiedere ogni volta di scegliere fra tre criteri prima di correggere |
| Controllo prima della stampa | Affinity Publisher 2, Preflight: controllo continuo («Live»), indicatore nella barra di stato grigio / verde / giallo / rosso, pulsante «Fix» dove si può correggere, doppio clic per andare all'oggetto; controlla fra l'altro abbondanza, immagini con DPI troppo bassi, font mancanti ([help Affinity](https://affinity.help/publisher2/en-US.lproj/pages/Publishing/preflight.html)) | un semaforo sempre visibile; ogni problema porta al punto dello spread; correzione dove è sicura | elenco tecnico in gergo di prestampa; controllo che parte solo all'esportazione |
| Annulla | pratica comune nelle app macOS: la voce del menu dice cosa annulla («Annulla Sposta»); le azioni annullabili non chiedono conferma (fonte non letta in questa sessione: la pagina delle Human Interface Guidelines non si è scaricata) | etichetta dell'azione e ritorno al punto | conferme per azioni annullabili |
| Accessibilità | WCAG 2.2 ([w3.org](https://www.w3.org/TR/WCAG22/)): 1.4.4 testo al 200 % «without loss of content or functionality»; 2.1.1 tutto da tastiera; 2.5.8 bersagli «at least 24 by 24 CSS pixels»; 2.3.3 animazioni disattivabili | i quattro requisiti misurati sopra | — |

**Per non somigliare ai concorrenti (rilievo LEG-004, `docs/mercato/competitor.md` §6.2).** La «story-first timeline» con i tagli tra le foto e la «Designer View» col doppio clic di SmartAlbums, le «Drop Zones» di Fundy e la galleria dei modelli scelti per numero di foto sono i tratti più riconoscibili. Nell'editor di oggi ci sono la galleria per numero di foto (`index.html:1958`, commento «come la scelta dei template di Smart Albums») e la schermata dei progetti a schede (`home/server.py`, riga 1: «come quella di Smart Albums»), oltre al nome «Rearrange» nel commento di `tpl_options` (`editor/server.py:862`). Nomi da non usare: Auto-Build, Smart…, Designer View, Cloud Proofing, Drop Zones, Album Builder, Design Wizard, Design For Me; DigiAlbum usa «Un'altra» e «Variante» per le alternative di uno spread, quindi anche quei nomi vanno evitati. La direzione della marca (stylebook §17) indica la strada nostra: scaffale degli album in lista con misure e stato, provini numerati con le quote, segni di piega, abbondanza tratteggiata, numerazione «07–08» in carattere mono, Verde Bottega come unico accento.

---

## 6. Sintesi

I cinque problemi più gravi:

1. **I file «Stampa · 300 dpi» non sono da stampa** (A-18, gravità 4): JPG e PDF vengono dalle miniature da 1200 px e perdono l'abbondanza. È il punto in cui il prodotto può far perdere un cliente al fotografo.
2. **Attesa cieca all'apertura e all'import** (A-03, A-16, gravità 4): 0,65 s per foto prima di poter fare qualunque cosa, e un riavvio che cancella la cronologia d'annulla.
3. **Le azioni che il fotografo ripete di più costano troppi gesti** (A-08, A-09, A-10): cambiare disposizione, sostituire, ritagliare. Il motore ha già tutto (modelli in 0,07 s), l'interfaccia lo nasconde.
4. **Nessun controllo di contenuto prima della consegna** (A-12, A-20): «Controlla album» guarda solo gli spazi; volti, piega, PPI, testi restano all'occhio dell'utente, mentre `anteprima.py` sa già controllare piega, ritagli forti e spazi.
5. **Spazio e attenzione rubati alla foto** (A-07, A-33, A-34): 15 % della finestra per lo spread a 1280 × 800, due file di pulsanti, tastiera bloccata dal Tab.

Difetti trovati durante l'analisi, da passare alla correzione dei bug indipendentemente dal ridisegno: A-23 (Ricollega nella cache), A-26 (messaggio di salvataggio sbagliato), A-01 (nome vuoto per la cartella «JPG»), A-30 (menu che resta aperto), A-11 (badge sopra il velo), A-13 (pannello Tono che taglia lo spread), A-14 (nomi del carattere discordanti), A-32 (pagina non aggiornata dopo modifiche via API).
