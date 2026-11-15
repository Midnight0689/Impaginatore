# Istruzioni per chi lavora su questo repository (persone e agenti)

Impaginatore è un programma desktop per impaginare album fotografici. Il ramo `main` è la versione amatoriale in uso dall'ideatore: non si tocca. Il lavoro per il prodotto commerciale avviene sul ramo `prodotto/2.0`.

## Da leggere prima di cominciare

1. `docs/PIANO.md`: cosa stiamo costruendo, in che ordine, chi fa cosa.
2. `docs/prodotto/REQUISITI-VOCALI.md`: requisiti e KPI.
3. `docs/architettura/ARCHITETTURA.md`: mappa del codice.
4. `CHANGELOG.md`: cosa è già cambiato. `CAMBIAMENTI.md` è il registro storico fino alla 1.5.2 e non si modifica più.

## Regole

- Lingua: italiano per codice (nomi esistenti), documenti, messaggi di commit e interfaccia. I testi visibili all'utente passano dal sistema di traduzione quando c'è.
- Le foto dell'utente non escono mai dal computer. Nessuna funzione può caricarle in rete.
- Nessun push e nessuna modifica a `main` senza richiesta esplicita del titolare.
- Commit piccoli, messaggio `tipo(area): descrizione`. Tipi: `feat`, `fix`, `sicurezza`, `refactor`, `test`, `doc`, `ci`, `brand`, `mercato`. Si aggiungono solo i propri file, con percorsi espliciti.
- Ogni modifica al comportamento ha un test. La copertura richiesta è 100 %; una riga esclusa va motivata accanto al `pragma`.
- Prima di dichiarare finito un lavoro: `ruff check` e `pytest` devono passare, e l'esito va riportato così com'è.
- I progetti salvati dagli utenti devono continuare ad aprirsi. Un cambio di formato richiede una migrazione provata da un test.

## Registro delle modifiche

`CHANGELOG.md` è l'unico registro, per le persone e per gli agenti. Ogni voce sta su una riga e segue questa forma:

```
- `ID` **area** — descrizione di cosa cambia per chi usa o sviluppa. _File:_ `percorso`, `percorso`. _Rif:_ `SEC-003`.
```

- `ID`: sigla del tipo più numero progressivo, mai riusato: `AGG` (aggiunto), `MOD` (modificato), `COR` (corretto), `SIC` (sicurezza), `RIM` (rimosso), `DOC` (documenti e contenuti).
- `area`: una tra `motore`, `editor`, `progetti`, `piattaforma`, `desktop`, `licenze`, `mcp`, `test`, `ci`, `installer`, `documenti`, `brand`, `mercato`, `sito`.
- `File` elenca i percorsi principali. `Rif` è facoltativo e rimanda a un rilievo dell'audit o a un compito del piano.

Le voci nuove vanno sotto `## [Non rilasciato]`, nella sezione del loro tipo. `strumenti/controlla_changelog.py` verifica la forma e la CI lo esegue.

## Struttura

| Cartella | Contenuto |
|---|---|
| `src/impaginatore/` | Il programma |
| `tests/` | Test |
| `docs/` | Piano, architettura, audit, mercato, manuali |
| `brand/` | Identità di marca: manuale, logo, colori, icone |
| `marketing/` | Sito, email, social, negozio |
| `legacy/` | Lanciatori della versione amatoriale |
| `.github/` | Pipeline |
