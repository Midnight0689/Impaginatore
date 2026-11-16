"""Lingua del sistema, per sceglierla al primo avvio (T-206).

Restituisce un codice come «it_IT», «en-GB» o «de», oppure None se il sistema non lo dice. Dove guardare:
    macOS   le lingue preferite dell'utente (defaults read -g AppleLanguages), poi le variabili d'ambiente
    Windows la lingua dell'interfaccia (GetUserDefaultUILanguage), poi le variabili d'ambiente
    Linux   LANGUAGE, LC_ALL, LC_MESSAGES, LANG (la prima non vuota, «C» e «POSIX» non contano)
"""
import ctypes
import locale
import os
import subprocess  # nosec B404  # un solo programma di sistema, argomenti in lista, senza shell

from . import sistema
from .processi import ambiente_figli

VARIABILI = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")


def _da_ambiente():
    for k in VARIABILI:
        v = (os.environ.get(k) or "").split(":")[0].split(".")[0].strip()
        if v and v not in ("C", "POSIX"): return v
    return None


def _mac():
    try:
        r = subprocess.run(["defaults", "read", "-g", "AppleLanguages"], capture_output=True, text=True, timeout=5, env=ambiente_figli())  # nosec B603, B607  # programma di sistema cercato nel PATH dell'utente; argomenti in lista, senza shell
    except (OSError, subprocess.SubprocessError): return None
    for riga in r.stdout.splitlines():                       # (\n    "it-IT",\n    "en-US"\n)
        v = riga.strip().strip(",").strip('"')
        if v and v not in "()": return v
    return None


def _windows():
    try: n = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError): return None
    return locale.windows_locale.get(n)


def del_sistema():
    """codice della lingua dell'utente secondo il sistema, o None"""
    s = sistema()
    if s == "mac": return _mac() or _da_ambiente()
    if s == "windows": return _windows() or _da_ambiente()
    return _da_ambiente()
