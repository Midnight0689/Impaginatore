# Registro delle modifiche

Scritto per Claude (e per Stefano): cosa è stato cambiato, perché, in quali file.
**Regola:** prima di toccare il programma si legge questo file; dopo ogni modifica si aggiunge una voce in cima (numero di versione = numero del commit, vedi riquadro Versione), poi commit + push. Le versioni si possono ripristinare dal riquadro Versione → "Versioni precedenti".

## Versione 9 — Nuova interfaccia in stile Apple (solo scuro)
- Tema scuro neutro (`--bg #1b1b1d`, blu di sistema `--blue` per i comandi; il GIALLO resta solo per la selezione delle cornici sulla pagina). Font di sistema, pulsanti arrotondati senza bordo, controlli segmentati, finestre sfocate, scrollbar sottili.
- Barra in alto con icone SVG (annulla/ripeti, modelli, progetto, versioni, pannelli, esporta); sotto 1180 px di larghezza restano solo le icone. «Salva» diventa blu quando c'è qualcosa da salvare. Tolte le emoji dai pulsanti dello spread.
- Tutto il tema è in fondo al blocco `<style>` di `index.html` e `home.html` (sezione «Tema scuro in stile Apple»): per tornare indietro basta il ripristino di versione. Nessuna funzione cambiata.

## Versione 8 — Torna indietro e registro modifiche
- Riquadro Versione: elenco delle ultime 20 versioni con «Torna a questa». Il ripristino crea una NUOVA versione (la storia resta intatta, gli altri Mac la ricevono come aggiornamento). — `Editor Album/home.py` (`elenco_versioni`, `ripristina_versione`), `home.html`.
- Questo file `CAMBIAMENTI.md`.

## Versione 7 — Pulsante versione
- Pillola «Versione N · aggiornata / disponibile la N+1 / non riesco a controllare» con pallino verde/giallo/rosso. — `home.html`, `index.html`.

## Versione 6 — Riquadro versione
- Versione in uso, ultima su GitHub, novità, «Controlla aggiornamenti». — `home.py` (`info_versione`), `home.html`.

## Versione 5 — Avviso di aggiornamento
- Il programma fa `git fetch` all'avvio e ogni 3 ore; mostra l'avviso e «Aggiorna ora» (pull --ff-only, setup.sh, riavvio). Nell'editor compare «⬆ Aggiornamento». — `home.py`, `home.html`, `index.html`.

## Versione 4 — Galleria: foto mancanti
- Foto mancante: bordo rosso + etichetta «⚠ MANCANTE», la miniatura resta (galleria e striscia foto libere). Attenzione: `S.photos[].n` è senza estensione, `S.mancanti` con estensione. — `index.html`.

## Versione 3 — Importa foto senza copie
- `do_import` non crea più link/copie in `<progetto>/Foto`: aggiunge i percorsi degli originali a `foto_extra`. — `editor.py`.

## Versione 2 — Nuovo progetto accanto alle foto
- Campo facoltativo «Cartella delle foto»: il progetto nasce in `<cartella cliente>/Impaginatore`, le foto restano dove sono. — `home.py` (`nuovo`, `/api/scegli-foto`), `home.html`.

## Versione 1 — Prima versione su GitHub
- Programma completo (home + editor), motore incluso in `motore/`, `Installa.command`, `Aggiorna.command`, skill `impaginatore-stefano`.
- Funzioni già presenti: modelli utente, duplica/copia/incolla spread, allinea, versioni e backup del progetto, ricollegamento foto, esporta/importa progetto (ZIP), rilevamento foto modificate da Lightroom, PDF/JPG con profilo sRGB, magnete al centro.
