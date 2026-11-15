# Registro delle modifiche

Tutte le modifiche dal ramo `prodotto/2.0` in poi. La forma delle voci è descritta in `AGENTS.md` (sezione «Registro delle modifiche») ed è la stessa per chi legge e per gli strumenti automatici. La storia fino alla versione 1.5.2 è in `CAMBIAMENTI.md`.

Numerazione: `maggiore.minore.correzione`. La 2.0.0 sarà la prima versione in vendita.

## [Non rilasciato]

### Aggiunto

- `AGG-001` **pacchetto** — Pacchetto Python installabile (Python 3.10 o successivo) con comando `impaginatore` per la schermata dei progetti e `impaginatore editor` per un album; versione in un solo posto. _File:_ `pyproject.toml`, `src/impaginatore/__init__.py`, `src/impaginatore/cli.py`, `uv.lock`. _Rif:_ `T-006`.
- `AGG-002` **piattaforma** — Strato unico per macOS, Windows e Linux: cartelle dei dati, finestre di scelta, cestino, «mostra nella cartella», font e profilo sRGB, pilotaggio di Photoshop (osascript su macOS, COM su Windows), avvio e riavvio dei processi. _File:_ `src/impaginatore/piattaforma/`, `src/impaginatore/servizio.py`. _Rif:_ `PORT-001`, `PORT-002`, `PORT-003`, `PORT-005`, `PORT-006`, `TEST-003`.
- `AGG-003` **aggiornamenti** — Interfaccia degli aggiornamenti con due implementazioni: git (quella della 1.5.2, solo da un checkout) e «non disponibili» per le installazioni da pacchetto. _File:_ `src/impaginatore/aggiornamenti/`. _Rif:_ `TEST-003`.
- `AGG-004` **test** — Suite pytest di 91 prove che gira senza Photoshop e senza foto vere: foto sintetiche, progetto della 1.5.2 riaperto e risalvato identico, processi veri, piattaforme simulate, pagine aperte in Chrome senza schermo. Copertura di partenza 74,5 %. _File:_ `tests/`. _Rif:_ `TEST-005`.

### Modificato

- `MOD-001` **motore** — Importare il motore non ha più effetti: il progetto si carica in modo esplicito e gli script girano con `python -m impaginatore.motore.<nome>`; lettura e scrittura del salvataggio concentrate in un modulo. Impaginazioni identiche alla 1.5.2. _File:_ `src/impaginatore/motore/`, `src/impaginatore/formato.py`. _Rif:_ `TEST-001`, `TEST-004`.
- `MOD-002` **editor** — L'editor si crea, si avvia e si ferma da codice, senza leggere la riga di comando all'importazione; finestre di scelta, font e Photoshop passano dallo strato di piattaforma. API e interfaccia invariate. _File:_ `src/impaginatore/editor/server.py`. _Rif:_ `TEST-001`, `TEST-002`.
- `MOD-003` **progetti** — La schermata dei progetti accetta `--porta` (anche 0 per una porta libera), `--progetti`, `--no-browser`, `--versione` e gira in una sola istanza. _File:_ `src/impaginatore/home/server.py`.
- `MOD-004` **installer** — I lanciatori della versione 1.x per macOS sono spostati in `legacy/macos/` e installano il pacchetto. _File:_ `legacy/macos/`.

### Corretto

- `COR-001` **progetti** — La richiesta della copertina rifiuta i nomi con `\\`, `.` e `..`. _File:_ `src/impaginatore/home/server.py`.
- `COR-002` **piattaforma** — Tolti i blocchi su Linux e Windows: percorsi POSIX dell'interprete, `os.fork`, font e profilo colore fissi di macOS, file aperti senza codifica esplicita. _File:_ `src/impaginatore/motore/`, `src/impaginatore/editor/server.py`, `src/impaginatore/home/server.py`. _Rif:_ `PORT-003`, `PORT-005`, `PORT-006`.

### Sicurezza

### Rimosso

- `RIM-001` **pacchetto** — Tolto il file `VERSION` dalla radice: la versione sta in `src/impaginatore/__init__.py`. _File:_ `VERSION`.

### Documenti e contenuti

- `DOC-001` **documenti** — Requisiti e KPI ricavati dai quattro vocali dell'ideatore, con le decisioni di prodotto che ne derivano. _File:_ `docs/prodotto/REQUISITI-VOCALI.md`.
- `DOC-002` **documenti** — Regole di lavoro per persone e agenti, forma del registro, struttura del repository. _File:_ `AGENTS.md`.
- `DOC-003` **documenti** — Piano di lavoro: organizzazione, fasi, compiti, dipendenze e criteri di accettazione. _File:_ `docs/PIANO.md`, `docs/piano.json`.
- `DOC-004` **documenti** — Questo registro, che sostituisce `CAMBIAMENTI.md` per il lavoro nuovo. _File:_ `CHANGELOG.md`.
- `DOC-005` **mercato** — Profilo di 19 concorrenti con prezzi e fonti al 15/11/2026, tabella comparativa, punti in cui siamo indietro, cinque argomenti di vendita difendibili, brevetti e marchi noti. _File:_ `docs/mercato/competitor.md`, `docs/mercato/competitor.json`. _Rif:_ `T-003`.
- `DOC-006` **documenti** — Audit della versione 1.5.2: 33 rilievi (10 sicurezza, 7 bug, 6 portabilità, 5 testabilità, 5 legali), 4 critici e 11 alti, 32 riprodotti. _File:_ `docs/audit/AUDIT-2026-11.md`, `docs/audit/rilievi.json`. _Rif:_ `T-002`.
- `DOC-007` **mercato** — Lead (fotografi e laboratori, con elenco CSV), tre fasce di prezzo una tantum con funzioni per fascia leggibili dal gestore licenze, confronto delle piattaforme di vendita con raccomandazione. _File:_ `docs/mercato/lead.md`, `docs/mercato/lead.csv`, `docs/mercato/prezzi.md`, `docs/mercato/tier.json`, `docs/mercato/canale-vendita.md`. _Rif:_ `T-004`.
- `DOC-008` **documenti** — Piano aggiornato: distribuzione senza conto Apple Developer né certificato Windows (comandi di installazione di una riga, firma propria delle release) e licenze emesse in proprio senza piattaforma esterna. _File:_ `docs/PIANO.md`, `docs/piano.json`. _Rif:_ `T-305`, `T-202`.
- `DOC-009` **brand** — Identità di marca: manuale di stile, simbolo «La Piega» e logotipo in SVG, palette Carta/Inchiostro/Verde Bottega con contrasti verificati, caratteri Newsreader, Instrument Sans e IBM Plex Mono (OFL), token W3C e CSS, icone dell'app, pagina di prova. _File:_ `brand/STYLEBOOK.md`, `brand/README.md`, `brand/tokens.json`, `brand/tokens.css`, `brand/logo/`, `brand/icona/`, `brand/font/`, `brand/anteprima.html`. _Rif:_ `T-005`.
- `DOC-010` **sito** — Album dimostrativo per le schermate: 62 foto di un matrimonio da Pexels, non versionate ma ricostruibili identiche dall'elenco delle fonti con licenza e impronta di ogni file. _File:_ `marketing/demo/FONTI.csv`, `marketing/demo/scarica_demo.py`, `marketing/demo/README.md`, `marketing/demo/provini.jpg`. _Rif:_ `T-501`.
- `DOC-011` **documenti** — Architettura della 2.0: moduli, processi e porte, formato dei progetti, stato globale residuo, punti di estensione, cosa non è verificato su macOS e Windows. _File:_ `docs/architettura/ARCHITETTURA.md`, `LEGGIMI.md`. _Rif:_ `T-006`.
- `DOC-012` **documenti** — Bozze legali da far rivedere a un avvocato: licenza d'uso in italiano e inglese, informativa sulla riservatezza, termini di vendita (diretta e tramite rivenditore), condizioni dell'assistenza a ore, avvisi delle librerie di terzi, schema per i laboratori, elenco delle questioni aperte. _File:_ `docs/legale/`. _Rif:_ `T-405`, `LEG-001`, `LEG-002`, `LEG-003`, `LEG-004`, `LEG-005`.
- `DOC-013` **mercato** — Negozio pronto senza conti esterni: guida di apertura, flusso d'acquisto con testi in italiano e inglese, strumento che emette, verifica e revoca le chiavi di licenza firmate Ed25519, formato della chiave per l'app; Polar predisposto come passo facoltativo. _File:_ `marketing/negozio/GUIDA-APERTURA.md`, `marketing/negozio/FLUSSO-ACQUISTO.md`, `marketing/negozio/chiavi/chiavi.py`, `marketing/negozio/chiavi/FORMATO-CHIAVE.md`, `marketing/negozio/polar/`, `marketing/negozio/ALTERNATIVE.md`. _Rif:_ `T-505`.
- `DOC-014` **mercato** — Piano di lancio a 90 giorni: lista d'attesa, beta con 25 fotografi, tre laboratori pilota, lancio il 23/02/2027, obiettivi e budget. _File:_ `marketing/lancio/PIANO-90-GIORNI.md`. _Rif:_ `T-506`.
