"""Installazione di una versione nuova (T-207): estrazione sicura (solo i file firmati, niente percorsi fuori, niente
collegamenti, limiti), elenco delle revoche, prova di avvio in un processo a parte, puntatore, ritorno indietro, pulizia."""
import hashlib
import json
import os
import stat
import subprocess
import zipfile

import pytest
from aiuti_aggiornamenti import SENZA_COVERAGE, SRC, pacchetto

from impaginatore import __version__
from impaginatore.aggiornamenti import Rifiutato, installazione, lanciatore, rilascio
from impaginatore.aggiornamenti.installazione import InstallazioneCompilata, InstallazionePython, estrai


def _man(pk):
    return json.loads(rilascio.manifesto(pk))


def _zip(p, voci):
    """ZIP con voci [(ZipInfo o nome, byte)]"""
    with zipfile.ZipFile(p, "w") as z:
        for zi, b in voci: z.writestr(zi, b)
    return str(p)


def _h(b): return hashlib.sha256(b).hexdigest()


def test_estrae_solo_i_file_firmati(tmp_path):
    pk = pacchetto(str(tmp_path), file={"impaginatore/a.py": b"A", "impaginatore/sotto/b.json": b"{}"})
    estrai(pk, _man(pk), str(tmp_path / "out"))
    fatti = sorted(os.path.relpath(os.path.join(r, f), tmp_path / "out") for r, _, fs in os.walk(tmp_path / "out") for f in fs)
    assert fatti == [os.path.join("impaginatore", n) for n in ("__init__.py", "a.py", os.path.join("sotto", "b.json"))], "i metadati della wheel restano fuori"


@pytest.mark.filterwarnings("ignore:Duplicate name")
@pytest.mark.parametrize("voci, chiave", [
    ([("impaginatore/estraneo.py", b"x")], "sistema.agg_file_non_ammesso"),                                    # non è nel manifesto
    ([("impaginatore/__init__.py", b"doppio")], "sistema.agg_file_non_ammesso"),                               # due volte lo stesso nome
    ([("impaginatore/../../fuori.py", b"x")], "sistema.agg_file_non_ammesso"),
])
def test_file_in_piu(tmp_path, voci, chiave):
    init = b'__version__ = "2.0.1"\n'
    m = dict(file={"impaginatore/__init__.py": _h(init), "impaginatore/../../fuori.py": _h(b"x")})
    pk = _zip(tmp_path / "p.whl", [("impaginatore/__init__.py", init), *voci])
    with pytest.raises(Rifiutato) as e: estrai(pk, m, str(tmp_path / "out"))
    assert e.value.chiave == chiave and not (tmp_path / "fuori.py").exists()


def test_collegamenti_cifrati_grandi(tmp_path, monkeypatch):
    init = b'__version__ = "2.0.1"\n'; m = dict(file={"impaginatore/__init__.py": _h(init), "impaginatore/x": _h(b"/etc/passwd")})
    link = zipfile.ZipInfo("impaginatore/x"); link.external_attr = (stat.S_IFLNK | 0o777) << 16
    pk = _zip(tmp_path / "l.whl", [("impaginatore/__init__.py", init), (link, b"/etc/passwd")])
    with pytest.raises(Rifiutato, match=r"non previsto \(impaginatore/x\)"): estrai(pk, m, str(tmp_path / "out-l"))
    assert not os.path.lexists(tmp_path / "out-l" / "impaginatore" / "x"), "nessun collegamento simbolico"
    pk = _zip(tmp_path / "g.whl", [("impaginatore/__init__.py", init), ("impaginatore/x", b"/etc/passwd")])
    orig = zipfile.ZipFile.infolist
    def cifrato(self):
        v = orig(self)
        v[-1].flag_bits |= 0x1                       # zipfile non scrive file cifrati: il bit si mette nella lettura
        return v
    with monkeypatch.context() as mp:
        mp.setattr(zipfile.ZipFile, "infolist", cifrato)
        with pytest.raises(Rifiutato, match=r"non previsto \(impaginatore/x\)"): estrai(pk, m, str(tmp_path / "out-c"))
    monkeypatch.setattr(installazione, "MAX_FILE", 5)
    with pytest.raises(Rifiutato, match="non previsto"): estrai(pk, m, str(tmp_path / "g1"))
    monkeypatch.setattr(installazione, "MAX_FILE", 1 << 20); monkeypatch.setattr(installazione, "MAX_ESTRATTO", 20)
    with pytest.raises(Rifiutato, match="più grande del previsto"): estrai(pk, m, str(tmp_path / "g2"))
    monkeypatch.setattr(installazione, "MAX_VOCI", 1)
    with pytest.raises(Rifiutato, match="non si legge"): estrai(pk, m, str(tmp_path / "g3"))


def test_impronte_e_file_mancanti(tmp_path):
    pk = pacchetto(str(tmp_path))
    m = _man(pk)
    with pytest.raises(Rifiutato, match="impronta diversa"): estrai(pk, dict(m, file=dict(m["file"], **{"impaginatore/__init__.py": "0" * 64})), str(tmp_path / "a"))
    with pytest.raises(Rifiutato, match=r"incompleto \(manca 1 file\)"): estrai(pk, dict(m, file=dict(m["file"], **{"impaginatore/manca.py": "0" * 64})), str(tmp_path / "b"))
    with pytest.raises(Rifiutato, match=r"incompleto \(mancano 2 file\)"): estrai(pk, dict(m, file=dict(m["file"], **{"impaginatore/manca.py": "0" * 64, "impaginatore/manca2.py": "0" * 64})), str(tmp_path / "b2"))
    (tmp_path / "rotto.whl").write_bytes(b"non uno zip")
    with pytest.raises(Rifiutato, match="non si legge"): estrai(str(tmp_path / "rotto.whl"), m, str(tmp_path / "c"))
    with pytest.raises(Rifiutato, match="non si legge"): estrai(str(tmp_path / "manca.whl"), m, str(tmp_path / "d"))


def test_elenco_delle_revoche(tmp_path, licenza, monkeypatch):
    d = tmp_path / "v"; r = d / "impaginatore" / "licenze"; r.mkdir(parents=True)
    assert installazione.controlla_revoche(str(d)) is False, "nessun elenco: niente da controllare"
    f = r / "revoche.json"
    f.write_text(json.dumps(licenza.chiavi.revoche([7, 9])), encoding="utf-8"); assert installazione.controlla_revoche(str(d)) is True
    f.write_text(json.dumps(licenza.chiavi.revoche([7], id_firma=5)), encoding="utf-8"); assert installazione.controlla_revoche(str(d)) is True, "chiave nuova (rotazione): vale la firma del manifesto"
    for testo in (json.dumps(dict(licenza.chiavi.revoche([7]), seriali=[7, 8])), "{rotto", json.dumps([1]), json.dumps(dict(licenza.chiavi.revoche([7]), id_firma="1")), "\udcff"):
        f.write_text(testo, encoding="utf-8", errors="surrogateescape")
        with pytest.raises(Rifiutato, match="licenze revocate"): installazione.controlla_revoche(str(d))
    from impaginatore.licenze import chiave as K
    monkeypatch.setattr(K, "CHIAVI_PUBBLICHE", {1: K.Pubblica(K.SEGNAPOSTO)})             # copia di sviluppo: il segnaposto (il repository ha le chiavi vere)
    f.write_text(json.dumps(dict(licenza.chiavi.revoche([7]), seriali=[7, 8])), encoding="utf-8")
    assert K.problemi_per_il_rilascio() and installazione.controlla_revoche(str(d)) is True


def test_prova_di_avvio_vera(tmp_path, monkeypatch):
    """la copia estratta si importa con questo Python (schermata, editor, motore) e dice la versione giusta"""
    for k in SENZA_COVERAGE: monkeypatch.delenv(k, raising=False)        # il processo della prova gira su una copia fuori da src
    pk = rilascio.pacchetto_da_sorgente(SRC, "2.0.1", str(tmp_path))
    estrai(pk, _man(pk), str(tmp_path / "v"))
    installazione.prova_avvio(str(tmp_path / "v"), "2.0.1")
    with pytest.raises(Rifiutato, match=r"non si avvia su questo computer \(IMPAGINATORE 2\.0\.1 True\)"): installazione.prova_avvio(str(tmp_path / "v"), "2.0.2")
    with open(tmp_path / "v" / "impaginatore" / "editor" / "server.py", "a", encoding="utf-8") as f: f.write("\nimport libreria_che_non_ce\n")
    with pytest.raises(Rifiutato, match="libreria_che_non_ce"): installazione.prova_avvio(str(tmp_path / "v"), "2.0.1")


def test_prova_di_avvio_che_non_parte(monkeypatch):
    def run(*a, **k): raise subprocess.TimeoutExpired("python", 1)
    monkeypatch.setattr(installazione.subprocess, "run", run)
    with pytest.raises(Rifiutato, match=r"\(TimeoutExpired\)"): installazione.prova_avvio("/x", "2.0.1")
    monkeypatch.setattr(installazione.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1, "", ""))
    with pytest.raises(Rifiutato, match=r"\(\?\)"): installazione.prova_avvio("/x", "2.0.1")


def test_installa_torna_e_pulisce(tmp_path, monkeypatch, licenza):
    prove = []
    i = InstallazionePython(prova=lambda r, v: prove.append((os.path.basename(r).split("-")[0], v)))
    assert i.pacchetto == "python" and i.disponibile and i.precedente() is None
    vecchie = os.path.join(lanciatore.cartella(), "versioni")
    for n in ("1.0.0", ".prepara-2.0.1-abcd", ".via-1234"): os.makedirs(os.path.join(vecchie, n))
    pk = pacchetto(str(tmp_path), file={"impaginatore/licenze/revoche.json": json.dumps(licenza.chiavi.revoche([3])).encode()})
    i.installa(_man(pk), pk)
    assert prove == [(".prepara", "2.0.1")] and lanciatore.leggi() == dict(formato=1, versione="2.0.1", precedente=__version__, confermata=False, tentativi=0, scartata=None)
    assert sorted(os.listdir(vecchie)) == ["2.0.1"] and lanciatore.copia("2.0.1"), "restano la versione nuova (e la precedente, se è una copia)"
    with open(os.path.join(vecchie, "2.0.1", lanciatore.COMPLETA), encoding="utf-8") as f: assert json.load(f) == {"versione": "2.0.1", "file": 2}
    monkeypatch.setattr(installazione, "__version__", "2.0.1")
    assert i.precedente() == __version__
    i.torna(__version__)
    assert lanciatore.leggi() == dict(formato=1, versione=__version__, precedente=None, confermata=True, tentativi=0, scartata="2.0.1")
    with pytest.raises(Rifiutato, match="solo alla versione"): i.torna("2.0.1")
    monkeypatch.setattr(installazione, "__version__", __version__)
    i.installa(_man(pk), pk)
    assert lanciatore.leggi()["scartata"] is None, "reinstallata: non è più scartata"
    lanciatore.scrivi(dict(lanciatore.leggi(), scartata="2.0.0"))
    pk2 = pacchetto(str(tmp_path / "2"), "2.0.2"); monkeypatch.setattr(installazione, "__version__", "2.0.1")
    i.installa(_man(pk2), pk2)
    assert lanciatore.leggi() == dict(formato=1, versione="2.0.2", precedente="2.0.1", confermata=False, tentativi=0, scartata="2.0.0")
    assert sorted(os.listdir(vecchie)) == ["2.0.1", "2.0.2"]
    monkeypatch.setattr(installazione, "__version__", "2.0.2")
    assert i.precedente() == "2.0.1"
    import shutil
    shutil.rmtree(os.path.join(vecchie, "2.0.1")); assert i.precedente() is None, "la copia precedente non c'è più"


def test_installazione_che_non_riesce_non_cambia_niente(tmp_path, licenza):
    pk = pacchetto(str(tmp_path), file={"impaginatore/licenze/revoche.json": b"{rotto"})
    i = InstallazionePython(prova=lambda r, v: 1 / 0)
    with pytest.raises(Rifiutato, match="licenze revocate"): i.installa(_man(pk), pk)
    pk = pacchetto(str(tmp_path / "b"))
    with pytest.raises(ZeroDivisionError): i.installa(_man(pk), pk)
    assert lanciatore.leggi() is None and os.listdir(os.path.join(lanciatore.cartella(), "versioni")) == [], "nessuna cartella a metà"


def test_togli(tmp_path, monkeypatch):
    installazione._togli(str(tmp_path / "manca"))
    (tmp_path / "a" / "b").mkdir(parents=True)
    monkeypatch.setattr(installazione.os, "rename", lambda a, b: (_ for _ in ()).throw(PermissionError("in uso")))
    installazione._togli(str(tmp_path / "a")); assert not (tmp_path / "a").exists(), "se non si rinomina si cancella dov'è"


def test_programma_compilato_e_interfaccia(monkeypatch):
    c = InstallazioneCompilata()
    assert not c.disponibile and c.motivo == "sistema.agg_app_compilata" and c.precedente() is None
    from impaginatore import piattaforma
    assert c.pacchetto == piattaforma.sistema()
    for f in (lambda: c.installa({}, ""), lambda: c.torna("1")):
        with pytest.raises(Rifiutato, match="installatore"): f()
    b = installazione.Installazione()
    assert b.precedente() is None and b.disponibile and b.pacchetto is None
    for f in (lambda: b.installa({}, ""), lambda: b.torna("1")):
        with pytest.raises(NotImplementedError): f()
