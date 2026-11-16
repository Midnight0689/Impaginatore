# Guida per chi sviluppa Impaginatore

Questa guida spiega come preparare l'ambiente, provare il programma, aggiungere funzioni e consegnare il lavoro.
Le regole del repository sono in [`AGENTS.md`](../../AGENTS.md): valgono per persone e agenti, e vincono su questa
guida. La mappa del codice è in [`docs/architettura/ARCHITETTURA.md`](../architettura/ARCHITETTURA.md).

Tutti i comandi qui sotto sono stati provati su Linux (Python 3.14, uv 0.6.6) il 16/11/2026, sul ramo `prodotto/2.0`.
Dove un comando non è stato provato, è scritto.

## 1. Le regole in breve

- Si lavora sul ramo `prodotto/2.0`. `main` è la versione amatoriale in uso: non si tocca. Niente push senza richiesta
  del titolare.
- Italiano per codice (nomi esistenti), documenti, messaggi di commit e interfaccia.
- Le foto dell'utente non escono mai dal computer: nessuna funzione le carica in rete.
- Ogni modifica al comportamento ha un test. Copertura richiesta: 100 % di righe e rami.
- Prima di dire «finito»: `ruff check` e `pytest` passano, e l'esito si riporta com'è.
- Commit piccoli, `tipo(area): descrizione`; si aggiungono solo i propri file, con percorsi espliciti.
- I progetti salvati devono continuare ad aprirsi: un cambio di formato vuole una migrazione provata da un test.
- Ogni cambiamento ha una voce in `CHANGELOG.md` (sezione 10).

## 2. Cosa serve

| Cosa | Perché |
|---|---|
| Python 3.11 o successivo | il programma; la CI prova 3.11, 3.12, 3.13 e 3.14 |
| [uv](https://docs.astral.sh/uv/) | ambiente e dipendenze dal file `uv.lock`; la CI usa la 0.13.6. `controlli.py dipendenze` vuole uv 0.8 o successivo |
| git | storia e controllo dei segreti |
| Chrome o Chromium (facoltativo) | test segnati `browser`: la pagina vera in un browser senza schermo |
| Photoshop (facoltativo, macOS o Windows) | test segnati `photoshop` e PSD |
| Linux: `xvfb-run`, PyGObject e WebKit2GTK (facoltativo) | test segnati `finestra` (finestra vera del programma) |

## 3. L'ambiente

Dalla cartella del codice:

```bash
uv sync --extra dev --extra mcp
```

Crea `.venv` con il programma installato in modo modificabile, gli strumenti di sviluppo (`pytest`, `pytest-cov`,
`coverage`, `ruff`) e l'SDK MCP. Gli extra:

| Extra | Cosa aggiunge |
|---|---|
| `dev` | pytest, pytest-cov, coverage, ruff |
| `mcp` | SDK ufficiale MCP (`mcp` 2.x): serve a `impaginatore mcp` e ai suoi test |
| `desktop` | pywebview: la finestra propria del programma. Senza, si apre il browser |
| `heic` | pillow-heif: foto HEIC/HEIF |

Per la finestra su Linux servono anche i pacchetti del sistema (Debian/Ubuntu: `python3-gi gir1.2-webkit2-4.1`) e un
ambiente con `--system-site-packages`: vedi [`LEGGIMI.md`](../../LEGGIMI.md). Gli extra `desktop` e `heic` non sono
stati provati per questa guida.

Senza uv si può usare `pip` (come in `LEGGIMI.md`), ma le versioni non sono quelle fissate in `uv.lock`.

## 4. Avviare il programma

```bash
uv run impaginatore                                   # schermata Album (finestra del programma, o browser)
uv run impaginatore --browser                         # nel browser anche se la finestra è disponibile
uv run impaginatore --porta 0 --no-browser --progetti ~/Album   # porta libera, niente finestra, album altrove
uv run impaginatore editor --progetto "<cartella>"    # solo l'editor di un album
uv run impaginatore mcp                               # server MCP su stdio (vedi docs/architettura/MCP.md)
```

All'avvio il programma scrive l'indirizzo, per esempio `Impaginatore: http://127.0.0.1:41133/  | progetti: …`.
Quell'indirizzo da solo non collega una scheda nuova: la pagina si apre con l'indirizzo di avvio monouso che il
programma passa alla finestra o al browser quando li apre lui (vedi [`SICUREZZA.md`](../architettura/SICUREZZA.md)).
Con `--no-browser` non si apre niente: serve ai test e agli strumenti.

Per non toccare i propri album e dati mentre si prova, si spostano le cartelle con le variabili d'ambiente:

```bash
IMPAGINATORE_DATI=/tmp/prova/dati IMPAGINATORE_CACHE=/tmp/prova/cache \
  uv run impaginatore --progetti /tmp/prova/Progetti
```

Le altre variabili (`IMPAGINATORE_DIALOGHI`, `IMPAGINATORE_FINESTRA`, `IMPAGINATORE_AGGIORNAMENTI`…) sono nella tabella
di `ARCHITETTURA.md`.

## 5. I test

```bash
uv run pytest                                  # tutti
uv run pytest tests/test_editor_operazioni.py  # un file
uv run pytest -k swappages                     # per nome
uv run pytest -m "not lento and not browser and not finestra and not photoshop"   # i veloci
```

I test segnati `browser`, `finestra` e `photoshop` si saltano da soli se manca quello che serve, e il riepilogo dice
perché (`-ra` è già nelle opzioni). Su Linux con Chrome la suite completa fa 880 test e ne salta 3 (finestra senza
pywebview, due con Photoshop), in circa 12 minuti.

### Le fixture principali (`tests/conftest.py`)

| Fixture | Cosa dà |
|---|---|
| `casa` (automatica) | una casa finta: `HOME`, `APPDATA`, `XDG_*` e cartelle del programma in `tmp_path`. Nessun test tocca i dati veri |
| `licenza` (automatica) | chiavi di prova generate per la sessione; di serie la prova gratuita |
| `foto_campione` | 10 foto sintetiche |
| `home`, `home_srv` | la schermata Album, come modulo o con il server |
| `progetto` | un album «Prova» 60 × 22,5 cm con le 10 foto |
| `editor` | l'editor di `progetto` su una porta libera: un `Client` con `get`, `post`, `codice` e il modulo in `editor.E` |
| `apri_editor` | apre l'editor su un album preparato dal test |

`tests/aiuti.py` ha il `Client` HTTP con il gettone; `tests/cdp.py` comanda Chrome senza schermo (`Browser`).

## 6. La copertura

```bash
python3 strumenti/controlli.py copertura
```

La soglia è `fail_under = 100` in `pyproject.toml`, per righe e rami: l'unico posto dove è scritta. Il rapporto va in
`htmlcov/` e `coverage.xml` (ignorati da git).

Una riga che non si può provare si esclude con un `pragma` e il motivo accanto, come in `home/server.py`:

```python
if pt: return pt  # pragma: no branch  # coverage 7.17 non vede un return dentro «with»; provato da test_apri_riusa_editor_lanciato_da_qui
```

Prima di escludere una riga, prova a scrivere il test: quasi sempre si può.

## 7. `strumenti/controlli.py`: gli stessi controlli della CI

Lo script gira con il Python del sistema (3.9 o successivo) e usa uv per l'ambiente del progetto.

| Comando | Cosa fa | Provato per questa guida |
|---|---|---|
| `python3 strumenti/controlli.py lint` | ruff e forma di `CHANGELOG.md` | sì: ok |
| `python3 strumenti/controlli.py test` | pytest | sì, tramite `copertura` |
| `python3 strumenti/controlli.py copertura` | pytest con copertura | sì: ok, 880 passati, 3 saltati, 100 % |
| `python3 strumenti/controlli.py bandit` | analisi statica di `src/` | sì: ok |
| `python3 strumenti/controlli.py dipendenze` | pip-audit sulle versioni di `uv.lock` | no: con uv 0.6.6 lo script dice «NON ESEGUITO» e chiede uv 0.8 |
| `python3 strumenti/controlli.py segreti` | gitleaks su tutta la storia (lo scarica la prima volta) | sì: ok |
| `python3 strumenti/controlli.py licenze` | licenze delle dipendenze contro quelle ammesse | sì: ok |
| `python3 strumenti/controlli.py sicurezza` | bandit, dipendenze, segreti, licenze | in parte (i quattro sopra, uno per uno) |
| `python3 strumenti/controlli.py tutto` | lint, copertura, sicurezza | in parte (i pezzi uno per uno) |

`--python 3.13` sceglie la versione di Python dell'ambiente dei test, come la matrice della CI. Lo script esce con 0 se
tutto va, 1 se un controllo fallisce, 2 se manca qualcosa per eseguirlo.

Su Linux, se Chrome non parte con un `TMPDIR` lungo, usa una cartella temporanea dal percorso corto
(`TMPDIR=/tmp/t python3 strumenti/controlli.py copertura`).

Altri strumenti:

- `uv run python strumenti/controlla_changelog.py`: solo la forma del registro (la chiama anche `lint`);
- `.venv/bin/python strumenti/schermate_ux.py --uscita <cartella> [scena…]`: schermate dell'interfaccia con un album di
  prova, nei due temi e due misure. Senza `--uscita` riscrive `docs/prodotto/ux/schermate/2.0/`. Serve Chrome.

## 8. Com'è fatto il codice

```
src/impaginatore/
  cli.py, __main__.py   il comando «impaginatore» (schermata Album, «editor», «mcp»)
  servizio.py           server HTTP locale (127.0.0.1) con i controlli di ogni richiesta
  sicurezza.py          gettone di sessione e indirizzi di avvio monouso
  percorsi.py           radici consentite per i percorsi che arrivano dalla pagina
  formato.py            l'unico modulo che legge e scrive album.json e progetto.json
  formato_1x.py         spec.py delle 1.x: letto senza eseguirlo, convertito
  validazione.py        controllo dei dati letti da un progetto
  archivio.py           estrazione sicura degli ZIP di progetto
  home/server.py        schermata Album
  editor/server.py      editor: stato, operazioni, annulla, controlli, esportazioni
  motore/               impaginazione: geometria, foto, volti, bozza, spazi, testo, PSD, PDF
  licenze/              fasce (tier.json), prova, sola lettura, filigrana, chiavi firmate
  mcp/                  server MCP per l'assistente AI
  desktop/              finestra del programma (pywebview)
  piattaforma/          differenze tra macOS, Windows e Linux: cartelle, finestre di scelta, font, Photoshop
  risorse/              pagine (home.html, index.html), testi (testi/it.json), statici della marca
```

Le pagine sono HTML con un solo script in linea. Parlano con il server con `fetch` e il gettone della sessione.
Lo stato dell'album sta nel server dell'editor: la pagina chiede le operazioni (`POST /api/op`) e ridisegna con lo
stato che riceve.

Documenti da leggere secondo il lavoro:

| Lavoro | Documento |
|---|---|
| operazioni dell'editor | [`OPERAZIONI.md`](../architettura/OPERAZIONI.md) |
| formato dei progetti e migrazioni | [`FORMATO-PROGETTO.md`](../architettura/FORMATO-PROGETTO.md) |
| sicurezza | [`SICUREZZA.md`](../architettura/SICUREZZA.md) |
| licenze e fasce | [`LICENZE.md`](../architettura/LICENZE.md) |
| assistente AI | [`MCP.md`](../architettura/MCP.md) |

## 9. Aggiungere un'operazione dell'editor

Ogni modifica dell'album passa da `do_op` in `editor/server.py`: è una transazione (riesce tutta o lo stato resta com'era),
un passo d'annulla con un nome, il controllo della licenza e il contatore di revisione. La pagina e l'assistente AI
usano le stesse operazioni.

Come esempio guarda `swappages` («Inverti le pagine»), già nel codice.

1. **Argomenti.** In `valida(o)` controlla gli argomenti *prima* di toccare lo stato. `s`, `at`, `side`, `photo`,
   `photos` e `names` si controllano già da soli se usi questi nomi; aggiungi solo i controlli propri dell'operazione.
2. **Effetto.** In `apply(o)` aggiungi un ramo `elif t == "nome":` che cambia solo lo stato in memoria (`SP`, `GD`,
   `CFG`). Niente file, niente rete: salvare è compito dell'autosalvataggio.
   ```python
   elif t == "swappages":                                # inverte le due pagine
       s_ = o["s"]
       SP[s_][0], SP[s_][1] = SP[s_][1], SP[s_][0]; GD[s_]["v"] = [round(VW - x, 1) for x in GD[s_]["v"]]
   ```
3. **Nome.** In `NOMI_OP` il nome per «Annulla» e «Ripeti», per esempio `swappages="Inverti pagine"`.
4. **Licenza.** Di serie un'operazione è `editor_completo`: c'è in tutte le fasce e si ferma in sola lettura. Se è una
   funzione a pagamento, aggiungila a `OP_FUNZIONI` in `licenze/__init__.py` con la chiave di `licenze/tier.json`.
5. **Pagina.** In `risorse/index.html` chiamala con `op({ op: "nome", s: cur, … })`. I testi passano da `t()`
   (sezione 11).
6. **Documento.** Aggiungi l'operazione a `docs/architettura/OPERAZIONI.md`.
7. **Assistente.** Se l'assistente deve poterla usare, servono un metodo in `mcp/strumenti.py`, la registrazione in
   `mcp/server.py` e i test in `tests/test_mcp_strumenti.py` (vedi `MCP.md`).
8. **Test.** Prova l'effetto, il nome del passo d'annulla, l'annulla, il rifiuto degli argomenti sbagliati (lo stato
   non cambia). Le operazioni con uno spread vanno aggiunte anche a `test_spread_che_non_esiste` in
   `tests/test_editor_operazioni.py`.

Un test d'esempio (provato con la fixture `editor`):

```python
import pytest


def op(c, **o): return c.post("/api/op", o)


def test_inverti_le_pagine(editor):
    c, E = editor, editor.E
    nomi = [p["n"] for p in c.get("/api/state")["photos"]]
    t = c.post("/api/templates", {"photos": nomi[:3]})["items"][0]
    op(c, op="newspread", pos=0, L=t["L"], R=t["R"])
    sx, dx = E.SP[0][0][0], E.SP[0][1][0]                       # modulo della pagina sinistra e della destra
    st = op(c, op="swappages", s=0)
    assert (E.SP[0][0][0], E.SP[0][1][0]) == (dx, sx)
    assert st["annulla"] == {"nome": "Inverti pagine", "s": 0}
    st = op(c, op="undo")
    assert st["annullato"] == {"nome": "Inverti pagine", "s": 0} and E.SP[0][0][0] == sx


def test_inverti_le_pagine_spread_che_non_esiste(editor):
    E = editor.E; prima = E.snap()
    with pytest.raises(ValueError, match="spread inesistente"): E.do_op(dict(op="swappages", s=5))
    assert E.snap() == prima and editor.codice("/api/op", {"op": "swappages", "s": 5}) == 400
```

Se l'operazione cambia quello che si salva, prova anche che l'album salvato si riapre (vedi `tests/test_formato.py`).

## 10. Il registro delle modifiche

`CHANGELOG.md` è l'unico registro. Ogni voce sta su una riga, sotto `## [Non rilasciato]`, nella sezione del suo tipo:

```
- `MOD-012` **editor** — Cosa cambia per chi usa o sviluppa. _File:_ `src/impaginatore/editor/server.py`. _Rif:_ `UX-001`.
```

Tipi (`AGG`, `MOD`, `COR`, `SIC`, `RIM`, `DOC`), numeri mai riusati e aree ammesse sono in `AGENTS.md`.
`python3 strumenti/controlli.py lint` controlla la forma. `CAMBIAMENTI.md` è il registro storico fino alla 1.5.2: non
si modifica più.

## 11. Aggiungere un testo dell'interfaccia

I testi visibili stanno in `src/impaginatore/risorse/testi/it.json`, una tabella `chiave → testo`:

- le chiavi cominciano con `comune.` (tutte e due le pagine), `home.` (schermata Album) o `editor.` (editor);
- i segnaposto sono in minuscolo tra graffe: `"editor.bozza.aggiungi_n": "Aggiungi {n} spread"`.

Il server mette nella pagina solo i testi del suo prefisso (`risorse.testi_pagina`), come `const TESTI`. Nella pagina:

- in HTML: `data-t="editor.x"` (testo), `data-t-title`, `data-t-aria`; nella schermata Album anche `data-t-ph`
  (segnaposto di un campo);
- in JavaScript: `t("editor.bozza.aggiungi_n", { n: 3 })`.

`tests/test_ux_editor_marca.py::test_testi_tutti_nella_tabella` controlla che ogni chiave usata dall'editor esista,
che non restino chiavi `editor.` inutilizzate e che i segnaposto abbiano la forma giusta. Una chiave costruita a pezzi
nel codice (per esempio `"editor.bozza.r_" + ritmo`) va aggiunta all'elenco delle chiavi dinamiche in quel test.

Oggi c'è solo l'italiano; le altre lingue arrivano con T-206. Nelle pagine restano alcuni testi scritti direttamente nel
codice (per esempio la linguetta «Tono» e i filtri della galleria): un testo nuovo va sempre nella tabella.

## 12. Regole di sicurezza

Il dettaglio è in [`SICUREZZA.md`](../architettura/SICUREZZA.md). Quelle che si toccano più spesso:

- **Niente rete.** Nessuna funzione manda foto o dati in rete. Il server ascolta solo su `127.0.0.1` e rifiuta altre
  origini.
- **Gettone.** Ogni richiesta alle API porta il gettone di sessione. Un indirizzo nuovo passa da `servizio.Gestore`,
  che lo controlla.
- **Percorsi.** Un percorso che arriva dalla pagina o da un progetto si usa solo dentro le radici consentite
  (`percorsi`, `RADICI.controlla`). Le cartelle nuove le sceglie l'utente in una finestra del sistema.
- **I progetti sono dati.** Mai `exec`, `eval` o `import` di qualcosa che viene da un progetto, da uno ZIP o da un nome
  di file. `tests/test_sicurezza.py` lo controlla.
- **Processi.** `subprocess` con gli argomenti in lista, mai `shell=True`. Un `# nosec` ha il motivo accanto.
- **Pagine.** Testi dell'utente nell'HTML solo con `escH` o `esc`; niente `alert`, `confirm`, `prompt`, `eval`,
  `window.open`, gestori in linea; `localStorage` sempre dentro `try`. Lo controlla
  `test_niente_finestre_del_browser_ne_codice_rischioso`.
- **Assistente AI.** Nessuno strumento prende un percorso; i testi dei progetti si passano come dati; le immagini solo
  con il consenso dell'utente.

## 13. Prima di consegnare

```bash
python3 strumenti/controlli.py lint
python3 strumenti/controlli.py copertura
```

Riporta l'esito com'è, compresi i test saltati e i controlli non eseguiti. Poi aggiungi la voce in `CHANGELOG.md` e fai
il commit con i soli file tuoi:

```bash
git add src/impaginatore/editor/server.py tests/test_editor_operazioni.py CHANGELOG.md
git commit -m "feat(editor): …"
```
