"""Statistiche d'uso facoltative (T-204, docs/architettura/STATISTICHE.md): spente di serie, accese solo con il consenso;
nel registro solo eventi dello schema (mai nomi, percorsi, testi); tutto si legge, si esporta e si cancella; nessuna
richiesta di rete finché il titolare non mette l'indirizzo del server; le statistiche non rompono mai un'operazione."""
import errno
import json
import os
import re
import shutil
import socket
import ssl
import stat
import threading
import time
import types
import urllib.error
import urllib.request

import pytest

from impaginatore import licenze, statistiche as S
from impaginatore.statistiche import invio, schema

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def pulite(monkeypatch):
    """ogni test parte da statistiche mai chieste, senza server, con lo stato in memoria azzerato"""
    monkeypatch.setattr(invio, "INDIRIZZO", "")
    S.processo("altro"); S._ALBUM.update(inizio=None, spread=0, vuoto=False, primo=False); S._OPS.update(cartella=None, conti={})
    yield


def beta(licenza, scadenza="2099-12-31", seriale=7, intestatario="Tester ZQX", **k):
    """mette una licenza beta privata (Studio, segni omaggio e beta) e restituisce il suo testo"""
    testo = licenza.chiavi.chiave(fascia="studio", flag=3, scadenza=scadenza, seriale=seriale, intestatario=intestatario, **k)
    licenza.usa(testo); return testo


def eventi():
    """gli eventi del registro (anche quello ruotato), nell'ordine"""
    return [json.loads(r) for r in S._righe_grezze()]


def nomi(ev=None):
    return [e["ev"] for e in (eventi() if ev is None else ev)]


# ---------------------------------------------------------------- schema
def test_schema_tipi():
    v = schema.valore
    assert v(schema.INTERO, 3.6, "x") == 4 and v(schema.INTERO, -5, "x") == 0 and v(schema.INTERO, 1e12, "x") == schema.MAX_INTERO
    for cattivo in (True, "3", None, float("nan"), float("inf")):
        with pytest.raises(schema.FuoriSchema): v(schema.INTERO, cattivo, "x")
    assert v(schema.DECIMALE, 22.46, "x") == 22.5 and v(schema.DECIMALE, -1, "x") == 0.0 and v(schema.DECIMALE, 1e9, "x") == schema.MAX_DECIMALE
    for cattivo in (False, "2", float("nan")):
        with pytest.raises(schema.FuoriSchema): v(schema.DECIMALE, cattivo, "x")
    assert v(schema.VERO, True, "x") is True
    with pytest.raises(schema.FuoriSchema): v(schema.VERO, 1, "x")
    assert v(schema.CODICE, "impaginatore.editor.server:do_op", "x") and v(schema.CODICE, "<lambda>", "x") == "<lambda>"
    for cattivo in ("/home/zqx/foto.jpg", "C:\\Clienti\\Rossi", "una frase con spazi", "", "x" * 101, 3):
        with pytest.raises(schema.FuoriSchema): v(schema.CODICE, cattivo, "x")
    assert v(schema.VERSIONE, "2.0.0", "x") == "2.0.0"
    with pytest.raises(schema.FuoriSchema): v(schema.VERSIONE, "Ubuntu SMP Rossi", "x")
    assert v(schema.elenco("a", "b"), "a", "x") == "a"
    with pytest.raises(schema.FuoriSchema): v(schema.elenco("a"), "Rossi", "x")
    assert v(schema.conteggi("a", "b"), {"b": 2.2, "a": 1}, "x") == {"a": 1, "b": 2}
    for cattivo in ({"zqx": 1}, ["a"], {"a": "1"}):
        with pytest.raises(schema.FuoriSchema): v(schema.conteggi("a"), cattivo, "x")


def test_schema_pulisci_e_righe():
    assert schema.pulisci("chiusura", {"durata_s": 12.4}) == {"durata_s": 12}
    assert schema.pulisci("errore", {"tipo": "KeyError", "riga": None}) == {"tipo": "KeyError"}, "i None si tolgono"
    with pytest.raises(schema.FuoriSchema): schema.pulisci("nome_file", {})
    with pytest.raises(schema.FuoriSchema): schema.pulisci("chiusura", {"percorso": "/x"})
    buona = {"v": 1, "t": "2026-11-16T10:00:00Z", "id": "a" * 32, "sessione": "b" * 12, "proc": "home", "ver": "2.0.0", "serie": 7, "ev": "chiusura", "durata_s": 3}
    schema.controlla_riga(buona)
    for guasto in ([], dict(buona, ev="altro"), {k: v for k, v in buona.items() if k != "sessione"}, dict(buona, id="Z" * 32), dict(buona, t=3),
                   dict(buona, v=1.5), dict(buona, proc="Rossi"), dict(buona, durata_s=2.5), dict(buona, nome="ZQX")):
        with pytest.raises(schema.FuoriSchema): schema.controlla_riga(guasto)


def test_schema_ha_tutte_le_operazioni_e_i_controlli_dell_editor():
    from impaginatore.editor import server as E
    from impaginatore.motore import bozza as BZ
    assert set(E.NOMI_OP) <= set(schema.OPERAZIONI), sorted(set(E.NOMI_OP) - set(schema.OPERAZIONI))
    assert set(BZ.RITMI) <= set(schema.RITMI)
    sorgente = open(E.__file__, encoding="utf-8").read()
    tipi = set(re.findall(r"""add\("[a-z]+", "([a-z_]+)\"""", sorgente)) | set(re.findall(r"""livello="[a-z]+", tipo="([a-z_]+)\"""", sorgente)) | {"stella_non_usata", "non_usata"}
    assert len(tipi) > 15 and tipi <= set(schema.TIPI_CONTROLLO), sorted(tipi - set(schema.TIPI_CONTROLLO))


def test_documento_nomina_ogni_evento_e_campo():
    doc = open(os.path.join(RADICE, "docs", "architettura", "STATISTICHE.md"), encoding="utf-8").read()
    for nome, campi in schema.EVENTI.items():
        assert f"`{nome}`" in doc, nome
        for c in campi: assert f"`{c}`" in doc, (nome, c)
    for c in schema.BUSTA: assert f"`{c}`" in doc, c
    for t in schema.TRAGUARDI: assert f"`{t}`" in doc, t


# ---------------------------------------------------------------- consenso, file, identificativo
def test_spente_di_serie_non_scrivono_niente(licenza):
    assert not os.path.exists(S.cartella()), "importare il modulo non crea niente"
    beta(licenza)
    S.evento("chiusura", durata_s=1); S.avvio(); S.operazione("swap", 0.1); S.svuota(); S.traguardo("primo_album"); S.errore(KeyError("x"))
    S.album_aperto(10, 0, [60, 22.5], 300, 0.2); S.controllo({"problemi": [], "conta": {}, "pronto": True}, 0.1, 1)
    S.esportazione({"formato": "jpg"}, 1); S.album_nuovo("/non/esiste", True); S.chiusura()
    assert S.scelta() is None and not S.attive() and not os.path.exists(S.cartella())
    st = S.stato()
    assert (st["attive"], st["scelta"], st["chiedere"], st["beta"], st["serie"], st["disponibili"], st["id"], st["eventi"]) == (False, None, True, True, 7, True, None, 0)
    assert st["invio"] == {"attivo": False, "server": None, "in_coda": 0} and st["testo"] == S.TESTO_CONSENSO


def test_disponibili_solo_con_la_beta_o_se_c_e_qualcosa(licenza, monkeypatch):
    st = S.stato(); assert not st["disponibili"] and not st["chiedere"] and st["serie"] is None, "licenza Studio: niente interruttore"
    S.imposta(False); assert S.stato()["disponibili"], "una scelta fatta si può sempre cambiare"
    monkeypatch.setattr(S, "SOLO_BETA", False); os.remove(os.path.join(S.cartella(), S.CONSENSO)); assert S.stato()["disponibili"]


def test_si_e_no(licenza):
    beta(licenza)
    st = S.imposta(True)
    assert st["attive"] and st["scelta"] == "si" and not st["chiedere"] and re.fullmatch(r"[0-9a-f]{32}", st["id"])
    d = S.cartella()
    assert stat.S_IMODE(os.stat(d).st_mode) == 0o700 or os.name == "nt"
    for f in (S.CONSENSO, S.INSTALLAZIONE, S.EVENTI): assert stat.S_IMODE(os.stat(os.path.join(d, f)).st_mode) == 0o600 or os.name == "nt", f
    ev = eventi(); assert nomi(ev) == ["consenso", "avvio"]
    assert all(e["serie"] == 7 and e["id"] == st["id"] and e["sessione"] == S.SESSIONE and e["proc"] == "altro" for e in ev)
    assert ev[1]["fascia"] == "studio" and ev[1]["beta"] is True and ev[1]["licenza"] == "attiva" and ev[1]["lingua"] == "it"
    st = S.imposta(False); assert not st["attive"] and st["scelta"] == "no" and st["eventi"] == 2, "il registro resta finché non lo cancelli"
    S.evento("chiusura", durata_s=1); assert len(eventi()) == 2
    with pytest.raises(ValueError, match="sì o no"): S.imposta("si")
    with open(os.path.join(d, S.CONSENSO), "w") as f: json.dump({"scelta": "si", "testo": S.TESTO_CONSENSO + 5}, f)
    assert S.scelta() is None, "un testo del consenso diverso: si richiede"


def test_con_un_server_il_consenso_si_richiede(licenza, monkeypatch):
    beta(licenza); S.imposta(True); assert S.attive()
    monkeypatch.setattr(invio, "INDIRIZZO", "https://statistiche.esempio.invalid/v1")
    assert S.scelta() is None and S.stato()["chiedere"] and S.testo_consenso() == S.TESTO_CONSENSO_INVIO
    S.evento("chiusura", durata_s=1); assert nomi() == ["consenso", "avvio"], "il sì al testo senza invio non vale per l'invio"
    S.imposta(True); assert S.attive() and eventi()[-2]["testo"] == S.TESTO_CONSENSO_INVIO


def test_file_rovinati_e_permessi(licenza, monkeypatch, caplog):
    beta(licenza); d = S._prepara()
    with open(os.path.join(d, S.CONSENSO), "w") as f: f.write("{rotto")
    assert S.scelta() is None
    with open(os.path.join(d, S.CONSENSO), "w") as f: f.write("[1]")
    assert S.scelta() is None
    with open(os.path.join(d, S.INSTALLAZIONE), "w") as f: json.dump({"id": "../ZQX"}, f)
    assert S.identificativo() is None
    nuovo = S.azzera_identificativo(); assert nuovo and S.azzera_identificativo() != nuovo
    monkeypatch.setattr(S.os, "chmod", lambda *a: (_ for _ in ()).throw(PermissionError(1, "no")))
    S._prepara(); assert "permessi della cartella" in caplog.text


def test_rotazione_del_registro(licenza, monkeypatch):
    beta(licenza); S.imposta(True); monkeypatch.setattr(S, "MAX_FILE", 600)
    for _ in range(6): S.evento("chiusura", durata_s=1)
    d = S.cartella()
    assert os.path.exists(os.path.join(d, S.EVENTI_VECCHI)) and os.path.getsize(os.path.join(d, S.EVENTI)) <= 600
    assert S.stato()["eventi"] == len(eventi()) and "chiusura" in nomi()


def test_eventi_fuori_schema_e_errori_interni(licenza, monkeypatch, caplog):
    beta(licenza); S.imposta(True); n = len(eventi())
    S.evento("nome_file", nome="ZQX.jpg"); S.evento("chiusura", percorso="/ZQX")
    assert len(eventi()) == n and "evento delle statistiche scartato: ?" in caplog.text and "scartato: chiusura" in caplog.text
    monkeypatch.setattr(S, "_scrivi", lambda r: 1 / 0)
    assert S.evento("chiusura", durata_s=1) is None, "un errore delle statistiche non arriva a chi le chiama"


def test_senza_licenza_beta_niente_numero_di_serie(licenza):
    S.imposta(True); assert all("serie" not in e for e in eventi())
    assert eventi()[1]["fascia"] == "studio" and eventi()[1]["beta"] is False


# ---------------------------------------------------------------- ambiente
def test_versione_del_sistema(monkeypatch):
    assert S._versione("6.8.0-149-generic") == "6.8.0" and S._versione("Rossi") is None and S._versione(None) is None
    monkeypatch.setattr(S, "sistema", lambda: "mac"); monkeypatch.setattr(S.platform, "mac_ver", lambda: ("14.6.1", ("", "", ""), "arm64"))
    assert S.versione_sistema() == "14.6.1"
    monkeypatch.setattr(S, "sistema", lambda: "windows"); monkeypatch.setattr(S.platform, "version", lambda: "10.0.22631")
    assert S.versione_sistema() == "10.0.22631"
    monkeypatch.setattr(S, "sistema", lambda: "linux"); monkeypatch.setattr(S.platform, "release", lambda: "6.8.0-149-generic")
    assert S.versione_sistema() == "6.8.0"


@pytest.mark.parametrize("macchina, attesa", [("AMD64", "x86_64"), ("aarch64", "arm64"), ("i686", "x86"), ("riscv64", "altra")])
def test_architettura(monkeypatch, macchina, attesa):
    monkeypatch.setattr(S.platform, "machine", lambda: macchina); assert S.architettura() == attesa


def test_memoria(monkeypatch):
    assert S.memoria_gb() is None or S.memoria_gb() >= 0
    monkeypatch.setattr(S.os, "sysconf", lambda k: (_ for _ in ()).throw(ValueError(k)), raising=False)

    class K32:
        def __init__(self, ok): self.ok = ok
        def GlobalMemoryStatusEx(self, p):
            p._obj.ullTotalPhys = 16 * 2 ** 30; return self.ok
    assert S.memoria_gb(K32(True)) == 16 and S.memoria_gb(K32(False)) is None
    import ctypes
    monkeypatch.delattr(ctypes, "windll", raising=False)
    assert S.memoria_gb() is None, "né sysconf né Windows: non si sa"


def test_avvio_finestra_licenza_chiusura(licenza, monkeypatch):
    beta(licenza); S.imposta(True)
    monkeypatch.setattr(licenze, "inizio_prova", lambda: None)
    S.avvio(finestra=True); ev = eventi()[-1]
    assert ev["finestra_programma"] is True and "giorni_dal_primo_avvio" not in ev and ev["core"] >= 1 and re.fullmatch(r"\d+\.\d+", ev["python"])
    S.finestra("album", {"larghezza": 1280, "altezza": 800.4, "scala": 2, "schermo_larghezza": True, "schermo_altezza": "ZQX", "titolo": "ZQX"})
    assert {k: v for k, v in eventi()[-1].items() if k not in schema.BUSTA} == {"pagina": "album", "larghezza": 1280, "altezza": 800, "scala": 2.0}
    S.licenza("tolta", licenze.stato())
    assert {k: v for k, v in eventi()[-1].items() if k not in schema.BUSTA} == {"azione": "tolta", "stato": "attiva", "fascia": "studio", "beta": True, "a_scadenza": True}
    S.processo("home"); S.chiusura(); S.chiusura()
    assert nomi().count("chiusura") == 1 and eventi()[-1]["proc"] == "home", "una volta sola per processo"
    S.processo("ZQX"); S.evento("chiusura", durata_s=0); assert eventi()[-1]["proc"] == "altro"


# ---------------------------------------------------------------- album, operazioni, traguardi
def test_operazioni_contate_e_scritte_a_gruppi(licenza):
    beta(licenza); S.imposta(True)
    S.album_aperto(10, 0, [60, 22.5], 300, 0.25)
    a = eventi()[-3:]
    assert nomi(a) == ["album_aperto", "traguardo", "traguardo"] and a[0]["ms"] == 250 and a[0]["sola_lettura"] is False and a[0]["larghezza_cm"] == 60.0
    assert [x["nome"] for x in a[1:]] == ["primo_album", "prime_foto"]
    S.operazione("swap", 0.01); S.operazione("swap", 0.03, assistente=True); S.operazione("ZQX", 0.001)
    S.operazione("swap", 0.002, licenze.NonConsentita("no")); S.operazione("swap", 0.002, ValueError("ZQX"))
    S.operazione("swap", 0.002, KeyError("ZQX"))
    n = len(eventi()); S.svuota(); ops = {e["op"]: e for e in eventi()[n:] if e["ev"] == "operazioni"}
    assert ops["swap"]["n"] == 5 and ops["swap"]["assistente"] == 1 and ops["swap"]["licenza"] == 1 and ops["swap"]["rifiutate"] == 1 and ops["swap"]["errori"] == 1
    assert ops["swap"]["ms_max"] == 30 and ops["swap"]["ms_tot"] == 46 and ops["altro"]["n"] == 1
    e = next(x for x in eventi() if x["ev"] == "errore"); assert e["tipo"] == "KeyError" and e["dove"] == "<ignoto>"
    S.svuota(); assert len(eventi()) == n + 2, "niente in sospeso: niente da scrivere"


def test_primo_spread_e_bozza_accettata(licenza):
    beta(licenza); S.imposta(True)
    S.album_aperto(10, 0, None, 300, 0.1)
    S.operazione("bozza", 0.5, spread=3, esito={"spread": 3, "foto": 10, "da": 0})
    ev = eventi()
    acc = next(e for e in ev if e["ev"] == "bozza_accettata"); assert (acc["spread"], acc["foto"], acc["assistente"]) == (3, 10, False)
    ps = next(e for e in ev if e["ev"] == "primo_spread"); assert ps["modo"] == "bozza" and ps["foto"] == 10 and ps["secondi"] >= 0
    assert {e["nome"] for e in ev if e["ev"] == "traguardo"} >= {"prima_bozza", "primo_spread"}
    S.operazione("newspreadsel", 0.1, spread=4); S.operazione("delete", 0.1, spread=2); S.operazione("swap", 0.1)
    assert nomi().count("primo_spread") == 1 and nomi().count("traguardo") == len({e["nome"] for e in eventi() if e["ev"] == "traguardo"}), "una volta sola"
    S.album_aperto(10, 0, None, 300, 0.1); S.operazione("newspreadsel", 0.1, assistente=True, spread=1)
    assert eventi()[-1]["ev"] == "primo_spread" and eventi()[-1]["modo"] == "assistente"
    S.album_aperto(10, 0, None, 300, 0.1); S.operazione("newspreadsel", 0.1, spread=1); assert eventi()[-1]["modo"] == "manuale"
    S.album_aperto(10, 2, None, 300, 0.1); n = len(eventi()); S.operazione("newspreadsel", 0.1, spread=3)
    assert "primo_spread" not in nomi(eventi()[n:]), "un album che aveva già spread non conta"


def test_traguardi_una_volta_per_installazione(licenza, monkeypatch):
    beta(licenza); S.imposta(True); licenze.stato()
    S.traguardo("prima_esportazione"); S.traguardo("prima_esportazione"); S.traguardo("ZQX")
    t = [e for e in eventi() if e["ev"] == "traguardo"]; assert len(t) == 1 and t[0]["secondi_dal_primo_avvio"] >= 0
    monkeypatch.setattr(licenze, "inizio_prova", lambda: None); S.traguardo("primo_controllo")
    assert "secondi_dal_primo_avvio" not in eventi()[-1]


def test_operazioni_dopo_un_cambio_di_cartella(licenza, monkeypatch, tmp_path):
    beta(licenza); S.imposta(True); S.operazione("swap", 0.1)
    monkeypatch.setenv("IMPAGINATORE_DATI", str(tmp_path / "altra"))
    S.svuota(); assert not os.path.exists(os.path.join(S.cartella(), S.EVENTI)), "i conteggi di un'altra cartella non si scrivono qui"


def test_ciclo_che_svuota(licenza, monkeypatch):
    beta(licenza); S.imposta(True); S.operazione("swap", 0.1)
    giri = []

    def dormi(s):
        giri.append(s)
        if len(giri) > 1: raise SystemExit
    monkeypatch.setattr(S, "time", types.SimpleNamespace(sleep=dormi, monotonic=time.monotonic, time=time.time))
    with pytest.raises(SystemExit): S._ciclo_svuota()
    assert giri == [S.OGNI, S.OGNI] and "operazioni" in nomi()
    assert S._STATO["filo"] is not None and S._avvia_filo() is None


def test_bozza_controllo_esportazione_importazione_preparazione(licenza):
    beta(licenza); S.imposta(True); S.album_aperto(10, 0, None, 300, 0.1)
    S.bozza_proposta({"foto": 10, "spreads": [1, 2, 3]}, "piene", 1.2); S.bozza_proposta({"spreads": None}, "ZQX", 0.1)
    b = [e for e in eventi() if e["ev"] == "bozza_proposta"]; assert (b[0]["spread"], b[0]["ritmo"], b[0]["ms"]) == (3, "piene", 1200) and b[1]["ritmo"] == "altro"
    r = {"problemi": [{"tipo": "risoluzione", "testo": "ZQX.jpg"}, {"tipo": "risoluzione"}, {"tipo": "nuovo_tipo"}], "conta": {"blocca": 1, "guarda": 2, "info": 0}, "pronto": False}
    S.controllo(r, 0.3, 5); c = eventi()[-2]
    assert c["ev"] == "controllo" and c["tipi"] == {"altro": 1, "risoluzione": 2} and (c["blocca"], c["guarda"], c["spread"], c["pronto"]) == (1, 2, 5, False)
    S.esportazione({"formato": "jpg", "totale": 3, "fatti": 3, "saltati": [{"spread": 1, "motivo": "ZQX"}], "errori": ["ZQX"]}, 4)
    e = eventi()[-2]; assert e["ev"] == "esportazione" and (e["saltati"], e["errori"], e["filigrana"], e["ms"]) == (1, 1, False, 4000) and eventi()[-1]["nome"] == "prima_esportazione"
    S.esportazione({"formato": "progetto", "totale": 1, "fatti": 1, "saltati": [], "errori": []}, 1); assert "filigrana" not in eventi()[-1]
    S.esportazione({"formato": "consegna", "totale": 1, "fatti": 1, "saltati": [], "errori": []}, 1); assert eventi()[-1]["nome"] == "prima_consegna"
    S.esportazione({"formato": "zqx", "totale": 1, "fatti": 0, "saltati": [], "errori": []}, 1); assert eventi()[-1]["formato"] == "altro"
    S.importazione("progetto_zip"); assert "foto" not in eventi()[-1] and "ms" not in eventi()[-1]
    S.importazione("foto", 4, 1, 0.5); assert eventi()[-1]["ev"] == "importazione" or eventi()[-1]["nome"] == "prime_foto"
    S.preparazione(10, 10, 2.5, False); assert eventi()[-1]["ms"] == 2500


def test_album_nuovo_legge_solo_le_misure(licenza, home):
    beta(licenza); S.imposta(True)
    p = home.nuovo({"nome": "Sposi ZQX", "w": "60", "h": "22,5"}); S.album_nuovo(p, False)
    e = [x for x in eventi() if x["ev"] == "album_nuovo"][0]
    assert {k: v for k, v in e.items() if k not in schema.BUSTA} == {"larghezza_cm": 60.0, "altezza_cm": 22.5, "cartella_foto": False, "catalogo": False}


# ---------------------------------------------------------------- errori
def _solleva_dentro():
    return schema.valore(schema.INTERO, "ZQX /home/zqx", "campo")


def test_errori_con_tipo_e_punto_mai_il_messaggio(licenza):
    beta(licenza); S.imposta(True)
    try: _solleva_dentro()
    except schema.FuoriSchema as e: dove, riga, origine = S.punto(e)
    assert dove == "impaginatore.statistiche.schema:_intero" and riga > 0 and origine == "impaginatore"
    try: json.loads("{ZQX")
    except ValueError as e:
        assert S.punto(e) == ("<ignoto>", None, "json")
        S.errore(e); assert len([x for x in eventi() if x["ev"] == "errore"]) == 0, "un ValueError è una richiesta rifiutata, non un errore"
        S.errore(e, attesi=True)
    S.errore(OSError(errno.ENOSPC, "No space left on device", "/home/ZQX/Clienti/foto.jpg"))
    S.errore(type("Errore ZQX", (Exception,), {})("ZQX"))
    err = [x for x in eventi() if x["ev"] == "errore"]
    assert err[0]["tipo"] == "JSONDecodeError" and err[0]["origine"] == "json" and err[0]["dove"] == "<ignoto>"
    assert err[1]["tipo"] == "OSError" and err[1]["errno"] == "ENOSPC" and err[2]["tipo"] == "<ignoto>"
    assert "ZQX" not in open(os.path.join(S.cartella(), S.EVENTI)).read()


# ---------------------------------------------------------------- per la pagina
def test_registro_esporta_cancella(licenza, tmp_path):
    beta(licenza)
    with pytest.raises(ValueError, match="vuoto"): S.esporta(str(tmp_path))
    S.imposta(True)
    for _ in range(5): S.evento("chiusura", durata_s=1)
    r = S.righe(3); assert r["totale"] == 7 and len(r["righe"]) == 3 and json.loads(r["righe"][-1])["ev"] == "chiusura"
    with pytest.raises(ValueError, match="non c'è più"): S.esporta(str(tmp_path / "manca"))
    f = S.esporta(str(tmp_path))
    assert os.path.dirname(f) == str(tmp_path) and re.fullmatch(r"impaginatore-statistiche-[0-9a-f]{8}-\d{8}-\d{6}\.jsonl", os.path.basename(f))
    assert stat.S_IMODE(os.stat(f).st_mode) == 0o600 or os.name == "nt"
    assert open(f).read().split("\n")[:-1] == S._righe_grezze()
    vecchio = S.identificativo(); S.azzera_identificativo(); S.evento("chiusura", durata_s=1)
    with open(os.path.join(S.cartella(), S.EVENTI), "a") as h: h.write("non json\n[1]\n" + json.dumps({"id": "ZQX"}) + "\n")
    dest = invio.Cartella(str(tmp_path / "server"))
    filo = S.cancella(dest); filo.join(5)
    assert S.stato()["eventi"] == 0 and S.attive() and S.identificativo(), "restano la scelta e l'identificativo"
    req = json.loads(open(tmp_path / "server" / "0001-cancella.json").read())
    assert req == {"formato": 1, "azione": "cancella", "ids": sorted([vecchio, S.identificativo()])}
    assert S.cancella() is None, "senza server la cancellazione è solo qui"
    os.remove(os.path.join(S.cartella(), S.INSTALLAZIONE)); assert S.cancella(dest) is None, "niente identificativi: niente da chiedere"


def test_chiedere_solo_con_la_beta_attiva(licenza):
    assert not S.chiedere()
    beta(licenza); assert S.chiedere()
    beta(licenza, scadenza="2026-11-10", emessa="2026-11-01"); assert not S.chiedere(), "beta finita: non si chiede più"
    beta(licenza); S.imposta(False); assert not S.chiedere()


# ---------------------------------------------------------------- invio
class Risposta:
    def __init__(self, status): self.status = status
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_https_manda_json_senza_cookie_ne_gettoni():
    chiamate = []

    def apri(rq, timeout):
        chiamate.append((rq, timeout)); return Risposta(204)
    d = invio.HTTPS("https://statistiche.esempio.invalid/v1", apri=apri)
    d.invia([{"ev": "chiusura"}]); d.cancella({"b" * 32, "a" * 32})
    rq, timeout = chiamate[0]
    assert rq.get_method() == "POST" and rq.full_url == "https://statistiche.esempio.invalid/v1" and timeout == invio.TIMEOUT
    assert {k.lower(): v for k, v in rq.header_items()} == {"content-type": "application/json", "user-agent": f"Impaginatore/{S.__version__}"}
    assert json.loads(rq.data) == {"formato": 1, "azione": "eventi", "eventi": [{"ev": "chiusura"}]}
    assert json.loads(chiamate[1][0].data)["ids"] == ["a" * 32, "b" * 32]
    with pytest.raises(invio.ErroreInvio, match="HTTP 500"): invio.HTTPS("https://x.invalid/", apri=lambda rq, timeout: Risposta(500)).invia([])
    for e in (urllib.error.URLError("no"), ConnectionResetError(), ValueError("x"), __import__("http.client").client.RemoteDisconnected()):
        def male(rq, timeout, e=e): raise e
        with pytest.raises(invio.ErroreInvio) as x: invio.HTTPS("https://x.invalid/", apri=male).invia([])
        assert str(x.value) == type(e).__name__, "solo il tipo dell'errore"


def test_https_controlla_indirizzo_certificato_proxy_e_reindirizzamenti(monkeypatch):
    for cattivo in ("http://x.it/", "https:///x", "https://utente:pw@x.it/", "ftp://x.it", ""):
        with pytest.raises(ValueError): invio.HTTPS(cattivo)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    lontano = invio.HTTPS("https://statistiche.esempio.invalid/v1")
    assert lontano.contesto.verify_mode == ssl.CERT_REQUIRED and lontano.contesto.check_hostname
    gestori = lontano._apri.__self__.handlers
    assert any(isinstance(h, invio._SenzaReindirizzi) for h in gestori) and not any(type(h) is urllib.request.HTTPRedirectHandler for h in gestori)
    assert any(isinstance(h, urllib.request.HTTPSHandler) and h._context is lontano.contesto for h in gestori)
    assert any(isinstance(h, urllib.request.ProxyHandler) and "https" in h.proxies for h in gestori), "un server vero: il proxy della rete, se c'è"
    vicino = invio.HTTPS("https://127.0.0.1:9/v1")
    assert not any(isinstance(h, urllib.request.ProxyHandler) for h in vicino._apri.__self__.handlers), "un indirizzo locale: mai un proxy"
    assert invio._SenzaReindirizzi().redirect_request(None, None, 302, "", {}, "https://altro/") is None
    assert invio.locale("localhost") and invio.locale("127.0.0.2") and invio.locale("::1") and not invio.locale("esempio.it") and not invio.locale(None)


def test_https_vero_verso_questo_computer_senza_proxy(monkeypatch):
    """una richiesta vera su 127.0.0.1 (nessuna rete): il proxy dell'ambiente non si usa e un server senza TLS non passa"""
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9"); monkeypatch.setenv("https_proxy", "http://127.0.0.1:9")
    s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(1); s.settimeout(10); arrivate = []

    def servi():
        try:
            c, _ = s.accept(); arrivate.append(c.recv(5)); c.sendall(b"HTTP/1.1 200 OK\r\n\r\n"); c.close()
        except OSError: pass
    t = threading.Thread(target=servi, daemon=True); t.start()
    with pytest.raises(invio.ErroreInvio): invio.HTTPS(f"https://127.0.0.1:{s.getsockname()[1]}/v1").invia([{"ev": "chiusura"}])
    t.join(10); s.close()
    assert arrivate and arrivate[0][:1] == b"\x16", "è arrivato l'inizio di una stretta di mano TLS, direttamente (senza proxy)"


def test_destinazione_e_lotti(monkeypatch):
    assert invio.destinazione() is None and not invio.attivo()
    monkeypatch.setattr(invio, "INDIRIZZO", "https://statistiche.esempio.invalid/v1")
    assert isinstance(invio.destinazione(), invio.HTTPS) and invio.attivo()
    monkeypatch.setattr(invio, "LOTTO_EVENTI", 3)
    assert [len(x) for x in invio.lotti(["x" * 10] * 7)] == [3, 3, 1]
    monkeypatch.setattr(invio, "LOTTO_BYTE", 25)
    assert [len(x) for x in invio.lotti(["x" * 10] * 5)] == [2, 2, 1] and list(invio.lotti([])) == []


def test_tentativi(monkeypatch):
    pause = []
    monkeypatch.setattr(invio, "time", types.SimpleNamespace(sleep=pause.append, time=time.time))
    esiti = [invio.ErroreInvio("x"), invio.ErroreInvio("y"), None]

    def fn():
        e = esiti.pop(0)
        if e: raise e
    assert invio.con_tentativi(fn) and pause == [5, 30]
    def sempre(): raise invio.ErroreInvio("x")
    pause.clear(); assert not invio.con_tentativi(sempre) and pause == [5, 30]
    fermo = threading.Event(); fermo.set(); assert not invio.con_tentativi(sempre, fermo), "chi chiude il programma non aspetta"
    assert invio.con_tentativi(lambda: None)


def test_giro_a_lotti_riprende_da_dove_era(tmp_path, monkeypatch):
    monkeypatch.setattr(invio, "LOTTO_EVENTI", 2); monkeypatch.setattr(invio, "ATTESE", (0, 0))
    d = tmp_path / "s"; d.mkdir(); assert invio.giro(invio.Cartella(str(tmp_path / "srv")), str(d)) == 0
    righe = [json.dumps({"n": i}) for i in range(5)]
    (d / invio.CODA).write_text("\n".join(righe[:2] + ["rotta", "{"] + righe[2:]) + "\n")
    arrivati, guasto = [], [False]

    class Dest(invio.Destinazione):
        def invia(self, ev):
            if guasto[0] and any(e["n"] == 3 for e in ev): raise invio.ErroreInvio("giù")
            arrivati.append([e["n"] for e in ev])
    guasto[0] = True
    assert invio.giro(Dest(), str(d)) == 2 and arrivati == [[0, 1]] and (d / invio.IN_INVIO).exists()
    (d / invio.CODA).write_text(json.dumps({"n": 9}) + "\n")
    guasto[0] = False
    assert invio.giro(Dest(), str(d)) == 3 and arrivati == [[0, 1], [2, 3], [4]], "le righe rotte si saltano, i lotti arrivati non si rimandano"
    assert not (d / invio.IN_INVIO).exists() and not (d / invio.PROGRESSO).exists() and (d / invio.CODA).exists()
    assert invio.giro(Dest(), str(d)) == 1 and arrivati[-1] == [9]
    for p in ("[1]", "{rotto", json.dumps({"inviati": -3})):
        (d / invio.PROGRESSO).write_text(p); assert invio._leggi_progresso(str(d / invio.PROGRESSO)) == 0
    with pytest.raises(NotImplementedError): invio.Destinazione().invia([])
    with pytest.raises(NotImplementedError): invio.Destinazione().cancella([])


def test_invio_con_un_server_finto(licenza, monkeypatch, tmp_path):
    """con un indirizzo, il registro va anche in coda e parte a giri; con la coda piena gli eventi restano solo nel registro"""
    beta(licenza)
    assert S.giro_invio() == 0, "senza server: niente giri"
    monkeypatch.setattr(invio, "INDIRIZZO", "https://statistiche.esempio.invalid/v1"); S.imposta(True)
    srv = invio.Cartella(str(tmp_path / "srv"))
    assert S.giro_invio(srv) == 2 and S.stato()["invio"]["in_coda"] == 0 and S.stato()["invio"]["server"] == "statistiche.esempio.invalid"
    monkeypatch.setattr(S, "MAX_CODA", 1); S.evento("chiusura", durata_s=1); S.evento("chiusura", durata_s=2)
    assert S.giro_invio(srv) == 1 and len(eventi()) == 4
    S.imposta(False); S.evento("chiusura", durata_s=1); assert S.giro_invio(srv) == 0
    lotti = [json.loads(open(os.path.join(tmp_path / "srv", f)).read()) for f in sorted(os.listdir(tmp_path / "srv"))]
    assert [len(x["eventi"]) for x in lotti] == [2, 1] and all(schema.controlla_riga(e) is None for x in lotti for e in x["eventi"])


def test_ciclo_e_avvio_dell_invio(licenza, monkeypatch):
    fermo = threading.Event()
    assert S.avvia_invio(fermo) is None, "oggi: nessun thread, nessuna rete"
    giri = []
    monkeypatch.setattr(S, "giro_invio", lambda fermo=None: giri.append(fermo))

    class Fermo:
        n = 0
        def wait(self, s): self.n += 1; return self.n > 2
    f = Fermo(); S.ciclo_invio(f, 0); assert giri == [f, f]
    monkeypatch.setattr(invio, "INDIRIZZO", "https://statistiche.esempio.invalid/v1"); fermo.set()
    t = S.avvia_invio(fermo); t.join(5); assert not t.is_alive()


def test_nessuna_richiesta_di_rete_senza_indirizzo(licenza, monkeypatch, tmp_path, home_srv):
    """il rilascio di oggi: INDIRIZZO vuoto. Nessuna funzione delle statistiche apre una connessione, accese o spente"""
    assert invio.INDIRIZZO == "" or os.environ.get("IMPAGINATORE_STATISTICHE_SERVER_DECISO"), "il server si accende con una decisione del titolare (DA-DECIDERE.md)"
    fuori = []
    connetti, indirizzi = socket.socket.connect, socket.getaddrinfo

    def connect(self, a):
        if not (isinstance(a, tuple) and a[0] in ("127.0.0.1", "::1")): fuori.append(a)
        return connetti(self, a)

    def getaddrinfo(host, *a, **k):
        if host not in ("127.0.0.1", "localhost", "::1"): fuori.append(host)
        return indirizzi(host, *a, **k)
    monkeypatch.setattr(socket.socket, "connect", connect); monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    beta(licenza); home_srv.post("/api/statistiche/consenso", {"si": True})
    for _ in range(3): S.evento("chiusura", durata_s=1)
    S.giro_invio(); assert S.avvia_invio(threading.Event()) is None and S.cancella() is None
    home_srv.post("/api/statistiche/cancella"); S.svuota(); S.chiusura()
    assert fuori == []
    assert not os.path.exists(os.path.join(S.cartella(), invio.CODA)), "senza server non c'è nemmeno la coda"


# ---------------------------------------------------------------- schermata Album
def test_richieste_della_schermata(home_srv, licenza, monkeypatch, tmp_path):
    h = home_srv
    st = h.get("/api/statistiche"); assert not st["disponibili"] and not st["chiedere"]
    beta(licenza); st = h.get("/api/statistiche"); assert st["chiedere"] and st["disponibili"] and st["serie"] == 7
    ok, r = h.prova("/api/statistiche/consenso", {"si": "forse"}); assert not ok and "sì o no" in r["errore"]
    st = h.post("/api/statistiche/consenso", {"si": True}); assert st["attive"] and st["eventi"] == 2
    h.post("/api/statistiche/finestra", {"larghezza": 1440, "altezza": 900, "scala": 2, "schermo_larghezza": 2880, "schermo_altezza": 1800})
    reg = h.get("/api/statistiche/registro"); assert reg["totale"] == 3 and json.loads(reg["righe"][-1])["pagina"] == "album"
    vecchio = st["id"]; st = h.post("/api/statistiche/azzera"); assert st["id"] != vecchio
    assert h.post("/api/statistiche/esporta") == {"annullato": True}, "nessuna cartella scelta"
    monkeypatch.setattr(h.modulo, "scegli_cartella", lambda msg=None: str(tmp_path))
    f = h.post("/api/statistiche/esporta")["file"]; assert os.path.dirname(f) == str(tmp_path)
    st = h.post("/api/statistiche/cancella"); assert st["eventi"] == 0 and st["attive"]
    assert h.codice("/api/statistiche/altro", {}) == 404
    st = h.post("/api/statistiche/consenso", {"si": False}); assert not st["attive"]


def test_schermata_annota_album_licenza_importazioni_ed_errori(home_srv, licenza, monkeypatch, tmp_path):
    h = home_srv; testo = beta(licenza); h.post("/api/statistiche/consenso", {"si": True})
    p = h.post("/api/nuovo", {"nome": "Sposi ZQX", "w": "30", "h": "20"})["path"]
    licenza.usa(None); h.post("/api/licenza/attiva", {"chiave": testo}); h.post("/api/licenza/rimuovi")
    licenza.usa(testo)
    monkeypatch.setattr(h.modulo, "importa_zip", lambda: p)
    monkeypatch.setattr(h.modulo.dialoghi, "scegli_catalogo", lambda *a: "/x/ZQX.json")
    monkeypatch.setattr(h.modulo.laboratori, "importa", lambda p: {"nome": "ZQX", "prodotti": 1, "verificato": True})
    h.post("/api/importa-zip"); h.post("/api/importa-catalogo")
    monkeypatch.setattr(h.modulo, "importa_zip", lambda: ""); monkeypatch.setattr(h.modulo.dialoghi, "scegli_catalogo", lambda *a: "")
    h.post("/api/importa-zip"); h.post("/api/importa-catalogo")
    monkeypatch.setattr(h.modulo, "lingue", lambda: (_ for _ in ()).throw(KeyError("ZQX")))
    assert h.codice("/api/lingua") == 400
    monkeypatch.setattr(h.modulo, "registro", lambda: (_ for _ in ()).throw(RuntimeError("/x/ZQX")))
    assert h.codice("/api/rimuovi", {"path": "x"}) == 400
    h.post("/api/esci")
    ev = eventi(); n = nomi(ev)
    assert n.count("album_nuovo") == 1 and [e["azione"] for e in ev if e["ev"] == "licenza"] == ["attivata", "tolta"]
    assert [e["tipo"] for e in ev if e["ev"] == "importazione"] == ["progetto_zip", "catalogo"]
    assert [(e["tipo"], e["dove"]) for e in ev if e["ev"] == "errore"] == [("KeyError", "impaginatore.home.server:do_GET"), ("RuntimeError", "impaginatore.home.server:do_POST")]
    assert n[-1] == "chiusura", "prima di uscire"
    assert "ZQX" not in "\n".join(S._righe_grezze())


def test_main_della_schermata_annota_avvio_e_chiusura(licenza, monkeypatch, tmp_path):
    from impaginatore.home import server as H
    beta(licenza); S.imposta(True)
    monkeypatch.setattr(H.desktop, "motore", lambda: None)

    class Srv:
        indirizzo_avvio = lambda self: "http://x"
        def serve_forever(self): raise KeyboardInterrupt
        def server_close(self): pass
    monkeypatch.setattr(H, "crea_server", lambda *a: Srv())
    assert H.main(["--porta", "0", "--progetti", str(tmp_path / "P"), "--no-browser"]) == 0
    assert nomi()[-2:] == ["avvio", "chiusura"] and eventi()[-1]["proc"] == "home" and eventi()[-2]["finestra_programma"] is False
    monkeypatch.setattr(H.desktop, "motore", lambda: object()); monkeypatch.setattr(H.desktop, "gettone", lambda: None)
    monkeypatch.setattr(H.desktop, "esegui", lambda m, srv, fermo: 5)
    assert H.main(["--porta", "0", "--progetti", str(tmp_path / "P")]) == 5
    assert nomi()[-2:] == ["avvio", "chiusura"] and eventi()[-2]["finestra_programma"] is True


# ---------------------------------------------------------------- editor
def test_editor_spento_non_scrive_niente(editor):
    c = editor
    p = c.post("/api/bozza", {}); c.post("/api/op", {"op": "bozza", "spreads": p["spreads"]})
    c.post("/api/controlla", {}); c.post("/api/statistiche/finestra", {"larghezza": 1})
    assert not os.path.exists(S.cartella())


def test_le_statistiche_non_rompono_le_operazioni(editor, licenza, monkeypatch):
    beta(licenza); S.imposta(True); c = editor
    monkeypatch.setattr(S, "_scrivi", lambda r: (_ for _ in ()).throw(OSError(errno.ENOSPC, "pieno")))
    monkeypatch.setattr(S, "_OPS", {"cartella": None, "conti": None})          # conti rotti: l'operazione si conta male, ma si fa
    p = c.post("/api/bozza", {}); assert p["foto"] == 10
    st = c.post("/api/op", {"op": "newspreadsel", "names": ["H01"], "pos": 0}); assert len(st["spreads"]) == 1
    assert c.post("/api/controlla", {})["conta"] is not None


def _foto_con_nomi(foto_campione, cartella):
    os.makedirs(cartella, exist_ok=True)
    for f in sorted(os.listdir(foto_campione)): shutil.copy2(os.path.join(foto_campione, f), os.path.join(cartella, "ZQX_" + f))
    return cartella


def test_nessun_nome_riconoscibile_nel_registro(home_srv, apri_editor, licenza, foto_campione, monkeypatch, tmp_path):
    """album, cartelle, foto, testi, intestatario e cliente con un segno riconoscibile («ZQX»): dopo un giro completo
    (album nuovo, editor, bozza, testi, controllo, esportazione, importazione, errori con percorsi nel messaggio) nel
    registro e nel file esportato non c'è nessun «ZQX», nessun percorso, nessun nome di foto"""
    h = home_srv; testo = beta(licenza, intestatario="Studio ZQX Rossi")
    h.post("/api/statistiche/consenso", {"si": True})
    licenza.usa(None); h.post("/api/licenza/attiva", {"chiave": testo})
    foto = _foto_con_nomi(foto_campione, str(tmp_path / "Clienti ZQX" / "Sposi ZQX Bianchi"))
    h.modulo.RADICI.scelta(foto)
    p = h.post("/api/nuovo", {"nome": "Matrimonio ZQX", "foto": foto, "w": "60", "h": "22,5"})["path"]
    h.post("/api/statistiche/finestra", {"larghezza": 1200, "titolo": "ZQX"})
    c = apri_editor(p); E = c.E
    c.post("/api/statistiche/finestra", {"larghezza": 1600, "altezza": 1000, "nome": "ZQX"})
    b = c.post("/api/bozza", {"ritmo": "piene"})
    c.post("/api/op", {"op": "bozza", "spreads": b["spreads"], "cid": "assistente-1"})
    c.post("/api/op", {"op": "testo", "nome": "Sposi ZQX", "data": "2026"})
    assert not c.prova("/api/op", {"op": "swap", "a": "ZQX_H01.jpg"})[0]
    assert not c.prova("/api/op", {"op": "ZQX_op"})[0]
    c.post("/api/op", {"op": "undo"}); c.post("/api/op", {"op": "redo"})
    vera = E.valida
    monkeypatch.setattr(E, "valida", lambda o: (_ for _ in ()).throw(RuntimeError(f"rotto {foto}/ZQX_H01.jpg")))
    assert not c.prova("/api/op", {"op": "swap"})[0]
    monkeypatch.setattr(E, "valida", vera)
    c.post("/api/controlla", {})
    c.post("/api/export", {"fmt": "jpg", "res": "bozza", "range": "1"})
    from aiuti import attendi_log
    attendi_log(c)
    nuove = _foto_con_nomi(foto_campione, str(tmp_path / "Altre ZQX"))
    E.RADICI.scelta(nuove); c.post("/api/import", {"paths": [nuove], "a_caldo": True})
    assert c.codice("/api/reveal", {"foto": "ZQX_manca.jpg"}) in (400, 404)
    E.ferma(); S.chiusura()
    monkeypatch.setattr(h.modulo, "scegli_cartella", lambda msg=None: str(tmp_path))
    f = h.post("/api/statistiche/esporta")["file"]
    testo_reg = "\n".join(S._righe_grezze()); esportato = open(f, encoding="ascii").read()
    for t in (testo_reg, esportato):
        for segno in ("ZQX", "Rossi", "Bianchi", "Matrimonio", "Sposi", "Studio", str(tmp_path), "Clienti", ".jpg", "H01", "/", "\\"):
            assert segno not in t, segno
    ev = eventi()
    for e in ev: schema.controlla_riga(e)
    visti = set(nomi(ev))
    assert visti >= {"consenso", "avvio", "licenza", "album_nuovo", "finestra", "album_aperto", "bozza_proposta", "bozza_accettata", "operazioni",
                     "primo_spread", "controllo", "esportazione", "importazione", "errore", "traguardo", "chiusura"}, visti
    ops = {e["op"]: e for e in ev if e["ev"] == "operazioni"}
    assert ops["bozza"]["assistente"] == 1 and ops["altro"]["rifiutate"] == 1 and ops["swap"]["rifiutate"] >= 1 and ops["swap"]["errori"] == 1 and "undo" in ops
    esp = next(e for e in ev if e["ev"] == "esportazione"); assert esp["formato"] == "jpg" and esp["fatti"] == 1 and esp["ms"] > 0
    assert next(e for e in ev if e["ev"] == "bozza_proposta")["ritmo"] == "piene"
    assert next(e for e in ev if e["ev"] == "album_nuovo")["cartella_foto"] is True
    assert all(e.get("serie") == 7 for e in ev), "con la licenza beta: il numero di serie, mai l'intestatario"


def test_editor_annota_preparazione_e_chiusura(editor, licenza, monkeypatch):
    beta(licenza); S.imposta(True); E = editor.E
    monkeypatch.setattr(E, "_prepara_foto", lambda *a: {})
    monkeypatch.setattr(E, "_volti_pronti", lambda t: None)
    E._prepara(E.PREP["gen"], ["a", "b"], ["a"], "x"); p = eventi()[-1]
    assert p["ev"] == "preparazione" and (p["miniature"], p["volti"], p["interrotta"]) == (2, 1, False)
    monkeypatch.setattr(E, "_prepara_foto", lambda *a: (_ for _ in ()).throw(OSError(errno.ENOSPC, "pieno /ZQX")))
    E._prepara(E.PREP["gen"], ["a"], [], "x")
    assert eventi()[-1]["interrotta"] is True and eventi()[-2]["errno"] == "ENOSPC"
    E._prepara(E.PREP["gen"] - 1, [], [], "x"); assert eventi()[-1]["interrotta"] is True, "il progetto è cambiato intanto"
    S.operazione("swap", 0.1); n = len(eventi()); E.ferma(); assert nomi(eventi()[n:]) == ["operazioni"]


def test_riavvio_dell_editor_scrive_i_conteggi(licenza, monkeypatch):
    from impaginatore.editor import server as E
    beta(licenza); S.imposta(True); S.operazione("swap", 0.1); riavvii = []
    monkeypatch.setattr(E.processi, "riesegui", lambda: riavvii.append(nomi()[-1]))
    E.riavvia_processo(); assert riavvii == ["operazioni"]
