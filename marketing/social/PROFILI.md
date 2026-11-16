# Profili social: nomi, biografie, in evidenza, link

Testi pronti per aprire i profili quando il titolare lo deciderà. **Nessun profilo è stato aperto e nessun nome è stato registrato o controllato sui servizi**: la disponibilità dei nomi utente si verifica il giorno dell’apertura, nell’ordine indicato.

I limiti di lunghezza e le fonti sono in `STRATEGIA.md` §6. Ogni riquadro qui sotto è preceduto da un commento `campo` che `strumenti/controlla_testi.py` usa per misurarlo. I link sono segnaposto da riempire in `strumenti/costanti.json`.

**Il link nella bio** è uno solo per canale e punta a una pagina del nostro sito con i link del momento (lista d’attesa prima del lancio, prova e prezzi dopo). Niente servizi esterni di «link in bio»: un conto in meno da aprire e nessun tracciamento di terzi. Prima del lancio la pagina rimanda a `{{link_lista}}`, dal 23 febbraio a `{{link_prova}}` e `{{link_prezzi}}`.

**Immagini:** foto del profilo `grafiche/profilo-verde.png` (consigliata: si riconosce anche piccola) o `grafiche/profilo.png`; copertine in `grafiche/copertina-*.png`. Si rigenerano con `strumenti/genera_grafiche.py`.

## Nome utente, uguale ovunque

Proposta: **impaginatore**. Alternative, in quest’ordine se il primo è preso: `impaginatore.album`, `impaginatore_app`, `impaginatoreapp`, `impaginatore.it`.

Un nome solo su tutti i canali, anche quelli che non usiamo subito (TikTok, Threads): chi ci cerca su un canale ci trova anche sugli altri, e nessuno può prendere il nome al posto nostro. Su YouTube l’handle ha da 3 a 30 caratteri; su TikTok il nome utente al massimo 24: `impaginatore` (12) va bene ovunque.

## Instagram (canale principale)

Nome (si cerca anche per questo, massimo 30 caratteri):

<!-- campo canale=instagram tipo=nome lingua=it -->
```text
Impaginatore album matrimonio
```

Biografia in italiano (massimo 150 caratteri):

<!-- campo canale=instagram tipo=bio lingua=it -->
```text
Il programma per impaginare album di matrimonio sul tuo computer. Le foto restano tue. Paghi una volta. Fatto da un fotografo.
```

Biografia in inglese, per quando il profilo parlerà anche a fotografi di altri paesi:

<!-- campo canale=instagram tipo=bio lingua=en -->
```text
Wedding album design software that runs on your computer. Your photos stay yours. Pay once. Made by a photographer.
```

Categoria: «Software». Pulsanti di contatto: solo email (`{{email_supporto}}`), niente telefono. Link: `{{sito}}`, pagina dei link del momento.

**In evidenza** (le storie fissate sotto la biografia; titoli corti perché sul telefono se ne leggono circa 15 caratteri). Copertine: fondo Carta, icone del brand in Inchiostro (stile delle icone di `brand/`), una per gruppo.

| Titolo | Che cosa contiene | Da quali uscite |
|---|---|---|
| Foto tue | La prova del wi‑fi, le tre promesse, dove finiscono le foto | U02, U06, U35 |
| Prezzi | Le tre licenze, prima con i prezzi di lancio e dal 24 aprile con il listino | U15, U22, U44 |
| Prova | Com’è fatta la prova, il primo album | U16, U25 |
| Assistenza | Le ore con una persona, che cosa resta gratis | U23, U43 |
| Mestiere | I consigli di bottega numerati | U07, U28, U36, U41 |
| Laboratori | Misure del laboratorio, cataloghi, edizione per laboratori (in arrivo) | U24, U32 |

Testi delle copertine «In evidenza» (uno per riga, nello stesso ordine):

<!-- campo canale=instagram tipo=evidenza lingua=it -->
```text
Foto tue
Prezzi
Prova
Assistenza
Mestiere
Laboratori
```

## Facebook (pagina, specchio di Instagram)

Nome della pagina: **Impaginatore**. Nome utente: `impaginatore` (stesse alternative). Categoria: «Software». Pulsante d’azione: «Iscriviti» verso `{{link_lista}}` fino al lancio, poi «Scopri di più» verso `{{link_prova}}`.

Descrizione breve (campo «Informazioni», massimo 255 caratteri):

<!-- campo canale=facebook tipo=descrizione lingua=it -->
```text
Impaginatore è un programma per impaginare album di matrimonio sul tuo computer. Le foto restano nelle tue cartelle, la licenza si paga una volta e non scade. Lo ha scritto un fotografo, per il suo lavoro.
```

<!-- campo canale=facebook tipo=descrizione lingua=en -->
```text
Impaginatore is software for laying out wedding albums on your computer. Your photos stay in your own folders; the licence is paid once and doesn’t expire. A photographer wrote it for his own work.
```

Gruppi: la pagina non pubblica nei gruppi di fotografi. Ci partecipa il fondatore, dal suo profilo personale, rispondendo a domande sull’impaginazione e citando il programma solo se pertinente e se il regolamento del gruppo lo consente (STRATEGIA.md §2).

## YouTube

Nome del canale: **Impaginatore**. Handle: `@impaginatore`. Banner: `grafiche/copertina-youtube.png` (2560 × 1440, testo nel centro 1546 × 423). Link nel canale: `{{sito}}`, `{{link_prova}}`, `{{link_manuale}}`.

Descrizione del canale in italiano (massimo 1000 caratteri):

<!-- campo canale=youtube tipo=descrizione lingua=it -->
```text
Impaginatore è un programma per impaginare album di matrimonio sul tuo computer, scritto da un fotografo per il suo lavoro.

Qui trovi le guide: come si imposta un album con le misure del tuo laboratorio, come si esporta in JPG, PDF e PSD a livelli. Video brevi, senza musica di sottofondo e senza fretta.

Tre cose che non cambiano: le foto restano sul tuo computer, la licenza si paga una volta, le misure sono in millimetri.

Domande e segnalazioni: {{email_supporto}}
```

<!-- campo canale=youtube tipo=descrizione lingua=en -->
```text
Impaginatore is wedding album design software that runs on your computer, written by a photographer for his own work.

Here you will find the guides: how to set up an album with your lab’s measurements, how to export JPG, PDF and layered PSD. Short videos, no background music, no rush.

Three things that don’t change: your photos stay on your computer, the licence is paid once, measurements are in millimetres.

Questions and reports: {{email_supporto}}
```

Playlist iniziali: «Il primo album», «Consigli di bottega», «Brevi» (gli Shorts).

## LinkedIn

### Pagina aziendale

Nome: **Impaginatore**. URL: `linkedin.com/company/impaginatore`. Logo: `grafiche/profilo.png`; copertina: `grafiche/copertina-linkedin.png` (1512 × 256). Settore: «Sviluppo di software». Sito: `{{sito}}`.

Slogan (tagline, massimo 120 caratteri):

<!-- campo canale=linkedin tipo=tagline lingua=it -->
```text
Software per impaginare album fotografici sul computer del fotografo. Licenza perpetua. Presto, edizioni per laboratori.
```

<!-- campo canale=linkedin tipo=tagline lingua=en -->
```text
Photo album design software that runs on the photographer’s computer. Perpetual licence. Lab editions coming.
```

Descrizione (massimo 2000 caratteri):

<!-- campo canale=linkedin tipo=descrizione lingua=it -->
```text
Impaginatore è un programma desktop per impaginare album fotografici, nato dal lavoro di un fotografo di matrimoni. È pensato per Mac, Windows e Linux.

Per i fotografi: impaginazione sul proprio computer, con le foto nelle proprie cartelle; nessuna funzione le carica in rete. Misure in millimetri con i valori del laboratorio, export in JPG, PDF e PSD a livelli. La licenza si paga una volta e non scade.

Per i laboratori di stampa: stiamo preparando un’edizione con il catalogo dei vostri formati e il vostro marchio, perché i file arrivino già con le misure giuste.

Per chi fa formazione: licenze per mostrare il programma ai corsisti.

Contatti: {{email_supporto}}
```

<!-- campo canale=linkedin tipo=descrizione lingua=en -->
```text
Impaginatore is desktop software for laying out photo albums, born from the work of a wedding photographer. It is designed for Mac, Windows and Linux.

For photographers: layout on your own computer, with the photos in your own folders; no feature uploads them. Measurements in millimetres with your lab’s values, export to JPG, PDF and layered PSD. The licence is paid once and doesn’t expire.

For print labs: an edition with your catalogue of formats and your brand, so files arrive with the right measurements.

For educators: licences to show the software to your students.

Contact: {{email_supporto}}
```

### Profilo personale del titolare

Copertina: `grafiche/copertina-linkedin-profilo.png` (1584 × 396; la foto del profilo copre l’angolo in basso a sinistra, lì non c’è niente). Esperienza: «Fondatore, Impaginatore». Il profilo personale pubblica le uscite marcate «LinkedIn (profilo del titolare)» nel calendario: è lì che i laboratori e le associazioni leggono, più che sulla pagina.

Riga sotto il nome, proposta (adattarla al titolo vero del titolare):

<!-- campo canale=linkedin tipo=titolo-profilo lingua=it -->
```text
Fondatore di Impaginatore · Software per album fotografici, sul computer del fotografo
```

## Solo il nome, per ora: TikTok e Threads

Non si pubblica al lancio (STRATEGIA.md §2). Si prende solo il nome `impaginatore`, con questa biografia, per non lasciarlo ad altri. Threads usa il nome di Instagram.

<!-- campo canale=tiktok tipo=bio lingua=it -->
```text
Album di matrimonio impaginati sul tuo computer. Paghi una volta.
```

<!-- campo canale=threads tipo=bio lingua=it -->
```text
Il programma per impaginare album di matrimonio sul tuo computer. Le foto restano tue. Paghi una volta.
```
