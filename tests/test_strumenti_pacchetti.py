"""Strumenti dei pacchetti di installazione (T-302): strumenti/compila.py (le parti che non chiedono Nuitka: versioni,
argomenti, licenze, pacchetto .deb) e strumenti/rilascio.py (controlli prima di un rilascio, cartella della release
firmata). Il programma compilato vero si prova con strumenti/verifica_pacchetto.py (docs/architettura/DISTRIBUZIONE.md)."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
from aiuti_aggiornamenti import pacchetto

from impaginatore import __version__, ed25519
from impaginatore.aggiornamenti import firmati

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRUMENTI = os.path.join(RADICE, "strumenti")
sys.path.insert(0, STRUMENTI)
import compila  # noqa: E402
import rilascio  # noqa: E402


# ---------------------------------------------------------------- compila.py
@pytest.mark.parametrize("v, win, deb", [("2.0.0", "2.0.0.0", "2.0.0"), ("2.0.0.dev0", "2.0.0.0", "2.0.0~~dev0"), ("2.0.1rc1", "2.0.1.0", "2.0.1~rc1"),
                                         ("2.1.0a2", "2.1.0.0", "2.1.0~a2"), ("2.0.1rc1.dev3", "2.0.1.0", "2.0.1~rc1~~dev3")])
def test_versioni_per_windows_e_debian(v, win, deb):
    assert compila.versione_windows(v) == win and compila.versione_debian(v) == deb
    with pytest.raises(SystemExit): compila.versione_debian("2.0")


@pytest.mark.skipif(not shutil.which("dpkg"), reason="serve dpkg")
def test_ordine_delle_versioni_debian_come_pep440():
    """dpkg mette le versioni nello stesso ordine di PEP 440 (aggiornare con apt non torna mai indietro)"""
    ordine = ["2.0.0.dev0", "2.0.0a1", "2.0.0b1", "2.0.0rc1.dev3", "2.0.0rc1", "2.0.0", "2.0.1.dev0", "2.0.1"]
    for a, b in zip(ordine, ordine[1:]):
        assert subprocess.run(["dpkg", "--compare-versions", compila.versione_debian(a), "lt", compila.versione_debian(b)]).returncode == 0, (a, b)


def test_nomi_dei_pacchetti():
    assert compila.nome_pacchetto("2.0.1", "linux") == "Impaginatore-2.0.1-linux.deb"
    assert compila.nome_pacchetto("2.0.1", "windows") == "Impaginatore-2.0.1-windows.exe"
    assert compila.nome_pacchetto("2.0.1", "mac-arm64") == "Impaginatore-2.0.1-mac-arm64.dmg"
    from impaginatore.aggiornamenti import sorgenti
    assert all(sorgenti._NOME.fullmatch(compila.nome_pacchetto("2.0.1rc1", k)) for k in rilascio.SISTEMI), "nomi che il programma accetta come asset"
    assert compila.chiave() in rilascio.SISTEMI and compila.sistema() in ("linux", "mac", "windows")


@pytest.mark.parametrize("sis", ["linux", "mac", "windows"])
def test_argomenti_di_nuitka(sis, tmp_path):
    a = compila.argomenti_nuitka(sis, "2.0.1", tmp_path, tmp_path / "r.xml", tmp_path / "m1x")
    assert a[:3] == [sys.executable, "-m", "nuitka"] and a[-1] == str(compila.ENTRATA)
    assert ("--mode=app" in a) == (sis == "mac") and ("--mode=standalone" in a) == (sis != "mac")
    for o in ("--include-package=impaginatore", "--include-package-data=impaginatore", "--python-flag=no_docstrings", "--nofollow-import-to=gi", "--noinclude-data-files=webview/lib/*.jar",
              "--nofollow-import-to=pytest", "--nofollow-import-to=pillow_heif", f"--report={tmp_path / 'r.xml'}"):
        assert o in a, o
    assert f"--include-data-files={tmp_path / 'm1x'}{os.sep}*.txt=impaginatore/risorse/motore_1x/" in a
    assert ("--nofollow-import-to=tkinter" in a) == (sis != "windows") and ("--enable-plugin=tk-inter" in a) == (sis == "windows")
    if sis == "windows": assert "--file-version=2.0.1.0" in a and "--windows-console-mode=attach" in a
    if sis == "mac": assert f"--macos-signed-app-name={compila.ID_MAC}" in a and "--macos-app-version=2.0.1" in a
    if sis == "linux": assert any(x.startswith("--linux-icon=") for x in a)
    assert f"--output-filename={'impaginatore' if sis == 'windows' else 'impaginatore-app'}" in a, "mai come la cartella dei dati impaginatore/ (Nuitka la rifiuta)"
    for x in a:
        if x.startswith(("--linux-icon=", "--windows-icon-from-ico=", "--macos-app-icon=")): assert os.path.isfile(x.split("=", 1)[1]), x


def test_entrata_e_copie_del_motore(tmp_path):
    r = subprocess.run([sys.executable, str(compila.ENTRATA), "--versione"], capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0 and r.stdout.strip() == f"Impaginatore {__version__}"
    d = compila.prepara_motore_1x(tmp_path / "m1x")
    assert sorted(os.listdir(d)) == ["album_libere.py.txt", "testo.py.txt"]
    assert (d / "testo.py.txt").read_bytes() == open(os.path.join(RADICE, "src", "impaginatore", "motore", "testo.py"), "rb").read()


def _rapporto(p, moduli):
    radice = ET.Element("nuitka-compilation-report")
    for m in moduli: ET.SubElement(radice, "module", name=m, kind="CompiledPythonModule")
    ET.ElementTree(radice).write(p)
    return p


def test_licenze_dei_componenti(tmp_path):
    prog = tmp_path / "Impaginatore"; (prog / "numpy.libs").mkdir(parents=True); (prog / "numpy.libs" / "libopenblas.so.0").write_bytes(b"x"); (prog / "impaginatore").write_bytes(b"x")
    r = _rapporto(tmp_path / "r.xml", ["impaginatore.cli", "numpy.core", "PIL.Image", "json", "nonesiste"])
    assert set(compila.distribuzioni_incluse(r)) == {"numpy", "pillow"}, "il programma stesso e la libreria standard no"
    e = compila.scrivi_licenze(prog, "linux", r)
    nomi = {c["nome"].lower(): c for c in e["componenti"]}
    assert set(nomi) == {"python", "numpy", "pillow"} and nomi["python"]["licenza"] == "PSF-2.0" and e["librerie_native"] == ["numpy.libs/libopenblas.so.0"]
    assert all(c["file"] for c in e["componenti"]) and all((prog / compila.LICENZE / f).is_file() for c in e["componenti"] for f in c["file"])
    assert json.loads((prog / compila.LICENZE / "componenti.json").read_text(encoding="utf-8")) == e
    m = tmp_path / "Impaginatore.app"; (m / "Contents" / "Resources").mkdir(parents=True)
    compila.scrivi_licenze(m, "mac", r); assert (m / "Contents" / "Resources" / compila.LICENZE / "componenti.json").is_file(), "macOS: dentro il bundle"


def test_licenza_dichiarata():
    import email.message
    class D:
        def __init__(self, **campi):
            self.metadata = email.message.Message()
            for k, v in campi.items():
                for x in (v if isinstance(v, list) else [v]): self.metadata[k] = x
    assert compila.licenza_dichiarata(D(**{"License-Expression": "MIT"})) == "MIT"
    assert compila.licenza_dichiarata(D(License="BSD-3-Clause")) == "BSD-3-Clause"
    assert compila.licenza_dichiarata(D(License="testo\nlungo", Classifier=["License :: OSI Approved :: MIT License", "Programming Language :: Python"])) == "MIT License"
    assert compila.licenza_dichiarata(D()) == "vedi i file della licenza"


def test_controllo_del_programma(tmp_path):
    prog = tmp_path / "P"; (prog / "impaginatore" / "risorse" / "motore_1x").mkdir(parents=True)
    with pytest.raises(SystemExit, match="motore per la 1.x"): compila.controlla_programma(prog)
    for n in ("album_libere.py.txt", "testo.py.txt"): (prog / "impaginatore" / "risorse" / "motore_1x" / n).write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="schermata di avvio"): compila.controlla_programma(prog)
    (prog / "impaginatore" / "risorse" / "avvio.html").write_text("x", encoding="utf-8"); compila.controlla_programma(prog)
    (prog / "numpy").mkdir(); (prog / "numpy" / "x.py").write_text("", encoding="utf-8"); compila.controlla_programma(prog)
    (prog / "impaginatore" / "cli.py").write_text("", encoding="utf-8")
    with pytest.raises(SystemExit, match="file sorgente"): compila.controlla_programma(prog)


def test_testi_del_pacchetto_deb():
    c = compila.controllo_deb("2.0.0.dev0", 123456)
    assert "Version: 2.0.0~~dev0\n" in c and "Installed-Size: 123456\n" in c and "Depends: python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1\n" in c
    assert c.endswith("\n") and all(r.startswith(" ") or ":" in r for r in c.strip().splitlines()), "campi e righe di continuazione"
    v = compila.voce_desktop(); assert "Exec=impaginatore\n" in v and v.startswith("[Desktop Entry]\n")
    d = compila.definizioni_iss("C:\\P", "C:\\U", "2.0.1rc1")
    assert d["NomeFile"] == "Impaginatore-2.0.1rc1-windows" and d["VersioneFile"] == "2.0.1.0"
    iss = open(compila.ISS, encoding="utf-8").read()
    assert all("{#" + k + "}" in iss for k in d if k != "Licenze") and "PrivilegesRequired=lowest" in iss


@pytest.mark.skipif(not shutil.which("dpkg-deb") or os.name == "nt", reason="serve dpkg-deb")
def test_pacchetto_deb(tmp_path):
    prog = tmp_path / "Impaginatore"; prog.mkdir()
    (prog / "impaginatore-app").write_bytes(b"#!/bin/sh\n"); (prog / "impaginatore-app").chmod(0o700); (prog / "libx.so").write_bytes(b"x")
    out = compila.pacchetto_deb(prog, tmp_path, "2.0.1rc1")
    assert out.name == "Impaginatore-2.0.1rc1-linux.deb"
    info = subprocess.run(["dpkg-deb", "-f", str(out), "Version", "Package", "Architecture"], capture_output=True, text=True).stdout
    assert info.split() == ["Version:", "2.0.1~rc1", "Package:", "impaginatore", "Architecture:", "amd64"]
    elenco = subprocess.run(["dpkg-deb", "-c", str(out)], capture_output=True, text=True).stdout
    assert re.search(r"-rwxr-xr-x root/root .* \./opt/impaginatore/impaginatore-app\n", elenco) and re.search(r"-rw-r--r-- root/root .* \./opt/impaginatore/libx\.so\n", elenco)
    assert "./usr/bin/impaginatore -> /opt/impaginatore/impaginatore-app" in elenco and "./usr/share/applications/impaginatore.desktop" in elenco
    assert "./usr/share/icons/hicolor/256x256/apps/impaginatore.png" in elenco


# ---------------------------------------------------------------- rilascio.py
PUB_FINTA = "11" * 32


def _changelog(tmp_path, versione):
    p = tmp_path / "CHANGELOG.md"
    p.write_text(f"# Registro\n\n## [{versione}] - 2026-12-01\n\n### Aggiunto\n\n- `AGG-001` **installer** — Pacchetti. _File:_ `strumenti/compila.py`.\n", encoding="utf-8")
    return p


def test_controlli_prima_del_rilascio(tmp_path, licenza):
    """le chiavi pubbliche vere sono nel codice (16/11/2026): il controllo passa su questo punto e si ferma solo se qualcuno
    rimette i segnaposto"""
    from impaginatore.licenze import chiave as K
    p = rilascio.problemi(__version__, chiavi_licenze=licenza.pubbliche_vere)                  # nei test le licenze usano una coppia di prova (conftest)
    assert not any("chiave" in x for x in p), p
    for frammento in ("REPOSITORY", "di sviluppo", f"[{__version__}]"):
        assert any(frammento in x for x in p), (frammento, p)
    p = rilascio.problemi(__version__, chiavi_aggiornamenti={1: firmati.SEGNAPOSTO}, chiavi_licenze={1: K.Pubblica(K.SEGNAPOSTO)})
    for frammento in ("chiave degli aggiornamenti", "chiave pubblica 1"):
        assert any(frammento in x for x in p), (frammento, p)
    buone = {1: K.Pubblica(ed25519.pubblica(bytes(32)).hex())}
    assert rilascio.problemi("2.0.1", _changelog(tmp_path, "2.0.1"), {1: PUB_FINTA}, buone, "studio/impaginatore") == []
    assert rilascio.problemi("2.0.2", _changelog(tmp_path, "2.0.1"), {1: PUB_FINTA}, buone, "studio/impaginatore") == ["CHANGELOG.md non ha la sezione «## [2.0.2]»"]
    r = subprocess.run([sys.executable, os.path.join(STRUMENTI, "rilascio.py"), "controlla"], capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 1 and "cose da sistemare" in r.stdout and "chiave" not in r.stdout, r.stdout


def test_prepara_una_release(tmp_path):
    s = os.path.join(STRUMENTI, "rilascio.py"); negozio = tmp_path / "negozio"
    env = dict(os.environ, IMPAGINATORE_NEGOZIO_DIR=str(negozio))
    def esegui(*a): return subprocess.run([sys.executable, s, *a], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
    r = subprocess.run([sys.executable, os.path.join(STRUMENTI, "aggiornamento.py"), "genera-coppia"], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
    pub = re.search(r'CHIAVI_FIDATE = \{1: "([0-9a-f]{64})"\}', r.stdout).group(1)
    art = tmp_path / "artefatti"; pacchetto(str(art / "wheel"), "2.0.1")
    for k in ("linux", "windows", "mac-arm64"):
        d = art / f"pacchetto-{k}"; d.mkdir(parents=True); (d / compila.nome_pacchetto("2.0.1", k)).write_bytes(k.encode() * 100)
    r = esegui("prepara", str(art), "--uscita", str(tmp_path / "rel"))
    assert r.returncode != 0 and "non è pronta per il rilascio" in r.stderr and "di sviluppo" not in r.stderr and "REPOSITORY" in r.stderr
    assert "non è quella di CHIAVI_FIDATE[1]" in r.stderr, "una chiave privata che non è quella vera: i programmi rifiuterebbero la release"
    assert not (tmp_path / "rel").exists()
    r = esegui("prepara", str(art), "--uscita", str(tmp_path / "rel"), "--prova", "--novita-it", "Pacchetti", "--novita-en", "Packages")
    assert r.returncode == 0, r.stderr
    rel = tmp_path / "rel"
    assert sorted(os.listdir(rel)) == sorted(["Impaginatore-2.0.1-linux.deb", "Impaginatore-2.0.1-mac-arm64.dmg", "Impaginatore-2.0.1-windows.exe", "NOTE.md", "SHA256SUMS",
                                              "impaginatore-2.0.1-py3-none-any.whl", "manifesto.json", "manifesto.json.sig"])
    m = firmati.verifica((rel / "manifesto.json").read_bytes(), (rel / "manifesto.json.sig").read_bytes(), {1: pub})
    assert set(m["pacchetti"]) == {"python", "linux", "windows", "mac-arm64"} and m["novita"] == {"it": ["Pacchetti"], "en": ["Packages"]}
    for riga in (rel / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        h, nome = riga.split("  "); assert hashlib.sha256((rel / nome).read_bytes()).hexdigest() == h
    note = (rel / "NOTE.md").read_text(encoding="utf-8")
    assert note.startswith("> **PROVA: NON PUBBLICARE.**") and "CHIAVI_FIDATE[1]" in note and "mac-x86_64" in note and "00-installazione.md" in note and (rel / "SHA256SUMS").read_text(encoding="utf-8").strip() in note
    r = esegui("prepara", str(art), "--uscita", str(rel), "--prova"); assert r.returncode != 0 and "non è vuota" in r.stderr
    r = esegui("prepara", str(art), "--uscita", str(tmp_path / "rel3"), "--prova", "--id", "2"); assert r.returncode != 0 and "Nessuna chiave dei rilasci 2" in r.stderr
    (art / "vecchio").mkdir(); (art / "vecchio" / "Impaginatore-2.0.0-linux.deb").write_bytes(b"x")
    r = esegui("prepara", str(art), "--uscita", str(tmp_path / "rel2"), "--prova"); assert r.returncode != 0 and "di un'altra versione" in r.stderr


def test_trova_i_pacchetti(tmp_path):
    with pytest.raises(SystemExit, match="una e una sola wheel"): rilascio.trova(tmp_path, "2.0.1")
    pacchetto(str(tmp_path / "w"), "2.0.1")
    with pytest.raises(SystemExit, match="Nessun pacchetto"): rilascio.trova(tmp_path, "2.0.1")
    for d in ("a", "b"): (tmp_path / d).mkdir(); (tmp_path / d / "Impaginatore-2.0.1-linux.deb").write_bytes(b"x")
    with pytest.raises(SystemExit, match="Più pacchetti linux"): rilascio.trova(tmp_path, "2.0.1")


def test_versione_minima_di_macos():
    otool = "\n".join(["Load command 9", "      cmd LC_BUILD_VERSION", " platform 1", "    minos 14.0", "      sdk 15.2",
                       "Load command 10", "      cmd LC_SOURCE_VERSION", "  version 0.0",
                       "Load command 11", "      cmd LC_VERSION_MIN_MACOSX", "  version 10.13", "      sdk 10.14",
                       "Load command 12", "      cmd LC_BUILD_VERSION", " platform 2", "    minos 17.0",
                       "Load command 13", "          cmd LC_LOAD_DYLIB", "compatibility version 1.0.0"])
    assert compila.minos(otool) == [(14, 0), (10, 13)], "solo macOS (platform 1), mai le versioni delle librerie"
