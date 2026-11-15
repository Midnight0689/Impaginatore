## Cosa cambia

<!-- Una o due frasi: cosa cambia per chi usa o sviluppa l'Impaginatore. -->

## Compito e rilievi

<!-- Compito del piano (T-xxx) e rilievi dell'audit chiusi (SEC-xxx, BUG-xxx, ...), se ci sono. -->

## Come è stato provato

<!-- Comandi eseguiti ed esito così come è uscito. Scrivi anche cosa non è stato provato (per esempio macOS o Windows). -->

## Controlli

- [ ] `python strumenti/controlli.py tutto` passa in locale (lint, copertura con la soglia di `pyproject.toml`, sicurezza)
- [ ] Ogni modifica al comportamento ha un test; ogni riga esclusa dalla copertura ha il motivo accanto al `pragma`
- [ ] Voce in `CHANGELOG.md` sotto `## [Non rilasciato]`, nella forma descritta in `AGENTS.md`
- [ ] I progetti già salvati continuano ad aprirsi (se cambia il formato: migrazione provata da un test)
- [ ] Nessuna funzione nuova può caricare in rete le foto dell'utente
- [ ] Nessun segreto, chiave privata o dato personale nei file e nei commit
