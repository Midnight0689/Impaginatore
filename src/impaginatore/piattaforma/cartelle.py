"""Cartelle del programma e dell'utente, per sistema.

Dati dell'utente (modelli salvati, valgono per tutti gli album):
    macOS   ~/Library/Application Support/Impaginatore
    Windows %APPDATA%\\Impaginatore
    Linux   $XDG_DATA_HOME/impaginatore  (di solito ~/.local/share/impaginatore)
Cache (si può cancellare, si rifà da sola): ~/Library/Caches/Impaginatore, %LOCALAPPDATA%\\Impaginatore\\Cache, $XDG_CACHE_HOME/impaginatore.
Le versioni fino alla 1.5 tenevano tutto in ~/.album-tools: file_dati() copia da lì il file che manca (senza toccare
l'originale), così i modelli già salvati si ritrovano. Le variabili IMPAGINATORE_DATI e IMPAGINATORE_CACHE cambiano le
cartelle (le usano i test).
"""
import os
import shutil
import string

from . import sistema

APP = "Impaginatore"


def home():
    return os.path.expanduser("~")


def legacy():
    """cartella degli strumenti delle versioni 1.x (ambiente Python, modelli, cache dei font)"""
    return os.path.join(home(), ".album-tools")


def _env_dir(nome, dflt):
    v = os.environ.get(nome)
    return os.path.abspath(os.path.expanduser(v)) if v else dflt


def dati_utente():
    """cartella dei dati dell'utente (non la crea)"""
    if os.environ.get("IMPAGINATORE_DATI"): return _env_dir("IMPAGINATORE_DATI", "")
    s = sistema()
    if s == "mac": return os.path.join(home(), "Library", "Application Support", APP)
    if s == "windows": return os.path.join(os.environ.get("APPDATA") or os.path.join(home(), "AppData", "Roaming"), APP)
    return os.path.join(_env_dir("XDG_DATA_HOME", os.path.join(home(), ".local", "share")), APP.lower())


def cache():
    """cartella della cache (non la crea)"""
    if os.environ.get("IMPAGINATORE_CACHE"): return _env_dir("IMPAGINATORE_CACHE", "")
    s = sistema()
    if s == "mac": return os.path.join(home(), "Library", "Caches", APP)
    if s == "windows": return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.join(home(), "AppData", "Local"), APP, "Cache")
    return os.path.join(_env_dir("XDG_CACHE_HOME", os.path.join(home(), ".cache")), APP.lower())


def file_dati(nome):
    """percorso di un file dei dati dell'utente; se non c'è ancora ma c'è nella cartella delle versioni 1.x, lo copia (migrazione non distruttiva)"""
    p = os.path.join(dati_utente(), nome)
    vecchio = os.path.join(legacy(), nome)
    if not os.path.exists(p) and os.path.isfile(vecchio):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True); shutil.copy2(vecchio, p)
        except OSError:
            return vecchio                                   # cartella nuova non scrivibile: si continua a usare quella vecchia
    return p


def _xdg_utente(chiave, dflt):
    """cartella speciale dell'utente su Linux (Scrivania, Documenti...) da ~/.config/user-dirs.dirs, con il nome nella lingua del sistema"""
    f = os.path.join(_env_dir("XDG_CONFIG_HOME", os.path.join(home(), ".config")), "user-dirs.dirs")
    try:
        with open(f, encoding="utf-8") as fh:
            for riga in fh:
                riga = riga.strip()
                if riga.startswith(chiave + "="):
                    v = riga.split("=", 1)[1].strip().strip('"').replace("$HOME", home())
                    if v and v != home(): return v
    except OSError:
        pass
    return os.path.join(home(), dflt)


def documenti():
    s = sistema()
    if s == "windows":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value: return buf.value     # CSIDL_PERSONAL: segue OneDrive e le cartelle spostate
        except Exception:
            pass
        return os.path.join(home(), "Documents")
    if s == "linux": return _xdg_utente("XDG_DOCUMENTS_DIR", "Documents")
    return os.path.join(home(), "Documents")


def cartelle_utente():
    """[(etichetta, percorso)] dei posti dell'utente per il selettore di foto del programma (solo quelli che esistono)"""
    if sistema() == "linux":
        cand = [("Scrivania", _xdg_utente("XDG_DESKTOP_DIR", "Desktop")), ("Documenti", documenti()), ("Immagini", _xdg_utente("XDG_PICTURES_DIR", "Pictures")),
                ("Download", _xdg_utente("XDG_DOWNLOAD_DIR", "Downloads")), ("Home", home())]
    else:
        h = home()
        cand = [("Scrivania", os.path.join(h, "Desktop")), ("Documenti", documenti()), ("Immagini", os.path.join(h, "Pictures")), ("Download", os.path.join(h, "Downloads")), ("Home", h)]
    return [(n, p) for n, p in cand if os.path.isdir(p)]


def scrivania():
    if sistema() == "linux": return _xdg_utente("XDG_DESKTOP_DIR", "Desktop")
    return os.path.join(home(), "Desktop")


def _sottocartelle(base):
    try: return [(v, os.path.join(base, v)) for v in sorted(os.listdir(base)) if not v.startswith(".") and os.path.isdir(os.path.join(base, v)) and not os.path.islink(os.path.join(base, v))]
    except OSError: return []


def volumi():
    """[(nome, percorso)] dei dischi esterni e delle altre unità, per il selettore di foto"""
    s = sistema()
    if s == "mac": return _sottocartelle("/Volumes")
    if s == "windows":
        return [(f"{d}:", f"{d}:\\") for d in string.ascii_uppercase if d not in "AB" and os.path.isdir(f"{d}:\\")]
    utente = os.path.basename(home())
    return _sottocartelle(os.path.join("/media", utente)) + _sottocartelle(os.path.join("/run", "media", utente)) + _sottocartelle("/mnt")


def radice_checkout():
    """cartella del repository git che contiene il pacchetto (si gira da un checkout: aggiornamenti con git, progetti in <radice>/Progetti), altrimenti None"""
    pacchetto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))         # .../src/impaginatore
    radice = os.path.dirname(os.path.dirname(pacchetto))
    if os.path.basename(os.path.dirname(pacchetto)) == "src" and os.path.exists(os.path.join(radice, ".git")) and os.path.isfile(os.path.join(radice, "pyproject.toml")): return radice
    return None


def progetti_predefinita():
    """cartella dove nascono i nuovi progetti: IMPAGINATORE_PROGETTI, poi <checkout>/Progetti (come nelle versioni 1.x), poi Documenti/Impaginatore/Progetti"""
    v = os.environ.get("IMPAGINATORE_PROGETTI")
    if v: return os.path.abspath(os.path.expanduser(v))
    r = radice_checkout()
    if r: return os.path.join(r, "Progetti")
    return os.path.join(documenti(), APP, "Progetti")
