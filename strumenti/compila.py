#!/usr/bin/env python3
"""Costruisce il programma compilato e il suo pacchetto di installazione, per il sistema su cui gira (T-302).

Come e perché: docs/architettura/DISTRIBUZIONE.md. In breve: Nuitka traduce in C e compila il pacchetto impaginatore e le
sue dipendenze (nessun file .py del programma nel pacchetto), poi il pacchetto del sistema:

    macOS     Impaginatore-<v>-mac-arm64.dmg / -mac-x86_64.dmg   Impaginatore.app (firma ad hoc, senza notarizzazione)
    Windows   Impaginatore-<v>-windows.exe                        installatore Inno Setup per l'utente (senza firma)
    Linux     Impaginatore-<v>-linux.deb                          /opt/impaginatore; usa GTK e WebKitGTK del sistema

Accanto a ogni pacchetto: <pacchetto>.sha256 (formato di sha256sum) e <pacchetto>.componenti.json (componenti di terze
parti con versione e licenza; le licenze intere sono dentro il programma, cartella licenze-terze-parti).

Gira nell'ambiente di compilazione, mai in quello di sviluppo (Nuitka non entra nel programma distribuito):
    UV_PROJECT_ENVIRONMENT=.venv-compilazione uv sync --locked --python 3.12 --extra desktop --extra mcp --extra compilazione
    .venv-compilazione/bin/python strumenti/compila.py                  (Windows: .venv-compilazione\\Scripts\\python.exe)
Su Linux serve Python 3.12, la versione del PyGObject di Ubuntu 24.04 (la finestra usa quello del sistema).

Opzioni:
    --uscita CARTELLA     dove vanno i pacchetti (di serie dist/pacchetti)
    --solo-programma      compila e basta (build/compila/<chiave>/Impaginatore[.app])
    --solo-pacchetto      impacchetta un programma già compilato
Esce con 0 se tutto è andato, 1 altrimenti.
"""
import argparse
import hashlib
import importlib.metadata as md
import json
import os
import platform
import re
import shutil
import subprocess  # nosec B404  # strumenti di costruzione (Nuitka, dpkg-deb, hdiutil, iscc, codesign) con argomenti in lista
import sys
import time
import xml.etree.ElementTree as ET  # nosec B405  # legge solo il rapporto scritto da Nuitka in questa stessa costruzione
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "src"))                      # anche da un ambiente senza il pacchetto installato (i test)

from impaginatore import __version__  # noqa: E402
from impaginatore.aggiornamenti import installazione  # noqa: E402
from impaginatore.formato_1x import CARTELLA_MOTORE_1X, MOTORE_1X  # noqa: E402

NOME = "Impaginatore"
COMANDO = "impaginatore"                                     # comando, pacchetto .deb, cartella in /opt, voce del menu, icone
# l'eseguibile: su Linux e macOS non può chiamarsi come il comando, perché accanto c'è la cartella dei dati del pacchetto
# (impaginatore/risorse/…): Nuitka lo rifiuta, e il disco del Mac non distingue maiuscole e minuscole
ESEGUIBILE = {"linux": "impaginatore-app", "mac": "impaginatore-app", "windows": "impaginatore"}      # Windows: impaginatore.exe
ENTRATA = RADICE / "strumenti" / "compilazione" / "avvio_impaginatore.py"
ISS = RADICE / "strumenti" / "compilazione" / "impaginatore.iss"
ICONE = RADICE / "brand" / "icona"
ID_MAC = "it.impaginatore.Impaginatore"                      # identificativo del bundle: non cambia più dopo il primo rilascio (DISTRIBUZIONE.md)
AUTORE = "Stefano Imperato"                                  # come in pyproject.toml
DIPENDENZE_DEB = ("python3-gi", "gir1.2-gtk-3.0", "gir1.2-webkit2-4.1")
LICENZE = "licenze-terze-parti"
PYTHON_LINUX = (3, 12)                                       # quello di Ubuntu 24.04: il PyGObject del sistema è compilato per lui

# moduli che non entrano mai nel programma: strumenti di sviluppo, e quelli che il programma prende dal sistema o non usa
ESCLUSI_SEMPRE = ("pytest", "_pytest", "coverage", "ruff", "nuitka", "setuptools", "pip", "IPython", "pillow_heif", "readline", "pydoc", "doctest", "unittest")
ESCLUSI = {
    "linux": ("gi", "cairo", "tkinter"),                     # gi e cairo del sistema (compilato.SoloGi); le finestre di scelta sono quelle di GTK
    "mac": ("gi", "cairo", "tkinter"),                       # finestre di scelta del Finder (osascript)
    "windows": ("gi", "cairo"),                              # tkinter serve: finestre di scelta senza WebView2
}
DA_INCLUDERE = ("anyio._backends._asyncio",)                 # caricato per nome dall'SDK MCP (anyio): Nuitka non lo vede da solo
# Linux: PyGObject («gi») e pycairo sono quelli del sistema (compilato.CARTELLE_GI) e importano moduli della libreria
# standard che il programma non usa: senza, la finestra non parte (gi/_option.py: «No module named 'optparse'») e si apre
# il browser. Sono tutti quelli che importano (fcntl e sys sono già dentro Python); un test li confronta con il gi del sistema
PER_GI_DEL_SISTEMA = ("collections", "contextlib", "functools", "importlib", "inspect", "optparse", "os", "pkgutil", "re", "signal", "socket",
                      "threading", "types", "warnings")
# file di dati di OpenCV per i volti (motore/album.py, _build_faces): Nuitka non li vede. Senza, i volti non si trovano e
# l'editor non lo dice (i ritagli non li evitano più); un test controlla che siano tutti quelli nominati nel codice
CASCATE_OPENCV = ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")
NOMI_LICENZA = re.compile(r"(?i)^(licen[cs]e|copying|notice|authors|copyright)")


def chiave():
    return installazione.chiave_pacchetto()


def sistema():
    return chiave().split("-")[0]


def nome_pacchetto(versione, chiave):
    estensione = {"mac": "dmg", "windows": "exe", "linux": "deb"}[chiave.split("-")[0]]
    return f"{NOME}-{versione}-{chiave}.{estensione}"


def _parti(versione):
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?(?:\.dev(\d+))?", versione)
    if not m: raise SystemExit(f"Versione non valida: {versione}")
    return m.groups()


def versione_windows(versione):
    """quattro numeri per le proprietà del file .exe: 2.0.1rc1 -> 2.0.1.0 (la versione intera resta nel nome del prodotto)"""
    a, b, c, *_ = _parti(versione)
    return f"{a}.{b}.{c}.0"


def versione_debian(versione):
    """versione per dpkg, con lo stesso ordine di PEP 440: 2.0.0.dev0 < 2.0.0a1 < 2.0.0rc1 < 2.0.0 («~» viene prima di tutto)"""
    a, b, c, pre, n, dev = _parti(versione)
    v = f"{a}.{b}.{c}"
    if pre: v += f"~{pre}{n}"
    if dev is not None: v += f"~~dev{dev}"
    return v


# ---------------------------------------------------------------- compilazione
def argomenti_nuitka(sis, versione, uscita, rapporto, motore_1x):
    """riga di comando di Nuitka per il sistema sis ("linux", "mac", "windows"). Nuitka gira in modalità UTF-8 («-X utf8»)
    perché il programma compilato la eredita da lui: il compilato non legge PYTHONUTF8 (Nuitka ignora le variabili PYTHON*)
    e senza su Windows scriverebbe in cp1252 nei tubi e nei registri, mentre il pacchetto Python dà UTF-8 a ogni processo
    figlio (processi.ambiente_figli)"""
    a = [sys.executable, "-X", "utf8", "-m", "nuitka", "--mode=app" if sis == "mac" else "--mode=standalone", f"--output-dir={uscita}",
         f"--output-filename={ESEGUIBILE[sis]}", "--include-package=impaginatore", "--include-package-data=impaginatore",
         f"--include-data-files={motore_1x}{os.sep}*.txt=impaginatore/risorse/{CARTELLA_MOTORE_1X}/", "--noinclude-data-files=webview/lib/*.jar",
         "--python-flag=no_docstrings", f"--report={rapporto}", "--assume-yes-for-downloads"]
    a += [f"--include-module={m}" for m in DA_INCLUDERE]
    a += [f"--include-data-files={cartella_cascate() / n}=cv2/data/{n}" for n in CASCATE_OPENCV]
    a += [f"--nofollow-import-to={m}" for m in (*ESCLUSI_SEMPRE, *ESCLUSI[sis])]
    if sis == "linux":
        a += [f"--linux-icon={ICONE / 'icona-256.png'}"] + [f"--include-module={m}" for m in PER_GI_DEL_SISTEMA]
    elif sis == "windows":
        vw = versione_windows(versione)
        a += ["--enable-plugin=tk-inter", "--windows-console-mode=attach", f"--windows-icon-from-ico={ICONE / 'icona.ico'}",
              f"--product-name={NOME}", f"--file-description={NOME}", f"--company-name={AUTORE}", f"--copyright=© {time.strftime('%Y')} {AUTORE}",
              f"--file-version={vw}", f"--product-version={vw}"]
    else:
        a += [f"--macos-app-icon={ICONE / 'icona.icns'}", f"--macos-app-name={NOME}", f"--macos-signed-app-name={ID_MAC}",
              f"--macos-app-version={'.'.join(_parti(versione)[:3])}", "--macos-app-mode=gui"]
    return a + [str(ENTRATA)]


def cartella_cascate():
    import cv2
    return Path(cv2.data.haarcascades)


def prepara_motore_1x(cartella):
    """le copie del motore per i progetti esportati per la 1.x (formato_1x.copia_motore), come testo tra le risorse:
    nel programma compilato i .py non ci sono"""
    cartella.mkdir(parents=True, exist_ok=True)
    for n in MOTORE_1X: shutil.copyfile(RADICE / "src" / "impaginatore" / "motore" / n, cartella / (n + ".txt"))
    return cartella


def programma(costruzione, sis):
    """cartella (Linux, Windows) o bundle (macOS) del programma compilato"""
    return costruzione / (f"{NOME}.app" if sis == "mac" else NOME)


def compila(costruzione, sis):
    if sis == "linux" and sys.version_info[:2] != PYTHON_LINUX:
        raise SystemExit(f"Su Linux si compila con Python {'.'.join(map(str, PYTHON_LINUX))} (questo è {platform.python_version()}): la finestra usa il PyGObject del sistema")
    shutil.rmtree(costruzione, ignore_errors=True); costruzione.mkdir(parents=True)
    m1x = prepara_motore_1x(costruzione / "motore_1x")
    inizio = time.time()
    env = dict(os.environ, PATH=os.pathsep.join([str(Path(sys.executable).parent), os.environ.get("PATH", "")]))          # patchelf dell'ambiente (extra «compilazione»)
    subprocess.run(argomenti_nuitka(sis, __version__, costruzione, costruzione / "compilazione.xml", m1x), check=True, cwd=RADICE, env=env)  # nosec B603  # Nuitka di questo ambiente, argomenti in lista
    fatto = costruzione / ("avvio_impaginatore.app" if sis == "mac" else "avvio_impaginatore.dist")
    dest = programma(costruzione, sis); fatto.rename(dest)
    print(f"Compilato in {time.time() - inizio:.0f} s: {dest}")
    return dest


# ---------------------------------------------------------------- componenti e licenze
def leggi_rapporto(rapporto):
    """radice del rapporto XML di Nuitka, letto sempre come UTF-8. Nuitka lo scrive in UTF-8 ma lo dichiara
    encoding='utf8', nome che expat non conosce: lo legge come una codifica a un byte e si ferma alla prima lettera non
    ASCII («not well-formed (invalid token)»). Succedeva su Windows, con la © di --copyright (pipeline, 16/11/2026)"""
    return ET.parse(rapporto, parser=ET.XMLParser(encoding="utf-8")).getroot()  # nosec B314  # il rapporto di Nuitka di questa costruzione


def distribuzioni_incluse(rapporto):
    """{nome normalizzato: Distribution} delle distribuzioni Python di cui Nuitka ha messo nel programma almeno un modulo
    (dal rapporto della compilazione); il programma stesso escluso"""
    radici = {(el.get("name") or "").split(".")[0] for el in leggi_rapporto(rapporto).iter("module")}
    da_modulo = md.packages_distributions()
    out = {}
    for r in sorted(radici):
        for n in da_modulo.get(r, []):
            d = md.distribution(n); k = re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower()
            if k != "impaginatore": out[k] = d
    return out


def licenza_dichiarata(d):
    m = d.metadata
    if m.get("License-Expression"): return m["License-Expression"]
    lic = (m.get("License") or "").strip()
    if lic and "\n" not in lic and len(lic) < 80: return lic
    classi = [c.split("::")[-1].strip() for c in m.get_all("Classifier") or [] if c.startswith("License ::")]
    return " / ".join(classi) or "vedi i file della licenza"


def file_di_licenza(d):
    """file di licenza della distribuzione: quelli dei metadati (licenses/…, LICENSE…) e quelli dei componenti che porta con
    sé (es. cv2/LICENSE-3RD-PARTY.txt, con FFmpeg e le altre librerie di OpenCV)"""
    out = []
    for f in d.files or []:
        nome = f.name
        if ".dist-info/licenses/" in str(f).replace("\\", "/") or NOMI_LICENZA.match(nome) or nome.startswith("LICENSE-3RD-PARTY"):
            p = Path(d.locate_file(f))
            if p.is_file() and p.suffix not in (".py", ".pyc", ".so", ".pyd", ".dll"): out.append(p)
    return sorted(set(out))


def licenza_python():
    for p in (Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE.txt"):
        if p.is_file(): return p
    raise SystemExit(f"Licenza di Python non trovata in {sys.base_prefix}")


def librerie_native(prog):
    return sorted(str(p.relative_to(prog)).replace("\\", "/") for p in prog.rglob("*") if p.is_file() and re.search(r"\.(so(\.\d+)*|dylib|dll|pyd)$", p.name))


def scrivi_licenze(prog, sis, rapporto):
    """licenze intere in <programma>/licenze-terze-parti/<distribuzione>/ e l'elenco dei componenti (componenti.json)"""
    base = prog / "Contents" / "Resources" if sis == "mac" else prog
    dest = base / LICENZE; shutil.rmtree(dest, ignore_errors=True); dest.mkdir(parents=True)
    componenti = []
    shutil.copyfile(licenza_python(), dest / "python-LICENSE.txt")
    componenti.append(dict(nome="Python", versione=platform.python_version(), licenza="PSF-2.0", file=["python-LICENSE.txt"]))
    for k, d in sorted(distribuzioni_incluse(rapporto).items()):
        cart = dest / f"{k}-{d.version}"; cart.mkdir()
        copiati = []
        for p in file_di_licenza(d):
            n = p.name if p.name not in copiati else f"{p.parent.name}-{p.name}"
            shutil.copyfile(p, cart / n); copiati.append(n)
        componenti.append(dict(nome=d.metadata["Name"], versione=d.version, licenza=licenza_dichiarata(d), file=[f"{cart.name}/{n}" for n in copiati]))
    elenco = dict(programma=NOME, versione=__version__, sistema=chiave(), python=platform.python_version(), componenti=componenti,
                  librerie_native=librerie_native(prog))
    (dest / "componenti.json").write_text(json.dumps(elenco, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    senza = [c["nome"] for c in componenti if not c["file"]]
    if senza: print(f"Attenzione: nessun file di licenza per {', '.join(senza)}: controllare a mano (DISTRIBUZIONE.md)")
    return elenco


def controlla_programma(prog):
    """nessun sorgente del programma nel pacchetto: né .py né .pyc del pacchetto impaginatore"""
    sorgenti = [str(p.relative_to(prog)) for p in prog.rglob("*") if p.suffix in (".py", ".pyc") and "impaginatore" in p.relative_to(prog).parts]
    if sorgenti: raise SystemExit(f"Nel programma compilato ci sono file sorgente: {sorgenti[:10]}")
    for n in MOTORE_1X:
        if not any(prog.rglob(n + ".txt")): raise SystemExit(f"Manca la copia del motore per la 1.x: {n}.txt")
    if not any(prog.rglob("avvio.html")): raise SystemExit("Manca la schermata di avvio (risorse/avvio.html)")
    for n in CASCATE_OPENCV:
        if not any(prog.rglob(n)): raise SystemExit(f"Manca il file di OpenCV per i volti: {n}")


# ---------------------------------------------------------------- pacchetti
def controllo_deb(versione, installata_kb):
    return "\n".join([
        f"Package: {COMANDO}", f"Version: {versione_debian(versione)}", "Section: graphics", "Priority: optional", "Architecture: amd64",
        f"Maintainer: {NOME} <supporto@impaginatore.example>", f"Installed-Size: {installata_kb}", f"Depends: {', '.join(DIPENDENZE_DEB)}",
        "Recommends: zenity", "Homepage: https://impaginatore.example",
        "Description: Impaginare album fotografici",
        " Impaginatore impagina album fotografici (spread, modelli, testi, correzioni) ed esporta JPG, PDF e PSD.",
        " Le foto restano sul computer.", ""])


def voce_desktop():
    return "\n".join(["[Desktop Entry]", "Type=Application", f"Name={NOME}", "Comment=Impaginare album fotografici", "Comment[en]=Lay out photo albums",
                      f"Exec={COMANDO}", f"Icon={COMANDO}", "Terminal=false", "Categories=Graphics;Photography;", f"StartupWMClass={COMANDO}", ""])


def pacchetto_deb(prog, uscita, versione):
    radice = prog.parent / "deb"; shutil.rmtree(radice, ignore_errors=True)
    opt = radice / "opt" / COMANDO; shutil.copytree(prog, opt, symlinks=True)
    for p in opt.rglob("*"):
        if p.is_file() and not p.is_symlink(): p.chmod(0o755 if os.access(p, os.X_OK) or p.name == ESEGUIBILE["linux"] else 0o644)
        elif p.is_dir(): p.chmod(0o755)
    (radice / "usr" / "bin").mkdir(parents=True); (radice / "usr" / "bin" / COMANDO).symlink_to(f"/opt/{COMANDO}/{ESEGUIBILE['linux']}")
    app = radice / "usr" / "share" / "applications"; app.mkdir(parents=True); (app / f"{COMANDO}.desktop").write_text(voce_desktop(), encoding="utf-8")
    for lato in (16, 32, 64, 128, 256, 512):
        d = radice / "usr" / "share" / "icons" / "hicolor" / f"{lato}x{lato}" / "apps"; d.mkdir(parents=True)
        shutil.copyfile(ICONE / f"icona-{lato}.png", d / f"{COMANDO}.png")
    doc = radice / "usr" / "share" / "doc" / COMANDO; doc.mkdir(parents=True)
    (doc / "copyright").write_text(f"{NOME} {versione}: software proprietario, tutti i diritti riservati ({AUTORE}).\n"
                                   f"Componenti di terze parti e loro licenze: /opt/{COMANDO}/{LICENZE}/ (componenti.json).\n", encoding="utf-8")
    kb = sum(p.stat().st_size for p in radice.rglob("*") if p.is_file() and not p.is_symlink()) // 1024
    (radice / "DEBIAN").mkdir(); (radice / "DEBIAN" / "control").write_text(controllo_deb(versione, kb), encoding="utf-8")
    for p in [radice, *radice.rglob("*")]:
        if p.is_dir(): p.chmod(0o755)
    out = uscita / nome_pacchetto(versione, "linux")
    subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(radice), str(out)], check=True)  # nosec B603, B607  # dpkg-deb del sistema di costruzione
    return out


def pacchetto_dmg(prog, uscita, versione, k):
    """firma ad hoc, copia con ditto e DMG. I file di dati che Nuitka mette in Contents/MacOS (cv2/data/*.xml, le risorse
    del programma) codesign li firma come codice, con la firma negli attributi estesi del file: shutil.copytree su macOS non
    li copia e la firma del bundle si rompe («code object is not signed at all», pipeline del 16/11/2026). ditto li copia;
    la firma si ricontrolla sulla copia che va nel DMG"""
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(prog)], check=True)  # nosec B603, B607  # firma ad hoc del bundle appena costruito (dopo le licenze)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(prog)], check=True)  # nosec B603, B607
    vol = prog.parent / "dmg"; shutil.rmtree(vol, ignore_errors=True); vol.mkdir()
    subprocess.run(["ditto", str(prog), str(vol / prog.name)], check=True)  # nosec B603, B607  # ditto di macOS: copia anche gli attributi estesi
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(vol / prog.name)], check=True)  # nosec B603, B607
    (vol / "Applicazioni").symlink_to("/Applications")
    out = uscita / nome_pacchetto(versione, k)
    if out.exists(): out.unlink()
    ripeti(["hdiutil", "create", "-volname", NOME, "-srcfolder", str(vol), "-fs", "HFS+", "-format", "UDZO", "-ov", str(out)])
    return out


def ripeti(cmd, volte=4, attesa=10):
    """esegue cmd e, se non va, lo riprova fino a `volte` volte: «hdiutil create» sui Mac di GitHub a volte risponde «Resource
    busy» (un altro processo del sistema tiene ancora aperti i file appena scritti) e va alla volta dopo"""
    for i in range(1, volte + 1):
        try: return subprocess.run(cmd, check=True)  # nosec B603  # strumenti del sistema di costruzione, argomenti in lista
        except subprocess.CalledProcessError:
            if i == volte: raise
            print(f"{cmd[0]} non è andato (tentativo {i} di {volte}): riprovo tra {attesa * i} s", flush=True)
            time.sleep(attesa * i)


def iscc():
    """ISCC.exe di Inno Setup 6: nel PATH o nella cartella dove lo mette il suo installatore"""
    for c in (shutil.which("iscc"), shutil.which("ISCC"), r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe", r"C:\Program Files\Inno Setup 6\ISCC.exe"):
        if c and Path(c).is_file(): return c
    raise SystemExit("Inno Setup 6 non trovato (ISCC.exe): https://jrsoftware.org/isinfo.php")


def definizioni_iss(prog, uscita, versione):
    return {"Versione": versione, "VersioneFile": versione_windows(versione), "Sorgente": str(prog), "Uscita": str(uscita),
            "NomeFile": nome_pacchetto(versione, "windows")[:-4], "Icona": str(ICONE / "icona.ico"), "Autore": AUTORE, "Licenze": LICENZE}


def pacchetto_exe(prog, uscita, versione):
    d = definizioni_iss(prog, uscita, versione)
    subprocess.run([iscc(), "/Q", *[f"/D{k}={v}" for k, v in d.items()], str(ISS)], check=True)  # nosec B603  # Inno Setup, argomenti in lista
    return uscita / (d["NomeFile"] + ".exe")


def impronta(percorso):
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def minos(testo_otool):
    """versioni minime di macOS dichiarate nei comandi di caricamento («otool -l»): minos di LC_BUILD_VERSION (macOS) e
    version di LC_VERSION_MIN_MACOSX"""
    out, cmd = [], None
    for r in testo_otool.splitlines():
        r = r.strip()
        if r.startswith("cmd "): cmd = r[4:]
        elif (cmd == "LC_BUILD_VERSION" and r.startswith("minos ")) or (cmd == "LC_VERSION_MIN_MACOSX" and r.startswith("version ")):
            out.append(tuple(int(x) for x in r.split()[1].split(".")))
        elif cmd == "LC_BUILD_VERSION" and r.startswith("platform ") and r.split()[1] not in ("1", "MACOS"): cmd = None          # solo macOS
    return out


def macos_minimo(prog):
    """la versione di macOS più alta chiesta da un file del bundle: sotto quella il programma non parte"""
    massimo = (0,)
    for p in prog.rglob("*"):
        if not p.is_file() or p.is_symlink(): continue
        with open(p, "rb") as f: testa = f.read(4)
        if testa not in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"): continue                     # Mach-O a 64 bit o universale
        r = subprocess.run(["otool", "-l", str(p)], capture_output=True, text=True, check=True)  # nosec B603, B607  # otool di Xcode, argomenti in lista
        massimo = max([massimo, *minos(r.stdout)])
    return ".".join(map(str, massimo))


def impacchetta(prog, sis, uscita, rapporto):
    elenco = scrivi_licenze(prog, sis, rapporto)
    controlla_programma(prog)
    if sis == "mac": elenco["macos_minimo"] = macos_minimo(prog); print(f"macOS minimo: {elenco['macos_minimo']}")
    uscita.mkdir(parents=True, exist_ok=True)
    if sis == "linux": out = pacchetto_deb(prog, uscita, __version__)
    elif sis == "mac": out = pacchetto_dmg(prog, uscita, __version__, chiave())
    else: out = pacchetto_exe(prog, uscita, __version__)
    Path(f"{out}.sha256").write_text(f"{impronta(out)}  {out.name}\n", encoding="utf-8")
    Path(f"{out}.componenti.json").write_text(json.dumps(elenco, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    mb = out.stat().st_size / 1e6
    print(f"Pacchetto: {out} ({mb:.1f} MB); programma {sum(p.stat().st_size for p in prog.rglob('*') if p.is_file()) / 1e6:.1f} MB su disco, {len(elenco['componenti'])} componenti")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="compila", description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uscita", default=str(RADICE / "dist" / "pacchetti"))
    g = ap.add_mutually_exclusive_group(); g.add_argument("--solo-programma", action="store_true"); g.add_argument("--solo-pacchetto", action="store_true")
    a = ap.parse_args(argv)
    sis = sistema(); costruzione = RADICE / "build" / "compila" / chiave()
    prog = programma(costruzione, sis) if a.solo_pacchetto else compila(costruzione, sis)
    if not a.solo_programma: impacchetta(prog, sis, Path(a.uscita).resolve(), costruzione / "compilazione.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
