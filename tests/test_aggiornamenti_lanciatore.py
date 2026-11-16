"""Lanciatore (T-207): numeri di versione, puntatore alla versione installata, scelta della copia da avviare, salto nella
copia (os.execv finto, e una volta vero in un processo a parte), versioni che non partono."""
import json
import logging
import os
import subprocess
import sys

import pytest
from aiuti_aggiornamenti import SRC, ambiente_senza_coverage

from impaginatore import __version__
from impaginatore.aggiornamenti import lanciatore as L
from impaginatore.aggiornamenti import rilascio
from impaginatore.piattaforma import processi


def _copia_finta(radice, versione, completa=True):
    d = os.path.join(radice, "impaginatore"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "__init__.py"), "w", encoding="utf-8") as f: f.write(f'"""x"""\n__version__ = "{versione}"\n')
    if completa: open(os.path.join(radice, L.COMPLETA), "w").close()
    return str(radice)


@pytest.fixture
def base(tmp_path, monkeypatch):
    """una base installata 2.0.0 (non un checkout) e la cartella delle versioni nei dati dell'utente"""
    b = _copia_finta(tmp_path / "base" / "site-packages", "2.0.0", completa=False)
    monkeypatch.setenv(L.VAR_BASE, b)
    for k in (L.VAR_SCELTA, L.VAR_FINTI): monkeypatch.setenv(k, ""); monkeypatch.delenv(k)           # così sparisce anche quello che scrive avvia()
    return b


def _slot(v, completa=True):
    return _copia_finta(os.path.join(L.cartella(), "versioni", v), v, completa)


@pytest.mark.parametrize("ordine", [["1.9.9", "2.0.0.dev0", "2.0.0a1", "2.0.0a2", "2.0.0b1", "2.0.0rc1.dev3", "2.0.0rc1", "2.0.0", "2.0.1.dev0", "2.0.1", "2.1.0", "10.0.0"]])
def test_ordine_delle_versioni(ordine):
    chiavi = [L.chiave(v) for v in ordine]
    assert chiavi == sorted(chiavi) and len(set(chiavi)) == len(chiavi)
    assert L.piu_nuova("2.0.1", "2.0.0") and not L.piu_nuova("2.0.0", "2.0.0") and not L.piu_nuova("2.0.0rc1", "2.0.0")
    assert [L.di_sviluppo(v) for v in ("2.0.0.dev0", "2.0.0a1", "2.0.0rc2", "2.0.0", "2.0.1")] == [True, True, True, False, False]
    assert L.maggiore("10.2.3") == 10 and L.valida(__version__)
    for v in ("", "2.0", "v2.0.0", "2.0.0-beta", "1.2.3.4", "2.0.0.post1", " 2.0.0", "12345.0.0", None, 2):
        assert not L.valida(v)
        with pytest.raises(ValueError): L.chiave(v)


def test_versione_letta_senza_importare(tmp_path):
    assert L.versione_in(SRC.rsplit(os.sep, 1)[0]) == __version__
    assert L.versione_in(str(tmp_path)) is None
    _copia_finta(tmp_path / "a", "non-una-versione", completa=False); assert L.versione_in(str(tmp_path / "a")) is None
    _copia_finta(tmp_path / "b", "2.0.3", completa=False); assert L.versione_in(str(tmp_path / "b")) == "2.0.3"


def test_checkout_e_base(tmp_path, monkeypatch):
    src = tmp_path / "repo" / "src"; src.mkdir(parents=True)
    assert not L.da_checkout(str(src))
    (tmp_path / "repo" / ".git").mkdir(); assert not L.da_checkout(str(src)), "manca pyproject.toml"
    (tmp_path / "repo" / "pyproject.toml").write_text("", encoding="utf-8"); assert L.da_checkout(str(src)) and not L.da_checkout(str(tmp_path / "repo"))
    assert not L.copie_ammesse(str(src)) and L.copie_ammesse(str(tmp_path))
    monkeypatch.setenv(L.VAR_FINTI, "/qualcosa"); assert L.copie_ammesse(str(src)), "le prove a mano dal checkout"
    monkeypatch.delenv(L.VAR_BASE, raising=False)
    assert L.base() == L.qui() == os.path.dirname(SRC)
    monkeypatch.setenv(L.VAR_BASE, "/altrove"); assert L.base() == "/altrove"


def test_puntatore(base, caplog):
    assert L.leggi() is None
    L.scrivi(dict(versione="2.0.1")); assert L.leggi() == dict(versione="2.0.1", formato=1)
    assert [n for n in os.listdir(L.cartella()) if n.endswith(".tmp")] == [], "nessun file a metà"
    p = os.path.join(L.cartella(), L.PUNTATORE)
    for testo in ("{rotto", "[1]", json.dumps(dict(formato=2, versione="9.0.0"))):
        with open(p, "w", encoding="utf-8") as f: f.write(testo)
        with caplog.at_level(logging.WARNING, logger="impaginatore.aggiornamenti"): assert L.leggi() is None
    assert "illeggibile" in caplog.text
    os.remove(p); os.mkdir(p)
    assert L.leggi() is None, "un puntatore che non si apre vale la base"


def test_copia_e_disponibile(base):
    assert L.copia("../../x") is None and L.copia("2.0.1") is None
    _slot("2.0.1", completa=False); assert L.copia("2.0.1") is None, "senza il segno .completa"
    _slot("2.0.1"); assert L.copia("2.0.1") == os.path.join(L.cartella(), "versioni", "2.0.1")
    _copia_finta(os.path.join(L.cartella(), "versioni", "2.0.2"), "2.0.9"); assert L.copia("2.0.2") is None, "la cartella dice un'altra versione"
    assert L.disponibile("2.0.0") and L.disponibile("2.0.1") and not L.disponibile("2.0.2") and not L.disponibile("x") and L.disponibile("2.0.0", base)


def test_scelta_della_copia(base, monkeypatch, tmp_path):
    assert L.scegli() == base, "nessun puntatore"
    s = _slot("2.0.1")
    L.scrivi(dict(versione="2.0.1", precedente="2.0.0", confermata=True)); assert L.scegli(conta=True) == s and L.leggi()["confermata"]
    for v in ("2.0.0", "1.9.0", "x", None, 3, "2.0.5"):
        L.scrivi(dict(versione=v)); assert L.scegli() == base, f"{v}: la base (mai indietro, mai una copia che non c'è)"
    monkeypatch.setenv(L.VAR_BASE, _copia_finta(tmp_path / "nuova", "2.0.2", completa=False))
    L.scrivi(dict(versione="2.0.1")); assert L.scegli() == str(tmp_path / "nuova"), "una base reinstallata più nuova vince sulle copie"
    monkeypatch.setenv(L.VAR_BASE, str(tmp_path / "senza-versione")); assert L.scegli() == str(tmp_path / "senza-versione")
    repo = tmp_path / "repo"; (repo / ".git").mkdir(parents=True); (repo / "pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.setenv(L.VAR_BASE, _copia_finta(repo / "src", "2.0.0", completa=False))
    L.scrivi(dict(versione="2.0.1")); assert L.scegli() == str(repo / "src"), "da un checkout il codice su cui si lavora"
    monkeypatch.setenv(L.VAR_FINTI, str(tmp_path)); assert L.scegli() == s


def test_una_versione_che_non_parte_torna_indietro(base, caplog):
    s = _slot("2.0.1")
    L.scrivi(dict(versione="2.0.1", precedente="2.0.0", confermata=False, tentativi="due", scartata=None))
    for n in range(1, L.MAX_TENTATIVI + 1):
        assert L.scegli(conta=True) == s and L.leggi()["tentativi"] == n
    assert L.scegli(conta=False) == s and L.leggi()["tentativi"] == L.MAX_TENTATIVI, "editor e server MCP non contano"
    with caplog.at_level(logging.WARNING, logger="impaginatore.aggiornamenti"): assert L.scegli(conta=True) == base
    assert L.leggi() == dict(formato=1, versione="2.0.0", precedente=None, confermata=True, tentativi=0, scartata="2.0.1") and "non è partita" in caplog.text
    s2 = _slot("2.0.2")
    L.scrivi(dict(versione="2.0.2", precedente="2.0.1", confermata=False, tentativi=L.MAX_TENTATIVI))
    assert L.scegli(conta=True) == s and L.leggi()["versione"] == "2.0.1", "torna alla precedente, anche se è una copia"
    L.scrivi(dict(versione="2.0.2", confermata=False, tentativi=0))
    assert L.conferma("2.0.2") and L.leggi()["confermata"] and not L.conferma("2.0.2") and not L.conferma("2.0.9") and L.scegli(conta=True) == s2


def test_conferma_della_versione_in_uso(base):
    assert L.conferma() is False, "nessun puntatore"
    L.scrivi(dict(versione=__version__, confermata=False, tentativi=2)); assert L.conferma() and L.leggi()["tentativi"] == 0


def test_avvia_salta_nella_copia(base, monkeypatch):
    salti = []
    monkeypatch.setattr(processi, "riesegui", lambda argv: salti.append(argv))
    monkeypatch.setattr(L, "qui", lambda: base)
    assert L.avvia(["--porta", "1"]) is None and salti == [], "nessuna copia: parte questa"
    s = _slot("2.0.1"); L.scrivi(dict(versione="2.0.1", precedente="2.0.0", confermata=False, tentativi=0))
    monkeypatch.delenv(L.VAR_BASE)
    monkeypatch.setattr(L, "base", lambda: base)
    assert L.avvia(["--porta", "1"]) == s
    assert salti == [[sys.executable, "-c", L.CODICE, s, "--porta", "1"]] and os.environ[L.VAR_SCELTA] == s and os.environ[L.VAR_BASE] == base
    assert L.leggi()["tentativi"] == 1
    for argv in (["editor", "--progetto", "x"], ["mcp"], ["_psd", "--spread", "1"], ["_rilancia", "0", "x"], ["--versione"], ["-h"]):
        os.environ.pop(L.VAR_SCELTA); assert L.avvia(argv) == s
    assert L.leggi()["tentativi"] == 1, "editor, server MCP, sottocomandi interni e --versione non contano come avvii della schermata"
    monkeypatch.setattr(L, "qui", lambda: s)
    assert L.avvia(["--porta", "1"]) is None and L.VAR_SCELTA not in os.environ, "nella copia scelta: si parte, e la variabile sparisce"
    assert L.avvia([]) is None and len(salti) == 7 and L.leggi()["tentativi"] == 2, "la copia stessa, scelta senza salto"


def test_avvia_non_salta(base, monkeypatch, caplog):
    salti = []
    monkeypatch.setattr(processi, "riesegui", lambda argv: salti.append(argv))
    monkeypatch.setattr(L, "qui", lambda: base)
    _slot("2.0.1"); L.scrivi(dict(versione="2.0.1", confermata=True))
    monkeypatch.setenv(L.VAR_SCELTA, "/un/altra/copia")
    with caplog.at_level(logging.WARNING, logger="impaginatore.aggiornamenti"): assert L.avvia([]) is None
    assert "non è quella partita" in caplog.text and salti == [], "già scelta una volta: mai un secondo salto"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert L.avvia([]) is None and salti == [], "programma compilato: niente copie"
    monkeypatch.delattr(sys, "frozen")
    from impaginatore import compilato
    monkeypatch.setitem(compilato.__dict__, "__compiled__", object())       # come lo mette Nuitka, prima ancora di compilato.prepara()
    assert L.avvia([]) is None and salti == [], "compilato con Nuitka: mai codice .py dalla cartella dei dati"
    monkeypatch.delitem(compilato.__dict__, "__compiled__")
    monkeypatch.setattr(L, "scegli", lambda conta: (_ for _ in ()).throw(PermissionError("dati")))
    with caplog.at_level(logging.WARNING, logger="impaginatore.aggiornamenti"): assert L.avvia([]) is None
    assert "non scelta (PermissionError)" in caplog.text and salti == []


def test_cli_passa_dal_lanciatore(monkeypatch):
    from impaginatore import cli
    from impaginatore.home import server as H
    visti = []
    monkeypatch.setattr(L, "avvia", lambda argv: visti.append(list(argv)))
    monkeypatch.setattr(H, "main", lambda argv: visti.append("home") or 0)
    assert cli.main(["--porta", "3"]) == 0 and visti == [["--porta", "3"], "home"]


@pytest.mark.lento
def test_salto_vero_nella_copia(tmp_path):
    """il comando vero (python -m impaginatore) con una copia 2.0.1 installata: os.execv nella copia, che dice la sua
    versione; con la variabile già impostata non salta più"""
    dati = tmp_path / "dati"; versioni = dati / "programma" / "versioni"
    pk = rilascio.pacchetto_da_sorgente(SRC, "2.0.1", str(tmp_path))
    import zipfile
    with zipfile.ZipFile(pk) as z: z.extractall(versioni / "2.0.1", [n for n in z.namelist() if n.startswith("impaginatore/")])
    (versioni / "2.0.1" / L.COMPLETA).write_text("{}", encoding="utf-8")
    (dati / "programma" / L.PUNTATORE).write_text(json.dumps(dict(formato=1, versione="2.0.1", precedente=__version__, confermata=True)), encoding="utf-8")
    env = ambiente_senza_coverage(); env.update(IMPAGINATORE_DATI=str(dati), **{L.VAR_FINTI: str(tmp_path)})
    for k in (L.VAR_BASE, L.VAR_SCELTA): env.pop(k, None)
    r = subprocess.run([sys.executable, "-m", "impaginatore", "--versione"], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120, cwd=os.path.dirname(SRC))
    assert r.returncode == 0 and r.stdout.strip() == "Impaginatore 2.0.1", r.stdout + r.stderr
    env[L.VAR_SCELTA] = os.path.dirname(SRC)
    r = subprocess.run([sys.executable, "-m", "impaginatore", "--versione"], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120, cwd=os.path.dirname(SRC))
    assert r.stdout.strip() == f"Impaginatore {__version__}", "la variabile dice che la scelta è già fatta"
