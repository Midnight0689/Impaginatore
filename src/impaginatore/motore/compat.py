"""Nomi delle versioni 1.x: «album», «album_libere» e «testo» come moduli di primo livello.

Ogni spec.py salvato dall'editor (formato 1.x, che resta quello di oggi) comincia con `from album import *` e, se ha
cornici libere, `from album_libere import *`; genera_psd_angolo.py aggiunge a genera_psd.py chiamate come
`__import__("album_libere")` e `__import__("testo")`. Nel pacchetto quei moduli si chiamano impaginatore.motore.album ecc.:
installa() aggiunge a sys.meta_path un cercatore che, solo per quei tre nomi, restituisce il modulo del pacchetto (lo
stesso oggetto: lo stato del progetto caricato è uno solo). Le copie di album_libere.py e testo.py che l'editor mette nella
cartella dei progetti non vengono più usate dal programma (restano per chi apre il progetto con gli script 1.x).
"""
import importlib
import importlib.abc
import importlib.util
import sys

NOMI = {"album": "impaginatore.motore.album", "album_libere": "impaginatore.motore.album_libere", "testo": "impaginatore.motore.testo"}


class _Alias(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, nome, path=None, target=None):
        if path is None and nome in NOMI: return importlib.util.spec_from_loader(nome, self)
        return None

    def create_module(self, spec):
        m = importlib.import_module(NOMI[spec.name])
        self.vere[spec.name] = m.__spec__
        return m

    def exec_module(self, modulo):
        # l'import ha appena sovrascritto __spec__ con quello del nome breve: rimetto quello vero (gli import relativi
        # interni al modulo lo confrontano con __package__)
        modulo.__spec__ = self.vere[modulo.__spec__.name]

    def __init__(self):
        self.vere = {}


_CERCATORE = _Alias()


def installa():
    """rende importabili i nomi 1.x (si può chiamare più volte)"""
    if not any(isinstance(f, _Alias) for f in sys.meta_path): sys.meta_path.insert(0, _CERCATORE)


def disinstalla():
    sys.meta_path[:] = [f for f in sys.meta_path if not isinstance(f, _Alias)]
    for n in NOMI:
        if sys.modules.get(n) is sys.modules.get(NOMI[n]): sys.modules.pop(n, None)
