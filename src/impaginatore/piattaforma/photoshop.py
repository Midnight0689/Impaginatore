"""Dove sta Photoshop e come gli si fa eseguire uno script ExtendScript (.jsx).

    macOS    /Applications/Adobe Photoshop 20xx, script via osascript («do javascript»)
    Windows  Programmi\\Adobe\\Adobe Photoshop 20xx\\Photoshop.exe, script via COM (cscript + VBScript, presenti in Windows)
    Linux    Photoshop non esiste: l'export PSD non è disponibile e motivo_assente() lo spiega

Le regole imparate sul Mac (script ASCII, $.evalFile invece di «POSIX file») sono in motore/photoshop.py.
Nessun dato (percorso, codice) entra nel testo di uno script AppleScript: arriva come argomento («on run argv»); il nome
dell'applicazione (dal disco) e il percorso dentro il codice JavaScript sono quotati (quota_applescript, json.dumps) (SEC-004).
"""
import glob
import json
import os
import subprocess  # nosec B404  # processi lanciati solo con argomenti in lista, mai con la shell
import tempfile

from .. import lingua
from . import sistema
from .processi import ambiente_figli

CARTELLA_APPLICAZIONI = "/Applications"          # macOS (i test la cambiano)


def _programmi():
    out = []
    for k in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        v = os.environ.get(k)
        if v and v not in out: out.append(v)
    return out or [r"C:\Program Files"]


def trova():
    """{"nome": "Adobe Photoshop 2026", "percorso": ...} dell'ultima versione installata, o None"""
    s = sistema()
    if s == "mac":
        A = CARTELLA_APPLICAZIONI
        for p in sorted(glob.glob(os.path.join(A, "Adobe Photoshop 20*", "Adobe Photoshop 20*.app")), reverse=True):
            return dict(nome=os.path.basename(p)[:-4], percorso=p)
        for p in sorted(glob.glob(os.path.join(A, "Adobe Photoshop*.app")), reverse=True):
            if "Beta" not in p: return dict(nome=os.path.basename(p)[:-4], percorso=p)
        return None
    if s == "windows":
        trovati = [p for d in _programmi() for p in glob.glob(os.path.join(d, "Adobe", "Adobe Photoshop*", "Photoshop.exe")) if "Beta" not in p]
        trovati.sort(key=lambda p: os.path.basename(os.path.dirname(p)), reverse=True)
        return dict(nome=os.path.basename(os.path.dirname(trovati[0])), percorso=trovati[0]) if trovati else None
    return None


def disponibile(): return trova() is not None


def motivo_assente():
    """frase per l'utente quando i PSD non si possono fare (nella lingua in uso)"""
    s = sistema()
    return lingua.t("motore.photoshop_mac" if s == "mac" else "motore.photoshop_windows" if s == "windows" else "motore.photoshop_linux")


def quota_applescript(s):
    """stringa AppleScript tra virgolette: barre rovesciate e virgolette protette"""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _do_javascript(ps, codice, timeout):
    """comando osascript che fa eseguire codice a Photoshop: il codice è il primo argomento dello script, non parte del testo"""
    return ["osascript", "-e", "on run argv", "-e", f"with timeout of {int(timeout)} seconds",
            "-e", f"tell application {quota_applescript(ps['nome'])} to do javascript (item 1 of argv)", "-e", "end timeout", "-e", "end run", codice]


_VBS = 'Dim a, r\r\nSet a = CreateObject("Photoshop.Application")\r\nr = a.DoJavaScriptFile(WScript.Arguments(0))\r\nWScript.StdOut.Write r\r\n'


def esegui_jsx(path, timeout=3600):
    """esegue lo script .jsx in Photoshop e restituisce quello che ha risposto (testo dell'ultimo valore, o l'errore)"""
    ps = trova()
    if ps is None: raise RuntimeError(motivo_assente())
    if sistema() == "mac":
        r = subprocess.run(_do_javascript(ps, f"$.evalFile(new File({json.dumps(os.path.abspath(path))}))", timeout), capture_output=True, text=True, encoding="utf-8", env=ambiente_figli())  # nosec B603  # osascript con il codice come argomento (SEC-004); argomenti in lista, senza shell: nessun dato passa da un interprete di comandi
        return (r.stdout + r.stderr).strip()
    with tempfile.TemporaryDirectory(prefix="impaginatore_ps_") as d:
        vbs = os.path.join(d, "esegui.vbs")
        with open(vbs, "w", encoding="ascii", newline="") as f: f.write(_VBS)
        r = subprocess.run(["cscript", "//nologo", vbs, os.path.abspath(path)], capture_output=True, timeout=timeout, env=ambiente_figli())  # nosec B603, B607  # programma di sistema cercato nel PATH dell'utente (chi lo cambia controlla già il suo account); argomenti in lista, senza shell
        return (r.stdout + r.stderr).decode("utf-8", "replace").strip()


def esegui_js(codice):
    """esegue poche righe di ExtendScript (es. l'elenco dei documenti aperti)"""
    ps = trova()
    if ps is None: raise RuntimeError(motivo_assente())
    if sistema() == "mac":
        r = subprocess.run(_do_javascript(ps, codice, 120), capture_output=True, text=True, encoding="utf-8", env=ambiente_figli())  # nosec B603  # osascript con il codice come argomento (SEC-004); argomenti in lista, senza shell: nessun dato passa da un interprete di comandi
        return (r.stdout + r.stderr).strip()
    with tempfile.TemporaryDirectory(prefix="impaginatore_ps_") as d:
        p = os.path.join(d, "codice.jsx")
        with open(p, "w", encoding="utf-8") as f: f.write(codice.encode("ascii", "backslashreplace").decode("ascii"))
        return esegui_jsx(p)
