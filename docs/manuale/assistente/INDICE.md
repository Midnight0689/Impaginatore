# L'assistente AI collegato a Impaginatore

Puoi collegare a Impaginatore un assistente AI, per esempio Claude. Gli chiedi a parole cosa fare sull'album («prepara
una bozza con tre foto per spread», «controlla l'album») e lui lo fa nel programma, mentre tu guardi.

Il collegamento usa MCP (Model Context Protocol), il sistema con cui Claude e altri assistenti usano programmi
esterni.

1. [Cos'è e cosa può fare](01-cos-e.md)
2. [Cosa vede l'assistente e cosa esce dal computer](02-cosa-vede.md) — **da leggere prima di collegarlo**
3. [Collegare Claude Desktop o Claude Code](03-collegare.md)
4. [Dieci richieste di esempio](04-esempi.md)
5. [Se non funziona](05-problemi.md)

In breve:

- L'assistente c'è nelle licenze Pro e Studio e nella prova gratuita.
- Ogni modifica dell'assistente la vedi nell'editor e la annulli con Ctrl+Z, come le tue.
- Di serie l'assistente riceve solo testo: nomi, misure, date, disposizioni. Le immagini gli arrivano solo se le
  accendi tu.
- Quello che l'assistente riceve va al suo fornitore (per Claude, Anthropic), fuori dal tuo computer.

Per chi sviluppa: i dettagli tecnici sono in [`docs/architettura/MCP.md`](../../architettura/MCP.md).
