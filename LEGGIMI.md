# Impaginatore

Programma per impaginare album fotografici (spread, modelli, testi, correzioni) ed esportare JPG, PDF e PSD per Photoshop.

## Primo avvio su un Mac (lanciatori della versione 1.x, in `legacy/macos/`)
1. Scarica questa cartella da GitHub (vedi sotto) e mettila dove vuoi.
2. Doppio clic su **legacy/macos/Installa.command** (una volta sola): crea l'ambiente Python con il programma, collega la skill di Claude, controlla Photoshop e font. Serve Python 3.10 o più recente (python.org).
3. Apri **legacy/macos/Impaginatore.app**.

## Da terminale (macOS, Windows, Linux)
```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"     # una volta (su Windows: .venv\Scripts\pip)
.venv/bin/impaginatore                                         # schermata dei progetti nel browser (porta 8765)
.venv/bin/impaginatore --porta 0 --no-browser --progetti ~/Album   # porta libera, senza browser, progetti altrove
.venv/bin/impaginatore editor --progetto "<cartella>"          # solo l'editor di un progetto
.venv/bin/python -m impaginatore.motore.anteprima --progetto "<cartella>" --nome v1   # script del motore
.venv/bin/pytest                                               # test (quelli con Photoshop si saltano dove manca)
.venv/bin/ruff check src tests
```
I PSD si creano solo dove c'è Photoshop (macOS, Windows); su Linux JPG e PDF.

## Aggiornare
Sul Mac secondario: doppio clic su **legacy/macos/Aggiorna.command**. Scarica le novità, aggiorna da solo l'ambiente e riavvia il programma.
Da un checkout git anche il riquadro Versione della schermata dei progetti scarica le novità; installato in altro modo, gli aggiornamenti automatici non ci sono.

## Cosa non è qui dentro
I progetti, le foto e i PSD (stanno nella cartella `Progetti/` o dove li tieni tu). Per portarli su un altro computer: **Progetto → Esporta progetto**
nell'editor e poi **Importa ZIP** nella schermata dei progetti.

## Cartelle
- `src/impaginatore/` programma (schermata progetti, editor, motore di impaginazione, piattaforma); mappa in `docs/architettura/ARCHITETTURA.md`
- `tests/` test automatici (`pytest`)
- `legacy/macos/` lanciatori per il Mac delle versioni 1.x (app, .command, setup.sh)
- `skill/impaginatore-stefano/` istruzioni per Claude
