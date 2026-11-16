"""T-106, verifica indipendente: un test per ogni nuovo rilievo VER-xxx di docs/audit/VERIFICA-2026-11.md.

Ogni test descrive il comportamento giusto e oggi fallisce: è segnato xfail(strict=True). Quando chi corregge chiude il
rilievo il test passa, pytest segnala XPASS come errore e il segno xfail va tolto insieme alla correzione.
Nessun test chiede davvero gigabyte di memoria: le prove di VER-005 girano in un processo figlio con un tetto (RLIMIT_AS)."""
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
from urllib.parse import quote

import pytest
from aiuti import attendi_log, crea_foto
from PIL import Image

from impaginatore import formato

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def xfail(rilievo, motivo):
    return pytest.mark.xfail(strict=True, reason=f"T-106: {rilievo} {motivo}")


def _spread(c):
    """lo stato con uno spread di tre foto (come lo farebbe la pagina)"""
    nomi = [p["n"] for p in c.get("/api/state")["photos"]]
    c.post("/api/op", dict(op="newspreadsel", names=nomi[:3], pos=0))
    return nomi


# ------------------------------------------------------------------ VER-001
_X001 = xfail("VER-001", "operazione accettata e salvata, poi progetto.json non si riapre (BUG-001 residuo)")


@pytest.mark.parametrize("op", [
    pytest.param(dict(op="tolta", photo=None), marks=_X001),
    pytest.param(dict(op="evg", value=1e7), marks=_X001),
    pytest.param(dict(op="testo", nome="Matrimonio " * 500), marks=_X001),
    pytest.param(dict(op="face", photo="{foto}", x=1e7, y=0.5), marks=_X001),
    pytest.param(dict(op="guides", s=0, v=[1e7], h=[]), marks=_X001),
    dict(op="tono_L", value=float("nan")),                                    # NaN: rifiutato alla lettura del JSON (servizio.leggi_json)
], ids=["tolta-null", "evg-1e7", "titolo-5500-caratteri", "face-1e7", "guide-1e7", "tono_L-NaN"])
def test_operazione_accettata_lascia_il_progetto_riapribile(editor, op):
    """un'operazione o si rifiuta (400) o lascia un progetto che la schermata Progetti riapre"""
    nomi = _spread(editor)
    op = {k: (nomi[0] if v == "{foto}" else v) for k, v in op.items()}
    try: editor.post("/api/op", op)
    except urllib.error.HTTPError as e:
        assert e.code == 400; return
    editor.post("/api/save", {})
    formato.leggi_progetto(editor.progetto)
    formato.leggi_album(os.path.join(editor.progetto, formato.ALBUM))


# ------------------------------------------------------------------ VER-003
@pytest.mark.parametrize("op", [
    dict(op="free", at=[0, "L", 0], x=float("nan"), y=0.1, w=0.5, h=0.5),     # NaN: rifiutato alla lettura del JSON (servizio.leggi_json)
    pytest.param(dict(op="ratio", s=0, r=1e7, ats=[["L", 0]]), marks=xfail("VER-003", "valori impossibili accettati: /api/state risponde 500 finché non si annulla")),
    dict(op="nudge", s=0, ats=[["L", 0]], dx=float("nan"), dy=0),
], ids=["free-NaN", "ratio-1e7", "nudge-NaN"])
def test_operazione_con_numeri_impossibili_non_rompe_lo_stato(editor, op):
    _spread(editor)
    try: editor.post("/api/op", op)
    except urllib.error.HTTPError as e: assert e.code == 400, e.code
    assert editor.codice("/api/state") == 200


# ------------------------------------------------------------------ VER-010
@pytest.mark.parametrize("campo,valore", [("spazio", "-5"), ("margine", "nan"), ("abb", "1e9")])
@xfail("VER-010", "/api/nuovo crea un progetto con misure che poi la lettura rifiuta")
def test_nuovo_non_crea_progetti_che_non_si_aprono(home, campo, valore):
    try: p = home.nuovo({"nome": "Misure", "w": "30", "h": "30", campo: valore})
    except ValueError: return
    formato.leggi_progetto(p)


# ------------------------------------------------------------------ VER-005
_RADDOPPIA = "S = 'xxxxxxx'\n" + "S += S\n" * 16                     # 458 752 caratteri, sotto MAX_TESTO
SPEC_GRANDI = {
    "prova-elenco-di-testi": ("1", "from album import *\n" + _RADDOPPIA + "L = [" + "S+S," * 55000 + "]\nSPREADS = []\n"),
    "lettura-TEXT-di-un-elenco": ("0", "from album import *\nfrom album_libere import *\n" + _RADDOPPIA + "L = [S]\n" + "L += L\n" * 17
                                  + "SPREADS = [[I(TEXT(L, 0, 0, 1, 1)), I()]]\n"),
}
_FIGLIO = r'''
import resource, sys
resource.setrlimit(resource.RLIMIT_AS, (1536 * 2**20, 1536 * 2**20))
from impaginatore import formato_1x
from impaginatore.formato import ErroreProgetto
try: formato_1x.leggi(open(sys.argv[1], "rb").read(), prova=sys.argv[2] == "1"); print("letto")
except ErroreProgetto: print("ErroreProgetto")
except MemoryError: print("MemoryError")
'''


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="RLIMIT_AS fa da tetto solo su Linux")
@pytest.mark.parametrize("caso", list(SPEC_GRANDI))
@xfail("VER-005", "spec.py nei limiti di formato_1x chiede decine di GB (MemoryError sotto un tetto di 1,5 GB)")
def test_spec_py_nei_limiti_non_esaurisce_la_memoria(tmp_path, caso):
    prova, testo = SPEC_GRANDI[caso]
    p = tmp_path / "spec.py"; p.write_text(testo, encoding="utf-8")
    r = subprocess.run([sys.executable, "-c", _FIGLIO, str(p), prova], capture_output=True, text=True, timeout=300)
    assert r.stdout.strip() == "ErroreProgetto", (r.stdout + r.stderr)[-300:]


# ------------------------------------------------------------------ VER-004
def _progetto_con_foto_esterna(apri_editor, progetto, tmp_path):
    """progetto arrivato come cartella con _cache/meta.json che punta a una foto fuori dal progetto"""
    fuori = tmp_path / "Privato"; crea_foto(str(fuori), [("segreta", 64, 48, None)])
    c = apri_editor(progetto); c.srv.shutdown(); c.srv.server_close(); c.E.ferma()
    mp = os.path.join(progetto, "_cache", "meta.json"); m = json.load(open(mp, encoding="utf-8"))
    m.append(dict(m[0], n="zz_ricordo.jpg", src=str(fuori / "segreta.jpg")))
    with open(mp, "w", encoding="utf-8") as f: json.dump(m, f)
    return apri_editor(progetto), fuori


@xfail("VER-004", "src di _cache/meta.json fuori dal progetto diventano radici (SEC-005 aggirato)")
def test_progetto_ricevuto_non_allarga_le_radici(apri_editor, progetto, tmp_path):
    c, fuori = _progetto_con_foto_esterna(apri_editor, progetto, tmp_path)
    assert c.codice("/api/ls?p=" + quote(str(fuori))) == 403
    assert c.codice("/api/fthumb?p=" + quote(str(fuori / "segreta.jpg"))) == 403


@xfail("VER-004", "«Esporta progetto» copia nel pacchetto un file fuori dal progetto indicato da meta.json")
def test_esporta_progetto_non_porta_via_file_esterni(apri_editor, progetto, tmp_path):
    c, fuori = _progetto_con_foto_esterna(apri_editor, progetto, tmp_path)
    segreta = (fuori / "segreta.jpg").read_bytes()
    dest = os.path.join(progetto, "uscita"); os.makedirs(dest)
    c.post("/api/prj_esporta", {"dest": dest, "foto": True})
    attendi_log(c)
    copiati = [os.path.join(r, f) for r, _, fs in os.walk(dest) for f in fs]
    assert not [f for f in copiati if open(f, "rb").read() == segreta]


# ------------------------------------------------------------------ VER-006
@xfail("VER-006", "il cookie della pagina vale come gettone delle API e il browser lo manda a ogni porta di 127.0.0.1")
def test_cookie_della_pagina_non_e_il_gettone(home_srv):
    url = home_srv.srv.indirizzo_avvio()
    c = http.client.HTTPConnection("127.0.0.1", home_srv.porta, timeout=30)
    c.request("GET", url.split(str(home_srv.porta), 1)[1], headers={"Host": f"127.0.0.1:{home_srv.porta}"})
    r = c.getresponse(); r.read(); c.close()
    valore = r.getheader("Set-Cookie").split(";", 1)[0].split("=", 1)[1]
    assert valore != home_srv.gettone


# ------------------------------------------------------------------ VER-011
def test_programmi_esterni_senza_gettone(monkeypatch, tmp_path):
    from impaginatore.piattaforma import azioni
    visti = []

    class Finto:
        returncode = 0

    def run(cmd, **kw): visti.append(kw.get("env")); return Finto()
    monkeypatch.setenv("IMPAGINATORE_GETTONE", "gettone-segreto")
    monkeypatch.setattr(azioni, "sistema", lambda: "linux")
    monkeypatch.setattr(azioni.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(azioni.subprocess, "run", run)
    azioni.mostra(str(tmp_path))
    assert visti and all("IMPAGINATORE_GETTONE" not in (e if e is not None else os.environ) for e in visti)


# ------------------------------------------------------------------ VER-002
@xfail("VER-002", "una foto troncata nella cartella fa morire l'editor all'apertura del progetto")
def test_foto_troncata_non_blocca_il_progetto(home, apri_editor):
    p = home.nuovo({"nome": "Scheda piena", "w": "30", "h": "30"})
    crea_foto(os.path.join(p, "Foto"), [("H01", 600, 400, "2026:01:01 10:00:00"), ("H02", 600, 400, "2026:01:01 10:00:01")])
    import io
    b = io.BytesIO(); Image.new("RGB", (800, 600), (9, 9, 9)).save(b, "JPEG")
    with open(os.path.join(p, "Foto", "troncata.jpg"), "wb") as f: f.write(b.getvalue()[:len(b.getvalue()) // 3])
    c = apri_editor(p)
    st = c.get("/api/state")
    assert {"H01", "H02"} <= {x["n"] for x in st["photos"]}


# ------------------------------------------------------------------ VER-012
def test_content_length_strano_ha_una_risposta(editor):
    s = socket.create_connection(("127.0.0.1", editor.porta), timeout=10)
    s.sendall(f"POST /api/op HTTP/1.1\r\nHost: 127.0.0.1:{editor.porta}\r\nX-Impaginatore-Gettone: {editor.gettone}\r\n"
              "Content-Type: application/json\r\nContent-Length: ²\r\n\r\n{}".encode("latin-1"))      # «²»: isdigit() vero, int() no
    r = b""
    try:
        while True:
            x = s.recv(65536)
            if not x: break
            r += x
    except socket.timeout: pass
    s.close()
    assert r.startswith(b"HTTP/1.") and r.split(b" ", 2)[1] in (b"400", b"411")


def test_avvio_con_corpo_non_oggetto_risponde_400(home_srv):
    assert home_srv.codice("/api/avvio", [1, 2]) == 400


# ------------------------------------------------------------------ VER-013
@pytest.mark.skipif(sys.platform.startswith("win"), reason="permessi POSIX")
def test_registro_leggibile_solo_da_chi_usa_il_programma():
    import logging

    from impaginatore import giornale
    f = giornale.configura("prova")
    try: assert os.stat(f).st_mode & 0o077 == 0, oct(os.stat(f).st_mode)
    finally:
        log = logging.getLogger(giornale.NOME)
        for h in [h for h in log.handlers if getattr(h, "baseFilename", None) == f]: log.removeHandler(h); h.close()


# ------------------------------------------------------------------ VER-007, VER-008
def _lock():
    with open(os.path.join(RADICE, "uv.lock"), encoding="utf-8") as f: return f.read()


@xfail("VER-007", "uv.lock non contiene pillow-heif (f09bc15): ogni comando --locked fallisce")
def test_lock_contiene_tutte_le_dipendenze():
    tomllib = pytest.importorskip("tomllib")
    with open(os.path.join(RADICE, "pyproject.toml"), "rb") as f: pj = tomllib.load(f)["project"]
    dip = list(pj.get("dependencies", [])) + [d for v in pj.get("optional-dependencies", {}).values() for d in v]
    nomi = {re.split(r"[ <>=!~;\[]", d, maxsplit=1)[0].lower().replace("_", "-") for d in dip}
    nel_lock = set(re.findall(r'^name = "([^"]+)"', _lock(), re.M))
    assert nomi - nel_lock == set()


@xfail("VER-008", "per Python 3.10 il lock fissa Pillow 12.3.0, con vulnerabilità note corrette in 13.0.0")
def test_pillow_del_lock_senza_vulnerabilita_note():
    versioni = re.findall(r'^name = "pillow"\nversion = "([^"]+)"', _lock(), re.M)
    assert versioni and all(tuple(int(x) for x in v.split(".")[:2]) >= (13, 0) for v in versioni), versioni
