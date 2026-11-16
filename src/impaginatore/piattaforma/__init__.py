"""Tutto ciò che cambia tra macOS, Windows e Linux, in un solo posto.

Il resto del programma non sa su che sistema gira: chiede a questi moduli.
- cartelle: dati dell'utente, cache, documenti, cartella dei progetti, posti e dischi per il selettore di foto
- dialoghi: finestre per scegliere file e cartelle (con un punto di aggancio per sostituirle, es. pywebview)
- azioni: mostra nel Finder / Esplora risorse / file manager, cestino
- font: cartelle dei font, font di ripiego, profilo sRGB
- photoshop: dove sta Photoshop e come gli si fanno eseguire gli script
- processi: ambiente dei processi figli, riavvio, distacco dal terminale

Il sistema si legge a ogni chiamata (sistema()), non una volta all'import: i test lo simulano cambiando sys.platform.
"""
import sys
import time

ATTESA_FILE_APERTO = 2.0          # secondi: quanto si riprova a sostituire o togliere un file che un altro processo sta leggendo


def sistema():
    """"mac", "windows" o "linux" (ogni altro Unix conta come linux)"""
    p = sys.platform
    if p == "darwin": return "mac"
    if p.startswith("win") or p.startswith("cygwin"): return "windows"
    return "linux"


def e_mac(): return sistema() == "mac"
def e_windows(): return sistema() == "windows"
def e_linux(): return sistema() == "linux"


def anche_se_aperto(azione, *argomenti):
    """azione(*argomenti), cioè os.replace o os.remove di un file che altri processi del programma leggono. Su Windows un
    file aperto da un altro processo non si sostituisce né si toglie (PermissionError) finché quello non lo chiude: la
    schermata dei progetti rilegge di continuo progetto.json, album.json e i file di sessione, e l'editor li riscrive (al
    salvataggio, prima di ripartire, appena ripartito). Lì si riprova per ATTESA_FILE_APERTO secondi. Su macOS e Linux
    un file aperto si sostituisce: un PermissionError è un permesso che manca davvero e arriva subito"""
    fine = time.monotonic() + ATTESA_FILE_APERTO
    while True:
        try: return azione(*argomenti)
        except PermissionError:
            if sistema() != "windows" or time.monotonic() >= fine: raise
            time.sleep(0.01)
