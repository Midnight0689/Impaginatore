# Impaginatore

Programma desktop per impaginare album fotografici: dalla cartella delle foto agli spread, con bozza automatica,
controllo prima della stampa ed esportazione in JPG, PDF e PSD a livelli per Photoshop. Le foto restano sul computer.

Versione in sviluppo: 2.0 (ramo `prodotto/2.0`). Il ramo `main` è la versione amatoriale 1.x in uso.

## Documenti

| Per chi | Dove |
|---|---|
| Chi usa il programma | [Manuale](docs/manuale/INDICE.md), con la [guida di installazione](docs/manuale/00-installazione.md) dei pacchetti (beta privata) |
| Chi collega un assistente AI (Claude) | [Guida all'assistente](docs/manuale/assistente/INDICE.md) |
| Chi sviluppa | [Guida per sviluppatori](docs/sviluppo/GUIDA.md), [regole del repository](AGENTS.md), [architettura](docs/architettura/ARCHITETTURA.md) |
| Chi segue il progetto | [Piano](docs/PIANO.md), [registro delle modifiche](CHANGELOG.md) |

## Da terminale (macOS, Windows, Linux)

Serve Python 3.11 o più recente. Con [uv](https://docs.astral.sh/uv/) (versioni fissate in `uv.lock`):

```bash
uv sync --locked --extra dev --extra mcp           # una volta: ambiente con strumenti di sviluppo e server MCP (la suite completa li vuole tutti e due)
uv run impaginatore                                # schermata Album nella finestra del programma, o nel browser
uv run impaginatore --browser                      # nel browser anche se la finestra è disponibile
uv run impaginatore --porta 0 --no-browser --progetti ~/Album   # porta libera, senza finestra né browser, album altrove
uv run impaginatore editor --progetto "<cartella>" # solo l'editor di un album
uv run impaginatore mcp                            # server MCP per l'assistente AI (stdio)
uv run pytest                                      # test (quelli con Photoshop, Chrome o la finestra si saltano dove manca)
python3 strumenti/controlli.py lint                # ruff e forma del registro, come la CI
python3 strumenti/controlli.py copertura           # test con copertura (soglia 100 %)
```

Senza uv:

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev,desktop]"   # su Windows: .venv\Scripts\pip
.venv/bin/impaginatore
```

Gli extra: `dev` (test e ruff), `mcp` (assistente AI), `desktop` (finestra propria del programma), `heic` (foto HEIC).
La suite completa dei test e la copertura al 100 % vogliono `dev` e `mcp` (`uv sync --locked --extra dev --extra mcp`,
o `pip install -e ".[dev,mcp]"`): senza `mcp` i test del server MCP si saltano con il motivo e la copertura non è completa.

I PSD si creano solo dove c'è Photoshop (macOS, Windows); su Linux JPG e PDF.
La finestra del programma usa WebKit su macOS e WebView2 su Windows (già nel sistema). Su Linux servono PyGObject e
WebKit2GTK del sistema (Debian/Ubuntu: `python3-gi gir1.2-webkit2-4.1`) e un ambiente creato con
`python3 -m venv --system-site-packages .venv`; se manca qualcosa il programma lo scrive e apre il browser.

## Versione 1.x sul Mac (lanciatori in `legacy/macos/`)

1. Scarica questa cartella da GitHub e mettila dove vuoi.
2. Doppio clic su **legacy/macos/Installa.command** (una volta sola): crea l'ambiente Python con il programma, collega
   la skill di Claude, controlla Photoshop e font. Serve Python 3.11 o più recente (python.org).
3. Apri **legacy/macos/Impaginatore.app**.

Per aggiornare: doppio clic su **legacy/macos/Aggiorna.command**. Scarica le novità, aggiorna l'ambiente e riavvia il
programma. Da un checkout git anche il riquadro Versione della schermata Album scarica le novità; installato in altro
modo, gli aggiornamenti automatici non ci sono.

## Cosa non è qui dentro

Gli album, le foto e i PSD: stanno nella cartella `Progetti/` o dove li tieni tu. Per portare un album su un altro
computer: nell'editor «⋯» › «Progetto e foto…» › «Copia del progetto», poi sull'altro computer «⋯» › «Importa ZIP…»
(o «Apri album esistente…») nella schermata Album.

## Cartelle

- `src/impaginatore/` il programma (schermata Album, editor, motore di impaginazione, licenze, server MCP, piattaforma)
- `tests/` test automatici (`pytest`)
- `docs/` piano, architettura, manuali, audit, documenti legali e di mercato
- `strumenti/` controlli della CI in locale, controllo del registro, schermate dell'interfaccia, compilazione e pacchetti
  (`compila.py`, `docs/architettura/DISTRIBUZIONE.md`: `.deb` provato su Linux, `.dmg` ed `.exe` in collaudo), rilascio,
  lettura delle statistiche della beta
- `brand/` identità di marca; `marketing/` sito, email, social
- `legacy/macos/` lanciatori per il Mac delle versioni 1.x (app, .command, setup.sh)
- `skill/impaginatore-stefano/` istruzioni per Claude (la skill che collega `legacy/macos/Installa.command`)
