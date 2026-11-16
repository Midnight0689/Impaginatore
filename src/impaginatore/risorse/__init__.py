"""File che il programma usa così come sono: le pagine dell'interfaccia (home.html, index.html), i file statici che le
pagine caricano (statici/: token della marca, caratteri con le loro licenze), la tabella dei testi in italiano e in
inglese (testi/<lingua>/<area>.json, vedi lingua.py) e la tabella della vibranza misurata in Photoshop (vib_lut.npz).
Fanno parte del pacchetto installato."""
import json
import os

CARTELLA = os.path.dirname(os.path.abspath(__file__))
TIPI_STATICI = {".css": "text/css; charset=utf-8", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
PREFISSI_TESTI = {"home.html": ("comune.", "home.", "statistiche."), "index.html": ("comune.", "editor.")}      # quali testi riceve ogni pagina (statistiche d'uso, T-204: solo la schermata Album)


def percorso(nome):
    return os.path.join(CARTELLA, nome)


def leggi(nome):
    with open(percorso(nome), "rb") as f: return f.read()


def statici():
    """file che le pagine possono chiedere a /risorse/<nome>: {nome: tipo}. Solo quelli della cartella statici con
    un'estensione nota: nessun altro file del pacchetto si raggiunge da lì"""
    d = percorso("statici")
    return {n: TIPI_STATICI[os.path.splitext(n)[1]] for n in sorted(os.listdir(d)) if os.path.splitext(n)[1] in TIPI_STATICI and os.path.isfile(os.path.join(d, n))}


def aree(lingua="it"):
    """nomi dei file della tabella di una lingua (senza .json): comune, home, editor, server…"""
    return sorted(n[:-5] for n in os.listdir(percorso(os.path.join("testi", lingua))) if n.endswith(".json"))


def testi_area(lingua, area):
    """{chiave: testo} di un file della tabella"""
    return json.loads(leggi(os.path.join("testi", lingua, f"{area}.json")).decode("utf-8"))


def testi(lingua="it"):
    """tabella dei testi di una lingua: {chiave: testo}, tutti i file insieme (lingua.py la legge una volta)"""
    d = {}
    for a in aree(lingua): d.update(testi_area(lingua, a))
    return d


def testi_pagina(pagina, lingua="it"):
    """i testi di una pagina in JSON da mettere dentro il suo script: nessun «<» (niente «</script>»), né i separatori
    di riga che JavaScript non accetta dentro le stringhe"""
    p = PREFISSI_TESTI.get(pagina, ("comune.",))
    d = {k: v for k, v in testi(lingua).items() if k.startswith(p)}
    return json.dumps(d, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
