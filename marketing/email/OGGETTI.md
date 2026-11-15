# Oggetti e preheader

Tre varianti per ogni email. La variante **A** è quella già scritta nel preheader dei sorgenti (il primo `<div>` nascosto dopo `<mj-body>`); se scegli B o C, cambia anche quel testo, oppure usa il campo «testo di anteprima» del servizio e togli il nostro, per non averne due.

Regole seguite:
- **Oggetto**: fra 21 e 50 caratteri, con la parte che conta nei primi 35, perché è quanto mostra un telefono. Il conteggio include i segnaposto così come sono: con i valori veri cambia di poco.
- **Preheader**: fra 40 e 110 caratteri. Completa l’oggetto, non lo ripete.
- Niente punti esclamativi, niente emoji, niente maiuscole gridate.
- Niente parole che i filtri e la marca puniscono: gratis, offerta, sconto, urgente, ultima occasione, garantito, «100%», e le parole vietate di `brand/STYLEBOOK.md` (lo stesso elenco che controlla `strumenti/compila.py`).
- Prezzi solo nella forma «69 € fino al {{data_fine_lancio}}, poi 89 €», mai barrati.
- Nell’email Rosetta, nessun marchio di concorrenti, né nell’oggetto né nel testo.
- Per i laboratori l’oggetto è quello di una lettera, non di una newsletter. Il seguito parte come **risposta** al primo messaggio (variante A, «Re: …»), così chi legge ha il contesto.

Il piano di lancio propone per il primo contatto l’oggetto «I file dei vostri fotografi già conformi, impaginati in metà tempo». Qui non c’è: «in metà tempo» non è ancora misurato. Si potrà usare dopo i piloti, quando i dati lo dimostrano.

Come scegliere: per le campagne alla lista, prova A contro B su una parte della lista (con Brevo, il test A/B è nel piano Standard). Per le email di servizio basta la A: chi le riceve le aspetta.

### benvenuto-chiave

servizio · subito dopo l'emissione della chiave

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | La tua licenza Impaginatore {{fascia}} | 38 | La chiave, il pulsante per attivarla e tre passi fino al primo spread. Conserva questa email. | 93 |
| B | Impaginatore {{fascia}}: la tua chiave | 38 | Pagamento ricevuto, fattura in allegato. L’attivazione avviene sul tuo computer, senza internet. | 96 |
| C | Chiave e fattura di Impaginatore {{fascia}} | 43 | Il pagamento è arrivato. Dentro: la chiave, come installare e il primo spread in cinque minuti. | 95 |

### benvenuto-chiave.en

service · right after the key is issued

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Your Impaginatore {{fascia}} licence | 36 | Your key, the button to activate it and three steps to your first spread. Keep this email. | 90 |
| B | Impaginatore {{fascia}}: your key | 33 | Payment received, invoice attached. Activation happens on your computer, with no internet needed. | 97 |
| C | Your key and invoice for Impaginatore {{fascia}} | 48 | Payment received. Inside: your key, how to install, and your first spread in five minutes. | 90 |

### lancio

campagna · 21/02 accesso anticipato (variante C), 23/02 ore 9 apertura (A o B)

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Impaginatore è pronto | 21 | Licenza perpetua: Pro costa 69 € fino al {{data_fine_lancio}}, poi 89 €. Le foto restano sul tuo computer. | 106 |
| B | Lo paghi una volta, e resta tuo | 31 | Impaginatore è disponibile: tre licenze, nessun abbonamento. Pro 69 € fino al {{data_fine_lancio}}, poi 89 €. | 109 |
| C | Per te, 48 ore prima: Impaginatore | 34 | Sei nella lista d’attesa: puoi comprarlo da oggi, al prezzo di lancio. Per tutti si apre il {{data_apertura}}. | 110 |

### lancio.en

campaign · same dates as the Italian version

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Impaginatore is ready | 21 | A perpetual licence: Pro is €69 until {{data_fine_lancio}}, then €89. Your photos stay on your computer. | 104 |
| B | Pay once, and it stays yours | 28 | Three licences, no subscription. Pro is €69 until {{data_fine_lancio}}, then €89. | 81 |
| C | For you, 48 hours early: Impaginatore | 37 | You’re on the waiting list, so you can buy it today at the launch price. It opens to everyone on {{data_apertura}}. | 115 |

### prova-giorno-1

campagna automatica · giorno 1 della prova

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Il primo spread in cinque minuti | 32 | Tre cose da provare oggi, con l’album di esempio o con le tue foto. Bastano dieci minuti. | 89 |
| B | Da dove partire con Impaginatore | 32 | Album di esempio, preset del tuo laboratorio, un export da guardare da vicino: tre passi per oggi. | 98 |
| C | La tua prova di 30 giorni è partita | 35 | Le funzioni del Pro tranne il PSD, nessun limite di spread. Ecco il primo passo. | 80 |

### prova-giorno-7

campagna automatica · giorno 7

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Una settimana dopo: come va? | 28 | Spaziature uniformi, tono uniforme, modelli personali: tre cose che fanno risparmiare tempo sull’album intero. | 110 |
| B | Tre funzioni che si scoprono tardi | 34 | Spazi e margini di tutto l’album con un comando, e i tuoi spread salvati come modelli. | 86 |
| C | Che cosa ti sta frenando? | 25 | Una domanda sola, e tre funzioni per l’album intero. Rispondi con una riga: leggo tutto. | 88 |

### prova-scadenza

campagna automatica · 3 giorni prima della scadenza (C solo durante il lancio)

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | La prova finisce il {{data_scadenza_prova}} | 43 | I tuoi album restano sul computer. Con la licenza riparti da dove sei, senza reinstallare. | 90 |
| B | Cosa succede ai tuoi album dopo la prova | 40 | Restano sul tuo computer, in sola lettura. Con la chiave riparti da dove sei. | 77 |
| C | Ultimi giorni di prova | 22 | Pro 69 € fino al {{data_fine_lancio}}, poi 89 €. Paghi una volta, la licenza non scade. | 87 |

### rosetta

campagna · S5, dopo la revisione legale; nessun marchio di concorrenti

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Il tuo programma per album si aprirà ancora? | 44 | Come controllare in un minuto se il tuo programma per album si aprirà ancora, e cosa fare prima di aggiornare. | 110 |
| B | macOS 28 e i vecchi programmi per album | 39 | Dopo macOS 27 Rosetta resta solo per alcuni giochi. Un controllo di un minuto, e cosa salvare prima. | 100 |
| C | Prima di aggiornare il Mac a macOS 28 | 37 | Se il tuo programma per album è solo Intel, esporta gli album che potresti dover riaprire. | 90 |

### laboratori-primo-contatto

da persona a persona · G1, a mano

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Preset {{nome_laboratorio}} per Impaginatore | 44 | Un preset con i vostri formati, abbondanze e piega, e un video di 90 secondi. | 77 |
| B | I vostri formati, già impostati per i fotografi | 47 | Un programma per album con il vostro catalogo dentro: i file vi arrivano già conformi. | 86 |
| C | File dei fotografi conformi alle vostre specifiche | 50 | Abbondanze e piega del {{formato_esempio}} già impostate. Video di 90 secondi. | 78 |

### laboratori-seguito

da persona a persona · G5, come risposta nella stessa conversazione

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Re: Preset {{nome_laboratorio}} per Impaginatore | 48 | L’album di prova esportato secondo le vostre specifiche, e un pilota di 90 giorni. | 82 |
| B | Album di prova nel vostro {{formato_esempio}} | 45 | Esportato secondo le vostre specifiche, da far controllare alla prestampa. | 74 |
| C | Un pilota di 90 giorni per {{nome_laboratorio}} | 47 | Da 10 a 20 vostri fotografi, con il vostro catalogo già impostato. | 66 |

### aggiornamento

campagna · a ogni versione

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Impaginatore {{versione}} è disponibile | 39 | {{novita_1_titolo}}, {{novita_2_titolo}} e altro. Inclusa nella tua licenza: te la propone il programma. | 104 |
| B | Impaginatore {{versione}}: {{novita_1_titolo}} | 46 | Tre novità e le correzioni. L’aggiornamento è incluso nella tua licenza. | 72 |
| C | Cosa cambia in Impaginatore {{versione}} | 40 | {{novita_1_titolo}} e altre due novità. Progetti, modelli e licenza restano come sono. | 86 |

### aggiornamento.en

campaign · every release

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Impaginatore {{versione}} is out | 32 | {{novita_1_titolo}}, {{novita_2_titolo}} and more. Included in your licence: the app offers it to you. | 102 |
| B | Impaginatore {{versione}}: {{novita_1_titolo}} | 46 | Three new features and the fixes. The update is included in your licence. | 73 |
| C | What’s new in Impaginatore {{versione}} | 39 | {{novita_1_titolo}} and two more changes. Projects, layouts and licence stay as they are. | 89 |

### rimborso-conferma

servizio · quando il bonifico di rimborso è partito

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Rimborso fatto: {{importo_rimborso}} | 36 | Il bonifico di {{importo_rimborso}} è partito. I tuoi album restano sul tuo computer. | 85 |
| B | Il tuo rimborso Impaginatore | 28 | Bonifico partito il {{data_rimborso}}, nota di credito in allegato. | 67 |
| C | Rimborso della richiesta {{numero_richiesta}} | 45 | Rimborso completo, già partito. Se vuoi, dicci cosa non ha funzionato. | 70 |

### attivazione-problema

servizio · risposta dell'assistenza; meglio come risposta al messaggio del cliente

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Sistemiamo l’attivazione di Impaginatore | 40 | Cosa fare, passo per passo. Se non basta, rispondi con uno screenshot. | 70 |
| B | Re: (l’oggetto scritto dal cliente) | 35 | Cosa fare, passo per passo. Se non basta, rispondi con uno screenshot. | 70 |
| C | Impaginatore: come attivare la chiave | 37 | La chiave va copiata tutta, circa 200 caratteri. Te la rimandiamo, con il pulsante. | 83 |

### assistenza-ore

servizio · dopo il pagamento delle ore

| | Oggetto | Car. | Preheader | Car. |
|---|---|---|---|---|
| A | Assistenza Impaginatore: ore confermate | 39 | Pagamento ricevuto. Rispondi con due o tre orari e l’argomento: ti mandiamo il link della videochiamata. | 104 |
| B | Le tue ore di assistenza sono pronte | 36 | Da usare a blocchi di 30 minuti entro il {{scadenza_ore}}. Si prenota rispondendo. | 82 |
| C | Prenota la tua assistenza Impaginatore | 38 | Due o tre orari e l’argomento, in risposta a questa email. Fattura in allegato. | 79 |
