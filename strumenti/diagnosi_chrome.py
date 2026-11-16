"""Diagnosi temporanea della CI (job Windows, browser): in quali condizioni Chrome con --remote-debugging-port scrive
DevToolsActivePort. Esce con 1 se non parte come lo avvia tests/cdp.py (casa finta dei test, cartelle create), così le
prove nel browser non girano 25 minuti per niente. Da togliere con il suo passo in .github/workflows/ci.yml."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))
from cdp import CHROME, OPZIONI  # noqa: E402

BASE = os.environ.get("RUNNER_TEMP") or tempfile.gettempdir()


def prova(nome, prof, env, porta=0):
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof); log = prof + ".log"
    with open(log, "wb") as u:
        p = subprocess.Popen([CHROME, *OPZIONI, f"--user-data-dir={prof}", f"--remote-debugging-port={porta}", "--enable-logging=stderr", "about:blank"],
                             stdout=u, stderr=subprocess.STDOUT, env=env)
    f = os.path.join(prof, "DevToolsActivePort"); inizio = time.time(); ok = False
    while time.time() - inizio < 20:
        if os.path.exists(f) and open(f, encoding="utf-8").read().strip(): ok = True; break
        if porta:
            try: urllib.request.urlopen(f"http://127.0.0.1:{porta}/json/version", timeout=2).read(); ok = True; break
            except OSError: pass
        time.sleep(0.2)
    stato = p.poll(); p.kill(); p.wait(10)
    uscita = open(log, encoding="utf-8", errors="replace").read()
    print(f"== {nome}: {'PARTE' if ok else 'NON PARTE'} in {time.time() - inizio:.1f} s, poll {stato}, profilo {sorted(os.listdir(prof))[:12]}", flush=True)
    print("   " + " | ".join(r for r in uscita.splitlines() if r.strip())[-600:], flush=True)
    return ok


def main():
    print("CHROME", CHROME, "BASE", BASE, flush=True)
    vero = dict(os.environ)
    casa = os.path.join(BASE, "casa"); os.makedirs(casa, exist_ok=True)
    finto = dict(vero, HOME=casa, USERPROFILE=casa, APPDATA=os.path.join(casa, "AppData", "Roaming"), LOCALAPPDATA=os.path.join(casa, "AppData", "Local"))
    prova("casa finta dei test, cartelle che non esistono", os.path.join(BASE, "d1"), finto)
    prova("ambiente vero", os.path.join(BASE, "d2"), vero)
    prova("ambiente vero, porta 9333", os.path.join(BASE, "d3"), vero, porta=9333)
    prova("casa finta, porta 9334", os.path.join(BASE, "d4"), finto, porta=9334)
    prova("casa finta con USERPROFILE vero", os.path.join(BASE, "d5"), dict(finto, USERPROFILE=vero.get("USERPROFILE", "")))
    os.makedirs(finto["LOCALAPPDATA"], exist_ok=True); os.makedirs(finto["APPDATA"], exist_ok=True)
    ok = prova("casa finta con le cartelle create (come tests/cdp.py)", os.path.join(BASE, "d6"), finto)
    lunga = os.path.join(tempfile.gettempdir(), "pytest-of-runneradmin", "pytest-9", "test_la_pagina_rispetta_la_sua0", "chrome-cdp")
    prova("ambiente vero, percorso come quello di pytest", lunga, vero)
    for chiave in (r"HKLM\SOFTWARE\Policies\Google\Chrome", r"HKCU\SOFTWARE\Policies\Google\Chrome") if os.name == "nt" else ():
        r = subprocess.run(["reg", "query", chiave, "/s"], capture_output=True, text=True, errors="replace")
        print("== criteri", chiave, (r.stdout or r.stderr).strip()[:800], flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
