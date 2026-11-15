# Requisiti e KPI estratti dai vocali dell'ideatore

Fonte: quattro messaggi vocali del 15/11/2026 (19:13, 19:18, 19:19, 19:21; 8 minuti e mezzo in tutto), trascritti in locale con Whisper `large-v3-turbo`. Le trascrizioni integrali non sono nel repository; qui c'è ciò che ne deriva per il prodotto.

## Cosa ha detto, in sintesi

1. **Le foto restano sul computer.** È l'unico vincolo dichiarato come non negoziabile: caricare le foto online è troppo pesante. Il programma può girare nel browser o come applicazione a sé, purché in locale.
2. **Oggi funziona così:** un'app lancia tutto e apre il browser; JPG e PDF li genera da solo, i PSD passano da Photoshop.
3. **I laboratori sono un mercato.** Idea: un Impaginatore personalizzato per ciascun laboratorio, con il suo catalogo di album. Il fotografo sceglie la configurazione dell'album (copertina, formato, carta), impagina, e alla fine consegna gli spread già conformi alle specifiche di stampa. Variante: il fotografo accede con le credenziali del laboratorio e il programma carica da solo il catalogo di quel laboratorio.
4. **I fotografi sono l'altro mercato.** I due programmi che contano sono SmartAlbums (Pixellu) e Fundy Designer, entrambi in abbonamento; gli altri fotografi usano InDesign.
5. **Licenza senza abbonamento.** A molti fotografi l'abbonamento non piace, e i programmi venduti una volta sola non esistono più. L'ideatore usa ancora uno SmartAlbums del 2012 che smetterà di funzionare quando macOS toglierà Rosetta: è da lì che nasce il progetto.
6. **L'interfaccia ricalca SmartAlbums.** Parole sue: stessa impostazione, stessi modelli, con funzioni in più e grafica un po' diversa. Si chiede lui stesso se possa essere un problema.
7. **Il punto di forza è l'intelligenza artificiale che lavora dentro il programma.** Ha trascinato a Claude la cartella delle foto scelte e quella degli originali: Claude ha creato l'impaginazione direttamente nell'editor, e lui ha rifinito a mano. Vuole che diventi un collegamento vero (MCP), come quello che usa con DaVinci Resolve: si lavora da soli oppure con l'AI. «Questa non la fa nessuno.»
8. **Bisogna fare presto.** Il mercato è fermo da anni; gli è già capitato di vedere un'idea sua uscire come prodotto altrui il giorno dopo.
9. L'interfaccia è curata ma migliorabile; il programma va aggiornato di continuo.

## Decisioni che ne derivano

| # | Decisione | Motivo |
|---|---|---|
| D1 | Applicazione desktop a sé (finestra propria), non sito web | Vincolo 1; un prodotto venduto non può aprirsi in una scheda del browser con un terminale dietro |
| D2 | Licenza perpetua, pagamento una tantum, tre fasce | Punto 5; scelta confermata dal committente |
| D3 | Server MCP come funzione di prima classe | Punto 7: è la differenza rispetto ai concorrenti |
| D4 | Interfaccia e marca ridisegnate per distinguersi da SmartAlbums | Punto 6: rischio legale e di immagine |
| D5 | Edizione Laboratorio come secondo prodotto, costruita su «pacchetti catalogo» | Punto 3; l'accesso con credenziali del laboratorio viene dopo |
| D6 | Dal pagamento al primo spread in meno di cinque minuti | Punto 8 e richiesta del committente |

## KPI

| KPI | Obiettivo | Come si misura |
|---|---|---|
| Foto caricate online | 0, sempre | Nessuna chiamata di rete con contenuto delle foto; test automatico che lo verifica |
| Tempo dall'acquisto al primo spread | meno di 5 minuti | Prova cronometrata su macchina pulita, per sistema operativo |
| Passaggi di installazione | 1 installer, 1 chiave | Conteggio dei clic nella prova |
| Sistemi supportati | macOS (Apple Silicon e Intel), Windows 10/11, Linux | Installer prodotti e provati dalla CI |
| Copertura dei test | 100 % righe e rami del codice Python | `pytest --cov`, soglia bloccante in CI |
| Rilievi di sicurezza aperti, gravità critica o alta | 0 | `docs/audit/rilievi.json` |
| Bozza di un album da 80 foto con l'AI | meno di 10 minuti, senza toccare l'editor | Prova con il server MCP |
| Somiglianza con SmartAlbums | nessun elemento riconoscibile | Revisione dell'interfaccia contro l'elenco dell'audit (rilievi `LEG-*`) |
| Laboratori contattati con offerta pilota | 10 a priorità A nel primo mese | `docs/mercato/lead.csv` |
