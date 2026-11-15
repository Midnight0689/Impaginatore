# Impaginatore

Programma per impaginare album fotografici (spread, modelli, testi, correzioni) ed esportare JPG, PDF e PSD per Photoshop.

## Primo avvio su un Mac
1. Scarica questa cartella da GitHub (vedi sotto) e mettila dove vuoi.
2. Doppio clic su **Installa.command** (una volta sola): crea l'ambiente Python, collega la skill di Claude, controlla Photoshop e font.
3. Apri **Impaginatore.app**.

## Windows (versione di prova)
1. Estrai lo ZIP (o `git clone`) in Documenti.
2. Doppio clic su **Installa.bat** (una volta sola): serve Python 3.9 o più recente da python.org, con «Add python.exe to PATH» spuntato.
3. Doppio clic su **Avvia Impaginatore.bat**. Per aggiornare: **Aggiorna.bat** (serve Git).
Su Windows si esportano JPG e PDF; i PSD per Photoshop per ora solo dal Mac.

## Aggiornare
Sul Mac secondario: doppio clic su **Aggiorna.command**. Scarica le novità, aggiorna da solo l'ambiente e riavvia il programma.
Sul Mac principale gli aggiornamenti li carica Claude dopo ogni modifica.

## Cosa non è qui dentro
I progetti, le foto e i PSD (stanno nella cartella `Progetti/` o dove li tieni tu). Per portarli su un altro Mac: **Progetto → Esporta progetto**
nell'editor e poi **Importa ZIP** nella schermata dei progetti.

## Cartelle
- `Editor Album/` programma (schermata progetti + editor)
- `motore/` script di impaginazione e Photoshop (copia della skill di impaginazione)
- `skill/impaginatore-stefano/` istruzioni per Claude
