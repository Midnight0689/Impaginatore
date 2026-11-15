# Stile di impaginazione di Stefano

Imparato impaginando il Battesimo di Anita (ottobre 2026), dopo cinque versioni e molte correzioni di Stefano e dei clienti.
Le correzioni di Stefano sono la parte più preziosa: spiegano dove una bozza "da grafico alle prime armi" diventa professionale.

## Le regole che Stefano non vuole vedere violate

1. **Spazio identico ovunque.** Un solo spazio tra le foto (2,5 mm a 300 ppi = 30 px), uguale in orizzontale, in verticale
   e anche sulla piega. Ha notato a occhio uno spazio più largo di 1 mm alla piega: "sta cosa devi evitare".
   Per questo la griglia mette le linee su pixel interi e le pagine immersive si fermano mezzo spazio prima della piega.
2. **Nessuna foto a cavallo della piega.** Ogni pagina si compone da sola. Si perde il "panorama", ma Stefano non lo vuole.
3. **Mai tagliare le persone.** Teste, mani, piedi, la mamma ai bordi di una foto di gruppo: controllare ogni ritaglio
   guardando la finestra di ritaglio sull'originale (analizza.py ritagli). Il riconoscimento volti sbaglia spesso
   (prende per volto una panchina, un'amaca, non vede chi è di profilo): in quei casi si fissa il centro a mano in
   "centri_volto". Se una foto orizzontale di gruppo non entra in una cornice verticale senza tagliare qualcuno, va
   cambiato il modulo, non il ritaglio.
4. **Misura esatta del formato, senza abbondanza, salvo diversa indicazione.** Il formato si chiede, l'abbondanza pure
   (o la mette il laboratorio). Aver aggiunto 3 mm per lato senza dirlo chiaramente ha fatto infuriare Stefano.
   Con "dimensioni_esatte" i pixel hanno il rapporto esatto del formato e i ppi si aggiustano di pochissimo
   (60 x 22,5 cm -> 7088 x 2658 px a 300,06 ppi): Photoshop mostra 60,00 x 22,50.
5. **Mai rigenerare un PSD che Stefano ha sistemato a mano.** Si modifica quel PSD (modifica_psd.py), con copia di sicurezza.

## Composizione

- **Griglia 12 x 8 per pagina** e pochi moduli che si ripetono: coerenza = professionalità.
  Moduli: FULL (al vivo), DUO (2 verticali), VLL (1 verticale + 2 orizzontali), V4 (1 verticale grande + 4 piccole),
  G4 (4 orizzontali), CV (1 verticale centrata sul bianco), SV (verticale piccola, "un sussurro"), PP (orizzontale con
  passe-partout), STRIP3 (3 verticali in fascia), COL2, BAND2.
- **Due tipi di pagina**: immersiva (la griglia arriva al bordo, look "flush" degli album fine art) e bianca
  (margine uguale sui 4 lati). L'emozione nasce dall'alternanza tra pieno e vuoto: dopo pagine piene, una pagina bianca
  con una sola foto. Dopo una pagina bianca, un volto a tutta pagina.
- **Gli spread si parlano**: il sorriso del fratello sul bianco accanto a papà e bimba fronte a fronte; il rumore della
  festa accanto a un bacio in bianco e nero. Accostare per sguardi, gesti, luce, non solo per orario.
- **Una foto protagonista per spread**, le altre di supporto. Più foto piccole = racconto veloce; una sola = pausa.
- **Bianco e nero come accento**, a coppie o per una pausa intima; mai a caso. Il BN segue la cornice, non la foto.
- **Capitoli** in ordine cronologico (es. servizio esterno -> casa -> chiesa -> festa), ognuno con un'apertura.
- **Climax sul rito**: due pagine intere (es. la mano sulla fronte / l'acqua in BN), preceduto da uno spread lento.
- **Chiusura dedicata alla bambina/sposi**: le foto più belle del soggetto, l'ultima pagina con la firma.
- **Primo piano su una foto quasi doppia** (z = 1,3–1,8 sui volti) per non ripetere la stessa inquadratura accanto.
- **Foto di gruppo**: le grandi (orizzontali) insieme in G4; le piccole verticali insieme, separate. Sono "le più belle"
  per i clienti: devono essere grandi abbastanza da riconoscere tutti.
- **Copertina**: spesso è una foto che sta anche nell'album; se la si toglie dall'album, ricomporre lo spread.
- Titolo: nome in serif corsivo (Bodoni Moda Italic), sottotitolo e data in maiuscoletto spaziato (Avenir Next), colore
  inchiostro caldo (58, 54, 51). Niente cornici, ombre, decorazioni.

## Cosa NON ha funzionato (non rifarlo)

- v1: spaziatura irregolare e foto sulla piega -> "sembra fatta da un grafico alle prime armi".
- v2: griglia corretta ma tutte le pagine uguali -> "hai fatto il compitino".
- v3: più varia ma senza un'idea -> salvata come "buona" ma "voglio che tu sia più creativo".
- v4: capitoli con titoletti scritti -> "non mi piace, ricomincia, voglio qualcosa di emozionante".
- v5: pagine immersive + bianche, spread che si parlano, climax e finale -> la direzione giusta.
  Da lì in poi solo correzioni puntuali (ritagli, scambi, colore, luminosità).

## Luminosità e colore per la stampa

- In stampa tutto esce più scuro dello schermo: Stefano ha chiesto due volte "più luminose".
  Base usata: +0,25 EV su tutto l'album.
- Uniformare per capitolo: un servizio esterno all'ombra era ~mezzo stop più scuro (pelle L* 51 contro 58): +0,4 EV
  su tutta la cartella, poi correzioni singole (+0,2 / +0,5) sulle foto fuori tono e piccole riduzioni su quelle già chiare.
- Misurare la pelle sui volti (L*), non la media dell'immagine. Mostrare sempre un prima/dopo prima di applicare.
- Dettagli/allestimenti con dominanti diverse nella stessa pagina (scatolina fredda, lecca-lecca rosati): bilanciamento
  del bianco con guadagni lineari all'80% della correzione piena, neutro appena caldo; lasciare un po' fredda la luce
  del tramonto (neutralizzarla del tutto la appiattisce).
- Le correzioni vanno in livelli agganciati e modificabili (Esposizione, Miscelatore canale "Bilanciamento bianco"),
  così Stefano le ritocca a occhio. In alternativa si fanno in Lightroom e si riesporta.
