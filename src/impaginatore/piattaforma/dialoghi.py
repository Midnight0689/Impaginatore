"""Finestre di sistema per scegliere cartelle, foto e file ZIP.

Il programma chiama sempre le funzioni di questo modulo (scegli_cartella, scegli_zip, scegli_percorsi); dietro c'è
un'implementazione per sistema:
    macOS            osascript (finestre del Finder)
    Windows, Linux   tkinter (in un processo a parte: le richieste arrivano dai thread del server HTTP)
    Linux senza tk   zenity o kdialog
    nessuna          annulla sempre (server senza schermo, test)
Punto di aggancio: imposta(implementazione) sostituisce le finestre per tutto il processo (es. quelle di pywebview nella
finestra desktop). La variabile IMPAGINATORE_DIALOGHI sceglie l'implementazione per nome (mac, tk, zenity, kdialog,
nessuno): vale anche per i processi dell'editor.
Ogni funzione restituisce "" (o []) se l'utente annulla.
"""
import importlib.util
import os
import shutil
import subprocess
import sys

from . import sistema

TIPI_FOTO = ("*.jpg", "*.jpeg", "*.JPG", "*.JPEG")


def senza_barra(p):
    """toglie la barra finale da una cartella, ma non dalla radice ("/", "C:\\")"""
    q = p.rstrip("/\\")
    return q if q and not q.endswith(":") else p


class Dialoghi:
    """interfaccia: le sottoclassi implementano _scegli(tipo, messaggio) -> [percorsi]; tipo = "cartella", "zip" o "foto" (più file)"""
    nome = "base"

    def _scegli(self, tipo, messaggio):
        raise NotImplementedError

    def scegli_cartella(self, messaggio="Scegli la cartella"):
        return senza_barra((self._scegli("cartella", messaggio) or [""])[0])

    def scegli_zip(self, messaggio="Scegli il file ZIP del progetto"):
        return (self._scegli("zip", messaggio) or [""])[0]

    def scegli_percorsi(self, cartella=False, messaggio=None):
        """una cartella (cartella=True) o una o più foto JPEG: elenco di percorsi"""
        if cartella: return self._scegli("cartella", messaggio or "Scegli la cartella")
        return self._scegli("foto", messaggio or "Scegli le foto")


class Nessuno(Dialoghi):
    nome = "nessuno"

    def _scegli(self, tipo, messaggio):
        return []


class Mac(Dialoghi):
    """finestre del Finder via osascript (come nelle versioni 1.x: stessi testi, stessi risultati)"""
    nome = "mac"

    def _scegli(self, tipo, messaggio):
        if tipo == "cartella": sc = f'POSIX path of (choose folder with prompt "{messaggio}")'
        elif tipo == "zip": sc = f'POSIX path of (choose file of type {{"public.zip-archive"}} with prompt "{messaggio}")'
        else: sc = (f'set fs to choose file with prompt "{messaggio}" of type {{"public.jpeg"}} with multiple selections allowed\nset out to ""\n'
                    'repeat with f in fs\nset out to out & POSIX path of f & linefeed\nend repeat\nreturn out')
        r = subprocess.run(["osascript", "-e", sc], capture_output=True, text=True, encoding="utf-8")
        return [x for x in r.stdout.split("\n") if x.strip()] if r.returncode == 0 else []        # la cartella arriva con la barra finale di AppleScript, come prima


_TK = r'''
import sys, tkinter as tk
from tkinter import filedialog
r = tk.Tk(); r.withdraw()
try: r.attributes("-topmost", True)
except Exception: pass
k, msg = sys.argv[1], sys.argv[2]
if k == "cartella": out = [filedialog.askdirectory(title=msg)]
elif k == "zip": out = [filedialog.askopenfilename(title=msg, filetypes=[("ZIP", "*.zip")])]
else: out = list(filedialog.askopenfilenames(title=msg, filetypes=[("JPEG", "*.jpg *.jpeg *.JPG *.JPEG")]))
sys.stdout.write("\n".join(x for x in out if x))
'''


class Tk(Dialoghi):
    """tkinter in un processo figlio (tkinter vuole il thread principale; il server risponde da altri thread)"""
    nome = "tk"

    def _scegli(self, tipo, messaggio):
        r = subprocess.run([sys.executable, "-c", _TK, tipo, messaggio], capture_output=True, text=True, encoding="utf-8")
        return [os.path.normpath(x) for x in r.stdout.split("\n") if x.strip()] if r.returncode == 0 else []


class Zenity(Dialoghi):
    nome = "zenity"

    def _scegli(self, tipo, messaggio):
        cmd = ["zenity", "--file-selection", "--title", messaggio]
        if tipo == "cartella": cmd.append("--directory")
        elif tipo == "zip": cmd += ["--file-filter", "ZIP | *.zip"]
        else: cmd += ["--multiple", "--separator", "\n", "--file-filter", "JPEG | " + " ".join(TIPI_FOTO)]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return [x for x in r.stdout.split("\n") if x.strip()] if r.returncode == 0 else []


class Kdialog(Dialoghi):
    nome = "kdialog"

    def _scegli(self, tipo, messaggio):
        base = os.path.expanduser("~")
        if tipo == "cartella": cmd = ["kdialog", "--title", messaggio, "--getexistingdirectory", base]
        elif tipo == "zip": cmd = ["kdialog", "--title", messaggio, "--getopenfilename", base, "*.zip"]
        else: cmd = ["kdialog", "--title", messaggio, "--getopenfilenames", base, " ".join(TIPI_FOTO), "--separate-output"]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return [x for x in r.stdout.split("\n") if x.strip()] if r.returncode == 0 else []


PER_NOME = {c.nome: c for c in (Nessuno, Mac, Tk, Zenity, Kdialog)}
_ATTUALE = [None]


def _tk_disponibile():
    if importlib.util.find_spec("tkinter") is None: return False
    return sistema() != "linux" or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def predefiniti():
    """l'implementazione giusta per questo sistema (o quella chiesta con IMPAGINATORE_DIALOGHI)"""
    n = os.environ.get("IMPAGINATORE_DIALOGHI", "").strip().lower()
    if n in PER_NOME: return PER_NOME[n]()
    s = sistema()
    if s == "mac": return Mac()
    if _tk_disponibile(): return Tk()
    if s == "linux":
        if shutil.which("zenity"): return Zenity()
        if shutil.which("kdialog"): return Kdialog()
    return Nessuno()


def imposta(implementazione):
    """sostituisce le finestre di scelta per tutto il processo (None = torna a quelle del sistema)"""
    _ATTUALE[0] = implementazione


def attuali():
    return _ATTUALE[0] or predefiniti()


def scegli_cartella(messaggio="Scegli la cartella"): return attuali().scegli_cartella(messaggio)
def scegli_zip(messaggio="Scegli il file ZIP del progetto"): return attuali().scegli_zip(messaggio)
def scegli_percorsi(cartella=False, messaggio=None): return attuali().scegli_percorsi(cartella, messaggio)
