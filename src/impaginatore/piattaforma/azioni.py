"""Azioni sui file che passano dal sistema: mostrare un file nel suo gestore (Finder, Esplora risorse, file manager) e
metterlo nel Cestino.

    macOS    open -R / Finder (osascript)
    Windows  explorer /select / Cestino via PowerShell
    Linux    FileManager1 su D-Bus (seleziona il file) o xdg-open sulla cartella / gio trash, oppure il cestino
             freedesktop scritto a mano (~/.local/share/Trash)

Regola (SEC-004): un percorso non entra mai nel testo di uno script (AppleScript, PowerShell): arriva come argomento
(«on run argv») o come variabile d'ambiente, e sempre assoluto (non può sembrare un'opzione come «-a»).
"""
import datetime
import os
import shutil
import subprocess
import urllib.parse

from . import cartelle, sistema
from .processi import ambiente_figli


def mostra(path):
    """apre la cartella del file e, dove si può, lo seleziona"""
    s = sistema(); path = os.path.abspath(path)
    if s == "mac": subprocess.run(["open", "-R", path], env=ambiente_figli()); return
    if s == "windows": subprocess.run(["explorer", "/select,", os.path.normpath(path)], env=ambiente_figli()); return
    uri = "file://" + urllib.parse.quote(os.path.abspath(path))
    if shutil.which("gdbus"):
        r = subprocess.run(["gdbus", "call", "--session", "--dest", "org.freedesktop.FileManager1", "--object-path", "/org/freedesktop/FileManager1",
                            "--method", "org.freedesktop.FileManager1.ShowItems", f"['{uri}']", ""], capture_output=True, timeout=10, env=ambiente_figli())
        if r.returncode == 0: return
    if shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", path if os.path.isdir(path) else os.path.dirname(path) or "."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, env=ambiente_figli())
        return
    raise OSError("non trovo un gestore di file da aprire (manca xdg-open)")


def cestina(path):
    """mette il file o la cartella nel Cestino (si può recuperare); solleva un errore se non riesce"""
    s = sistema()
    if s == "mac":
        subprocess.run(["osascript", "-e", "on run argv", "-e", 'tell application "Finder" to delete (POSIX file (item 1 of argv) as alias)', "-e", "end run",
                        os.path.abspath(path)], check=True, capture_output=True, env=ambiente_figli()); return
    if s == "windows":                                   # con -Command gli argomenti dopo lo script diventerebbero testo dello script: il percorso passa dall'ambiente
        ps = ("Add-Type -AssemblyName Microsoft.VisualBasic; $p = $env:IMPAGINATORE_PERCORSO; if (Test-Path -LiteralPath $p -PathType Container) "
              "{ [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($p, 'OnlyErrorDialogs', 'SendToRecycleBin') } else "
              "{ [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p, 'OnlyErrorDialogs', 'SendToRecycleBin') }")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], check=True, capture_output=True,
                       env=ambiente_figli(dict(os.environ, IMPAGINATORE_PERCORSO=os.path.normpath(os.path.abspath(path))))); return
    if shutil.which("gio") and subprocess.run(["gio", "trash", "--", os.path.abspath(path)], capture_output=True, env=ambiente_figli()).returncode == 0: return
    cestina_freedesktop(path)


def cestina_freedesktop(path, cestino=None):
    """cestino della specifica freedesktop.org (quello di GNOME, KDE, XFCE...), nella cartella dell'utente: il file si recupera dal file manager"""
    path = os.path.abspath(path)
    if not os.path.lexists(path): raise FileNotFoundError(path)
    base = cestino or os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(cartelle.home(), ".local", "share"), "Trash")
    files, info = os.path.join(base, "files"), os.path.join(base, "info")
    os.makedirs(files, exist_ok=True); os.makedirs(info, exist_ok=True)
    nome = os.path.basename(path.rstrip(os.sep)); k = 1; dest = nome
    while os.path.lexists(os.path.join(files, dest)) or os.path.exists(os.path.join(info, dest + ".trashinfo")):
        k += 1; dest = f"{nome}.{k}"
    ti = os.path.join(info, dest + ".trashinfo")
    with open(ti, "x", encoding="utf-8") as f:
        f.write(f"[Trash Info]\nPath={urllib.parse.quote(path)}\nDeletionDate={datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
    try: os.rename(path, os.path.join(files, dest))          # solo sullo stesso disco: altrimenti meglio fermarsi che copiare gigabyte di foto
    except OSError:
        os.remove(ti); raise
