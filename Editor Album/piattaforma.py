"""Tutto ciò che cambia tra Mac e Windows, in un solo posto: finestre per scegliere file e cartelle, «mostra nel Finder / Esplora risorse»,
cestino, percorsi dell'ambiente Python, cartelle dei font, riavvio dopo un aggiornamento. Il resto del programma non sa su che sistema gira."""
import os, subprocess, sys

MAC = sys.platform == "darwin"
WIN = os.name == "nt"
TOOLS = os.path.join(os.path.expanduser("~"), ".album-tools")


def venv_python():
    return os.path.join(TOOLS, "venv", "Scripts", "python.exe") if WIN else os.path.join(TOOLS, "venv", "bin", "python")


def font_dirs():
    if WIN: return [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
    return ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]


def font_ripiego():
    return (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf") if WIN else "/System/Library/Fonts/Helvetica.ttc"), 0


def env_utf8(env=None):
    """su Windows i file di testo si aprirebbero in cp1252: i programmi figli partono sempre in UTF-8"""
    e = dict(os.environ if env is None else env); e["PYTHONUTF8"] = "1"; return e


_TK = r'''
import sys, tkinter as tk
from tkinter import filedialog
r = tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
k, msg = sys.argv[1], sys.argv[2]
if k == "folder": out = [filedialog.askdirectory(title=msg)]
elif k == "zip": out = [filedialog.askopenfilename(title=msg, filetypes=[("ZIP", "*.zip")])]
else: out = list(filedialog.askopenfilenames(title=msg, filetypes=[("JPEG", "*.jpg *.jpeg *.JPG *.JPEG")]))
print("\n".join(x for x in out if x))
'''


def _tk(kind, msg):
    r = subprocess.run([sys.executable, "-c", _TK, kind, msg], capture_output=True, text=True, encoding="utf-8")
    return [os.path.normpath(x) for x in r.stdout.split("\n") if x.strip()] if r.returncode == 0 else []


def scegli_cartella(msg="Scegli la cartella"):
    if WIN: return (_tk("folder", msg) or [""])[0]
    r = subprocess.run(["osascript", "-e", f'POSIX path of (choose folder with prompt "{msg}")'], capture_output=True, text=True)
    return r.stdout.strip().rstrip("/") if r.returncode == 0 else ""


def scegli_zip(msg="Scegli il file ZIP del progetto"):
    if WIN: return (_tk("zip", msg) or [""])[0]
    r = subprocess.run(["osascript", "-e", f'POSIX path of (choose file of type {{"public.zip-archive"}} with prompt "{msg}")'], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def scegli_foto(cartella=False):
    """elenco di percorsi: una cartella (cartella=True) o una o più foto JPEG; vuoto se annulli"""
    if WIN: return _tk("folder" if cartella else "photos", "Scegli la cartella" if cartella else "Scegli le foto")
    if cartella: sc = 'POSIX path of (choose folder with prompt "Scegli la cartella")'
    else: sc = ('set fs to choose file with prompt "Scegli le foto" of type {"public.jpeg"} with multiple selections allowed\nset out to ""\n'
                'repeat with f in fs\nset out to out & POSIX path of f & linefeed\nend repeat\nreturn out')
    r = subprocess.run(["osascript", "-e", sc], capture_output=True, text=True)
    return [x for x in r.stdout.split("\n") if x.strip()] if r.returncode == 0 else []


def mostra_file(path):
    """apre la cartella del file e lo seleziona (Finder / Esplora risorse)"""
    if WIN: subprocess.run(["explorer", "/select,", os.path.normpath(path)])
    elif MAC: subprocess.run(["open", "-R", path])
    else: subprocess.run(["xdg-open", os.path.dirname(path)])


def cestina(path):
    """mette il file o la cartella nel Cestino (si può recuperare); solleva un errore se non riesce"""
    if WIN:
        ps = ("Add-Type -AssemblyName Microsoft.VisualBasic; $p = $args[0]; if (Test-Path -LiteralPath $p -PathType Container) "
              "{ [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($p, 'OnlyErrorDialogs', 'SendToRecycleBin') } else "
              "{ [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p, 'OnlyErrorDialogs', 'SendToRecycleBin') }")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps, os.path.normpath(path)], check=True, capture_output=True)
    else:
        subprocess.run(["osascript", "-e", f'tell application "Finder" to delete POSIX file "{path}"'], check=True, capture_output=True)


def prepara_ambiente(base, timeout=900):
    """ricrea/aggiorna l'ambiente Python (setup.sh sul Mac, setup.bat su Windows); restituisce il processo finito o None se manca lo script"""
    s = os.path.join(base, "motore", "scripts", "setup.bat" if WIN else "setup.sh")
    if not os.path.exists(s): return None
    return subprocess.run(["cmd", "/c", s] if WIN else ["zsh", s], capture_output=True, text=True, timeout=timeout)


def riapri_programma(base):
    """avvia di nuovo il programma tra un secondo e mezzo, fuori da questo processo (che sta per chiudersi)"""
    if WIN:
        bat = os.path.join(base, "Avvia Impaginatore.bat")
        subprocess.Popen(["cmd", "/c", f'ping -n 3 127.0.0.1 >nul & start "" "{bat}"'], creationflags=0x00000008 | 0x00000200, close_fds=True)
    else:
        subprocess.Popen(["/bin/sh", "-c", f'sleep 1.5; open "{os.path.join(base, "Impaginatore.app")}"'], start_new_session=True)
