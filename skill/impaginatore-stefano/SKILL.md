---
name: impaginatore-stefano
description: Impaginare album fotografici (battesimi, matrimoni, comunioni, servizi di famiglia) di Stefano usando il programma Impaginatore (editor web con spread, modelli, testi, export JPG/PDF/PSD). Usala SEMPRE quando Stefano parla di preparare/impaginare un album, spread, bozza, PSD dell'album, modifiche del cliente sugli spread, copertina o PDF per WhatsApp. Ha la precedenza sulla skill impaginazione-album-stefano, che resta solo come motore di riserva.
---

# Impaginatore: modo predefinito per gli album di Stefano

Rispondi in italiano, breve e diretto, con immagini quando aiutano. La cartella del programma è quella che contiene questo file: risali da `skill/impaginatore-stefano/` (il link in `~/.claude/skills` punta al repository). Chiamala `ROOT`. Python: `~/.album-tools/venv/bin/python`.

## Flusso
1. **Ambiente**: se manca `~/.album-tools/venv`, di' a Stefano di lanciare `ROOT/Installa.command`.
2. **Programma**: controlla `http://127.0.0.1:8765/api/ping`; se non risponde apri `ROOT/Impaginatore.app` (oppure `Avvia Impaginatore.command`).
3. **Progetto**: nuovo con `POST /api/nuovo` (`nome`, `w`, `h` in cm, opz. `abb`, `spazio`, `margine`) oppure «Apri progetto esistente». Poi `POST /api/apri` con `path` → restituisce la porta dell'editor.
4. **Foto**: informazioni (formato, misure, cliente) chieste a Stefano; selezione in alta con `motore/scripts/abbina.py`, analisi con `analizza.py`, bozza con `anteprima.py` (vedi `motore/SKILL_originale.md` per i parametri). Le foto stanno in `Foto/` del progetto o nelle cartelle indicate in `progetto.json`.
5. **Rifinitura**: nell'editor (spread, modelli, cornici, testi, allinea, versioni). Esporta JPG/PDF/PSD dall'editor.
6. **Regole di stile e Photoshop**: `motore/references/stile.md` e `photoshop.md`.

## Regole d'oro
- Con l'editor aperto NON modificare `spec.py` a mano: lo salva l'editor (autosave 2 s). Per modifiche via script chiudi/riavvia prima l'editor, dopo aver controllato che non ci siano modifiche non salvate.
- Mai toccare PSD già ritoccati a mano da Stefano; mai sovrascrivere i suoi PDF/esportazioni.
- Non usare undo/redo sull'editor vivo per test: lavora su una copia del progetto.
- Dati globali dell'utente (`~/.album-tools/modelli_utente.json`) non vanno cancellati; i test usano un HOME finto.
- Dopo ogni modifica al codice: test su copia, riavvio dell'editor, poi `git commit` + `git push` e di' a Stefano che sull'Air basta **Aggiorna.command**.
