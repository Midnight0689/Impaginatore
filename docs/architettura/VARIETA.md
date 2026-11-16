# Varietà delle disposizioni

Il titolare: «la versione 1.5.x produceva modelli troppo uguali a valle della generazione automatica. Dovrebbe invece
creare modelli molto diversi tra loro creando una grande differenziazione e varietà».

Questo documento dice da dove veniva la somiglianza, come la si misura, cosa è cambiato e dove si regola.

## Da dove veniva la somiglianza

| Dove | Cosa faceva | Effetto |
|---|---|---|
| `editor/server.py`, `tpl_options` | proposte in ordine di solo costo (somma delle differenze di proporzioni fra foto e cornici); doppioni tolti solo se la geometria è identica | le prime proposte erano la stessa disposizione specchiata o con le pagine scambiate (STRIP3+CV e CV+STRIP3, X13 e X13M, BAND2+COL2 e COL2+BAND2), a distanza zero una dall'altra |
| `editor/server.py`, `disposizioni` («Altra disposizione») | stesso ordine per costo | pressioni di fila davano disposizioni quasi uguali |
| `editor/server.py`, `BUILD`/`LAYS` | moduli sulla griglia 12 × 8 della pagina: le cornici hanno le proporzioni della griglia, non delle foto | con foto tutte orizzontali (3:2) su un 60 × 22,5 entrano solo FULL, PP, COL2, BAND2, G4; con tutte verticali DUO, V4, STRIP3, CV, SV. Pochi schemi possibili, sempre quelli |
| `motore/bozza.py`, `punteggio` e `_scegli` | la disposizione meno costosa; l'unica regola contro la ripetizione era «non la stessa coppia di moduli tre volte di fila» | su 300 foto orizzontali 13 schemi in 106 spread, 66 spread che ripetono uno schema degli 8 prima |

## La misura (`motore/varieta.py`)

Una disposizione si guarda come la vede chi sfoglia l'album: le caselle normalizzate sullo spread.

- **Descrittore** (`descrivi`): un'immagine ridotta dello spread (16 × 48 celle; per ogni cella la misura e la forma
  della casella che la copre), la stessa specchiata sulla piega, e alcuni numeri: caselle per pagina, caselle a cavallo
  della piega, parte coperta, peso della foto più grande, pagine con il margine bianco, simmetria.
- **Distanza** (`distanza`): metà geometria (differenza delle immagini ridotte, la minore fra diritta e specchiata),
  metà struttura (i numeri e la famiglia). 0 la stessa disposizione, anche specchiata o con le pagine scambiate; 1
  niente in comune.
- **Famiglia** (`famiglia`): per pagina `vuota`, `intera`, `respiro` (poche foto piccole su tanto bianco), `coppia`,
  `dominante`, `griglia`, `striscia`, `mosaico`; per lo spread le due pagine in ordine alfabetico («coppia+intera»),
  oppure `piega` se una foto attraversa la piega. L'editor la mostra sotto le proposte e nella pillola di «Altra
  disposizione» (testi `editor.fam.*`).
- **Schema** (`Descrittore.schema`): la geometria quantizzata sulle celle, uguale per la specchiata. Due spread con lo
  stesso schema sono «la stessa disposizione».

`misura_proposte` (famiglie, distanza media e minima, coppie quasi uguali sotto 0,15) e `misura_sequenza` (schemi e
famiglie diversi, ripetizioni entro 8 spread, distanza fra spread vicini) servono ai test e a rifare i numeri qui sotto.

## Cosa è cambiato

1. **Moduli adattivi** (`ADATTIVI` in `editor/server.py`, 17 moduli, 27 voci di `LAYS`): cornici libere calcolate
   sulla pagina vera, con le proporzioni delle foto (3:2, 2:3) e lo stesso spazio G fra le foto, su ogni formato. Una
   grande con una colonna o una fila di piccole (CO3, CV2, FO3, FO4), griglie e strisce di orizzontali o verticali con il
   margine (GO6, GV4, GV6, SO3, SR3, SV4), una grande e piccole sotto o a fianco (DO3, DO4, DV3, MO4), pagine con tanto
   bianco (RO1, RV2), una verticale al vivo su metà pagina (VI1). Sono moduli di pagina come gli altri: il progetto
   salva le cornici libere, quindi i progetti si aprono anche con le versioni di prima (nessun cambio di formato).
2. **Ordine delle proposte** (`ordine_vario`): la prima resta la meno costosa fra i moduli di sempre (quella che la
   1.5.x metteva prima, se una di loro rispetta le foto); poi ogni volta quella che rende più basso costo per foto +
   0,9 × somiglianza con la più vicina già messa + 0,25 × volte che la sua famiglia c'è già + 1 se il suo schema c'è
   già (massima rilevanza marginale, `varieta.ordina`). Le prime 40 così, le altre per costo. Un volto noto tagliato o
   sulla piega pesa come mezza foto molto tagliata (`PENALITA_VOLTO`). La disposizione attuale resta in testa.
3. **«Altra disposizione»** (`ordine_disposizioni`): stesso ordine vario fra quelle che rispettano le foto, poi quelle
   che tagliano di più dal taglio minore. L'esito dice la famiglia. L'ordine non dipende dalla disposizione attuale:
   avanti e indietro restano coerenti (UX-001).
4. **Bozza** (`bozza._scegli`, con la vista che `tpl_options` restituisce): in quest'ordine
   - a cavallo della piega solo se il prodotto del laboratorio non ha una zona della piega (`piega_mm`);
   - non più difetti della migliore: pagina vuota, foto «sola» che divide la pagina o in una cornice sotto il 35 %
     della pagina, volto noto tagliato o sulla piega (`_duro`);
   - ritaglio entro ×1,25, o non oltre la meno tagliata + 5 % se tagliano tutte;
   - punteggio entro 0,35 + 0,08 × foto dalla migliore; il ritmo scelto rispettato quanto la più rispettosa;
   - poi la minore fra punteggio + costo + ripetizione: somiglianza con gli ultimi quattro spread (0,7, 0,4, 0,2, 0,1),
     stessa famiglia degli ultimi due (0,45, 0,2), stesso schema negli ultimi 8 (1,2), due spread a cavallo della piega
     negli ultimi 8 (0,8).
   Ogni spread della proposta ha `fam` e `schema`; `schemi` dice quante geometrie diverse usa la bozza (il foglio lo
   mostra come «disposizioni diverse»). Lo stesso seme dà la stessa bozza; «Rifalla» cambia seme.
5. **Velocità**: `tpl_options` salta prima di abbinare le foto le disposizioni che non possono stare entro
   `TAGLIO_PIU` (limite dal confronto delle proporzioni in ordine) e calcola le cornici di ogni modulo una volta per
   pagina. In media 0,06 s per gruppo (0,05 prima), al massimo 0,25 s con 8 foto.

L'assistente (MCP) usa le stesse funzioni (`/api/bozza`, operazione `disposizione`): ha la stessa varietà.

## I numeri

Insiemi sintetici (solo proporzioni e date: 60 foto per le proposte, 10/40/120/300 per la bozza; orizzontali 3:2 con
qualche 4:3 e 16:9, verticali, miste 55/37/8 %, con panoramiche), album 60 × 22,5, gruppi da 2 a 8 foto. Prima = il
codice di `origin/prodotto/2.0` a 920b9a3, dopo = questo.

Prime 8 proposte per le stesse foto (media sui gruppi):

| Foto | Famiglie prima → dopo | Distanza media | Distanza minima | Coppie quasi uguali (su 28) |
|---|---|---|---|---|
| orizzontali | 1,76 → 5,43 | 0,258 → 0,502 | 0,024 → 0,168 | 5,00 → 1,14 |
| verticali | 2,14 → 6,57 | 0,303 → 0,510 | 0,000 → 0,220 | 11,14 → 0,00 |
| miste | 2,19 → 3,76 | 0,351 → 0,470 | 0,018 → 0,154 | 5,10 → 1,19 |
| con panoramiche | 1,43 → 1,81 | 0,217 → 0,268 | 0,024 → 0,064 | 7,00 → 4,33 |

«Altra disposizione», distanza media fra pressioni di fila: 0,245 → 0,539 (orizzontali), 0,228 → 0,541 (verticali),
0,295 → 0,544 (miste), 0,211 → 0,313 (con panoramiche).

Bozza di 300 foto, seme 0 (schemi diversi · spread che ripetono uno schema degli 8 prima · spread con ritaglio oltre
×1,25 · ritaglio medio):

| Foto | Prima | Dopo |
|---|---|---|
| orizzontali | 13 · 66 · 24 · ×1,159 | 26 · 13 · 6 · ×1,140 |
| verticali | 12 · 70 · 1 · ×1,102 | 31 · 12 · 0 · ×1,107 |
| miste | 32 · 29 · 9 · ×1,116 | 67 · 6 · 5 · ×1,099 |
| con panoramiche | 34 · 29 · 36 · ×1,161 | 60 · 8 · 33 · ×1,151 |

Pagine vuote: le stesse. Foto «sole» in una cornice piccola: da 0–7 per bozza a 0. Rispetto del ritmo scelto: simile
o meglio (verticali 0,61 → 0,98), orizzontali 0,71 → 0,62.

## Dove si regola

Le costanti stanno in cima ai file, ognuna con il suo commento: `varieta.py` (`QUANTI`, `PESO_SOMIGLIANZA`,
`PESO_FAMIGLIA`, `DOPPIONE`, `FINESTRA`, `PESI_VICINI`, `PESI_FAMIGLIA`, `SCHEMA_RIPETUTO`, `PIEGA_VICINA`),
`bozza.py` (`MARGINE`, `MARGINE_FOTO`, `PESO_COSTO`, `TAGLIO_IN_PIU`, `PAGINA_SOLA`), `editor/server.py`
(`TAGLIO_PIU`, `PENALITA_VOLTO`, `ADATTIVI`). `tests/test_varieta.py` fissa le soglie che la varietà deve tenere.

## Limiti

- Con foto tutte panoramiche le possibilità restano poche (una panoramica sta bene solo in poche cornici): la varietà
  cresce poco.
- La misura guarda la geometria, non il contenuto delle foto: due disposizioni diverse con foto simili possono sembrare
  simili lo stesso.
- I moduli adattivi non stanno sulla griglia 12 × 8 di pagina: si spostano e si ridimensionano come le cornici libere.
