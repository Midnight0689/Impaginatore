# Foto dimostrative per le schermate di vendita

- **Cosa c'è**: `foto/` contiene 62 JPEG (`DEMO_0001.jpg`…`DEMO_0062.jpg`, lato lungo 3000 px, circa 43 MB in tutto: 39 orizzontali, 16 verticali, 4 quadrate, 3 panoramiche 2:1) che raccontano un matrimonio dai dettagli del mattino alla fine della festa. Ogni file ha l'EXIF `DateTimeOriginal` progressivo (20/09/2025, data fittizia) e l'autore in `Artist`. `provini.jpg` è il foglio provini. `foto/` è esclusa da git.
- **Provenienza**: tutte da Pexels. 55 foto vengono da un unico servizio di Andrea Prochilo, scattato il 18/09/2025. Le altre 7 (scambio degli anelli, allestimento, boutonniere, spumante, confettata, brindisi, torta) vengono da altri autori e non mostrano i volti degli sposi. Riga per riga, `FONTI.csv` riporta pagina, autore, licenza, data di scaricamento, ritaglio e sha256: è la prova di provenienza e va versionato.
- **Licenza verificata il 15/11/2026** su https://www.pexels.com/license/ e https://www.pexels.com/terms-of-service/ (termini aggiornati al 20/10/2026). La licenza permette l'uso gratuito, anche commerciale, e la modifica. L'attribuzione non è obbligatoria e non serve chiedere il permesso.
- **Si può**: usarle nelle schermate dell'app, sul sito, nelle email e nei video di presentazione di Impaginatore, anche ritagliate o modificate. Citare gli autori è gradito.
- **Non si può**:
  - vendere o ridistribuire le foto in sé, anche dentro pacchetti di esempio scaricabili;
  - caricarle su altre piattaforme di foto o sfondi;
  - usarle come logo o marchio;
  - suggerire che le persone ritratte, o gli autori, approvino o usino Impaginatore (niente testimonianze inventate, niente "i nostri clienti");
  - mostrare le persone in modo offensivo o fuorviante.
- **Liberatorie**: Pexels non garantisce le liberatorie delle persone ritratte, che qui sono riconoscibili. In Italia l'uso pubblicitario del ritratto richiede il consenso (art. 96-97 L. 633/1941, art. 10 c.c.), e questa verifica resta a nostro carico. Prima di usare un volto in primo piano in una pubblicità (banner, copertina, annuncio) chiedere conferma scritta ad Andrea Prochilo, oppure usare solo dettagli e scatti di spalle.
- **Esclusioni**: sono state scartate le foto con loghi (auto d'epoca, consolle del DJ, tamburo), con nomi leggibili su inviti e menù, con minori in primo piano e quelle che su Pexels risultano rimosse (404).
- **Rigenerare**: `uv run marketing/demo/scarica_demo.py`. Lo script usa solo la libreria standard e Pillow, in versione fissata. Riscarica gli originali dalla CDN pubblica di Pexels, applica ritagli ed EXIF e controlla lo sha256 di ogni file. Con `--cache DIR` gli originali restano su disco. Con `--aggiorna-hash` si riscrivono gli hash dopo aver cambiato il CSV.
- **Unsplash e Pixabay**: non sono state usate, perché le loro pagine bloccano lo scaricamento automatico (verifica anti-bot su unsplash.com, errore 403 su pixabay.com) e la richiesta era di non aggirare protezioni.
