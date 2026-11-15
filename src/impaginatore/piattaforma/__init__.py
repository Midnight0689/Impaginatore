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


def sistema():
    """"mac", "windows" o "linux" (ogni altro Unix conta come linux)"""
    p = sys.platform
    if p == "darwin": return "mac"
    if p.startswith("win") or p.startswith("cygwin"): return "windows"
    return "linux"


def e_mac(): return sistema() == "mac"
def e_windows(): return sistema() == "windows"
def e_linux(): return sistema() == "linux"
