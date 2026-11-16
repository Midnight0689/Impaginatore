"""File che il programma usa così come sono: le pagine dell'interfaccia (home.html, index.html), i file statici che le
pagine caricano (statici/: token della marca, caratteri con le loro licenze), la tabella dei testi dell'interfaccia
(testi/it.json) e la tabella della vibranza misurata in Photoshop (vib_lut.npz). Fanno parte del pacchetto installato."""
import json
import os

CARTELLA = os.path.dirname(os.path.abspath(__file__))
TIPI_STATICI = {".css": "text/css; charset=utf-8", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
PREFISSI_TESTI = {"home.html": ("comune.", "home."), "index.html": ("comune.", "editor.")}      # quali testi riceve ogni pagina


def percorso(nome):
    return os.path.join(CARTELLA, nome)


def leggi(nome):
    with open(percorso(nome), "rb") as f: return f.read()


def statici():
    """file che le pagine possono chiedere a /risorse/<nome>: {nome: tipo}. Solo quelli della cartella statici con
    un'estensione nota: nessun altro file del pacchetto si raggiunge da lì"""
    d = percorso("statici")
    return {n: TIPI_STATICI[os.path.splitext(n)[1]] for n in sorted(os.listdir(d)) if os.path.splitext(n)[1] in TIPI_STATICI and os.path.isfile(os.path.join(d, n))}


def testi(lingua="it"):
    """tabella dei testi dell'interfaccia: {chiave: testo} (T-206 aggiungerà le altre lingue)"""
    return json.loads(leggi(os.path.join("testi", f"{lingua}.json")).decode("utf-8"))


def testi_pagina(pagina, lingua="it"):
    """i testi di una pagina in JSON da mettere dentro il suo script: nessun «<» (niente «</script>»), né i separatori
    di riga che JavaScript non accetta dentro le stringhe"""
    p = PREFISSI_TESTI.get(pagina, ("comune.",))
    d = {k: v for k, v in testi(lingua).items() if k.startswith(p)}
    return json.dumps(d, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
