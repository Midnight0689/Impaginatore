---
name: impaginazione-album-stefano
description: Impagina album fotografici (battesimi, matrimoni, comunioni, servizi di famiglia) nello stile di Stefano e genera i PSD per la stampa in Photoshop, con cornici modificabili, correzioni di luminosità per la stampa e PDF di bozza per il cliente. Usala ogni volta che Stefano parla di impaginare un album, fare gli spread, una bozza o anteprima album, i PSD dell'album, SmartAlbums, una selezione del cliente da impaginare, modifiche del cliente sugli spread (scambia, togli, metti a colori, primo piano), copertina dell'album o il PDF da mandare su WhatsApp, anche se non usa la parola "impaginazione".
---

# Impaginazione album (stile Stefano)

Flusso completo: selezione del cliente -> foto in alta -> analisi -> spec dell'impaginazione -> anteprime approvate ->
PSD in Photoshop -> verifiche -> correzioni del cliente -> PDF per il cliente.
Prima di comporre leggi `references/stile.md` (le regole che Stefano pretende e cosa non ha funzionato).
Prima di toccare Photoshop leggi `references/photoshop.md` (trappole già incontrate).

Stefano scrive in italiano, in modo diretto e veloce; vuole vedere immagini, non descrizioni. Rispondi in italiano,
breve, e manda sempre l'immagine di controllo. Quando qualcosa è sbagliato per colpa tua, dillo e correggilo.

## 0. Ambiente (una volta per Mac, anche sul MacBook Air)

```bash
zsh <skill>/scripts/setup.sh        # crea ~/.album-tools/venv, ultima riga = python da usare
```
Tutti gli script si lanciano con quel python, da `<skill>/scripts/`, con `--progetto <cartella del progetto>`.
Serve Photoshop (2026) in /Applications. Font: Bodoni Moda Italic e Avenir Next; se mancano sul Mac, le anteprime
usano font di sistema e nei PSD scegli font installati (`font_titolo_ps` / `font_testo_ps` in progetto.json).

## 1. Raccogli le informazioni (chiedi solo quello che non sai)

- **Formato chiuso/aperto in cm** (es. 30 x 22,5 chiuso = spread 60 x 22,5) e **numero massimo di spread**.
- **Abbondanza**: chiedila esplicitamente. Default 0 (misura esatta); il laboratorio può volerla o aggiungerla lui.
- **Dove sono le foto**: la cartella della selezione del cliente (spesso JPG web a bassa risoluzione) e le cartelle
  complete in alta da Lightroom (una per capitolo, es. "PORTICCIOLO", "BATTESIMO").
- **Album di riferimento** di Stefano (PDF o pagine JPG): guardali, ma lo stile di riferimento è in `references/stile.md`.
- Nome, sottotitolo, data per il titolo.

Crea la cartella di progetto (di solito `<album>/Impaginazione/`) con `progetto.json` partendo da
`assets/progetto_esempio.json` (tutti i campi sono spiegati lì: formato, dimensioni_esatte, spazio_mm 2,5, margine_mm 10,
esposizione, centri_volto, foto_extra, tolte, uscita_psd).

## 2. Foto in alta

```bash
python abbina.py --web "<selezione cliente>" --originali "<cartella cap.1>" "<cartella cap.2>" --dest "<album>/Selezione Alta" --prova
```
Prima con `--prova`. Se dice che gli originali sono **identici alla versione web** o piccoli, Stefano non ha riesportato
in alta da Lightroom: diglielo e aspetta che lo faccia, poi rilancia. Segnala nomi doppi tra cartelle e foto con
post-produzione diversa (chiedi quale versione usare). Poi senza `--prova` per copiare: scrive anche `origine.json`.

## 3. Guarda le foto

```bash
python analizza.py --progetto P provini       # tutte le foto numerate in ordine di scatto: guardale TUTTE
python analizza.py --progetto P luminosita    # pelle L* per cartella: capitoli più scuri da uniformare per la stampa
```
Raggruppa per momenti (capitoli), individua la foto più bella del soggetto (apertura e finale), le coppie che si
"parlano", le quasi-doppie (primo piano su una delle due), i gruppi grandi e piccoli, i dettagli.

## 4. Componi la spec e le anteprime

Scrivi `P/spec.py` (modello in `assets/spec_esempio.py`): `SPREADS = [(pagina sinistra, pagina destra), ...]`
con le foto indicate per nome file. Segui `references/stile.md`: griglia 12x8, moduli ripetuti, pagine immersive e
bianche alternate, una protagonista per spread, BN come accento, capitoli, climax sul rito, finale sul soggetto.

```bash
python anteprima.py --progetto P --nome v1                 # controllo + Anteprime/Anteprima v1 - N spread.jpg + Sequenza v1.txt
python analizza.py --progetto P ritagli 3,6,9              # finestre di ritaglio sugli originali: nessuno tagliato
```
Il controllo deve dire: 0 problemi, 0 doppie, nessuna foto non usata (salvo quelle in "tolte"). Guarda TU l'anteprima
con occhio critico prima di mandarla (spazi, ritagli, persone tagliate, ritmo), poi mandala con una spiegazione breve
dell'idea. Salva le versioni approvate in sottocartelle (es. "v3 approvata"), non sovrascriverle.

Correzioni del cliente: spesso arrivano come screenshot con segni colorati (frecce = scambio, X = togli o sposta,
pallini colorati = raggruppa per colore). Interpreta, e quando un segno è ambiguo chiedi con domande a scelta
(AskUserQuestion) prima di cambiare. Rimanda sempre l'anteprima degli spread toccati (`--spread 6,7`).

## 5. Luminosità e colore per la stampa

Le foto in stampa escono più scure: proponi `esposizione.globale` (es. +0,25), una base per cartella per i capitoli più
scuri e correzioni singole. Mostra il confronto prima di applicare:
```bash
python anteprima.py --progetto P --prima-dopo 3,4
python analizza.py --progetto P colore 20        # dominanti e guadagni proposti per bilanciamento_bianco
```
Le correzioni diventano livelli agganciati e modificabili nei PSD (Esposizione, Bilanciamento bianco).

## 6. PSD in Photoshop

```bash
python genera_psd.py --progetto P --spread 1,14     # prima una prova su 1-2 spread (uno con testo), falla vedere
python genera_psd.py --progetto P                   # poi tutti
python verifica_psd.py --progetto P --confronta-spec
```
Poi esporta un JPG di controllo da Photoshop e guardalo. Mostra a Stefano lo spread di prova prima di generarli tutti.

## 7. Modifiche quando Stefano ha già lavorato sui PSD

Se un PSD è stato salvato dopo la generazione, **è suo**: genera_psd.py lo salta da solo. Modificalo sul posto:
```bash
python modifica_psd.py --progetto P scambia 4:_DSC3457 5:_DSC3513
python modifica_psd.py --progetto P sostituisci 23:_DSC8801 _DSC9355
python modifica_psd.py --progetto P colore 15:_DSC0299        # oppure: bn, esposizione 4:_DSC3674 0.95
python modifica_psd.py --progetto P rifai-pagina 9 sinistra   # dopo aver aggiornato spec.py: rifà solo quella pagina
```
Ogni comando fa una copia di sicurezza in `PSD_vecchi/backup_<data-ora>/`; dillo a Stefano. Dopo: verifica_psd.py
ed esportazione di controllo. Leggi i valori attuali dai PSD (Stefano ritocca le esposizioni a mano): non rimetterli ai
valori di progetto.json. Foto nuove prese dalle cartelle complete vanno aggiunte a "foto_extra".

## 8. PDF per il cliente

```bash
python esporta_pdf.py --progetto P --nome "Album Anita - bozza" --copertina _DSC9383,_DSC9376   # ipotesi A/B
python esporta_pdf.py --progetto P --nome "Album Anita - definitivo" --copertina _DSC8814
```
Esporta i PSD come sono (anche modificati a mano), ~5 MB: va su WhatsApp. Controlla la pagina 1 prima di mandarlo.

## Regole d'oro (dettagli in references/)
- Spazio identico ovunque, anche sulla piega; nessuna foto sulla piega; persone mai tagliate.
- Misura esatta chiesta e verificata in cm in Photoshop; abbondanza solo se richiesta.
- Mai sovrascrivere il lavoro di Stefano: niente rigenerazioni sui PSD toccati, copie di sicurezza, nessun documento
  aperto con modifiche non salvate.
- Verifica sempre i file reali (psd-tools + JPG esportato), non solo la spec.
