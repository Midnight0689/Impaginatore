# Kit social di Impaginatore

Materiali pronti per i social delle 12 settimane intorno al lancio (S-3 → S8, dal 1° febbraio al 25 aprile 2027), compito T-504 di `docs/PIANO.md`. Nessun profilo è aperto e niente è pubblicato: si apre e si pubblica quando lo decide il titolare.

| File | Che cosa contiene |
|---|---|
| `STRATEGIA.md` | Canali e perché, pilastri, frequenza, metriche, misure dei canali con le fonti, cosa non fare |
| `PROFILI.md` | Nomi utente, biografie in italiano e inglese, «In evidenza», link, per canale |
| `CALENDARIO.md` · `CALENDARIO.csv` | 49 uscite con data, testo completo in italiano (10 anche in inglese), più la riserva MCP. **File generati** |
| `COPIONI.md` | Sei video verticali, inquadratura per inquadratura. **File generato** |
| `sorgenti/uscite.txt` · `sorgenti/copioni.md` | Da qui si cambiano i testi |
| `modelli/` | Le grafiche, in HTML e CSS con i colori e i caratteri del brand (`social.css` importa `brand/tokens.css` e `brand/font/font.css`) |
| `modelli/uscite/` | Grafiche di una sola uscita (U02, U10, U37, U49) e della riserva MCP (`mcp-…`) |
| `grafiche/` | I PNG da caricare. **Non versionati**: si rigenerano |
| `anteprime/` | Tavole alla misura di un telefono (`telefono-*.png`, versionate) e con le zone coperte dall’interfaccia (`zone-*.png`, non versionate), più `contrasti.txt` |
| `strumenti/` | `genera_grafiche.py`, `componi_testi.py`, `controlla_testi.py`, `listino.py`, `costanti.json` |

## Comandi

Dalla radice del repository:

```sh
# grafiche: tutte, o solo quelle nominate; poi le tavole in anteprime/
uv run --no-project --with pillow python marketing/social/strumenti/genera_grafiche.py
uv run --no-project --with pillow python marketing/social/strumenti/genera_grafiche.py scheda-prezzo U37-rosetta

# testi: ricompone CALENDARIO.md, CALENDARIO.csv e COPIONI.md dai sorgenti
python3 marketing/social/strumenti/componi_testi.py

# controllo automatico di testi e grafiche: esce con 1 se trova errori
python3 marketing/social/strumenti/controlla_testi.py
```

`genera_grafiche.py` usa Google Chrome senza interfaccia (o Chromium; variabile `CHROME` per un altro percorso) e Pillow, che `uv` scarica in una cartella temporanea senza installarlo nel progetto; `--no-project` evita che `uv` sincronizzi l’ambiente del programma e riscriva `uv.lock`. Ci mette circa due minuti per tutte le grafiche. I PNG contengono le foto dimostrative: se mancano, lo script lo dice e si scaricano con `marketing/demo/scarica_demo.py`. Le grafiche oltre 1 MB vengono segnalate: vanno bene per i canali (il limite più stretto è il banner di YouTube, 6 MB) ma non si versionano.

Gli altri due script usano solo la libreria standard di Python.

## Da dove arrivano numeri e date

- **Prezzi, computer, giorni di prova e di rimborso, ore di assistenza**: solo da `docs/mercato/tier.json`, attraverso `strumenti/listino.py`. Nei testi si scrivono come `{{pro.lancio}}`, `{{frase.pro}}` («79 € fino al 23 aprile, poi 99 €»), `{{ore.5}}`; nelle grafiche come `data-valore="pro.lancio"`. Se cambia il listino, si rilanciano i due script e il controllo.
- **Date, link, confronto con gli abbonamenti, valori ancora da decidere**: `strumenti/costanti.json`.
- Una chiave sconosciuta ferma gli script: un refuso non arriva in un post.

## Come si usa, una settimana tipo

1. Il lunedì si apre `CALENDARIO.md` alla settimana giusta: per ogni uscita c’è canale, ora, grafica e testo.
2. Si rigenerano le grafiche di quella settimana e si guardano in `anteprime/` (le tavole `zone-*` mostrano in rosso ciò che l’interfaccia copre o taglia).
3. Si programmano i post con gli strumenti nativi dei canali (Meta Business Suite, LinkedIn, YouTube Studio), copiando il testo dal riquadro così com’è.
4. Si cambia il link nella bio se il campo «Link» lo chiede.
5. Nei giorni di uscita si risponde ai commenti due volte al giorno.

## Modelli grafici

Ogni modello dichiara nella testa misura, temi (chiaro e scuro), lingue e zone di sicurezza; `genera_grafiche.py` ne fa un PNG per ogni combinazione (`nome[-scuro][.en].png`).

| Modello | Misura | Uso |
|---|---|---|
| `profilo-verde` · `profilo` | 1080 × 1080 | Immagine del profilo, tutti i canali (si vede il cerchio) |
| `copertina-facebook` | 1702 × 630 | Copertina della pagina Facebook |
| `copertina-youtube` | 2560 × 1440 | Banner del canale YouTube |
| `copertina-linkedin` · `copertina-linkedin-profilo` | 1512 × 256 · 1584 × 396 | Pagina aziendale e profilo del titolare |
| `post-verticale` | 1080 × 1350 | Post 4:5 con spread in scala (U01) |
| `post-quadrato` | 1080 × 1080 | Post 1:1, annuncio della data (U05, U09) |
| `storia` | 1080 × 1920 | Storia 9:16, accesso anticipato (U14) |
| `carosello-copertina` · `carosello-interna` · `carosello-chiusura` | 1080 × 1350 | Caroselli (U02; schema per U24, U27, U41) |
| `annuncio-lancio` · `annuncio-lancio-storia` | 1080 × 1350 · 1080 × 1920 | Lancio (U15–U17, U19) |
| `scheda-prezzo` · `scheda-prezzo-listino` | 1080 × 1350 | Le tre licenze, con il prezzo di lancio e dopo il 23 aprile |
| `scheda-ore` | 1080 × 1350 | Assistenza a ore (U23, U43) |
| `citazione` | 1080 × 1350 | Consigli di bottega (U07, U28, U36) |
| `prima-dopo` | 1080 × 1350 | Spazi a occhio e spazi uniformi, in scala (U11) |
| `copertina-video` | 1920 × 1080 | Miniatura dei video YouTube (U18) |
| `copertina-reel` | 1080 × 1920 | Copertina di reel e Shorts (V1–V6) |
| `segnaposto-schermata` | 1080 × 1350 | Pagina di carosello con una schermata dell’app (U24) |
| `uscite/U02-pagina-3` · `uscite/U02-pagina-4` | 1080 × 1350 | Pagine 3 e 4 del carosello «Tre promesse» |
| `uscite/U10-tre-anni` | 1080 × 1350 | Fare i conti su tre anni (U10, U13) |
| `uscite/U37-rosetta` | 1080 × 1350 | Offerta macOS 28 (U37–U39) |
| `uscite/U49-ultimo-giorno` | 1080 × 1920 | Storia dell’ultimo giorno del prezzo di lancio |
| `uscite/mcp-bozza-claude` | 1080 × 1350 | Riserva MCP (R01, R02) |

Per un’uscita con testi diversi da quelli del modello si copia il modello in `modelli/uscite/` con il nome dell’uscita (es. `U28-consiglio-02.html`), si cambiano i testi e si rigenera. I file che cominciano con `_` non vengono resi.

## Segnaposto da riempire prima di pubblicare

| Che cosa | Dove | Note |
|---|---|---|
| Link: sito, lista d’attesa, prova, prezzi, installazione, assistenza, laboratori, manuale, offerta macOS 28, guida a Claude; email di assistenza | `strumenti/costanti.json` (`sito`, `link_*`, `email_supporto`) | Finché sono vuoti restano scritti `{{link_…}}` nei testi composti; il controllo li elenca come avvisi |
| Prezzi dell’offerta macOS 28 | `costanti.json`: `prezzo_rosetta_pro`, `prezzo_rosetta_studio` | Proposta del piano: 49 € e 99 €, da approvare con il parere del legale (PIANO-90-GIORNI §3.2). Finché sono vuoti la grafica U37 mostra il segnaposto |
| Confronto con gli abbonamenti | `costanti.json`: `confronto.*` | Valori del 15/11/2026; da rileggere prima di U10 e U13 (un abbonamento rincara dal 1/1/2027) |
| Caso di studio di un beta tester | `costanti.json`: `caso.nome`, `caso.citazione`, `caso.dato` | Solo dati veri e consenso scritto (U27) |
| Webinar con un laboratorio | `costanti.json`: `webinar.laboratorio`, `webinar.data` | Solo se confermato e con il consenso del laboratorio (U32) |
| Video di un formatore | `costanti.json`: `educator.nome`, `educator.canale` | U40 |
| Schermate dell’app | `modelli/schermate/pannello-misure.png` (888 × 700), `modelli/schermate/video-primo-album.png` (760 × 640) | Dopo l’interfaccia ridisegnata (T-205) e le schermate di T-501; ora i modelli mostrano un riquadro con misura e nome del file |
| Riprese dei video | `riprese/V1-01-wifi.mov` e seguenti, elencate in `COPIONI.md` | Cartella non versionata |
| Nomi di beta tester, laboratori, formatori | testi delle uscite U17, U27, U32, U40 | Solo con il consenso scritto di ciascuno |
| Presenza alla Convention ANFM | U09, U19, U20 | Le righe sulla Convention si tolgono se la presenza non è confermata |

## Se cambia qualcosa

- **La data del lancio**: si cambiano le date in `costanti.json` (`data.*`), `INIZIO_S0` in `strumenti/componi_testi.py` e le date delle uscite in `sorgenti/uscite.txt`; poi si ricompone e si controlla (il controllo verifica che i giorni della settimana scritti nei testi tornino con le date).
- **Il listino**: basta `docs/mercato/tier.json`, poi i due script e il controllo.
- **Dopo il 23 aprile**: per i prezzi si usa `scheda-prezzo-listino`, mai più `scheda-prezzo`. Il controllo segnala un prezzo di lancio in un’uscita datata dopo la fine del lancio.

**Se le 300 licenze di lancio finiscono prima del 23 aprile**, al posto di U44–U49 si pubblica, su Instagram e Facebook, questo testo (e si toglie il prezzo di lancio dalla pagina):

```text
Le licenze a prezzo di lancio sono finite oggi, prima del previsto. Grazie a chi ha comprato e a chi ci ha scritto anche solo per una domanda.

Da adesso valgono i prezzi di listino, che restano quelli, senza promozioni a sorpresa. La prova gratuita resta com’è.

Link nella bio.
```

## Riserva MCP

Le uscite R01–R03 e la grafica `uscite/mcp-bozza-claude` riguardano la bozza dell’album preparata da Claude tramite il server MCP, che non è ancora rilasciato. Restano fuori dal calendario e **si pubblicano solo dopo il rilascio del server MCP** (T-203) e della sua guida (T-403). Prima: rileggere la frase sulla riservatezza di R01 e R02 con la guida (`docs/manuale/assistente/`): dice che l’assistente è facoltativo (Pro, Studio e prova), che testi e misure vanno al programma assistente e al suo fornitore, che le immagini sono spente di serie e che gli originali non partono mai; togliere dalla grafica la fascia «Riserva» (`<p class="riserva">`). Il controllo automatico vieta di nominare Claude o MCP fuori dalla riserva.

## Controllo automatico

`strumenti/controlla_testi.py` legge sorgenti, testi composti, profili, copioni e grafiche, e verifica:

- parole vietate dallo `STYLEBOOK.md` (italiano e inglese), emoji, punti esclamativi, maiuscole urlate;
- che ogni importo in euro sia nel listino di `tier.json` (o nel confronto di `costanti.json`), che un prezzo di lancio compaia sempre con «fino al 23 aprile, poi» e il listino della stessa licenza, con «una volta» e l’IVA; niente prezzi barrati né «invece di»; nessun prezzo di lancio dopo il 23 aprile;
- che le ore di assistenza non siano presentate come risparmio;
- nessun nome di concorrenti o di laboratori (fuori dalle parti marcate come interne);
- i limiti di lunghezza di ogni canale e il numero di hashtag;
- che Claude e MCP compaiano solo nella riserva, senza data, con il marcatore e con grafiche `mcp-…`;
- giorni della settimana coerenti con le date; niente uscite di sabato, a Pasqua, a Pasquetta e il 25 aprile;
- che i file composti siano aggiornati e che modelli e grafiche citati esistano.
