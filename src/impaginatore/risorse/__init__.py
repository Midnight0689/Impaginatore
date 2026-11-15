"""File che il programma usa così come sono: le pagine dell'interfaccia (home.html, index.html) e la tabella della vibranza
misurata in Photoshop (vib_lut.npz). Fanno parte del pacchetto installato."""
import os

CARTELLA = os.path.dirname(os.path.abspath(__file__))


def percorso(nome):
    return os.path.join(CARTELLA, nome)


def leggi(nome):
    with open(percorso(nome), "rb") as f: return f.read()
