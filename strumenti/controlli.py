#!/usr/bin/env python3
"""Esegue in locale gli stessi controlli della CI (.github/workflows/ci.yml e sicurezza.yml, che chiamano questo file).

    python strumenti/controlli.py lint          ruff e forma del registro (CHANGELOG.md)
    python strumenti/controlli.py test          pytest
    python strumenti/controlli.py copertura     pytest con copertura; soglia: fail_under in pyproject.toml;
                                                rapporto in htmlcov/ e coverage.xml
    python strumenti/controlli.py sicurezza     bandit, dipendenze, segreti, licenze (sotto)
    python strumenti/controlli.py tutto         lint, copertura (comprende i test) e sicurezza

    python strumenti/controlli.py bandit        analisi statica del codice in src/
    python strumenti/controlli.py dipendenze    pip-audit su tutte le versioni fissate in uv.lock
    python strumenti/controlli.py segreti       gitleaks su tutta la storia git
    python strumenti/controlli.py licenze       licenze delle dipendenze contro LICENZE_AMMESSE

    --python 3.13   versione di Python dell'ambiente dei test (come la matrice della CI)

Serve uv nel PATH (la CI usa la versione scritta in .github/workflows/ci.yml; «dipendenze» vuole uv 0.8 o successivo).
Lo script gira con Python 3.9 o successivo su Linux, macOS e Windows; l'ambiente del progetto lo crea uv (.venv).
Le versioni degli strumenti sono fissate qui sotto e valgono per la CI e per chi lavora in locale.
Esce con 0 se tutto è in ordine, 1 se un controllo fallisce, 2 se manca qualcosa per eseguirli.
"""
import argparse
import hashlib
import io
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent

# interprete con cui uv esegue gli strumenti di sicurezza (indipendente dalla matrice dei test)
PYTHON_STRUMENTI = "3.12"
BANDIT = "bandit==1.9.4"
PIP_AUDIT = "pip-audit==2.10.1"
PIP_LICENSES = "pip-licenses==5.5.5"

# bandit blocca su ogni rilievo, di qualsiasi gravità. Un falso positivo si annota nel punto esatto, mai con esclusioni
# globali: «usedforsecurity=False» per gli hash che non proteggono niente, altrimenti «# nosec B603, B607  # motivo».
# Il motivo va dopo un secondo «#»: bandit legge come nomi di controlli tutte le parole tra «nosec» e il «#» seguente.
BANDIT_SOGLIA = ["--severity-level", "all", "--confidence-level", "all"]

# gitleaks: binario ufficiale dalle release di GitHub, SHA-256 copiati da gitleaks_8.30.1_checksums.txt
# (e confrontati con il digest che GitHub mostra per ogni allegato)
GITLEAKS_VERSIONE = "8.30.1"
GITLEAKS_SHA256 = {
    ("linux", "x64"): "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    ("linux", "arm64"): "e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080",
    ("darwin", "x64"): "dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709",
    ("darwin", "arm64"): "b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5",
    ("windows", "x64"): "d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e",
    ("windows", "arm64"): "b95f5e4f5c425cedca7ee203d9afd29597e692c4924a12ed42f970537c72cc0f",
}

# una versione di Python per ogni ramo di «resolution-markers» in uv.lock (< 3.12, da 3.12 a 3.13, >= 3.14): le dipendenze
# installate cambiano da un ramo all'altro. Se il lock ne aggiunge uno, va aggiunto anche qui.
PYTHON_LICENZE = ("3.11", "3.12", "3.14")

# Licenze compatibili con un programma proprietario distribuito compilato: solo permissive. Niente GPL, LGPL, AGPL, MPL,
# EPL, SSPL né licenze sconosciute: una dipendenza così va valutata a parte prima di aggiungerla qui.
# pip-licenses confronta le stringhe per intero (nomi SPDX, nomi dei classificatori PyPI o espressioni SPDX composte),
# quindi un'espressione composta si aggiunge solo se tutte le sue parti sono già ammesse.
LICENZE_AMMESSE = (
    "MIT", "MIT License", "MIT-CMU",
    "BSD License", "BSD-2-Clause", "BSD-3-Clause", "0BSD",
    "Apache-2.0", "Apache Software License",
    "ISC", "ISC License (ISCL)",
    "PSF-2.0", "Python Software Foundation License",
    "Zlib", "CC0-1.0",
    "HPND", "Historical Permission Notice and Disclaimer (HPND)",
    "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0",       # numpy dalla 2.3
    "MIT-0",                                                    # cffi dalla 2.1 (extra «desktop», solo su Windows: pythonnet)
    "Apache-2.0 OR BSD-3-Clause",                               # cryptography (extra «mcp», via pyjwt[crypto]): a scelta tra due licenze già ammesse
)


class Mancante(Exception):
    """manca qualcosa per eseguire i controlli (uscita 2)"""


def mostra(cmd):
    return subprocess.list2cmdline(cmd) if os.name == "nt" else shlex.join(cmd)


def esegui(cmd, env=None):
    cmd = [str(c) for c in cmd]
    print(f"\n$ {mostra(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=RADICE, env=env) == 0


def uv():
    trovato = shutil.which("uv")
    if not trovato:
        raise Mancante("serve uv nel PATH: https://docs.astral.sh/uv/getting-started/installation/")
    return trovato


def versione_uv():
    uscita = subprocess.run([uv(), "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", uscita)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def strumento(pacchetto, comando, *argomenti):
    """comando di uno strumento a versione fissa, in un ambiente a parte gestito da uv (non tocca .venv)"""
    return [uv(), "tool", "run", "--python", PYTHON_STRUMENTI, "--from", pacchetto, comando, *argomenti]


def nel_progetto(*comando):
    """comando nell'ambiente del progetto con gli extra di sviluppo e l'SDK del server MCP (i suoi test e la sua copertura),
    alle versioni esatte di uv.lock"""
    return [uv(), "run", "--locked", "--extra", "dev", "--extra", "mcp", *comando]


# ---------------------------------------------------------------- controlli

def ruff():
    return esegui(nel_progetto("ruff", "check"))


def registro():
    return esegui([sys.executable, "strumenti/controlla_changelog.py"])


def test():
    return esegui(nel_progetto("pytest"))


def copertura():
    # pytest-cov legge la soglia da [tool.coverage.report] fail_under e fallisce se la copertura è sotto
    return esegui(nel_progetto("pytest", "--cov", "--cov-report=term", "--cov-report=xml", "--cov-report=html"))


def bandit():
    return esegui(strumento(BANDIT, "bandit", "-r", "src", "-q", *BANDIT_SOGLIA))


def dipendenze():
    """pip-audit su tutte le versioni del lock, comprese quelle che valgono solo per un'altra versione di Python o un
    altro sistema (un requirements.txt verrebbe filtrato dai marcatori dell'interprete che esegue pip-audit)"""
    if versione_uv() < (0, 8, 0):
        raise Mancante("«dipendenze» vuole uv 0.8 o successivo (esportazione pylock.toml): aggiornalo con «uv self update»")
    with tempfile.TemporaryDirectory(prefix="controlli-") as tmp:
        lock = Path(tmp, "pylock.toml")
        if not esegui([uv(), "export", "--locked", "--all-extras", "--no-emit-project", "--format", "pylock.toml", "--quiet", "-o", lock]):
            return False
        return esegui(strumento(PIP_AUDIT, "pip-audit", "--locked", "--strict", "--progress-spinner", "off", tmp))


def licenze():
    """licenze delle dipendenze del programma (senza gli extra di sviluppo, con la finestra desktop e il server MCP), installate in
    ambienti temporanei. Valgono quelle di questo sistema: pywebview su Linux porta bottle, proxy-tools e
    typing-extensions; le dipendenze solo per macOS (pyobjc) e Windows (pythonnet, clr-loader, cffi) le controlla
    chi esegue il controllo su quei sistemi"""
    ok = True
    with tempfile.TemporaryDirectory(prefix="controlli-") as tmp:
        for versione in PYTHON_LICENZE:
            ambiente = Path(tmp, "py" + versione)
            env = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(ambiente))
            if not esegui([uv(), "sync", "--locked", "--no-install-project", "--extra", "desktop", "--extra", "mcp", "--quiet", "--python", versione], env=env):
                ok = False
                continue
            interprete = ambiente / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            ok = esegui(strumento(PIP_LICENSES, "pip-licenses", "--python", interprete, "--from=mixed", "--allow-only=" + ";".join(LICENZE_AMMESSE))) and ok
    return ok


def _sistema():
    sistema = {"Linux": "linux", "Darwin": "darwin", "Windows": "windows"}.get(platform.system())
    macchina = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower())
    if (sistema, macchina) not in GITLEAKS_SHA256:
        raise Mancante(f"gitleaks {GITLEAKS_VERSIONE} non ha un binario verificato per {platform.system()} {platform.machine()}")
    return sistema, macchina


def _cache():
    if os.environ.get("CONTROLLI_CACHE"):
        base = Path(os.environ["CONTROLLI_CACHE"])
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "impaginatore-controlli"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches" / "impaginatore-controlli"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "impaginatore-controlli"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _sha256(dati):
    return hashlib.sha256(dati).hexdigest()


def gitleaks(cartella):
    """scarica (una volta, in cache) l'archivio ufficiale di gitleaks, ne verifica lo SHA-256 a ogni uso ed estrae il
    solo eseguibile in «cartella»"""
    sistema, macchina = _sistema()
    atteso = GITLEAKS_SHA256[(sistema, macchina)]
    nome = f"gitleaks_{GITLEAKS_VERSIONE}_{sistema}_{macchina}." + ("zip" if sistema == "windows" else "tar.gz")
    archivio = _cache() / nome
    dati = archivio.read_bytes() if archivio.is_file() else b""
    if _sha256(dati) != atteso:
        url = f"https://github.com/gitleaks/gitleaks/releases/download/v{GITLEAKS_VERSIONE}/{nome}"
        print(f"scarico {url}", flush=True)
        with urllib.request.urlopen(url, timeout=120) as r:       # indirizzo https fisso; il contenuto si verifica sotto
            dati = r.read()
        if _sha256(dati) != atteso:
            raise Mancante(f"SHA-256 di {nome} diverso da quello pubblicato: {_sha256(dati)} invece di {atteso}")
        archivio.write_bytes(dati)
    eseguibile = "gitleaks.exe" if sistema == "windows" else "gitleaks"
    if sistema == "windows":
        with zipfile.ZipFile(io.BytesIO(dati)) as z: contenuto = z.read(eseguibile)
    else:
        with tarfile.open(fileobj=io.BytesIO(dati), mode="r:gz") as t: contenuto = t.extractfile(eseguibile).read()
    destinazione = Path(cartella, eseguibile)
    destinazione.write_bytes(contenuto)
    destinazione.chmod(0o755)
    return destinazione


def segreti():
    """gitleaks su tutti i commit raggiungibili (in CI serve il checkout con fetch-depth: 0); i falsi positivi si
    escludono con la loro impronta in .gitleaksignore"""
    if not (RADICE / ".git").exists():
        raise Mancante("«segreti» va eseguito in un checkout git")
    with tempfile.TemporaryDirectory(prefix="controlli-") as tmp:
        return esegui([gitleaks(tmp), "git", "--redact", "--verbose", "--no-color", "--no-banner", "--exit-code", "1", "."])


# ---------------------------------------------------------------- comandi

GRUPPI = {
    "lint": [("ruff", ruff), ("registro", registro)],
    "test": [("test", test)],
    "copertura": [("copertura", copertura)],
    "bandit": [("bandit", bandit)],
    "dipendenze": [("pip-audit", dipendenze)],
    "segreti": [("gitleaks", segreti)],
    "licenze": [("licenze", licenze)],
}
GRUPPI["sicurezza"] = GRUPPI["bandit"] + GRUPPI["dipendenze"] + GRUPPI["segreti"] + GRUPPI["licenze"]
GRUPPI["tutto"] = GRUPPI["lint"] + GRUPPI["copertura"] + GRUPPI["sicurezza"]


def main(argv=None):
    for flusso in (sys.stdout, sys.stderr):
        try: flusso.reconfigure(errors="replace")       # console Windows con code page senza «—» o «»
        except (AttributeError, ValueError): pass
    p = argparse.ArgumentParser(prog="controlli.py", description="Gli stessi controlli della CI, in locale.")
    p.add_argument("comando", choices=list(GRUPPI))
    p.add_argument("--python", help="versione di Python dell'ambiente dei test, per esempio 3.11 (imposta UV_PYTHON)")
    a = p.parse_args(argv)
    if a.python:
        os.environ["UV_PYTHON"] = a.python
    esiti = []
    for nome, controllo in GRUPPI[a.comando]:
        try:
            esiti.append((nome, "ok" if controllo() else "FALLITO"))
        except Mancante as e:
            print(f"\nerrore: {e}", file=sys.stderr, flush=True)
            esiti.append((nome, "NON ESEGUITO"))
    print("\nriepilogo:")
    for nome, esito in esiti:
        print(f"  {esito:13} {nome}")
    stati = {esito for _, esito in esiti}
    return 1 if "FALLITO" in stati else 2 if "NON ESEGUITO" in stati else 0


if __name__ == "__main__":
    sys.exit(main())
