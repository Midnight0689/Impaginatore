# Sicurezza

## Versioni supportate

| Versione | Correzioni di sicurezza |
|---|---|
| 2.x (in sviluppo sul ramo `prodotto/2.0`) | Sì |
| 1.x (versione amatoriale sul ramo `main`) | No: chi la usa passerà alla 2.0 |

## Come segnalare una vulnerabilità

Scrivi a **[CONTATTO DA DEFINIRE: indirizzo email dedicato alla sicurezza]**.

Non aprire una segnalazione (issue), una discussione o una pull request per una vulnerabilità: resterebbe leggibile da tutti quelli che hanno accesso al repository prima che ci sia una correzione.

Nel messaggio indica:

- versione dell'Impaginatore e sistema operativo;
- che cosa permette di fare la vulnerabilità e a chi;
- i passi per riprodurla, oppure una prova di concetto;
- se vuoi essere citato nelle note della correzione, e con quale nome.

Non mandare foto di persone reali: se serve un'immagine per riprodurre il problema, usa una foto di prova.

## Cosa succede dopo

- Conferma di ricezione entro **[DA CONFERMARE: 5 giorni lavorativi]**.
- Una prima valutazione (confermata o no, gravità) entro **[DA CONFERMARE: 15 giorni lavorativi]**.
- La correzione esce in una nuova versione; la descrizione della vulnerabilità si pubblica dopo, d'accordo con chi l'ha segnalata.

## Cosa interessa di più

- Qualunque modo di far uscire dal computer le foto dell'utente: il programma non deve mai caricarle in rete.
- Eseguire codice aprendo un progetto o un archivio ZIP ricevuto da altri.
- Comandare l'editor o la schermata dei progetti da un sito aperto nel browser (il server interno ascolta su 127.0.0.1).
- Installare un aggiornamento o un installer senza che la firma venga verificata.
- Attivare il programma con una chiave di licenza contraffatta.
- Il server MCP: azioni sui file dell'utente oltre a quelle previste.

## Fuori ambito

- Attacchi che richiedono di avere già il controllo del computer o dell'account dell'utente.
- Problemi della versione 1.x che non esistono nella 2.x.
- Vulnerabilità di Photoshop, del sistema operativo o del browser.

## Controlli automatici

A ogni modifica e ogni settimana girano l'analisi statica del codice, la ricerca di vulnerabilità note nelle dipendenze, la ricerca di segreti nella storia git e il controllo delle licenze delle dipendenze (`.github/workflows/sicurezza.yml`). Gli stessi controlli si eseguono in locale con `python strumenti/controlli.py sicurezza`.
