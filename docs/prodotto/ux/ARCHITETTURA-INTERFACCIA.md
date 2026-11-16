# Architettura dell'interfaccia 2.0 (T-209)

Come si dispone l'interfaccia ridisegnata: zone, barre, pannello contestuale, menu, scorciatoie, regola dei clic. È la base per T-205 e mette insieme le proposte di [`PROPOSTE.md`](PROPOSTE.md). Gli schemi sono a blocchi, nel tema scuro predefinito, con i token di `brand/tokens.css`; sono a 1280 × 800, la finestra di riferimento dell'analisi.

| Schema | Cosa mostra |
|---|---|
| [`schemi/primo-avvio.svg`](schemi/primo-avvio.svg) | primo avvio con la prova già attiva |
| [`schemi/album.svg`](schemi/album.svg) | schermata «Album» a scaffale |
| [`schemi/editor.svg`](schemi/editor.svg) | editor, vista Impagina, una foto selezionata |
| [`schemi/editor-sistema.svg`](schemi/editor-sistema.svg) | editor con il pannello Controlla e il riepilogo di «Sistema» |
| [`schemi/consegna.svg`](schemi/consegna.svg) | finestra Consegna, con lo stato durante e dopo |

Gli schemi sono stati resi con Chrome senza schermo e guardati uno per uno; nessun testo si sovrappone. I nomi delle foto e dei clienti sono inventati.

## Principi

1. **La foto al centro.** Lo spread è largo 2,67 volte l'altezza (60 × 22,5 cm): lo spazio che conta è quello orizzontale. I pannelli laterali sono stretti, le foto da usare stanno sotto, e la tela si allarga a tutta la finestra con un tasto.
2. **Un solo pulsante primario per schermata.** Nell'editor è «Consegna…». Tutto il resto è secondario o sta nei menu.
3. **I comandi stanno dove sta l'oggetto.** Una barra compare sotto la foto selezionata con le quattro azioni più frequenti; il pannello di destra cambia con la selezione. I menu dell'applicazione hanno tutto, con le scorciatoie scritte accanto.
4. **Tutto si annulla, niente conferme.** Le azioni annullabili non chiedono conferma e dicono cosa hanno fatto; quelle che cambiano tutto l'album mostrano prima l'anteprima, poi si annullano con un passo solo.
5. **Le parole del fotografo.** Pagina piena, pagina bianca, primo piano, piega, abbondanza, laboratorio, bozza, consegna. Nessun gergo tecnico in vista (L*, JSON, `spec.py`), nessun nome preso dai concorrenti.
6. **Numeri in mono, accanto alle cose.** Misure, ppi, numeri degli spread («07–08») in IBM Plex Mono a cifre tabellari, come chiede il manuale (stylebook §17).

## Schermate

### Primo avvio

Una schermata sola, senza moduli ([schema](schemi/primo-avvio.svg)): area grande per trascinare la cartella, «Scegli la cartella…», la frase sulla prova e quella sulle foto che restano sul computer, «Ho una chiave» in alto a destra. Dopo il primo album la schermata diventa «Album». Dettagli in UX-015 e UX-017.

### Album

Elenco a scaffale ([schema](schemi/album.svg)), al posto delle schede di oggi.

| Zona | Contenuto |
|---|---|
| Barra (52 px) | marchio; ricerca (compare oltre i 12 album); «Nuovo album…» secondario |
| Area per trascinare (76 px) | «Trascina qui la cartella delle foto per un album nuovo» e la frase sulle foto che restano dove sono |
| Elenco | una riga da 80 px per album: miniatura del primo spread, nome (Newsreader), cartella, formato, spread, foto, stato, ultima modifica. Al passaggio del mouse: «Apri» e «⋯» (Mostra nella cartella, Duplica, Togli dall'elenco). Doppio clic o Invio apre |
| Stato dell'album | In lavorazione · Inviato al cliente il … · Consegnato il … (dalle versioni con nome, UX-020) · Senza foto · Non si apre (con «Ripristina la copia delle …», UX-005) |
| Riga in basso (40 px) | solo negli ultimi 7 giorni di prova: «Prova: restano 5 giorni · Compra una chiave»; numero di album |

Trascinare una cartella su una riga aggiunge le foto a quell'album. Un album si apre nella stessa finestra; «‹ Album» torna qui.

### Editor, vista Impagina

([schema](schemi/editor.svg))

| Zona | Misura a 1280 × 800 | Contenuto |
|---|---|---|
| Barra in alto | 44 px | vedi «Barra in alto» |
| Colonna degli spread | 136 px | «Copertina», poi «01–02», «03–04»… in mono con la miniatura; spread corrente contornato; trascinare per riordinare; «+» per uno spread vuoto. Tasto destro: Duplica, Elimina, Sposta, Consegna solo questo |
| Barra dello spread | 36 px | numero «07–08», tipo di pagina per lato («Sinistra: Piena · Destra: Bianca»), «Altra disposizione  D», «Testo  T», zoom «Adatta ▾» |
| Tela | il resto | spread con segni di piega sopra e sotto, abbondanza tratteggiata in cinabro tenue, quote in mono accanto alla selezione. Spread a vista intera: 824 × 309 px, il 24,9 % della finestra (oggi 15,3 %) |
| Barra della selezione | 34 px, sotto lo spread | compare con una selezione, vedi più sotto |
| Cassetto delle foto | 160 px, sotto la tela | filtro in una riga («Da usare 38 · Tutte 100 · ★ 12 · Colore»), «Aggiungi foto…», miniature in ordine di scatto. Si trascina su una cornice per sostituire, fra due spread per crearne uno, sulla tela vuota per un nuovo spread. Si chiude con un tasto e si allarga trascinando il bordo |
| Pannello di destra | 272 px | contestuale, vedi «Pannello contestuale» |

### Editor, vista Foto

Serve a scegliere: preferite, tolte, etichette, e a creare spread dalle foto scelte. Non ha schema: la struttura è quella di oggi, semplificata.

| Zona | Contenuto |
|---|---|
| Griglia | miniature grandi, in ordine di scatto; filtro in una riga, «Da usare» predefinito; ordinamento e grandezza in «⋯» |
| Colonna di destra | senza selezione: «Prepara la bozza» (Pro, Studio, prova) e «Comincia a mano»; con foto scelte: «Per queste 4 foto» con le disposizioni come provini numerati e «Dove: dopo lo spread 07–08 ▾». Un clic crea lo spread **e apre la vista Impagina su quello spread** (A-05) |

### Editor con «Controlla» e «Sistema»

([schema](schemi/editor-sistema.svg)) L'indicatore nella barra in alto apre il pannello Controlla al posto di quello contestuale, largo 336 px. In cima il riepilogo di quello che si sistema da solo, con «Sistema 9» e «Cosa cambia» (che mostra prima e dopo sullo spread). Sotto, i gruppi «Blocca la stampa», «Da guardare», «Si sistemano da soli», «Per sapere», ognuno con «Vai». Sullo spread il problema è contornato in ocra con una pillola che lo nomina. Dopo «Sistema», un avviso: «Sistemato: spazi in 4 spread, tono di 5 foto. · Annulla». Dettagli in UX-014.

### Consegna

([schema](schemi/consegna.svg)) Un foglio sopra l'editor, non una finestra separata: si chiude con Esc e lo spread resta sotto.

| Parte | Contenuto |
|---|---|
| Testa | «Consegna», album, spread, formato |
| Stato del controllo | una riga: «Pronto per la stampa. 1 da guardare: …» con «Vai» (chiude il foglio e porta allo spread). Se c'è un problema che blocca, il pulsante primario resta spento con il motivo |
| Destinazioni | tre riquadri: Al laboratorio, Al cliente, A Photoshop. Quello non disponibile è tratteggiato con il motivo scritto (Linux, fascia Essenziale). È scelta l'ultima destinazione usata per quell'album |
| Dettagli | cambiano con la destinazione: laboratorio e formato file; spread (tutti o una scelta); esposizione per la stampa (impostazione dell'album); cartella |
| Piede | frase su dove finiscono i file; «Annulla»; primario «Consegna 35 spread» |
| Durante | il foglio si chiude; nella barra in alto «Spread 12 di 35 · circa 14 s · Ferma» e si continua a lavorare |
| Dopo | «35 spread pronti in Esportazioni/Laboratorio · Mostra»; versione salvata con nome |

## Barra in alto

Da sinistra a destra (44 px):

| Elemento | Comportamento |
|---|---|
| «‹ Album» | torna alla schermata Album; l'album è già salvato |
| Nome dell'album (Newsreader) e «60 × 22,5 cm · 35 spread» (mono, tenue) | clic sul nome: rinomina sul posto. Clic sul formato: foglio Formato e abbondanza. Il nome non si tronca prima di 24 caratteri |
| Foto · Impagina | selettore delle due viste (⌘1, ⌘2) |
| «Salvato alle 10:42» | testo, non pulsante. Mentre salva: «Salvo…» solo oltre 0,4 s. Se non riesce: riga rossa fissa (vedi PROPOSTE, «Salvataggio visibile»). Durante la preparazione delle foto o una consegna diventa l'avanzamento: «Preparo le foto · 34 di 100» |
| Indicatore del controllo | pillola con pallino: grigio «Controllo…», verde «Pronto», ocra «3 da controllare», cinabro «1 blocca la stampa». Clic: pannello Controlla |
| Foto mancanti | non è più un elemento a parte: le foto mancanti sono nel controllo, in «Blocca la stampa» |
| «Consegna…» | unico pulsante primario (Verde Bottega). ⌘E |

Spariscono dalla barra: Annulla e Ripeti (menu Modifica e tasti; l'etichetta dell'azione è nel menu), Modelli (pannello di destra e D), Salva, Progetto, Versioni (menu File), scorciatoie (menu Aiuto e ?), sfondo della tela e pannelli (menu Vista).

## Barra della selezione

Compare sotto lo spread, allineata alla selezione, e non copre mai la foto selezionata.

| Selezione | Comandi | «⋯» |
|---|---|---|
| Una foto | Sostituisci · Altra disposizione · Ritaglia · B/N | Primo piano, Tutta pagina, Proporzioni originali, Preferita, Togli dallo spread, Disponi ▸, Ritocco ▸, Mostra nella cartella |
| Più foto | Stessa misura · Allinea ▾ · Altra disposizione | Disponi ▸, Togli dallo spread |
| Un testo | carattere ▾ · corpo · allineamento · colore | Stile ▸, Elimina |
| Nessuna | la barra non c'è; la barra dello spread basta | — |

## Pannello contestuale

Il pannello di destra mostra una cosa sola, scelta dalla selezione. Il titolo dice cosa.

| Quando | Titolo e contenuto |
|---|---|
| Nessuna selezione | **Spread 07–08**: tipo di pagina per lato (Piena / Bianca), sfondo della pagina; sotto, **Altre disposizioni** come provini numerati (UX-021) |
| Una foto | **Foto selezionata**: nome, misura in cm e ppi effettivi (verdi sopra 200, ocra 150–200, cinabro sotto 150), Primo piano, Esposizione, Bianco e nero; chiusi: Luce, Colore, Altro (angolo, opacità, bordo, ombra). Sotto, **Altre disposizioni** |
| Più foto | **3 foto selezionate**: allineamento, stessa misura, spazio fra le foto con il valore in mono |
| Un testo | **Testo**: stile, carattere (scelta breve OFL in cima), corpo, interlinea, spaziatura, colore |
| Indicatore del controllo | **Controlla** (336 px, UX-014) |

Sotto i 1280 px di larghezza il pannello diventa un foglio che entra da destra sopra la tela e si chiude con Esc. Con la tela piena (F) non c'è.

## Menu dell'applicazione

Menu nativi della finestra desktop. Su macOS il primo menu ha il nome del programma; su Windows e Linux le sue voci vanno in File (Impostazioni, Esci) e in Aiuto (Informazioni, Licenza). Le voci riprendono i comandi dell'interfaccia, così ogni funzione si trova anche senza conoscere il tasto destro.

| Menu | Voci |
|---|---|
| Impaginatore | Informazioni su Impaginatore · Licenza… · Impostazioni… · Esci |
| File | Nuovo album… · Apri album… · Album recenti ▸ · Chiudi album · — · Aggiungi foto… · Ricollega le foto… · — · Salva una versione… · Versioni… · Mostra nella cartella · — · Esporta l'album in un archivio… · Importa un archivio… |
| Modifica | Annulla «Elimina spread 07–08» · Ripeti · — · Taglia · Copia · Incolla · Elimina · Seleziona tutto · — · Copia il ritocco · Incolla il ritocco |
| Album | Prepara la bozza… · — · Nuovo spread · Duplica spread · Elimina spread · Sposta prima · Sposta dopo · — · Altra disposizione · Disposizione precedente · Inverti le pagine · — · Copertina… · Formato e abbondanza… · — · Controlla · Sistema… |
| Foto | Sostituisci… · Sposta nella cornice · Primo piano · Bianco e nero · — · Preferita · Tolta · Etichetta ▸ · — · Uniforma il tono dello spread · Disponi ▸ |
| Vista | Foto · Impagina · — · Tela piena · Adatta lo spread · Ingrandisci · Riduci · — · Righelli · Guide · Magnete · Blocca le guide · — · Sfondo della tela ▸ · Tema ▸ (Sistema, Scuro, Chiaro) |
| Consegna | Consegna… · Ripeti l'ultima consegna · — · Al laboratorio… · Al cliente… · A Photoshop… |
| Aiuto | Guida rapida · Scorciatoie da tastiera · — · Salva la diagnostica… · Scrivi all'assistenza · Cerca aggiornamenti |

## Scorciatoie

Sono scritte con i simboli del sistema: ⌘ ⇧ ⌥ su macOS, Ctrl Maiusc Alt su Windows e Linux (oggi sono solo con i simboli Mac, A-27). I tasti senza modificatori valgono solo quando il fuoco non è in un campo di testo, come oggi.

| Azione | macOS | Windows, Linux | Oggi |
|---|---|---|---|
| Altra disposizione / precedente | D / ⇧D | D / Maiusc+D | — (M apre la galleria) |
| Altre disposizioni nel pannello | M | M | M apre la galleria sopra la tela |
| Sostituisci | S | S | — |
| Sposta nella cornice / esci | Invio / Esc | Invio / Esc | doppio clic |
| Bianco e nero | B | B | — |
| Testo | T | T | T |
| Preferita, Tolta, Etichette | P, X, 1–7, 0 | P, X, 1–7, 0 | uguali |
| Anteprima grande | Z, Spazio | Z, Spazio | uguali |
| Spread precedente / successivo | ↑ ↓, Pag↑ Pag↓ | ↑ ↓, Pag↑ Pag↓ | ↑ ↓ |
| Sposta la selezione di 0,01 / 0,1 cm | frecce / ⇧ frecce | frecce / Maiusc+frecce | uguali |
| Livelli | [ ] { } + − | [ ] { } + − | uguali |
| Tela piena (nasconde i pannelli) | F | F | Tab |
| Fuoco al comando successivo / precedente | Tab / ⇧Tab | Tab / Maiusc+Tab | intercettato (A-34) |
| Controlla | C | C | — |
| Consegna… / ripeti l'ultima | ⌘E / ⇧⌘E | Ctrl+E / Ctrl+Maiusc+E | — |
| Vista Foto / Impagina | ⌘1 / ⌘2 | Ctrl+1 / Ctrl+2 | — |
| Adatta / ingrandisci / riduci | ⌘0 / ⌘+ / ⌘− | Ctrl+0 / Ctrl++ / Ctrl+− | Alt+rotella, pizzico |
| Duplica spread | ⌘D | Ctrl+D | uguale |
| Annulla / Ripeti | ⌘Z / ⇧⌘Z | Ctrl+Z / Ctrl+Y e Ctrl+Maiusc+Z | ⌘Z / ⇧⌘Z |
| Salva una versione | ⇧⌘S (⌘S risponde «Salvato») | Ctrl+Maiusc+S | ⌘S salva |
| Elenco delle scorciatoie | ? | ? | ? |

Le lettere D, S, B, C, F oggi sono libere nell'editor (verificato nel gestore dei tasti, `index.html:2119–2158`); ⌘D resta «Duplica spread».

## Un clic o due

Regola: **un clic** per ogni azione che si annulla e tocca uno spread; **due tempi** (foglio con anteprima, poi conferma con il numero) per le azioni che cambiano tutto l'album o scrivono file; **conferma vera** solo per ciò che non si annulla.

| Azione | Clic oggi | Proposta | Perché |
|---|---|---|---|
| Altra disposizione | 3–5 per prova | 1 (D) | annullabile, sul posto |
| Sostituisci e riadatta | 4 + scelta | 1 trascinamento o 2 clic | annullabile, la pillola offre «Tieni la cornice di prima» |
| Bianco e nero | 3 (menu › Tutti i comandi › voce) o scorrere l'ispettore | 1 (B/N nella barra) | annullabile |
| Elimina spread | 2 con `confirm()` | 1 + avviso «Annulla» | annullabile |
| Spazi uguali in uno spread | 3–4 | 1 («Sistema» sulla riga del controllo) | annullabile |
| Tono dello spread | 4+ per foto, a mano | 1 («Uniforma») | annullabile |
| Prepara la bozza | non esiste | 2: foglio con anteprima, «Usa questa bozza» | cambia tutto l'album: va vista prima |
| Sistema tutto l'album | non esiste | 2: riepilogo con i numeri, «Sistema 9» | come sopra |
| Consegna | 2 (JPG), 3 con conferma (PSD) | 2: foglio, «Consegna 35 spread» | scrive file: si vede cosa e dove |
| Tornare a una versione | 2 + riavvio | 2 + «Annulla» | si annulla |
| Ricollega le foto | 1 + finestra di sistema | 2: proposta con l'elenco, «Usa questi file» | tocca i collegamenti di più foto |
| Eliminare un modello personale | 2 con `confirm()` | 1 + avviso «Annulla» per 30 s | diventa annullabile |
| Sostituire PSD ritoccati a mano | spunta + conferma | spunta + conferma vera | non si annulla: si perde il ritocco |
| Chiudere durante una consegna | — | conferma vera | si perdono i file a metà |

Le conferme vere sono fogli dentro la finestra con il verbo sul pulsante («Sostituisci 3 PSD ritoccati»), mai `confirm()`.

## Finestra desktop (pywebview)

Vincoli per T-201, letti da `docs/architettura/ARCHITETTURA.md` (§ finestra desktop: home e editor restano server locali; la finestra punta al loro indirizzo; i dialoghi passano da `dialoghi.imposta`). Nulla di questo è stato provato: la finestra non esiste ancora.

| Tema | Indicazione | Da verificare in T-201 |
|---|---|---|
| Una finestra | Album ed editor nella stessa finestra; «‹ Album» naviga. L'editor resta un processo separato | che il cambio di indirizzo non faccia lampeggiare la finestra |
| Misura minima | 1024 × 700; la misura e la posizione si ricordano | — |
| Menu | menu nativi della tabella sopra, con le scorciatoie; la pagina riceve il comando come se fosse un tasto | supporto dei menu dell'applicazione in pywebview su macOS, Windows e GTK |
| Finestre di sistema | per cartelle e file si usano quelle native (`dialoghi.imposta`); lo sfoglia file interno sparisce | — |
| Trascinare una cartella | il percorso completo serve a `home.nuovo()` | che pywebview dia il percorso completo degli elementi trascinati (in un browser normale non si può) su tutti e tre i sistemi |
| Conferme | niente `confirm()`, `alert()`, `prompt()`: fogli nella pagina | comportamento di `confirm()` nella vista web di ciascun sistema, se ne resta qualcuno |
| Chiusura | chiudere la finestra con una consegna in corso chiede conferma; altrimenti chiude e basta (l'album è salvato) | — |
| Schermi ad alta densità | spread disegnato alla densità dello schermo | nitidezza delle anteprime su schermi Retina e Windows al 150 % |

## Italiano e inglese

- Tutti i testi passano dal sistema di traduzione (T-206); questo documento usa i testi italiani.
- L'italiano è in genere più lungo dell'inglese: le misure si fissano sui testi italiani, con un margine del 30 % per lingue future. I pulsanti hanno larghezza libera, non fissa; nessun testo dentro un'icona.
- Nomi inglesi da evitare perché già usati dai concorrenti: «Rearrange», «Auto-Build», «Smart…», «Designer View», «Drop Zones», «Album Builder», «Design Wizard», «Design For Me», «Cloud Proofing». Proposta di glossario, da confermare con T-206: Altra disposizione = *Next layout*; Altre disposizioni = *Other layouts*; Prepara la bozza = *Draft the album*; Controlla = *Check*; Sistema = *Fix*; Consegna = *Deliver*; Al laboratorio = *To the lab*; Al cliente = *To the client*; Pagina piena = *Full-bleed page*; Pagina bianca = *White page*; Primo piano = *Close-up*; Tela piena = *Full canvas*.
- Numeri e misure con le regole della lingua: «2,5 mm» e «0,25 EV» in italiano, «2.5 mm» in inglese. Nei mercati di lingua inglese i laboratori vendono anche formati in pollici (12 × 12 in): il pacchetto del laboratorio (T-208) deve poter dichiarare l'unità, e l'interfaccia mostrarla.

## Tema scuro e chiaro

- I colori vengono solo dai token `--imp-app-*` (tela, pannello, barra, sollevato, bordo, testo, testo tenue, selezione, accento) e dai semantici (successo, attenzione, errore, info). Nessun colore scritto a mano nell'editor.
- Scuro predefinito, chiaro disponibile (Vista › Tema). La tela resta grigia neutra (croma zero) in tutti e due: la foto non deve prendere colore dall'interfaccia.
- Selezione: contorno 1,5 px bianco nel tema scuro, inchiostro nel chiaro, con maniglie quadrate. Il Verde Bottega è riservato al pulsante primario, al fuoco e alle misure giuste. Le misure usano i semantici: uguale = successo, da controllare = attenzione, errore = errore; il rosa di oggi sparisce.
- Gli schemi sono nel tema scuro; il tema chiaro è lo stesso schema con i token chiari. Prima di T-205 vanno misurati i contrasti delle coppie nuove (testo tenue su pannello, testo sul primario) con lo strumento del manuale (stylebook §9).

## Accessibilità

- Ordine del fuoco: barra in alto → colonna degli spread → barra dello spread → tela (Tab da una cornice all'altra, Invio per selezionare) → barra della selezione → pannello di destra → cassetto delle foto.
- Ogni icona ha un nome accessibile; i pannelli sono regioni con un titolo; gli avvisi passano da una regione `status`.
- Bersagli di almeno 24 × 24 px; testo dell'interfaccia 13 px, numeri 12 px, mai sotto 12.
- Movimento ridotto: transizioni a zero, nessuna sfocatura.
- Al 200 %: il pannello di destra e il cassetto diventano fogli; la colonna degli spread mostra solo i numeri; la tela resta visibile.
