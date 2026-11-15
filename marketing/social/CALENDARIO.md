# Calendario social, 12 settimane intorno al lancio

> File generato da `strumenti/componi_testi.py` a partire da `sorgenti/uscite.txt`: non si modifica a mano.
> Prezzi dal listino `2026-11-15d` (`docs/mercato/tier.json`), date e link da `strumenti/costanti.json`.

Da martedì 2 febbraio 2027 a venerdì 23 aprile 2027: da tre settimane prima del lancio (S-3) alla fine del prezzo di lancio (S8), con le settimane di `marketing/lancio/PIANO-90-GIORNI.md`. 49 uscite con data, tutte con il testo completo in italiano; 10 anche in inglese (le più importanti). In fondo, 3 uscite di riserva sulla bozza con Claude, da pubblicare solo dopo il rilascio del server MCP.

Come si legge: ogni uscita ha un ID stabile (U01…), il canale, il formato, il pilastro, il modello grafico in `modelli/` e il PNG da caricare in `grafiche/` (si rigenera con `strumenti/genera_grafiche.py`). Il testo nel riquadro si copia così com’è, hashtag compresi. Su Instagram i link non sono cliccabili: il testo dice «link nella bio» e il campo «Link» dice quale link mettere nella bio quel giorno.

Regole del calendario: nessuna uscita di sabato, a Pasqua e Pasquetta (28 e 29 marzo) e il 25 aprile; di solito alle 9:00, alle 12:30 o alle 18:00 (il giorno del lancio si segue l’ora dell’email); un post per canale al giorno, più eventuali storie, salvo il giorno del lancio.

Segnaposto ancora vuoti, da riempire in `strumenti/costanti.json` prima di pubblicare: `{{link_lista}}`, `{{link_laboratori}}`, `{{link_prova}}`, `{{link_installa}}`, `{{link_manuale}}`, `{{email_supporto}}`, `{{link_prezzi}}`, `{{caso.nome}}`, `{{caso.citazione}}`, `{{caso.dato}}`, `{{webinar.laboratorio}}`, `{{webinar.data}}`, `{{prezzo_rosetta_pro}}`, `{{prezzo_rosetta_studio}}`, `{{link_rosetta}}`, `{{educator.nome}}`, `{{educator.canale}}`, `{{link_guida_claude}}`, `{{link_assistenza}}`.

## Riepilogo

| Data | Giorno | Ora | Sett. | ID | Canale | Formato | Pilastro | Titolo | EN |
|---|---|---|---|---|---|---|---|---|---|
| 02/02 | martedì | 12:30 | S-3 | U01 | Instagram | post 4:5 | Bottega | Perché esiste Impaginatore |  |
| 03/02 | mercoledì | 18:00 | S-3 | U03 | Instagram | storia con sondaggio | Mestiere | Sondaggio: dove impagini |  |
| 04/02 | giovedì | 12:30 | S-3 | U02 | Instagram | carosello 5 pagine 4:5 | Le foto restano tue | Tre promesse | sì |
| 05/02 | venerdì | 09:00 | S-3 | U04 | LinkedIn (profilo del titolare) | post con immagine 4:5 | Bottega | Da strumento personale a prodotto |  |
| 08/02 | lunedì | 09:00 | S-2 | U05 | Instagram e Facebook | post 1:1 | Resta tuo | La data | sì |
| 10/02 | mercoledì | 12:30 | S-2 | U06 | Instagram | reel 9:16, 30 s (copione V1) | Le foto restano tue | Stacco il wi-fi ed esporto l’album |  |
| 11/02 | giovedì | 12:30 | S-2 | U07 | Instagram | post 4:5 | Mestiere | Consiglio di bottega 01: la piega |  |
| 12/02 | venerdì | 09:00 | S-2 | U08 | LinkedIn (pagina Impaginatore) | post con immagine 1,91:1 | Mestiere | Per i laboratori di stampa |  |
| 12/02 | venerdì | 12:30 | S-2 | U09 | Facebook (pagina) | post 1:1 | Le foto restano tue | La data, su Facebook |  |
| 15/02 | lunedì | 12:30 | S-1 | U10 | Instagram | post 4:5 | Resta tuo | Fare i conti su tre anni | sì |
| 17/02 | mercoledì | 12:30 | S-1 | U11 | Instagram | post 4:5 | Mestiere | Gli stessi spazi su tutto l’album |  |
| 18/02 | giovedì | 18:00 | S-1 | U12 | Instagram | storia, 2 schermate di testo | Bottega | Versione congelata |  |
| 19/02 | venerdì | 09:00 | S-1 | U13 | LinkedIn (profilo del titolare) | post con immagine 4:5 | Resta tuo | Licenza perpetua, nel 2027 |  |
| 21/02 | domenica | 09:00 | S-1 | U14 | Instagram e Facebook | storia 9:16 | Resta tuo | Accesso anticipato | sì |
| 23/02 | martedì | 09:00 | S0 | U15 | Instagram | post 4:5 | Resta tuo | Impaginatore è pronto | sì |
| 23/02 | martedì | 09:05 | S0 | U16 | Instagram e Facebook | storia 9:16 | Resta tuo | Lancio, storia |  |
| 23/02 | martedì | 09:30 | S0 | U17 | LinkedIn (profilo del titolare e pagina Impaginatore) | post con immagine 4:5 | Bottega | Lancio su LinkedIn | sì |
| 23/02 | martedì | 10:00 | S0 | U18 | YouTube | video 16:9, 3–5 min (guida all’installazione) | Assistenza e prova | Come si installa Impaginatore (Mac, Windows, Linux) |  |
| 23/02 | martedì | 12:00 | S0 | U19 | Facebook (pagina) | post 4:5 | Resta tuo | Lancio su Facebook |  |
| 24/02 | mercoledì | 10:00 | S0 | U20 | Instagram | storia 9:16, foto dallo stand | Bottega | Convention ANFM, giorno 1 |  |
| 25/02 | giovedì | 12:30 | S0 | U21 | Instagram | reel 9:16, 40 s (copione V3) | Mestiere | Dalla cartella alla bozza |  |
| 26/02 | venerdì | 12:30 | S0 | U22 | Instagram | post 4:5 | Resta tuo | Quale licenza scegliere |  |
| 02/03 | martedì | 12:30 | S1 | U23 | Instagram | post 4:5 | Assistenza e prova | Un’ora con una persona | sì |
| 03/03 | mercoledì | 12:30 | S1 | U24 | Instagram | carosello 4 pagine 4:5 | Mestiere | Le misure del laboratorio, una volta sola |  |
| 04/03 | giovedì | 18:00 | S1 | U25 | YouTube Shorts e Instagram | short/reel 9:16, 25 s (copione V2) | Assistenza e prova | Una riga per installarlo |  |
| 05/03 | venerdì | 09:00 | S1 | U26 | LinkedIn (profilo del titolare) | post di solo testo | Bottega | Una chiave senza server |  |
| 09/03 | martedì | 12:30 | S2 | U27 | Instagram | carosello 4:5 | Mestiere | Caso di studio di un beta tester |  |
| 10/03 | mercoledì | 12:30 | S2 | U28 | Instagram | post 4:5 | Mestiere | Consiglio di bottega 02: l’abbondanza |  |
| 11/03 | giovedì | 12:30 | S2 | U29 | Instagram | post 1:1 | Assistenza e prova | Il passaparola |  |
| 12/03 | venerdì | 09:00 | S2 | U30 | LinkedIn (pagina Impaginatore) | post di solo testo | Mestiere | File pronti per il laboratorio |  |
| 16/03 | martedì | 12:30 | S3 | U31 | Facebook (pagina) | post con video 9:16 (copione V1) | Le foto restano tue | La prova del wi-fi, su Facebook |  |
| 17/03 | mercoledì | 18:00 | S3 | U32 | Instagram | storia 9:16 | Mestiere | Webinar con un laboratorio |  |
| 18/03 | giovedì | 12:30 | S3 | U33 | Instagram | reel 9:16, 35 s (copione V4) | Mestiere | Lo spread finisce in Photoshop |  |
| 19/03 | venerdì | 12:30 | S3 | U34 | Facebook (pagina) | post 4:5 | Assistenza e prova | Com’è fatta la prova |  |
| 23/03 | martedì | 12:30 | S4 | U35 | Instagram | post 4:5 | Le foto restano tue | Dove finiscono le foto |  |
| 25/03 | giovedì | 12:30 | S4 | U36 | Instagram | post 4:5 | Mestiere | Consiglio di bottega 03: la bozza al cliente |  |
| 31/03 | mercoledì | 12:30 | S5 | U37 | Instagram | post 4:5 | Resta tuo | Offerta macOS 28 | sì |
| 01/04 | giovedì | 09:00 | S5 | U38 | LinkedIn (profilo del titolare) | post con immagine 4:5 | Resta tuo | macOS 28 e i programmi vecchi |  |
| 02/04 | venerdì | 12:30 | S5 | U39 | Facebook (pagina) | post 4:5 | Resta tuo | Offerta macOS 28, su Facebook |  |
| 06/04 | martedì | 12:30 | S6 | U40 | Instagram | storia 9:16, condivisione | Mestiere | Il video di un educator |  |
| 07/04 | mercoledì | 12:30 | S6 | U41 | Instagram | carosello 6 pagine 4:5 | Mestiere | Cinque controlli prima della stampa |  |
| 09/04 | venerdì | 09:00 | S6 | U42 | LinkedIn (pagina Impaginatore) | post di solo testo | Bottega | Per chi fa formazione |  |
| 13/04 | martedì | 12:30 | S7 | U43 | Instagram | post 4:5 | Assistenza e prova | Inizio stagione: 5 ore |  |
| 15/04 | giovedì | 12:30 | S7 | U44 | Instagram | post 4:5 | Resta tuo | Promemoria onesto |  |
| 16/04 | venerdì | 09:00 | S7 | U45 | LinkedIn e Facebook | post con immagine 4:5 | Resta tuo | Il prezzo di lancio finisce il 23 aprile | sì |
| 20/04 | martedì | 12:30 | S8 | U46 | Instagram | reel 9:16, 45 s (copione V5) | Assistenza e prova | Tre domande che ci fate |  |
| 22/04 | giovedì | 12:30 | S8 | U47 | Facebook (pagina) | post 4:5 | Resta tuo | Domani finisce il prezzo di lancio |  |
| 23/04 | venerdì | 09:00 | S8 | U48 | Instagram | post 4:5 | Resta tuo | Oggi l’ultimo giorno |  |
| 23/04 | venerdì | 09:05 | S8 | U49 | Instagram e Facebook | storia 9:16 | Resta tuo | Ultimo giorno, storia | sì |

Uscite per pilastro: Mestiere 14; Le foto restano tue 5; Resta tuo 16; Bottega 7; Assistenza e prova 7.

## Settimana S-3 · dal 1 febbraio al 7 febbraio

Dal piano di lancio: Proposte a podcast e riviste, accordi con 5 educator, materiali per la Convention.

### U01 · martedì 2 febbraio 2027, 12:30 · Instagram · Perché esiste Impaginatore

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Bottega |
| Modello | post-verticale |
| Grafica | grafiche/post-verticale.png |
| Invito all’azione | Iscriviti alla lista d’attesa |
| Link | {{link_lista}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #impaginazionealbum |
| Note | Primo post del profilo. Si fissa in cima fino al lancio, insieme a U02 e U05. |
| Caratteri | 754 in italiano |

Testo in italiano:

```text
Il programma per album che uso dal 2012 smetterà di aprirsi quando il Mac toglierà il livello di compatibilità su cui gira. Non l’ho scelto io: succede.

Un album dura una vita. Lo strumento con cui lo fai dovrebbe durare almeno quanto il tuo lavoro.

Così, tra un matrimonio e l’altro, ne ho scritto uno. Si chiama Impaginatore. Lavora sul tuo computer, con le foto nelle tue cartelle. Lo paghi una volta e la versione che compri resta tua.

Lo uso da anni sui miei album. In queste settimane lo sto preparando perché lo possano usare anche altri fotografi. Esce a febbraio.

Se vuoi sapere il giorno, la lista d’attesa è al link nella bio. Ti scrivo due volte: per la data e per il lancio.

#fotografodimatrimonio #albumdimatrimonio #impaginazionealbum
```

### U03 · mercoledì 3 febbraio 2027, 18:00 · Instagram · Sondaggio: dove impagini

| Campo | Valore |
|---|---|
| Formato | storia con sondaggio |
| Pilastro | Mestiere |
| Modello | nessuno (testo e adesivo «sondaggio» nell’app, fondo Carta) |
| Grafica | nessuna |
| Invito all’azione | Rispondi al sondaggio |
| Link | nessuno |
| Hashtag | nessuno |
| Note | Le risposte servono a scegliere i prossimi consigli di bottega. Nessun marchio nelle opzioni. |
| Caratteri | 210 in italiano |

Testo in italiano:

```text
Testo sullo schermo: Dove impagini i tuoi album, oggi?
Adesivo sondaggio: «Un programma per album» / «A mano, in Photoshop»
Seconda storia, il giorno dopo: i risultati, senza commenti sui programmi degli altri.
```

### U02 · giovedì 4 febbraio 2027, 12:30 · Instagram · Tre promesse

| Campo | Valore |
|---|---|
| Formato | carosello 5 pagine 4:5 |
| Pilastro | Le foto restano tue |
| Modello | carosello-copertina, carosello-interna, U02-pagina-3, U02-pagina-4, carosello-chiusura |
| Grafica | grafiche/carosello-copertina.png, grafiche/carosello-interna.png, grafiche/uscite/U02-pagina-3.png, grafiche/uscite/U02-pagina-4.png, grafiche/carosello-chiusura.png |
| Invito all’azione | Iscriviti alla lista d’attesa |
| Link | {{link_lista}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #impaginazionealbum #fotografiadimatrimonio |
| Hashtag in inglese | #weddingphotographer #weddingalbum #albumdesign |
| Caratteri | 684 in italiano, 590 in inglese |

Testo in italiano:

```text
Tre promesse, scritte prima di vendere una sola copia.

1. Le foto restano sul tuo computer. Nessuna funzione le carica in rete, e il programma lavora anche senza connessione.
2. Paghi una volta. La licenza non scade: la versione che compri resta tua anche se un giorno smetti di aggiornare.
3. Al decimo di millimetro. Margini, spazio tra le foto e abbondanza si impostano in millimetri, con i valori del tuo laboratorio.

Se una di queste tre cose un giorno cambiasse, avremmo smesso di fare il programma che volevamo fare.

Esce a febbraio. Per sapere il giorno: lista d’attesa, link nella bio.

#fotografodimatrimonio #albumdimatrimonio #impaginazionealbum #fotografiadimatrimonio
```

Testo in inglese («Three promises»):

```text
Three promises, written before selling a single copy.

1. Your photos stay on your computer. No feature uploads them, and the app works offline.
2. Pay once. The licence doesn’t expire: the version you buy is yours to keep, even if one day you stop updating.
3. To a tenth of a millimetre. Margins, spacing and bleed are set in millimetres, with your lab’s values.

If any of these three ever changed, we would have stopped making the software we set out to make.

Out in February. To hear the date first, join the waiting list: link in bio.

#weddingphotographer #weddingalbum #albumdesign
```

### U04 · venerdì 5 febbraio 2027, 09:00 · LinkedIn (profilo del titolare) · Da strumento personale a prodotto

| Campo | Valore |
|---|---|
| Formato | post con immagine 4:5 |
| Pilastro | Bottega |
| Modello | post-verticale |
| Grafica | grafiche/post-verticale.png |
| Invito all’azione | Commenta o scrivimi |
| Link | {{link_lista}} |
| Hashtag | #fotografia #software #matrimonio |
| Caratteri | 654 in italiano |

Testo in italiano:

```text
Da qualche anno impagino gli album di matrimonio con un programma che ho scritto per me. A febbraio diventa un prodotto: si chiama Impaginatore.

Tre scelte che sul mercato dei software per album non sono scontate:
– le foto restano sul computer del fotografo, nessuna funzione le carica in rete;
– la licenza si paga una volta e non scade;
– le misure si danno in millimetri, con i valori del laboratorio di stampa.

Se lavori in un laboratorio di stampa, in un’associazione di fotografi o nella formazione, mi interessa parlarti prima del lancio. Il programma esce martedì 23 febbraio.

Lista d’attesa: {{link_lista}}

#fotografia #software #matrimonio
```

## Settimana S-2 · dal 8 febbraio al 14 febbraio

Dal piano di lancio: Email «data» alla lista d’attesa; codici di segnalazione ai beta tester; ultimo controllo dei testi.

### U05 · lunedì 8 febbraio 2027, 09:00 · Instagram e Facebook · La data

| Campo | Valore |
|---|---|
| Formato | post 1:1 |
| Pilastro | Resta tuo |
| Modello | post-quadrato |
| Grafica | grafiche/post-quadrato.png |
| Invito all’azione | Iscriviti alla lista d’attesa |
| Link | {{link_lista}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #impaginazionealbum |
| Hashtag in inglese | #weddingphotographer #weddingalbum #albumdesign |
| Note | Stesso giorno dell’email «data» alla lista (PIANO-90-GIORNI, S-2). Su Facebook al posto di «link nella bio» si incolla {{link_lista}}. |
| Caratteri | 423 in italiano, 383 in inglese |

Testo in italiano:

```text
La data: martedì 23 febbraio.

Quel giorno Impaginatore si può comprare e provare per 30 giorni, senza carta. Chi è in lista d’attesa può comprarlo 48 ore prima, da domenica 21 febbraio, al prezzo di lancio.

Il prezzo lo scriviamo qui il giorno del lancio, insieme a tutto quello che contiene ogni licenza. Nessun abbonamento.

Lista d’attesa: link nella bio.

#fotografodimatrimonio #albumdimatrimonio #impaginazionealbum
```

Testo in inglese («The date»):

```text
The date: Tuesday 23 February.

That day you can buy Impaginatore, or try it for 30 days without a card. People on the waiting list can buy it 48 hours earlier, from Sunday 21 February, at the launch price.

We will post the price here on launch day, with everything each licence includes. No subscription.

Waiting list: link in bio.

#weddingphotographer #weddingalbum #albumdesign
```

### U06 · mercoledì 10 febbraio 2027, 12:30 · Instagram · Stacco il wi-fi ed esporto l’album

| Campo | Valore |
|---|---|
| Formato | reel 9:16, 30 s (copione V1) |
| Pilastro | Le foto restano tue |
| Modello | copertina-reel |
| Grafica | grafiche/copertina-reel.png |
| Invito all’azione | Iscriviti alla lista d’attesa |
| Link | {{link_lista}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #privacy |
| Note | Girato sul computer del titolare con la versione beta e l’album dimostrativo (foto Pexels senza volti in primo piano). |
| Caratteri | 416 in italiano |

Testo in italiano:

```text
Una prova che puoi rifare tu, il giorno che lo installi: stacco il wi‑fi ed esporto un album intero.

Impaginatore lavora sui file che hai già, nelle tue cartelle. Non c’è un archivio online da cui dipendere e nessuna funzione carica le foto in rete. Le foto dei tuoi sposi restano dove le hai messe tu.

Esce martedì 23 febbraio. Lista d’attesa al link nella bio.

#fotografodimatrimonio #albumdimatrimonio #privacy
```

### U07 · giovedì 11 febbraio 2027, 12:30 · Instagram · Consiglio di bottega 01: la piega

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Mestiere |
| Modello | citazione |
| Grafica | grafiche/citazione.png |
| Invito all’azione | Salva il post |
| Link | nessuno |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #consiglidifotografia |
| Caratteri | 512 in italiano |

Testo in italiano:

```text
Consiglio di bottega, numero uno.

Tieni i volti lontani dalla piega. Quanto lontano non lo decide il programma: lo decide la rilegatura. Un album a lay-flat si apre piatto, uno cucito no, e la zona da evitare cambia.

Chiedi al tuo laboratorio la misura per ogni rilegatura che usi, scrivila da qualche parte e impostala una volta sola. Poi non ci pensi più.

Ogni settimana, fino al lancio, un consiglio dal banco di lavoro. Salvalo se ti serve.

#fotografodimatrimonio #albumdimatrimonio #consiglidifotografia
```

### U08 · venerdì 12 febbraio 2027, 09:00 · LinkedIn (pagina Impaginatore) · Per i laboratori di stampa

| Campo | Valore |
|---|---|
| Formato | post con immagine 1,91:1 |
| Pilastro | Mestiere |
| Modello | copertina-linkedin-profilo |
| Grafica | grafiche/copertina-linkedin-profilo.png |
| Invito all’azione | Scrivici per un’edizione per laboratori |
| Link | {{link_laboratori}} |
| Hashtag | #stampafotografica #fotolibri #fotografia |
| Note | Nomi dei laboratori pilota solo con il loro consenso scritto. |
| Caratteri | 524 in italiano |

Testo in italiano:

```text
Impaginatore esce martedì 23 febbraio. Per chi stampa album, che cosa cambia?

Il fotografo imposta formato, margini, spazio tra le foto e abbondanza in millimetri, con i valori che gli dà il laboratorio. Esporta JPG o PDF; con le licenze Pro e Studio anche PSD a livelli. Il progetto e le foto restano sul suo computer.

Per i laboratori stiamo preparando un’edizione con il vostro catalogo di formati e il vostro marchio. Se volete saperne di più, scriveteci: {{link_laboratori}}

#stampafotografica #fotolibri #fotografia
```

### U09 · venerdì 12 febbraio 2027, 12:30 · Facebook (pagina) · La data, su Facebook

| Campo | Valore |
|---|---|
| Formato | post 1:1 |
| Pilastro | Le foto restano tue |
| Modello | post-quadrato |
| Grafica | grafiche/post-quadrato.png |
| Invito all’azione | Iscriviti alla lista d’attesa |
| Link | {{link_lista}} |
| Hashtag | nessuno |
| Note | Variante per Facebook di U05: qui il link è cliccabile. L’ultima riga solo se la presenza alla Convention ANFM è confermata. |
| Caratteri | 349 in italiano |

Testo in italiano:

```text
Impaginatore esce martedì 23 febbraio.

È un programma per impaginare album di matrimonio sul tuo computer: le foto restano nelle tue cartelle, la licenza si paga una volta. Chi è in lista d’attesa può comprarlo 48 ore prima, al prezzo di lancio.

Lista d’attesa: {{link_lista}}

Ci trovi anche alla Convention ANFM di Padova, dal 24 al 27 febbraio.
```

## Settimana S-1 · dal 15 febbraio al 21 febbraio

Dal piano di lancio: Versione di lancio congelata. Domenica 21: accesso anticipato di 48 ore per la lista d’attesa.

### U10 · lunedì 15 febbraio 2027, 12:30 · Instagram · Fare i conti su tre anni

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Resta tuo |
| Modello | U10-tre-anni |
| Grafica | grafiche/uscite/U10-tre-anni.png |
| Invito all’azione | Iscriviti alla lista d’attesa |
| Link | {{link_lista}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #abbonamenti |
| Hashtag in inglese | #weddingphotographer #weddingalbum #albumdesign |
| Note | Pubblicità comparativa senza marchi: da far vedere al legale prima (PIANO-90-GIORNI, S-4). Fonti in docs/mercato/prezzi.md. Prima di pubblicare rileggere i prezzi e aggiornare confronto.* in costanti.json: dal 1/1/2027 uno dei tre abbonamenti rincara. |
| Caratteri | 578 in italiano, 549 in inglese |

Testo in italiano:

```text
Facciamo due conti, senza nomi.

Un abbonamento annuale a un software per album costava, al 15/11/2026, da 250 a 290 $ l’anno: circa 20 € al mese. In tre anni sono 36 mensilità.

Impaginatore Pro costa 99 €, una volta, IVA esclusa: più o meno quanto 5 mesi di abbonamento. Gli altri mesi non li paghi, e la versione che hai comprato resta tua.

Al lancio Pro costa 79 € fino al 23 aprile, poi 99 €, sempre una volta e IVA esclusa.

Le fonti dei prezzi le pubblichiamo nella pagina prezzi. Lista d’attesa al link nella bio.

#fotografodimatrimonio #albumdimatrimonio #abbonamenti
```

Testo in inglese («Doing the maths over three years»):

```text
Let’s do the maths, without names.

On 15 Nov 2026, an annual album software subscription cost $250 to $290 a year: about €20 a month. Over three years, that’s 36 monthly payments.

Impaginatore Pro costs €99, one-time, VAT excluded: roughly 5 months of subscription. You don’t pay for the other months, and the version you bought is yours to keep.

At launch, Pro costs €79 until 23 April, then €99, still one-time and VAT excluded.

Price sources are on our pricing page. Waiting list: link in bio.

#weddingphotographer #weddingalbum #albumdesign
```

### U11 · mercoledì 17 febbraio 2027, 12:30 · Instagram · Gli stessi spazi su tutto l’album

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Mestiere |
| Modello | prima-dopo |
| Grafica | grafiche/prima-dopo.png |
| Invito all’azione | Iscriviti alla lista d’attesa |
| Link | {{link_lista}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #impaginazionealbum |
| Caratteri | 573 in italiano |

Testo in italiano:

```text
A sinistra, una pagina impaginata a occhio: spazi da 3,0 mm in orizzontale e quasi 10 in verticale, margini diversi su ogni lato. A destra, la stessa pagina con 5,0 mm ovunque e 15,0 mm di margine.

Su una pagina la differenza si vede appena. Su quaranta spread, sfogliando, si sente.

Con le licenze Pro e Studio, Impaginatore rende uniformi spazi e tono su tutte le pagine dell’album. Poi ogni spread lo puoi ancora cambiare a mano.

Disegno in scala vera, album 30 × 30 cm. Lista d’attesa al link nella bio.

#fotografodimatrimonio #albumdimatrimonio #impaginazionealbum
```

### U12 · giovedì 18 febbraio 2027, 18:00 · Instagram · Versione congelata

| Campo | Valore |
|---|---|
| Formato | storia, 2 schermate di testo |
| Pilastro | Bottega |
| Modello | nessuno (testo nell’app, fondo Inchiostro) |
| Grafica | nessuna |
| Invito all’azione | Rispondi alla storia |
| Link | nessuno |
| Hashtag | nessuno |
| Caratteri | 261 in italiano |

Testo in italiano:

```text
Schermata 1: Da oggi la versione di lancio è congelata. Fino al martedì 23 febbraio correggiamo solo errori, niente funzioni nuove.
Schermata 2: Hai una domanda sul programma? Rispondi a questa storia: le domande più frequenti finiscono nelle risposte del sito.
```

### U13 · venerdì 19 febbraio 2027, 09:00 · LinkedIn (profilo del titolare) · Licenza perpetua, nel 2027

| Campo | Valore |
|---|---|
| Formato | post con immagine 4:5 |
| Pilastro | Resta tuo |
| Modello | U10-tre-anni |
| Grafica | grafiche/uscite/U10-tre-anni.png |
| Invito all’azione | Iscriviti alla lista d’attesa |
| Link | {{link_lista}} |
| Hashtag | #fotografia #software #abbonamenti |
| Note | Dopo il parere del legale, come U10. |
| Caratteri | 604 in italiano |

Testo in italiano:

```text
Una domanda che mi fanno spesso: perché vendere una licenza perpetua nel 2027?

Perché chi impagina album lavora su progetti che durano anni: l’album si riapre per una ristampa, per una copia ai genitori, per un anniversario. Un programma che smette di aprirsi se smetti di pagare non va d’accordo con questo lavoro.

Impaginatore Pro costa 99 €, una volta, IVA esclusa. Al lancio 79 € fino al 23 aprile, poi 99 €. La chiave si verifica sul computer, senza server: il programma si apre anche senza connessione.

Esce martedì 23 febbraio. Lista d’attesa: {{link_lista}}

#fotografia #software #abbonamenti
```

### U14 · domenica 21 febbraio 2027, 09:00 · Instagram e Facebook · Accesso anticipato

| Campo | Valore |
|---|---|
| Formato | storia 9:16 |
| Pilastro | Resta tuo |
| Modello | storia |
| Grafica | grafiche/storia.png |
| Invito all’azione | Controlla l’email |
| Link | {{link_lista}} (adesivo link) |
| Hashtag | nessuno |
| Note | Domenica: è l’unica uscita nel fine settimana, insieme all’email dell’accesso anticipato. |
| Caratteri | 249 in italiano, 260 in inglese |

Testo in italiano:

```text
Testo sullo schermo: Da oggi, 48 ore prima di tutti.
Testo piccolo: Se sei in lista d’attesa, ti è arrivata un’email con il link per comprare al prezzo di lancio. Per tutti si apre martedì 23 febbraio.
Adesivo link: «Lista d’attesa» → {{link_lista}}
```

Testo in inglese («Early access»):

```text
On-screen text: From today, 48 hours before everyone.
Small text: If you are on the waiting list, an email with the purchase link at the launch price is in your inbox. Sales open to everyone on Tuesday 23 February.
Link sticker: «Waiting list» → {{link_lista}}
```

## Settimana S0 · dal 22 febbraio al 28 febbraio

Dal piano di lancio: Lancio martedì 23 alle 9; Convention ANFM a Padova da mercoledì 24 a sabato 27.

### U15 · martedì 23 febbraio 2027, 09:00 · Instagram · Impaginatore è pronto

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Resta tuo |
| Modello | annuncio-lancio |
| Grafica | grafiche/annuncio-lancio.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #impaginazionealbum #fotografiadimatrimonio |
| Hashtag in inglese | #weddingphotographer #weddingalbum #albumdesign |
| Note | Si fissa in cima al profilo per tutto il periodo di lancio. Alle 9 in punto, con l’email di lancio. |
| Caratteri | 869 in italiano, 777 in inglese |

Testo in italiano:

```text
Impaginatore è pronto.

Impagini l’album sul tuo computer, con le foto nelle tue cartelle: nessuna funzione le carica in rete. Paghi una volta, la licenza non scade.

Tre licenze, prezzi di lancio, una volta, IVA esclusa:
– Essenziale: 39 € fino al 23 aprile, poi 49 €. 1 computer, 30 modelli d’autore, JPG e PDF.
– Pro: 79 € fino al 23 aprile, poi 99 €. 2 computer, impaginazione automatica dell’album, spazi e tono uniformi, PSD a livelli.
– Studio: 119 € fino al 23 aprile, poi 149 €. 5 computer, un’ora di assistenza inclusa e la prossima versione maggiore.

Prova gratuita di 30 giorni, senza carta: tutte le funzioni del Pro tranne il PSD, con una filigrana sugli export. Su Mac e Windows si installa con una riga; su Linux c’è l’AppImage o il pacchetto .deb.

Link nella bio.

#fotografodimatrimonio #albumdimatrimonio #impaginazionealbum #fotografiadimatrimonio
```

Testo in inglese («Impaginatore is ready»):

```text
Impaginatore is ready.

You lay out the album on your computer, with the photos in your own folders: no feature uploads them. Pay once; the licence doesn’t expire.

Three licences, launch prices, one-time, VAT excluded:
– Essenziale: €39 until 23 April, then €49. 1 computer, 30 designer layouts, JPG and PDF.
– Pro: €79 until 23 April, then €99. 2 computers, automatic album layout, even spacing and tone, layered PSD.
– Studio: €119 until 23 April, then €149. 5 computers, one hour of support included, and the next major version.

Free 30-day trial, no card: every Pro feature except PSD, with a watermark on exports. On Mac and Windows it installs with one line; on Linux there’s an AppImage or a .deb package.

Link in bio.

#weddingphotographer #weddingalbum #albumdesign
```

### U16 · martedì 23 febbraio 2027, 09:05 · Instagram e Facebook · Lancio, storia

| Campo | Valore |
|---|---|
| Formato | storia 9:16 |
| Pilastro | Resta tuo |
| Modello | annuncio-lancio-storia |
| Grafica | grafiche/annuncio-lancio-storia.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} (adesivo link) |
| Hashtag | nessuno |
| Caratteri | 228 in italiano |

Testo in italiano:

```text
Testo sullo schermo: Impaginatore è pronto. Sul tuo computer, con le tue foto. Paghi una volta.
Prezzo nella grafica: Pro 79 € fino al 23 aprile, poi 99 €, una volta, IVA esclusa.
Adesivo link: «Prova 30 giorni» → {{link_prova}}
```

### U17 · martedì 23 febbraio 2027, 09:30 · LinkedIn (profilo del titolare e pagina Impaginatore) · Lancio su LinkedIn

| Campo | Valore |
|---|---|
| Formato | post con immagine 4:5 |
| Pilastro | Bottega |
| Modello | annuncio-lancio |
| Grafica | grafiche/annuncio-lancio.png |
| Invito all’azione | Prova gratis per 30 giorni |
| Link | {{link_prova}} |
| Hashtag | #fotografia #software #matrimonio |
| Hashtag in inglese | #photography #software |
| Caratteri | 676 in italiano, 596 in inglese |

Testo in italiano:

```text
Oggi esce Impaginatore, il programma con cui impagino i miei album di matrimonio, ora per tutti i fotografi.

Lavora sul computer, senza conti online e senza caricare le foto da nessuna parte. Si paga una volta: Pro costa 79 € fino al 23 aprile, poi 99 €, IVA esclusa. Ci sono anche Essenziale e Studio, per chi lavora con un computer solo o con uno studio intero.

Ringrazio i fotografi che l’hanno provato in queste settimane: alcune delle cose che trovate dentro sono nate dalle loro segnalazioni.

Prova gratuita di 30 giorni, senza carta: {{link_prova}}
Laboratori di stampa e associazioni: scrivetemi, ci sono edizioni pensate per voi.

#fotografia #software #matrimonio
```

Testo in inglese («Launch on LinkedIn»):

```text
Today we release Impaginatore, the software I use to lay out my own wedding albums, now for every photographer.

It runs on your computer, with no online account and no photo uploads. You pay once: Pro costs €79 until 23 April, then €99, VAT excluded. There are also Essenziale and Studio, for a single computer or a whole studio.

Thank you to the photographers who tested it in recent weeks: some of what you will find inside came from their reports.

Free 30-day trial, no card: {{link_prova}}
Print labs and associations: get in touch, there are editions made for you.

#photography #software
```

### U18 · martedì 23 febbraio 2027, 10:00 · YouTube · Come si installa Impaginatore (Mac, Windows, Linux)

| Campo | Valore |
|---|---|
| Formato | video 16:9, 3–5 min (guida all’installazione) |
| Pilastro | Assistenza e prova |
| Modello | copertina-video |
| Grafica | grafiche/copertina-video.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_installa}} |
| Hashtag | #impaginatore #albumdimatrimonio |
| Note | Titolo del video = titolo qui sopra (massimo 100 caratteri). Il testo è la descrizione. Il video lungo lo registra il fondatore (PIANO-90-GIORNI, S-6); la versione breve è il copione V2. |
| Caratteri | 741 in italiano |

Testo in italiano:

```text
Su Mac e Windows Impaginatore si installa con un comando di una riga; su Linux con l’AppImage o il pacchetto .deb. In questo video vediamo che cosa fa quel comando, passo per passo, e come si apre il primo album.

Capitoli
00:00 Che cosa serve
00:40 Mac
01:40 Windows
02:40 Linux: AppImage e .deb
03:30 Il primo progetto e la prova di 30 giorni

Il comando scarica il programma dal nostro sito e, prima di installarlo, controlla la nostra firma digitale: se il file non è quello che abbiamo pubblicato, si ferma.

Pagina di installazione, con il comando da copiare: {{link_installa}}
Manuale: {{link_manuale}}
Se qualcosa non va, scrivici: {{email_supporto}}. Gli errori del programma li correggiamo gratis.

#impaginatore #albumdimatrimonio
```

### U19 · martedì 23 febbraio 2027, 12:00 · Facebook (pagina) · Lancio su Facebook

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Resta tuo |
| Modello | annuncio-lancio |
| Grafica | grafiche/annuncio-lancio.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} |
| Hashtag | nessuno |
| Note | L’ultimo paragrafo solo se la presenza alla Convention ANFM è confermata. |
| Caratteri | 545 in italiano |

Testo in italiano:

```text
Impaginatore è pronto.

Un programma per impaginare album di matrimonio sul tuo computer. Le foto restano nelle tue cartelle, la licenza si paga una volta e non scade.

Prezzi di lancio, una volta, IVA esclusa:
Essenziale 39 € fino al 23 aprile, poi 49 €
Pro 79 € fino al 23 aprile, poi 99 €
Studio 119 € fino al 23 aprile, poi 149 €

Prova gratuita di 30 giorni, senza carta: {{link_prova}}
Prezzi e differenze tra le licenze: {{link_prezzi}}

Da domani siamo alla Convention ANFM di Padova: se passi, ti mostriamo un album impaginato dal vivo.
```

### U20 · mercoledì 24 febbraio 2027, 10:00 · Instagram · Convention ANFM, giorno 1

| Campo | Valore |
|---|---|
| Formato | storia 9:16, foto dallo stand |
| Pilastro | Bottega |
| Modello | nessuno (foto del banco, senza volti di visitatori) |
| Grafica | nessuna |
| Invito all’azione | Passa a trovarci |
| Link | nessuno |
| Hashtag | nessuno |
| Note | Solo se la presenza alla Convention è confermata da ANFM. Nessuna foto di visitatori senza il loro consenso. |
| Caratteri | 197 in italiano |

Testo in italiano:

```text
Testo sullo schermo: Convention ANFM, Padova. Fino a sabato impaginiamo un album dal vivo, in dieci minuti di demo.
Seconda storia: Vuoi provarlo sul tuo portatile? Portalo: lo installiamo insieme.
```

### U21 · giovedì 25 febbraio 2027, 12:30 · Instagram · Dalla cartella alla bozza

| Campo | Valore |
|---|---|
| Formato | reel 9:16, 40 s (copione V3) |
| Pilastro | Mestiere |
| Modello | copertina-reel |
| Grafica | grafiche/copertina-reel.png (testo da cambiare: «Dalla cartella alla bozza») |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #impaginazionealbum |
| Caratteri | 435 in italiano |

Testo in italiano:

```text
Dalla cartella delle foto scelte alla prima bozza dell’album, sul mio portatile.

Con Pro e Studio, Impaginatore prepara la bozza dell’album intero con le foto che hai scelto, poi rende uniformi spazi e tono. Da lì comincia il lavoro vero: sposti, cambi, decidi ogni spread. La bozza è automatica, la firma è tua.

Prova gratuita di 30 giorni, senza carta: link nella bio.

#fotografodimatrimonio #albumdimatrimonio #impaginazionealbum
```

### U22 · venerdì 26 febbraio 2027, 12:30 · Instagram · Quale licenza scegliere

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Resta tuo |
| Modello | scheda-prezzo |
| Grafica | grafiche/scheda-prezzo.png |
| Invito all’azione | Confronta le licenze |
| Link | {{link_prezzi}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio |
| Caratteri | 605 in italiano |

Testo in italiano:

```text
Quale licenza ti serve? Tre domande.

Lavori su un computer solo e ti bastano JPG e PDF? Essenziale: 39 € fino al 23 aprile, poi 49 €.
Vuoi la bozza automatica dell’album e i PSD a livelli, su fisso e portatile? Pro: 79 € fino al 23 aprile, poi 99 €.
Siete in più persone, fino a 5 computer? Studio: 119 € fino al 23 aprile, poi 149 €, con un’ora di assistenza e la prossima versione maggiore.

Sempre una volta, IVA esclusa. Se cambi idea, passi alla licenza superiore: da Essenziale a Pro costa 50 €.

Rimborso entro 30 giorni se non fa per te. Link nella bio.

#fotografodimatrimonio #albumdimatrimonio
```

## Settimana S1 · dal 1 marzo al 7 marzo

Dal piano di lancio: Seguito ai contatti della Convention; «1 ora per partire» a chi ha appena comprato.

### U23 · martedì 2 marzo 2027, 12:30 · Instagram · Un’ora con una persona

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Assistenza e prova |
| Modello | scheda-ore |
| Grafica | grafiche/scheda-ore.png |
| Invito all’azione | Prenota un’ora |
| Link | {{link_assistenza}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio |
| Hashtag in inglese | #weddingphotographer #weddingalbum #albumdesign |
| Note | Nessun confronto fra il prezzo per ora dei pacchetti. |
| Caratteri | 550 in italiano, 509 in inglese |

Testo in italiano:

```text
Un’ora con una persona, quando ti serve.

In videochiamata o da remoto: l’installazione, il primo album, i formati del tuo laboratorio, il passaggio a Photoshop.

49 € per un’ora. Se preferisci non pensarci più, ci sono anche i pacchetti da 5 ore (249 €) e da 10 ore (499 €): un solo pagamento, ore valide 12 mesi, usate a blocchi di 30 minuti. IVA esclusa.

Restano gratis per tutti il manuale, le guide video e la correzione degli errori del programma: se il problema è nostro, non paghi.

Link nella bio.

#fotografodimatrimonio #albumdimatrimonio
```

Testo in inglese («An hour with a person»):

```text
An hour with a person, when you need it.

By video call or remote session: installation, your first album, your lab’s formats, moving to Photoshop.

€49 for one hour. If you’d rather not think about it again, there are also 5-hour (€249) and 10-hour (€499) packs: one payment, hours valid for 12 months, used in 30-minute blocks. VAT excluded.

The manual, video guides and bug fixes stay free for everyone: if the problem is ours, you don’t pay.

Link in bio.

#weddingphotographer #weddingalbum #albumdesign
```

### U24 · mercoledì 3 marzo 2027, 12:30 · Instagram · Le misure del laboratorio, una volta sola

| Campo | Valore |
|---|---|
| Formato | carosello 4 pagine 4:5 |
| Pilastro | Mestiere |
| Modello | carosello-copertina, segnaposto-schermata, carosello-interna, carosello-chiusura |
| Grafica | da comporre quando ci sono le schermate (T-501): pannello-misure.png nella pagina 3 |
| Invito all’azione | Salva il post |
| Link | {{link_manuale}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #stampafotografica |
| Note | Pagina 3 = segnaposto-schermata finché non c’è la schermata vera (modelli/schermate/pannello-misure.png, 888 × 700 px). |
| Caratteri | 513 in italiano |

Testo in italiano:

```text
Le misure del laboratorio, impostate una volta sola.

Pagina 2: chiedi al laboratorio formato, abbondanza e margine di sicurezza per ogni prodotto che usi.
Pagina 3: in Impaginatore li scrivi in millimetri nel pannello misure, insieme allo spazio tra le foto.
Pagina 4: li salvi come preset e li ritrovi in ogni album nuovo.

Un errore di abbondanza costa una ristampa. Un preset costa due minuti.

Il manuale con tutti i passaggi è al link nella bio.

#fotografodimatrimonio #albumdimatrimonio #stampafotografica
```

### U25 · giovedì 4 marzo 2027, 18:00 · YouTube Shorts e Instagram · Una riga per installarlo

| Campo | Valore |
|---|---|
| Formato | short/reel 9:16, 25 s (copione V2) |
| Pilastro | Assistenza e prova |
| Modello | copertina-reel |
| Grafica | grafiche/copertina-reel.png (testo da cambiare: «Una riga per installarlo») |
| Invito all’azione | Guarda la guida completa |
| Link | {{link_installa}} |
| Hashtag | #impaginatore #albumdimatrimonio |
| Note | Su YouTube il titolo dello Short è il titolo qui sopra. Su Instagram il testo finisce con «link nella bio». |
| Caratteri | 308 in italiano |

Testo in italiano:

```text
Una riga nel Terminale del Mac, o in PowerShell su Windows, e Impaginatore è installato. Prima di installare, il comando controlla la nostra firma sul file.

La guida completa, anche per Linux, è sul nostro canale YouTube. Pagina con il comando da copiare: {{link_installa}}

#impaginatore #albumdimatrimonio
```

### U26 · venerdì 5 marzo 2027, 09:00 · LinkedIn (profilo del titolare) · Una chiave senza server

| Campo | Valore |
|---|---|
| Formato | post di solo testo |
| Pilastro | Bottega |
| Modello | nessuno |
| Grafica | nessuna |
| Invito all’azione | Commenta |
| Link | nessuno |
| Hashtag | #fotografia #software |
| Caratteri | 592 in italiano |

Testo in italiano:

```text
Dietro Impaginatore c’è una scelta tecnica che i fotografi non vedono, ma che spiega molto di come lavoriamo.

La licenza è una chiave firmata. Il programma la verifica sul computer, senza chiamare nessun server. Vuol dire che non c’è un conto da tenere aperto, che il programma si apre anche senza connessione e che, se un giorno noi smettessimo di esistere, la tua copia continuerebbe a funzionare.

La chiave porta il nome di chi l’ha comprata, e il programma lo mostra. Il resto è fiducia tra professionisti.

Ogni ordine lo evadiamo a mano, entro 2 ore lavorative.

#fotografia #software
```

## Settimana S2 · dal 8 marzo al 14 marzo

Dal piano di lancio: Caso di studio di un beta tester; spinta sulle segnalazioni.

### U27 · martedì 9 marzo 2027, 12:30 · Instagram · Caso di studio di un beta tester

| Campo | Valore |
|---|---|
| Formato | carosello 4:5 |
| Pilastro | Mestiere |
| Modello | citazione (frase del beta tester), carosello-interna, carosello-chiusura |
| Grafica | da comporre con i dati del caso di studio |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #impaginazionealbum |
| Note | Si pubblica solo con dati veri e il consenso scritto del fotografo (PIANO-90-GIORNI, S2). Nome, frase e dato vanno in costanti.json (caso.*). Niente numeri inventati. |
| Caratteri | 403 in italiano |

Testo in italiano:

```text
{{caso.nome}} ha impaginato con Impaginatore gli album della sua stagione invernale, durante la prova riservata ai beta tester.

«{{caso.citazione}}»

Il dato che ci ha dato lui: {{caso.dato}}. È il suo caso, con le sue foto e il suo modo di lavorare: il tuo può essere diverso, ed è per questo che la prova dura 30 giorni.

Link nella bio.

#fotografodimatrimonio #albumdimatrimonio #impaginazionealbum
```

### U28 · mercoledì 10 marzo 2027, 12:30 · Instagram · Consiglio di bottega 02: l’abbondanza

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Mestiere |
| Modello | citazione (testo da cambiare: consiglio 02) |
| Grafica | grafiche/citazione.png (consiglio 02) |
| Invito all’azione | Salva il post |
| Link | nessuno |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #consiglidifotografia |
| Caratteri | 519 in italiano |

Testo in italiano:

```text
Consiglio di bottega, numero due.

L’abbondanza non è un margine: è la parte di foto che il laboratorio taglia via. Se una foto arriva al bordo della pagina, deve uscire oltre il rifilo di quanto chiede il laboratorio, altrimenti dopo il taglio resta un filo bianco.

Il contrario vale per i testi e i volti: tienili dentro il margine di sicurezza, lontani dal rifilo.

Due misure da chiedere al laboratorio, una volta: abbondanza e margine di sicurezza.

#fotografodimatrimonio #albumdimatrimonio #consiglidifotografia
```

### U29 · giovedì 11 marzo 2027, 12:30 · Instagram · Il passaparola

| Campo | Valore |
|---|---|
| Formato | post 1:1 |
| Pilastro | Assistenza e prova |
| Modello | post-quadrato (testo da cambiare: «Passaparola») |
| Grafica | da comporre da post-quadrato |
| Invito all’azione | Usa il tuo codice |
| Link | nessuno |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio |
| Caratteri | 377 in italiano |

Testo in italiano:

```text
Se hai già Impaginatore, nella email della chiave trovi un codice personale.

Chi compra con il tuo codice ha il 10% di sconto sulla licenza. Tu, per ogni amico che compra, ricevi 30 minuti di assistenza, che si sommano.

Nessuna classifica e nessun premio a sorpresa: un collega che ne aiuta un altro, come succede già tra fotografi.

#fotografodimatrimonio #albumdimatrimonio
```

### U30 · venerdì 12 marzo 2027, 09:00 · LinkedIn (pagina Impaginatore) · File pronti per il laboratorio

| Campo | Valore |
|---|---|
| Formato | post di solo testo |
| Pilastro | Mestiere |
| Modello | nessuno |
| Grafica | nessuna |
| Invito all’azione | Scrivici per un’edizione per laboratori |
| Link | {{link_laboratori}} |
| Hashtag | #stampafotografica #fotolibri |
| Caratteri | 502 in italiano |

Testo in italiano:

```text
Una domanda per chi lavora in un laboratorio di stampa: quanti file di album vi tornano indietro perché le misure non sono quelle giuste?

Impaginatore permette al fotografo di salvare come preset le misure di ogni vostro prodotto: formato, abbondanza, margine, spazio tra le foto. Nell’edizione per laboratori il catalogo dei formati arriva già dentro il programma, con il vostro marchio.

Se volete vederla, organizziamo una dimostrazione da remoto: {{link_laboratori}}

#stampafotografica #fotolibri
```

## Settimana S3 · dal 15 marzo al 21 marzo

Dal piano di lancio: Controllo dei piloti; primo webinar con un laboratorio.

### U31 · martedì 16 marzo 2027, 12:30 · Facebook (pagina) · La prova del wi-fi, su Facebook

| Campo | Valore |
|---|---|
| Formato | post con video 9:16 (copione V1) |
| Pilastro | Le foto restano tue |
| Modello | copertina-reel |
| Grafica | grafiche/copertina-reel.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} |
| Hashtag | nessuno |
| Note | Riuso del reel V1 (U06) per chi segue solo la pagina Facebook. |
| Caratteri | 292 in italiano |

Testo in italiano:

```text
Una prova che puoi fare anche tu: staccare il wi‑fi ed esportare un album intero.

Impaginatore lavora sui file che hai già, nelle tue cartelle. Nessuna funzione carica le foto in rete: le foto dei tuoi sposi restano sul tuo computer.

Prova gratuita di 30 giorni, senza carta: {{link_prova}}
```

### U32 · mercoledì 17 marzo 2027, 18:00 · Instagram · Webinar con un laboratorio

| Campo | Valore |
|---|---|
| Formato | storia 9:16 |
| Pilastro | Mestiere |
| Modello | storia (testi da cambiare) |
| Grafica | da comporre da storia |
| Invito all’azione | Iscriviti al webinar |
| Link | link del laboratorio (adesivo link) |
| Hashtag | nessuno |
| Note | Solo se il webinar è confermato (PIANO-90-GIORNI, S3) e il laboratorio ha dato il consenso a essere nominato. Valori in costanti.json (webinar.*). |
| Caratteri | 202 in italiano |

Testo in italiano:

```text
Testo sullo schermo: Webinar con {{webinar.laboratorio}}, {{webinar.data}}. Come preparare i file dell’album perché tornino stampati come li hai visti.
Adesivo link: «Iscriviti» → pagina del laboratorio
```

### U33 · giovedì 18 marzo 2027, 12:30 · Instagram · Lo spread finisce in Photoshop

| Campo | Valore |
|---|---|
| Formato | reel 9:16, 35 s (copione V4) |
| Pilastro | Mestiere |
| Modello | copertina-reel |
| Grafica | grafiche/copertina-reel.png (testo da cambiare: «Il PSD a livelli») |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #photoshop |
| Caratteri | 417 in italiano |

Testo in italiano:

```text
Uno spread impaginato, esportato come PSD a livelli e aperto in Photoshop: ogni foto sul suo livello, pronta per l’ultima rifinitura.

Il PSD a livelli è nelle licenze Pro e Studio e serve Photoshop installato sul computer. JPG e PDF li hai con tutte le licenze.

Prova gratuita di 30 giorni: link nella bio. Nella prova il PSD non c’è, tutto il resto del Pro sì.

#fotografodimatrimonio #albumdimatrimonio #photoshop
```

### U34 · venerdì 19 marzo 2027, 12:30 · Facebook (pagina) · Com’è fatta la prova

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Assistenza e prova |
| Modello | carosello-interna (pagina 2 di U02) |
| Grafica | grafiche/carosello-interna.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} |
| Hashtag | nessuno |
| Caratteri | 403 in italiano |

Testo in italiano:

```text
Com’è fatta la prova di Impaginatore, senza sorprese.

Dura 30 giorni e non chiede la carta. Ha tutte le funzioni del Pro tranne il PSD a livelli. Gli export hanno una filigrana. Alla fine della prova i tuoi progetti restano apribili, in sola lettura: niente va perso.

Se compri, la chiave arriva entro 2 ore lavorative e la filigrana sparisce dagli export successivi.

Scarica la prova: {{link_prova}}
```

## Settimana S4 · dal 22 marzo al 28 marzo

Dal piano di lancio: Bilancio di metà lancio. Pasqua il 28/03: niente uscite il 28 e il 29.

### U35 · martedì 23 marzo 2027, 12:30 · Instagram · Dove finiscono le foto

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Le foto restano tue |
| Modello | carosello-interna |
| Grafica | grafiche/carosello-interna.png |
| Invito all’azione | Salva il post |
| Link | nessuno |
| Hashtag | #fotografodimatrimonio #privacy #albumdimatrimonio |
| Caratteri | 482 in italiano |

Testo in italiano:

```text
Quando impagini un album, dove finiscono le foto dei tuoi sposi?

Con Impaginatore restano dove le hai messe tu: nelle tue cartelle, sul tuo disco. Il programma non ha un archivio online e nessuna funzione le carica in rete. Lo puoi verificare da solo: stacca il wi‑fi e lavora come sempre.

È una regola scritta del progetto, non un’impostazione che si può cambiare. Ai tuoi clienti puoi dirlo così: le vostre foto le ho solo io.

#fotografodimatrimonio #privacy #albumdimatrimonio
```

### U36 · giovedì 25 marzo 2027, 12:30 · Instagram · Consiglio di bottega 03: la bozza al cliente

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Mestiere |
| Modello | citazione (testo da cambiare: consiglio 03) |
| Grafica | grafiche/citazione.png (consiglio 03) |
| Invito all’azione | Salva il post |
| Link | nessuno |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #consiglidifotografia |
| Note | Ultima uscita prima di Pasqua: niente uscite il 28 e il 29 marzo. |
| Caratteri | 376 in italiano |

Testo in italiano:

```text
Consiglio di bottega, numero tre.

Alla coppia manda la bozza in PDF, con gli spread numerati. Chiedi le modifiche per numero di spread, non per descrizione: «nello spread 14 togliamo la foto in basso» si capisce al primo colpo, «quella foto con la zia» no.

Un giro di modifiche, al massimo due. Poi si stampa.

#fotografodimatrimonio #albumdimatrimonio #consiglidifotografia
```

## Settimana S5 · dal 29 marzo al 4 aprile

Dal piano di lancio: Offerta Rosetta, con i testi rivisti dal legale; podcast e riviste; forum.

### U37 · mercoledì 31 marzo 2027, 12:30 · Instagram · Offerta macOS 28

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Resta tuo |
| Modello | U37-rosetta |
| Grafica | grafiche/uscite/U37-rosetta.png |
| Invito all’azione | Mandaci la licenza o la fattura |
| Link | {{link_rosetta}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #macos |
| Hashtag in inglese | #weddingphotographer #weddingalbum #albumdesign |
| Note | Solo con il parere del legale e i prezzi approvati in costanti.json (PIANO-90-GIORNI §3.2). Nessun marchio di concorrenti, nemmeno nei commenti: le domande sui nomi si portano in privato. |
| Caratteri | 484 in italiano, 437 in inglese |

Testo in italiano:

```text
Hai un vecchio software per album con licenza perpetua che su macOS 28 non si aprirà più?

Mandaci la licenza o la fattura del vecchio programma. Ti diamo Impaginatore Pro a {{prezzo_rosetta_pro}} o Studio a {{prezzo_rosetta_studio}}, una volta, IVA esclusa. L’offerta vale fino al 31 dicembre 2027.

Sei un fotografo che ha comprato il suo strumento per tenerlo: ne sappiamo qualcosa, è da lì che nasce Impaginatore.

Link nella bio.

#fotografodimatrimonio #albumdimatrimonio #macos
```

Testo in inglese («macOS 28 offer»):

```text
Do you own an old perpetual-licence album app that won’t open on macOS 28?

Send us the licence or invoice of your old software. We’ll give you Impaginatore Pro for {{prezzo_rosetta_pro}} or Studio for {{prezzo_rosetta_studio}}, one-time, VAT excluded. The offer runs until 31 December 2027.

You bought your tool to keep it. So did we: that’s where Impaginatore comes from.

Link in bio.

#weddingphotographer #weddingalbum #albumdesign
```

### U38 · giovedì 1 aprile 2027, 09:00 · LinkedIn (profilo del titolare) · macOS 28 e i programmi vecchi

| Campo | Valore |
|---|---|
| Formato | post con immagine 4:5 |
| Pilastro | Resta tuo |
| Modello | U37-rosetta |
| Grafica | grafiche/uscite/U37-rosetta.png |
| Invito all’azione | Inoltra a un collega |
| Link | {{link_rosetta}} |
| Hashtag | #fotografia #macos #software |
| Note | Come U37: dopo il parere del legale. |
| Caratteri | 604 in italiano |

Testo in italiano:

```text
Apple ha annunciato che macOS 27 sarà l’ultima versione con Rosetta, il livello che fa girare sui Mac nuovi i programmi scritti per i processori Intel. Alcuni software per album comprati anni fa con licenza perpetua, su macOS 28, non si apriranno più.

Per chi è in questa situazione abbiamo un’offerta fino al 31 dicembre 2027: Impaginatore Pro a {{prezzo_rosetta_pro}} o Studio a {{prezzo_rosetta_studio}}, una volta, IVA esclusa, mostrando la licenza o la fattura del vecchio programma.

Se conosci un fotografo che ci lavora ancora, giragli questo post: {{link_rosetta}}

#fotografia #macos #software
```

### U39 · venerdì 2 aprile 2027, 12:30 · Facebook (pagina) · Offerta macOS 28, su Facebook

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Resta tuo |
| Modello | U37-rosetta |
| Grafica | grafiche/uscite/U37-rosetta.png |
| Invito all’azione | Mandaci la licenza o la fattura |
| Link | {{link_rosetta}} |
| Hashtag | nessuno |
| Note | Come U37: dopo il parere del legale. |
| Caratteri | 316 in italiano |

Testo in italiano:

```text
Hai un vecchio software per album con licenza perpetua che su macOS 28 non si aprirà più?

Fino al 31 dicembre 2027: Impaginatore Pro a {{prezzo_rosetta_pro}} o Studio a {{prezzo_rosetta_studio}}, una volta, IVA esclusa. Basta mostrarci la licenza o la fattura del vecchio programma.

Come funziona: {{link_rosetta}}
```

## Settimana S6 · dal 5 aprile al 11 aprile

Dal piano di lancio: Contenuti degli educator, con i loro codici di affiliazione.

### U40 · martedì 6 aprile 2027, 12:30 · Instagram · Il video di un educator

| Campo | Valore |
|---|---|
| Formato | storia 9:16, condivisione |
| Pilastro | Mestiere |
| Modello | nessuno (condivisione del video dell’educator) |
| Grafica | nessuna |
| Invito all’azione | Guarda il video |
| Link | video dell’educator (adesivo link) |
| Hashtag | nessuno |
| Note | Solo se l’educator pubblica il video (PIANO-90-GIORNI, S6). Valori in costanti.json (educator.*). Il codice affiliato lo comunica l’educator, non noi. |
| Caratteri | 213 in italiano |

Testo in italiano:

```text
Testo sullo schermo: {{educator.nome}} ha provato Impaginatore sul suo canale {{educator.canale}}. Lo trovi qui sotto, con le sue opinioni: belle e meno belle.
Adesivo link: «Guarda il video» → video dell’educator
```

### U41 · mercoledì 7 aprile 2027, 12:30 · Instagram · Cinque controlli prima della stampa

| Campo | Valore |
|---|---|
| Formato | carosello 6 pagine 4:5 |
| Pilastro | Mestiere |
| Modello | carosello-copertina, carosello-interna (×4), carosello-chiusura |
| Grafica | da comporre (titoli delle pagine qui sotto) |
| Invito all’azione | Salva il post |
| Link | nessuno |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio #stampafotografica |
| Caratteri | 551 in italiano |

Testo in italiano:

```text
Cinque controlli prima di mandare un album in stampa. Salvalo per la prossima consegna.

1. Le foto ci sono tutte, e sono gli originali: non le anteprime.
2. Niente volti e niente testi nella zona della piega.
3. Le foto al vivo escono oltre il rifilo di tutta l’abbondanza.
4. I testi sono dentro il margine di sicurezza.
5. Hai riletto nomi e date con la coppia, per iscritto.

Che le foto ci siano tutte, Impaginatore lo controlla da solo prima di ogni export. Il resto è il tuo occhio.

#fotografodimatrimonio #albumdimatrimonio #stampafotografica
```

### U42 · venerdì 9 aprile 2027, 09:00 · LinkedIn (pagina Impaginatore) · Per chi fa formazione

| Campo | Valore |
|---|---|
| Formato | post di solo testo |
| Pilastro | Bottega |
| Modello | nessuno |
| Grafica | nessuna |
| Invito all’azione | Scrivici |
| Link | {{link_laboratori}} |
| Hashtag | #fotografia #formazione |
| Caratteri | 356 in italiano |

Testo in italiano:

```text
Fai formazione per fotografi di matrimonio, in aula o su YouTube?

Cerchiamo alcuni formatori a cui dare una licenza Pro gratuita per mostrare Impaginatore ai corsisti, con un accordo di affiliazione scritto per chi lo consiglia. Nessun obbligo di parlarne bene: ci interessa che venga mostrato com’è.

Scrivici: {{email_supporto}}

#fotografia #formazione
```

## Settimana S7 · dal 12 aprile al 18 aprile

Dal piano di lancio: Promemoria onesto sulla fine del prezzo di lancio; pacchetto «inizio stagione: 5 ore».

### U43 · martedì 13 aprile 2027, 12:30 · Instagram · Inizio stagione: 5 ore

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Assistenza e prova |
| Modello | scheda-ore |
| Grafica | grafiche/scheda-ore.png |
| Invito all’azione | Prenota le ore |
| Link | {{link_assistenza}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio |
| Note | Pacchetto «inizio stagione» (PIANO-90-GIORNI, S7): stessi prezzi del listino delle ore, nessuno sconto. |
| Caratteri | 439 in italiano |

Testo in italiano:

```text
La stagione dei matrimoni sta per cominciare. Se vuoi arrivarci con il programma già sistemato, prenota 5 ore di assistenza: 249 €, IVA esclusa, un solo pagamento.

Le usi a blocchi di 30 minuti, quando ti servono, per 12 mesi: un’ora adesso per i preset dei tuoi laboratori, mezz’ora a giugno quando arriva il primo album grande, un’ora per i PSD.

Se ti basta un’ora, sono 49 €. Link nella bio.

#fotografodimatrimonio #albumdimatrimonio
```

### U44 · giovedì 15 aprile 2027, 12:30 · Instagram · Promemoria onesto

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Resta tuo |
| Modello | scheda-prezzo |
| Grafica | grafiche/scheda-prezzo.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio |
| Note | Stessa settimana dell’email di promemoria (PIANO-90-GIORNI, S7). Una volta sola, senza conti alla rovescia. |
| Caratteri | 529 in italiano |

Testo in italiano:

```text
Un promemoria, una volta sola: il prezzo di lancio finisce il 23 aprile a mezzanotte, o prima se arriviamo a 300 licenze.

Essenziale 39 € fino al 23 aprile, poi 49 €. Pro 79 € fino al 23 aprile, poi 99 €. Studio 119 € fino al 23 aprile, poi 149 €. Sempre una volta, IVA esclusa.

Se sei a metà della prova e non hai ancora deciso, va bene così: la prova dura 30 giorni e il listino dopo il lancio resta quello. Se compri e non fa per te, hai 30 giorni per il rimborso.

Link nella bio.

#fotografodimatrimonio #albumdimatrimonio
```

### U45 · venerdì 16 aprile 2027, 09:00 · LinkedIn e Facebook · Il prezzo di lancio finisce il 23 aprile

| Campo | Valore |
|---|---|
| Formato | post con immagine 4:5 |
| Pilastro | Resta tuo |
| Modello | scheda-prezzo |
| Grafica | grafiche/scheda-prezzo.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} |
| Hashtag | #fotografia #software |
| Hashtag in inglese | #photography #software |
| Caratteri | 439 in italiano, 427 in inglese |

Testo in italiano:

```text
Il prezzo di lancio di Impaginatore finisce il 23 aprile a mezzanotte, o prima se arriviamo a 300 licenze.

Fino ad allora: Essenziale 39 € fino al 23 aprile, poi 49 €; Pro 79 € fino al 23 aprile, poi 99 €; Studio 119 € fino al 23 aprile, poi 149 €. Una volta, IVA esclusa.

Dopo, il listino non cambia per promozioni o ricorrenze. Se vuoi prima provare, la prova dura 30 giorni e non chiede la carta: {{link_prova}}

#fotografia #software
```

Testo in inglese («The launch price ends on 23 April»):

```text
Impaginatore’s launch price ends on 23 April at midnight, or earlier if we reach 300 licences.

Until then: Essenziale €39 until 23 April, then €49; Pro €79 until 23 April, then €99; Studio €119 until 23 April, then €149. One-time, VAT excluded.

After that, the list price doesn’t change for promotions or holidays. If you want to try it first, the trial lasts 30 days and needs no card: {{link_prova}}

#photography #software
```

## Settimana S8 · dal 19 aprile al 25 aprile

Dal piano di lancio: Fine del prezzo di lancio venerdì 23 aprile a mezzanotte, o prima a 300 licenze.

### U46 · martedì 20 aprile 2027, 12:30 · Instagram · Tre domande che ci fate

| Campo | Valore |
|---|---|
| Formato | reel 9:16, 45 s (copione V5) |
| Pilastro | Assistenza e prova |
| Modello | copertina-reel |
| Grafica | grafiche/copertina-reel.png (testo da cambiare: «Tre domande, tre risposte») |
| Invito all’azione | Scarica la prova |
| Link | {{link_prova}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio |
| Caratteri | 401 in italiano |

Testo in italiano:

```text
Le tre domande che ci fate più spesso, in 45 secondi.

Funziona senza connessione? Sì, dopo l’installazione non serve la rete.
Su quanti computer? Uno con Essenziale, 2 con Pro, 5 con Studio.
E se smetto di aggiornare? La versione che hai comprato resta tua e continua ad aprirsi.

Le altre risposte sono nella pagina delle domande frequenti. Link nella bio.

#fotografodimatrimonio #albumdimatrimonio
```

### U47 · giovedì 22 aprile 2027, 12:30 · Facebook (pagina) · Domani finisce il prezzo di lancio

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Resta tuo |
| Modello | scheda-prezzo |
| Grafica | grafiche/scheda-prezzo.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_prezzi}} |
| Hashtag | nessuno |
| Caratteri | 264 in italiano |

Testo in italiano:

```text
Domani, 23 aprile, finisce il prezzo di lancio di Impaginatore: Pro 79 € fino al 23 aprile, poi 99 €, una volta, IVA esclusa.

Non lo diciamo per metterti fretta: preferiamo che nessuno lo scopra il giorno dopo.

Prezzi e differenze tra le licenze: {{link_prezzi}}
```

### U48 · venerdì 23 aprile 2027, 09:00 · Instagram · Oggi l’ultimo giorno

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Resta tuo |
| Modello | scheda-prezzo |
| Grafica | grafiche/scheda-prezzo.png |
| Invito all’azione | Scarica la prova |
| Link | {{link_prezzi}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio |
| Note | Se le 300 licenze finiscono prima, al posto di questa uscita si pubblica un grazie (testo nel README, «Se il lancio finisce prima»). |
| Caratteri | 442 in italiano |

Testo in italiano:

```text
Oggi è l’ultimo giorno del prezzo di lancio. Fino a mezzanotte: Essenziale 39 € fino al 23 aprile, poi 49 €; Pro 79 € fino al 23 aprile, poi 99 €; Studio 119 € fino al 23 aprile, poi 149 €. Una volta, IVA esclusa.

Grazie a chi ha comprato in questi due mesi, e a chi ci ha scritto anche solo per una domanda. Da domani il listino resta quello che vedi, senza promozioni a sorpresa.

Link nella bio.

#fotografodimatrimonio #albumdimatrimonio
```

### U49 · venerdì 23 aprile 2027, 09:05 · Instagram e Facebook · Ultimo giorno, storia

| Campo | Valore |
|---|---|
| Formato | storia 9:16 |
| Pilastro | Resta tuo |
| Modello | U49-ultimo-giorno |
| Grafica | grafiche/uscite/U49-ultimo-giorno.png |
| Invito all’azione | Vai ai prezzi |
| Link | {{link_prezzi}} (adesivo link) |
| Hashtag | nessuno |
| Caratteri | 359 in italiano, 332 in inglese |

Testo in italiano:

```text
Testo sullo schermo: Ultimo giorno del prezzo di lancio. Fino a mezzanotte valgono questi prezzi; da domani si torna al listino, che resta quello.
Prezzi nella grafica: Essenziale 39 € fino al 23 aprile, poi 49 €; Pro 79 € fino al 23 aprile, poi 99 €; Studio 119 € fino al 23 aprile, poi 149 €. Una volta, IVA esclusa.
Adesivo link: «Prezzi» → {{link_prezzi}}
```

Testo in inglese («Last day, story»):

```text
On-screen text: Last day of the launch price. These prices hold until midnight; from tomorrow it’s the list price, and that stays.
Prices in the graphic: Essenziale €39 until 23 April, then €49; Pro €79 until 23 April, then €99; Studio €119 until 23 April, then €149. One-time, VAT excluded.
Link sticker: «Prices» → {{link_prezzi}}
```

## Riserva MCP, da pubblicare solo dopo il rilascio del server MCP

Queste uscite non hanno data. Si programmano solo quando il server MCP (T-203) e la sua guida (T-403) sono rilasciati, dopo aver verificato quali dati passano a Claude. Le grafiche hanno il nome che comincia con `mcp-` e una fascia «Riserva» da togliere quel giorno.

### R01 · senza data · Instagram · Claude prepara la bozza

**Riserva MCP: da pubblicare solo dopo il rilascio del server MCP.**

| Campo | Valore |
|---|---|
| Formato | post 4:5 |
| Pilastro | Bottega |
| Modello | mcp-bozza-claude |
| Grafica | grafiche/uscite/mcp-bozza-claude.png |
| Invito all’azione | Leggi la guida |
| Link | {{link_guida_claude}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio |
| Note | Prima di pubblicare: verificare con la guida T-403 quali dati passano a Claude (nomi dei file, metadati, anteprime) e scrivere la frase sulla riservatezza di conseguenza. Togliere dalla grafica la fascia «Riserva». |
| Caratteri | 469 in italiano |

Testo in italiano:

```text
Da oggi Impaginatore funziona con Claude.

Gli chiedi una prima bozza dell’album, con le tue indicazioni: formato, numero di spread, ordine della giornata. Claude prepara la bozza dentro l’editor tramite MCP. Poi decidi tu, spread per spread; quelli che hai già rifinito a mano non li tocca.

È una possibilità in più, non un obbligo: Impaginatore funziona come prima anche senza.

La guida per collegarlo è al link nella bio.

#fotografodimatrimonio #albumdimatrimonio
```

### R02 · senza data · LinkedIn (profilo del titolare) · Impaginatore e Claude, su LinkedIn

**Riserva MCP: da pubblicare solo dopo il rilascio del server MCP.**

| Campo | Valore |
|---|---|
| Formato | post con immagine 4:5 |
| Pilastro | Bottega |
| Modello | mcp-bozza-claude |
| Grafica | grafiche/uscite/mcp-bozza-claude.png |
| Invito all’azione | Leggi la guida |
| Link | {{link_guida_claude}} |
| Hashtag | #fotografia #software |
| Note | Stesse verifiche di R01. |
| Caratteri | 351 in italiano |

Testo in italiano:

```text
Impaginatore ora ha un server MCP: Claude può preparare la bozza di un album dentro l’editor, seguendo le indicazioni del fotografo.

Abbiamo tenuto ferma una regola: la bozza la prepara Claude, ogni spread lo decide il fotografo. Gli spread rifiniti a mano non vengono più toccati.

Guida al collegamento: {{link_guida_claude}}

#fotografia #software
```

### R03 · senza data · Instagram · Dalla richiesta alla bozza

**Riserva MCP: da pubblicare solo dopo il rilascio del server MCP.**

| Campo | Valore |
|---|---|
| Formato | reel 9:16, 40 s |
| Pilastro | Mestiere |
| Modello | copertina-reel |
| Grafica | da comporre: mcp-copertina-reel (copia di copertina-reel con meta mcp) |
| Invito all’azione | Leggi la guida |
| Link | {{link_guida_claude}} (nella bio) |
| Hashtag | #fotografodimatrimonio #albumdimatrimonio |
| Note | Copione da scrivere dopo il rilascio, con l’interfaccia vera. Stesse verifiche di R01. |
| Caratteri | 282 in italiano |

Testo in italiano:

```text
Scrivo a Claude che cosa voglio: album 30 × 30 cm, una quarantina di spread, la cerimonia in ordine di tempo. Claude prepara la bozza dentro Impaginatore. Poi la riprendo io, spread per spread.

La guida per collegarlo è al link nella bio.

#fotografodimatrimonio #albumdimatrimonio
```
