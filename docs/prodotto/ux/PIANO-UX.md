# Piano UX: cosa entra nella 2.0 (T-209)

Divide le proposte di [`PROPOSTE.md`](PROPOSTE.md) in tre gruppi, le lega ai compiti T-201…T-208 di `docs/PIANO.md` e propone un ordine. Il gruppo «entro la 2.0» è quello che T-205 realizza; la scelta finale spetta al titolare.

## Come si è scelto

Una proposta entra nella 2.0 se vale almeno una di queste condizioni:

1. **È venduta.** `docs/mercato/tier.json` promette in Pro e Studio `impaginazione_automatica_album`, `correzione_spaziature_album`, `uniformita_tono`, `preset_laboratori` (anche in Essenziale) ed `export_psd_livelli`. Oggi l'impaginazione automatica dell'album non esiste e l'uniformità del tono non si può applicare dall'interfaccia.
2. **Corregge un problema di gravità 4 o un difetto che produce un risultato sbagliato** (A-03, A-18, A-23).
3. **È un obbligo già scritto.** LEG-003 (caratteri) e LEG-004 (somiglianza con il concorrente) devono essere chiusi da T-205.
4. **Serve al KPI D6**, dal pagamento al primo spread in meno di 5 minuti.

## I tre gruppi

### Entro la 2.0

| ID | Proposta | Sforzo | Perché ora | Dipende da |
|---|---|---|---|---|
| UX-011 | Stampa dagli originali, con abbondanza | M | difetto: file da stampa ricavati dalle miniature (A-18, gravità 4) | — |
| UX-004 | Ricollega sicuro | S | difetto: collega una foto alla sua miniatura (A-23) | — |
| UX-012 | Editor subito, foto preparate in sottofondo, import senza riavvio | M | gravità 4 (A-03); KPI D6 | — |
| UX-001 | Altra disposizione con un tasto | S | azione «un pulsante» più frequente | — |
| UX-002 | Sostituisci e riadatta | S | azione «un pulsante»; evita tagli ×2,28 | — |
| UX-003 | Annulla che dice cosa annulla, niente conferme inutili | S | fiducia; serve a tutte le azioni «un pulsante» | — |
| UX-005 | Recupero di un album danneggiato | S | un utente pagante non deve perdere un album | UX-022 |
| UX-006 | Menu contestuale per compiti | S | parte del ridisegno | — |
| UX-007 | Messaggi riscritti | S | parte del ridisegno | T-206 |
| UX-008 | Stati vuoti che portano avanti | S | primo avvio, KPI D6 | — |
| UX-009 | Aggiornamento dal vivo | S | senza, l'MCP non si vede lavorare (A-32) | T-203 |
| UX-010 | Tono in parole e «Uniforma» | S–M | `uniformita_tono` venduta | UX-014 |
| UX-013 | Consegna | M | `preset_laboratori` venduta in tutte le fasce; fine del flusso | UX-011, T-208 |
| UX-014 | Controlla e Sistema | M–L | `correzione_spaziature_album` venduta; nessun controllo di contenuto oggi | — |
| UX-015 | Trascina la cartella | M | KPI D6 | T-201 |
| UX-016 | Tela grande e barra della selezione | M | struttura del ridisegno | T-005 |
| UX-017 | Primo avvio con prova senza moduli | M | KPI D6 | T-202 |
| UX-018 | Prepara la bozza | L | `impaginazione_automatica_album` venduta e assente | UX-003; da progettare insieme a T-203 |
| UX-019 (minimo) | Tab libero, nomi accessibili, bersagli, movimento ridotto, scorciatoie per sistema | S | gravità 3 (A-34); costa poco dentro UX-016 | — |
| UX-021 | Altre disposizioni come provini | M | LEG-004 | UX-001 |
| UX-022 | Schermata Album a scaffale | M | LEG-004 | — |
| UX-023 | Testo con caratteri OFL | M | LEG-003 | T-005 |

**Se il tempo non basta**, il taglio minimo per il lancio è: UX-011, UX-004, UX-012, UX-001, UX-002, UX-003, UX-016, UX-021, UX-022, UX-023 (gli obblighi), UX-014 nella sola parte «Controlla» e UX-013 senza i pacchetti dei laboratori. In quel caso `tier.json` va riallineato prima di vendere: `impaginazione_automatica_album` e `uniformita_tono` non possono restare fra le funzioni Pro se non ci sono.

### 2.1

| ID | Proposta | Sforzo | Perché dopo |
|---|---|---|---|
| UX-019 (resto) | Tastiera completa sulla tela, verifica con uno strumento di accessibilità, 200 % | M | il minimo è nella 2.0 |
| UX-020 | Salvataggio visibile e versioni con nome | M | utile, non blocca la vendita; il salvataggio automatico c'è già |
| UX-024 | Copertina | L | dipende dai pacchetti dei laboratori (T-208) e dalla loro descrizione delle copertine |
| UX-026 | Tema chiaro | S | il tema scuro è il predefinito; costa poco una volta usati i token |

### Più avanti

| ID | Proposta | Perché |
|---|---|---|
| UX-025 | Revisione col cliente: versioni a confronto, PDF solo degli spread cambiati | serve UX-020; da progettare con i fotografi pilota |
| — | Invio diretto ai laboratori | richiede credenziali e accordi con i laboratori; resta escluso ogni invio di foto senza un'azione esplicita dell'utente verso un servizio da lui scelto |

## Legami con il piano

| Compito | Cosa serve dalle proposte | Cosa serve alle proposte |
|---|---|---|
| T-201 Finestra desktop | menu nativi e scorciatoie per sistema ([architettura](ARCHITETTURA-INTERFACCIA.md#menu-dellapplicazione)); niente `confirm()`; misura minima 1024 × 700 | il percorso completo della cartella trascinata (UX-015); le finestre di sistema al posto dello sfoglia file interno |
| T-202 Licenze e prova | il primo avvio senza moduli e la chiave incollabile (UX-017); le voci con il lucchetto senza finestre insistenti; filigrana detta prima della consegna | lo stato della licenza per spegnere Prepara la bozza, Sistema album, Uniforma l'album e A Photoshop in Essenziale |
| T-203 Server MCP | le operazioni `bozza`, `controlla`, `sistema`, `sostituisci` (UX-018, UX-014, UX-002) si scrivono una volta nel motore e servono sia ai pulsanti sia all'assistente; la prova ha mostrato che oggi l'impaginazione via API va a pezzi | l'aggiornamento dal vivo della pagina (UX-009) |
| T-204 Strumentazione | le metriche di ogni proposta, solo con consenso; «Aiuto › Salva la diagnostica» | — |
| T-205 Interfaccia | realizza il gruppo «entro la 2.0» | i token e i caratteri della marca (T-005) |
| T-206 Italiano e inglese | i testi della tabella «prima e dopo» (UX-007); il glossario inglese senza nomi dei concorrenti; numeri e unità per lingua | — |
| T-207 Aggiornamenti | la voce «Aiuto › Cerca aggiornamenti» al posto della pillola nella schermata dei progetti | — |
| T-208 Pacchetti dei laboratori | formati al primo album (UX-015), destinazione «Al laboratorio» (UX-013), copertina (UX-024), unità in pollici per i mercati di lingua inglese | — |

## Ordine proposto

1. **Correzioni senza ridisegno** (possono andare subito, anche prima di T-205, con un test ciascuna): UX-011 stampa dagli originali; UX-004 ricollega sicuro; messaggio di «Salva» (A-26); nome vuoto per la cartella «JPG» (A-01); menu di «Correggi spazi» che resta aperto (A-30); `rev` in `/api/ping` per UX-009.
2. **Motore, prima dell'interfaccia** (serve anche a T-203): preparazione in sottofondo e import a caldo (UX-012); nome e spread di ogni passo d'annulla, gruppi d'annulla (UX-003, UX-001); operazione `sostituisci` (UX-002); operazioni `controlla` e `sistema`, con il calcolo degli spazi spostato dalla pagina al motore (UX-014); operazione `bozza` (UX-018).
3. **Struttura dell'interfaccia** (T-205, con i token di T-005): disposizione delle zone e barra della selezione (UX-016), pannello contestuale e provini (UX-021), schermata Album (UX-022), menu contestuale (UX-006), stati vuoti (UX-008), testo (UX-023), accessibilità minima (UX-019), messaggi (UX-007 con T-206).
4. **Azioni «un pulsante» nell'interfaccia**: D, Sostituisci e riadatta, indicatore e pannello Controlla, Uniforma, foglio della bozza.
5. **Con la finestra desktop, le licenze e i laboratori**: trascinare la cartella (UX-015), primo avvio (UX-017), Consegna con i pacchetti (UX-013), recupero dalla schermata Album (UX-005).
6. **Prova con cinque fotografi** prima del rilascio: flusso 1 e flusso 5 cronometrati, KPI D6 su macchina pulita, quota della tela misurata con lo stesso script di questa analisi, verifica legale della somiglianza (LEG-004).

## Cinque cose che cambiano la prima impressione

1. **Si trascina la cartella e in pochi secondi si lavora.** Oggi: finestra di sistema, nome da scrivere, 90 s di rotellina.
2. **«Prepara la bozza» propone tutto l'album, con anteprima.** Oggi: tre gesti per ogni spread, e il primo modello lascia una pagina vuota una volta su quattro.
3. **Lo spread è grande e pulito.** Oggi occupa il 15 % della finestra fra due file di pulsanti; domani il 25 % con i pannelli aperti, più della metà con la tela piena.
4. **D cambia disposizione, sostituire riadatta.** Le due correzioni più frequenti diventano un gesto, sempre annullabile.
5. **Un semaforo dice se l'album è pronto, e «Consegna» produce file nitidi per il laboratorio.** Oggi si controllano solo gli spazi e i file da stampa vengono dalle miniature.
