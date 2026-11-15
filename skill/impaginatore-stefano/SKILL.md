---
name: impaginatore-stefano
description: Impaginare album fotografici (battesimi, matrimoni, comunioni, servizi di famiglia) di Stefano usando il programma Impaginatore (editor web con spread, modelli, testi, export JPG/PDF/PSD). Usala SEMPRE quando Stefano parla di preparare/impaginare un album, spread, bozza, PSD dell'album, modifiche del cliente sugli spread, copertina o PDF per WhatsApp. Ha la precedenza sulla skill impaginazione-album-stefano, che resta solo come motore di riserva.
---

# Impaginatore: modo predefinito per gli album di Stefano

Rispondi in italiano, breve e diretto, con immagini quando aiutano. La cartella del programma è quella che contiene questo file: risali da `skill/impaginatore-stefano/` (il link in `~/.claude/skills` punta al repository). Chiamala `ROOT`. Python: quello dell'ambiente dove è installato il programma (sul Mac `~/.album-tools/venv/bin/python`, creato da `ROOT/legacy/macos/setup.sh`; altrove l'ambiente dove si è fatto `pip install -e ROOT`). Il codice sta in `ROOT/src/impaginatore/` (mappa in `ROOT/docs/architettura/ARCHITETTURA.md`).

## Flusso
1. **Ambiente**: se manca `~/.album-tools/venv` (o `python -c "import impaginatore"` fallisce), di' a Stefano di lanciare `ROOT/legacy/macos/Installa.command`.
2. **Programma**: controlla `http://127.0.0.1:8765/api/ping`; se non risponde apri `ROOT/legacy/macos/Impaginatore.app` (oppure `legacy/macos/Avvia Impaginatore.command`, o da terminale `python -m impaginatore`).
3. **Progetto**: nuovo con `POST /api/nuovo` (`nome`, `w`, `h` in cm, opz. `abb`, `spazio`, `margine`) oppure «Apri progetto esistente». Poi `POST /api/apri` con `path` → restituisce la porta dell'editor.
4. **Foto**: informazioni (formato, misure, cliente) chieste a Stefano; selezione in alta con `python -m impaginatore.motore.abbina`, analisi con `python -m impaginatore.motore.analizza`, bozza con `python -m impaginatore.motore.anteprima` (parametri in `references/SKILL_originale.md`). Le foto stanno in `Foto/` del progetto o nelle cartelle indicate in `progetto.json`.
5. **Rifinitura**: nell'editor (spread, modelli, cornici, testi, allinea, versioni). Esporta JPG/PDF/PSD dall'editor.
6. **Regole di stile e Photoshop**: `references/stile.md` e `references/photoshop.md` (in questa cartella).

## Regole d'oro
- Con l'editor aperto NON modificare `spec.py` a mano: lo salva l'editor (autosave 2 s). Per modifiche via script chiudi/riavvia prima l'editor, dopo aver controllato che non ci siano modifiche non salvate.
- Mai toccare PSD già ritoccati a mano da Stefano; mai sovrascrivere i suoi PDF/esportazioni.
- Non usare undo/redo sull'editor vivo per test: lavora su una copia del progetto.
- Dati globali dell'utente (modelli salvati: `~/Library/Application Support/Impaginatore/modelli_utente.json`; le 1.x li tenevano in `~/.album-tools/`, da dove vengono copiati) non vanno cancellati; i test usano un HOME finto (`pytest` dalla cartella `ROOT`).
- Prima di modificare il programma leggi `CAMBIAMENTI.md`; dopo ogni modifica aggiungi in cima una voce (cosa, perché, file) con il numero della nuova versione.
- Dopo ogni modifica al codice: test su copia, riavvio dell'editor, poi `git commit` + `git push` e di' a Stefano che sull'Air basta **legacy/macos/Aggiorna.command**.

- Se qualcosa va storto dopo una modifica: riquadro Versione → «Versioni precedenti» → «Torna a questa» (crea una nuova versione, non cancella nulla).
