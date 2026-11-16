# Operazioni dell'editor per l'interfaccia e per l'assistente

Le operazioni nuove dei passi 1 e 2 di `docs/prodotto/ux/PIANO-UX.md` stanno nel motore e nel server dell'editor, non
nella pagina: l'interfaccia (T-205) e il server MCP (T-203) chiamano le stesse funzioni e ottengono gli stessi risultati.
Si usano in due modi:

- **HTTP**, con il gettone della sessione (`docs/architettura/SICUREZZA.md`): `POST /api/op` con `{"op": …}` per quelle
  che cambiano l'album, gli altri indirizzi indicati sotto per quelle che non lo cambiano;
- **nello stesso processo**: `editor.server.do_op(o)` con lo stesso JSON, oppure le funzioni nominate qui sotto.

Ogni operazione che cambia l'album passa da `do_op`: un passo d'annulla, i controlli di `controlla_stato` (niente
progetti salvati che poi non si aprono), il contatore `rev`. Le funzioni a pagamento passano dal cancello della licenza
(`licenze.consentita`, chiavi di `docs/mercato/tier.json`): se la fascia non le comprende la risposta è 403 con il motivo.

## Risposta di `/api/op`

Lo stato dell'editor (`state()`, che contiene già `annulla` e `ripeti`), più:

| Campo | Quando | Cosa |
|---|---|---|
| `annulla`, `ripeti` | sempre (anche in `/api/state`) | `{nome, s}` del passo che farebbero adesso «Annulla» e «Ripeti» (`nome` da `NOMI_OP`, `s` lo spread da mostrare), oppure `null` |
| `esito` | operazioni che hanno un risultato da dire | vedi la tabella delle operazioni |
| `annullato` / `ripetuto` | `op: "undo"` / `"redo"` | `{nome, s}` del passo appena annullato o ripetuto: «Annullato: Sostituisci foto (spread 4)» |

`gruppo` (facoltativo, testo fino a 100 caratteri) in una qualsiasi operazione: le operazioni di fila con lo stesso
gruppo diventano un passo solo d'annulla (trascinamenti, cursori, tasti tenuti premuti). `disposizione` ha un gruppo da
sé per spread e pagina: le pressioni di D di fila si annullano insieme.

## Operazioni che cambiano l'album (`POST /api/op`)

| `op` | Parametri | `esito` | Licenza | UX |
|---|---|---|---|---|
| `disposizione` | `s`, `passo` 1 o -1, `side` `"L"`/`"R"`/assente (tutto lo spread) | `{disposizione, di, taglia, a_mano, lato}`: la n-esima di quante, il ritaglio peggiore (1 = nessuno), se si partiva da una disposizione fatta a mano | — | UX-001 |
| `sostituisci` | `at` `[s, side, idx]`, `photo` (nome senza estensione), `adatta` (di serie `true`) | `{scambiata_con, adattata, taglia, lato}`: lo spread da cui veniva la foto (se era già nell'album le due si scambiano), se la disposizione è stata riadattata (ritaglio oltre ×1,25: prima la pagina, poi lo spread) | — | UX-002 |
| `spazi` | `s`, `modo` `std`/`freq`/`custom`, `cm` (con `custom`, fino a 10) | `{corretti, diversi}` | — | UX-014 |
| `sistema` | `spread` (elenco di indici, assente = tutto l'album), `spazi` (di serie `true`), `tono` (`true`/`false`/assente), `modo`, `cm` | `{spazi, tono}`: quanti spread e quante foto ha corretto | spazi su più spread o su tutto l'album: `correzione_spaziature_album` (in Essenziale uno spread alla volta); tono: `uniformita_tono` (assente = se la licenza lo comprende) | UX-014 |
| `bozza` | `spreads` (quelli di `/api/bozza`, come li ha mostrati il foglio) oppure le opzioni di `/api/bozza` per una proposta nuova; `pos` (di serie in fondo) | `{spread, foto, da}` | `impaginazione_automatica_album` | UX-018 |

«Sistema» non cambia disposizioni né foto scelte e non tocca i volti: corregge spazi e tono, in un solo passo d'annulla.

## Operazioni che non cambiano l'album

| Indirizzo | Funzione | Richiesta | Risposta | Licenza | UX |
|---|---|---|---|---|---|
| `POST /api/controlla` | `controlla(spreads, tono, modo, cm)` | `{spread?, tono?, modo?, cm?}` | `{problemi: [{livello, tipo, s, side, idx, foto, testo, sistema}], conta: {blocca, guarda, info}, sistema: {spazi, tono, restano}, pronto}` | nessuna (il tono solo se la licenza lo comprende) | UX-014 |
| `POST /api/bozza` | `bozza(o)` | `{ritmo: alterna/piene/bianche, per_spread 1–8 \| spread (quanti), stelle, seme}` | `{spreads: [{L, R, foto, nomi, capitolo, inizio, ora, taglia}], capitoli, foto, per_spread}`; almeno 10 foto da usare | `impaginazione_automatica_album` | UX-018 |
| `GET /img/bozza/<n>?k=` | `bozza_jpg(n, k)` | — | anteprima JPEG dello spread n dell'ultima proposta | `impaginazione_automatica_album` | UX-018 |
| `POST /api/ricollega` | `ricollega(cartella, prova, scelte)` | `{cartella, prova?, scelte?: {foto: file}}` | `{trovate, mancanti, totale, diverse, proposte}`; con `prova` non cambia niente | — | UX-004 |
| `POST /api/import` con `a_caldo: true` | `do_import` + `aggiungi_a_caldo()` | `{paths, a_caldo: true}` | `{importate, saltate, riavvio: false, aggiunte}`: niente riavvio, annulla e ripeti restano | come l'import | UX-012 |
| `GET /api/ping` | — | — | `{boot, agg, path, rev, prep}`: `rev` cambia a ogni modifica (anche fatta dall'assistente), `prep` a ogni miniatura preparata | — | A-30, UX-012 |

Livelli di `controlla`: `blocca` (foto mancante o danneggiata, sotto 150 ppi, fuori dalla pagina), `guarda` (150–200 ppi,
volto tagliato o vicino alla piega, ritaglio oltre ×1,25, spazi diversi, pagina vuota, foto fuori tono, foto ripetuta),
`info` (foto non usate, con la stella o no). `sistema: true` vuol dire che «Sistema» lo corregge da solo.

## Calcoli del motore riusabili

- `motore/spazi.py`: `stato(rett, G, PPI, modo, valore)` e `correggi(...)`, stessi risultati di `gapStat`/`gapFix`
  della pagina (provato da un test nel browser su tre spread e tre riferimenti).
- `motore/bozza.py`: `capitoli`, `gruppi`, `punteggio`, `proposta(foto, opzioni, ritmo, per_spread, stelle, seme)`.
- `editor.server.disposizioni(s, side)`: le disposizioni possibili per le foto dello spread o della pagina, in ordine.
- `motore/album.foto_rgb(i, originale, serve)`: la miniatura (o il riquadro grigio se non è pronta) oppure l'originale
  alla misura che serve; i JPG «Stampa · 300 dpi» si fanno dagli originali, con l'abbondanza (UX-011).

## Preparazione in sottofondo (UX-012)

`impaginatore editor --sottofondo` (o `inizializza(progetto, home, sottofondo=True)`) apre il progetto con i soli
metadati. Le miniature che mancano si fanno in ordine di scatto su tutti i core meno uno, ognuna scritta accanto e poi
rinominata; i volti arrivano alla fine. Finché una miniatura non c'è, anteprime, Tono e riquadro Design mostrano il
riquadro grigio con le proporzioni della foto; la stampa legge gli originali e non ne è toccata. L'avanzamento sta in
`state().prep` (`{fatte, totale, volti, attivo}`) e in `ping.prep`. Un cambio di progetto ferma la preparazione e
scarta quello che finisce dopo. Di serie è spenta: la pagina non la usa ancora (T-205).
