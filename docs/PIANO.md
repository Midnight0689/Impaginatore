# Piano di lavoro: da prototipo a prodotto in vendita

Stato dei compiti aggiornato in `docs/piano.json` (stessi identificativi). Requisiti e KPI: `docs/prodotto/REQUISITI-VOCALI.md`.

## Punto di partenza

Versione 1.5.2: 6.500 righe tra Python e JavaScript, 175 commit, un solo utente. Gira solo su macOS, si installa con uno script che crea un ambiente Python, si apre nel browser, si aggiorna con `git pull`. Il file di salvataggio di un album è codice Python che viene eseguito. Non ci sono test automatici senza foto vere, né licenze, né installer.

## Dove arriviamo (versione 2.0.0)

Un'applicazione desktop con finestra propria per macOS, Windows e Linux, installata con un solo file, attivata con una chiave, venduta una volta sola in tre fasce. Le foto restano sul computer. Un server MCP permette a Claude e ad altri assistenti di costruire l'album dentro l'editor.

## Scelte tecniche

| Tema | Scelta | Perché |
|---|---|---|
| Linguaggio | Resta Python | Il motore usa Pillow, NumPy, OpenCV e psd-tools; riscrivere costa mesi e non porta vendite |
| Finestra | pywebview (WebKit su macOS e Linux, WebView2 su Windows) | Riusa l'interfaccia esistente, nessun browser incluso, installer piccolo |
| Server interno | `http.server` su 127.0.0.1, porta casuale, gettone di sessione, controllo di Host e Origin | Nessun sito aperto nel browser deve poter comandare l'editor |
| Salvataggio | JSON al posto di `spec.py`, con migrazione dei vecchi progetti | Un album ricevuto da un collega non deve poter eseguire codice |
| Protezione del codice | Compilazione con Nuitka | Compila in codice macchina: offusca e accelera l'avvio |
| Licenze | Chiave firmata Ed25519 verificata in locale, attivazione in rete solo al primo avvio | Funziona senza connessione; la piattaforma di vendita emette le chiavi |
| Installer | `.dmg` firmato e notarizzato, `.exe` Inno Setup firmato, AppImage e `.deb` | Un file, due clic |
| Costruzione e rilascio | GitHub Actions su runner dei tre sistemi | Non servono tre computer; ogni rilascio è riproducibile |
| MCP | Server stdio incluso nell'installer, più comando per registrarlo in Claude | È la funzione che distingue il prodotto |
| Lingue | Italiano e inglese | Italia prima, estero subito dopo |

## Organizzazione

Fable 5.2 fa da orchestratore: decide l'architettura, scrive i mandati, controlla le consegne, tiene il registro e risponde al titolare. Ogni compito è eseguito da un agente Opus 5.5 con un ruolo e una cartella di competenza; chi scrive codice non rivede il proprio lavoro.

| Ruolo | Competenza |
|---|---|
| Principal Engineer | Struttura del pacchetto, piattaforme, architettura |
| Security & QA Lead | Audit, verifica delle correzioni |
| Ingegneri di prodotto | Sicurezza, test, finestra desktop, licenze, MCP, interfaccia |
| Release Engineer | Pipeline, compilazione, installer, firma |
| Analista di mercato, Go-to-market | Concorrenti, lead, prezzi, canale di vendita |
| Brand & Design Director | Identità, manuale di stile |
| Autori | Documentazione, sito, email, social |

## Fasi e compiti

Un compito parte quando sono chiusi quelli da cui dipende. Compiti senza dipendenze comuni girano in parallelo.

### Fase 0 — Scoperta

| ID | Compito | Consegna | Accettazione |
|---|---|---|---|
| T-001 | Trascrizione dei vocali, requisiti e KPI | `docs/prodotto/REQUISITI-VOCALI.md` | Fatto |
| T-002 | Audit di sicurezza, bug, portabilità, testabilità, rischi legali | `docs/audit/` | Ogni rilievo ha scenario concreto e stato di verifica |
| T-003 | Profilo dei concorrenti | `docs/mercato/competitor.*` | Ogni prezzo ha fonte e data |
| T-004 | Lead, prezzi e fasce, canale di vendita | `docs/mercato/lead.*`, `prezzi.md`, `tier.json`, `canale-vendita.md` | Tre fasce, la centrale consigliata; una piattaforma raccomandata |
| T-005 | Identità di marca | `brand/` | Logo leggibile a 16 px, contrasti calcolati |
| T-006 | Fondamenta: pacchetto installabile, tre sistemi, base di test | `src/`, `tests/`, `docs/architettura/` | Si installa e gira su Linux; i vecchi progetti si aprono identici |

### Fase 1 — Consolidamento (dipende da T-002 e T-006)

| ID | Compito | Accettazione |
|---|---|---|
| T-101 | Salvataggio in JSON e migrazione da `spec.py` | Nessun `exec` su dati dell'utente; progetti 1.x aperti e confrontati da un test |
| T-102 | Server interno protetto: gettone, Host/Origin, percorsi, ZIP, limiti | Tutti i rilievi `SEC` critici e alti chiusi, ognuno con un test che fallisce senza la correzione |
| T-103 | Correzione dei bug confermati | Ogni `BUG` confermato chiuso con test |
| T-104 | Copertura al 100 % | Soglia bloccante su righe e rami |
| T-105 | Prove dell'interfaccia nel browser | I flussi principali girano in un browser pilotato |
| T-106 | Verifica indipendente delle correzioni | Il Security Lead riprova ogni rilievo |

### Fase 2 — Prodotto (dipende dalla Fase 1; T-202 anche da T-004, T-205 da T-005)

| ID | Compito | Accettazione |
|---|---|---|
| T-201 | Finestra desktop con pywebview | Si apre senza browser né terminale; dialoghi di sistema nativi |
| T-202 | Licenze, fasce e prova gratuita | Le funzioni seguono `tier.json`; chiave contraffatta rifiutata; funziona senza rete dopo l'attivazione |
| T-203 | Server MCP | Claude crea un progetto, importa foto, impagina ed esporta senza toccare l'editor |
| T-204 | Strumentazione: registro strutturato, diagnostica, telemetria solo con consenso | Nessun dato inviato senza consenso esplicito; mai contenuto o nomi delle foto |
| T-205 | Interfaccia ridisegnata con la marca | Chiusi i rilievi `LEG` sull'interfaccia |
| T-206 | Italiano e inglese | Nessun testo fisso nel codice dell'interfaccia |
| T-207 | Aggiornamenti dalle release | Avviso di nuova versione, scaricamento verificato con firma |
| T-208 | Pacchetti catalogo per i laboratori | Un file descrive formati, abbondanze e copertine; un esempio incluso |

### Fase 3 — Distribuzione (T-301 parte dopo T-006; il resto dopo la Fase 2)

| ID | Compito | Accettazione |
|---|---|---|
| T-301 | Pipeline di controllo: lint, test sui tre sistemi, copertura, registro | Verde su macOS, Windows, Linux |
| T-302 | Compilazione e installer | Un file per sistema, prodotto dalla pipeline |
| T-303 | Rilascio su tag: costruzione, firma, checksum, SBOM, note dal registro | Un tag produce una release completa |
| T-304 | Sicurezza della filiera: CodeQL, audit delle dipendenze, ricerca di segreti, Dependabot | Attivi e bloccanti |
| T-305 | Firma del codice | Richiede i certificati del titolare (vedi sotto) |

### Fase 4 — Documentazione

| ID | Compito |
|---|---|
| T-401 | Manuale d'uso con schermate |
| T-402 | Guida di installazione e attivazione |
| T-403 | Guida al server MCP |
| T-404 | Guida per sviluppatori e `README.md` |
| T-405 | Bozze di contratto di licenza e informativa sulla riservatezza, da far rivedere a un legale |

### Fase 5 — Mercato (dipende da T-003, T-004, T-005; T-501 anche da T-205)

| ID | Compito |
|---|---|
| T-501 | Schermate dell'applicazione renderizzate con album dimostrativi |
| T-502 | Pagina di vendita |
| T-503 | Modelli di email (lancio, benvenuto con chiave, laboratori) |
| T-504 | Kit per i social: modelli grafici, calendario, testi |
| T-505 | Negozio: configurazione della piattaforma scelta |
| T-506 | Piano di lancio a 90 giorni |

## Cosa può fare solo il titolare

- Accordo con l'ideatore su proprietà del codice, quote e uso del repository (oggi è suo e privato).
- Parere di un legale sulla somiglianza con SmartAlbums e sui contratti.
- Partita IVA e conto sulla piattaforma di vendita.
- Certificati di firma: Apple Developer (99 $/anno) e certificato di firma del codice per Windows.
- Dominio del sito.
