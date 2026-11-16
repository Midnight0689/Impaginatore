"""Schermata dei progetti: elenco, nuovo progetto, apertura, importazione ZIP, cestino, aggiornamenti (nel processo dei test;
l'editor vero parte come processo a parte solo in test_processi.py)."""
import json
import os
import sys
import time
import types
import zipfile

import pytest

from impaginatore import aggiornamenti
from impaginatore.piattaforma import azioni, dialoghi


class Finti(dialoghi.Dialoghi):
    def __init__(self, risposte): self.risposte = list(risposte)

    def _scegli(self, tipo, messaggio): return [self.risposte.pop(0)] if self.risposte else []


def test_pagina_ed_elenco(home_srv):
    c = home_srv
    html = c.raw("/").decode("utf-8"); assert '<script nonce="' in html and "__NONCE__" not in html and c.gettone not in html, "il gettone arriva dalla sessionStorage (VER-006)"
    assert c.get("/api/ping") == {"ok": True}
    r = c.get("/api/progetti"); assert r["progetti"] == [] and r["cartella"] == c.modulo.PROGETTI
    a = c.get("/api/aggiornamento"); assert a["attuale"]["rel"] and not a["da_aggiornare"]
    assert a["errore"] == "" and a["disponibile"] is False and "non disponibili" in a["motivo"], "spenti non è un errore di rete"
    assert c.get("/api/versioni") == {"versioni": []} and c.post("/api/controlla")["motivo"]
    ok, r = c.prova("/api/aggiorna", {}); assert not ok and "non disponibili" in r["errore"].lower()
    ok, r = c.prova("/api/ripristina", {"codice": "abc1234"}); assert not ok
    ok, r = c.prova("/api/boh"); assert not ok and r["errore"] == "non trovato"
    ok, r = c.prova("/api/boh", {}); assert not ok


def test_nuovo_progetto(home_srv, tmp_path):
    c = home_srv
    p = c.post("/api/nuovo", {"nome": "Sposi: A/B", "w": "30,5", "h": 30, "abb": "3"})["path"]
    assert os.path.basename(p) == "Sposi- A-B" and os.path.isdir(os.path.join(p, "Foto"))
    with open(os.path.join(p, "progetto.json"), encoding="utf-8") as f: cfg = json.load(f)
    assert cfg["formato_cm"] == [30.5, 30.0] and cfg["abbondanza_mm"] == 3.0 and cfg["foto"] == os.path.join(p, "Foto")
    assert c.post("/api/nuovo", {"nome": "Sposi: A/B", "w": 30, "h": 30})["path"].endswith("Sposi- A-B 2")
    for d, msg in (({"nome": "", "w": 1, "h": 1}, "nome"), ({"nome": "X", "w": 1, "h": 30}, "Misure"), ({"nome": "X", "w": "a", "h": 30}, "could not convert"), ({"nome": "X", "w": -3, "h": 30}, "misura")):
        ok, r = c.prova("/api/nuovo", d); assert not ok and msg in r["errore"], r
    # progetto accanto alle foto del cliente: <cartella>/Impaginatore, foto lasciate dove sono, in registro
    cli = tmp_path / "Cliente"; cli.mkdir()
    ok, r = c.prova("/api/nuovo", {"nome": "Cliente", "w": 30, "h": 30, "foto": str(cli)}); assert not ok and "Scegli" in r["errore"], "cartella non scelta con la finestra"
    dialoghi.imposta(Finti([str(cli)])); assert c.post("/api/scegli-foto")["path"] == str(cli)
    p2 = c.post("/api/nuovo", {"nome": "Cliente", "w": 30, "h": 30, "foto": str(cli) + os.sep})["path"]
    assert p2 == str(tmp_path / "Impaginatore"), "accanto alla cartella delle foto"
    ok, r = c.prova("/api/nuovo", {"nome": "X", "w": 30, "h": 30, "foto": str(tmp_path / "no")}); assert not ok
    el = c.get("/api/progetti")["progetti"]
    assert {x["nome"] for x in el} == {"Sposi: A/B", "Cliente"} and len(el) == 3 and any(x["esterno"] for x in el)
    c.post("/api/rimuovi", {"path": p2}); assert len(c.get("/api/progetti")["progetti"]) == 2


def test_elenco_con_progetto_rovinato(home_srv):
    c = home_srv
    p = c.post("/api/nuovo", {"nome": "Rotto", "w": 30, "h": 30})["path"]
    with open(os.path.join(p, "progetto.json"), "w", encoding="utf-8") as f: f.write("{non json")
    el = c.get("/api/progetti")["progetti"]; assert el[0]["errore"] and el[0]["nome"] == "Rotto"


def test_copertina(home_srv, editor):
    c = home_srv
    el = c.get("/api/progetti")["progetti"]; x = next(e for e in el if e["nome"] == "Prova")
    assert x["foto"] == 10 and x["cover"] and x["spread"] == 0
    q = f"/api/cover?path={x['path']}&n={x['cover']}"
    assert c.raw(q.replace(" ", "%20"))[:2] == b"\xff\xd8"
    for n in ("../progetto.json", "..\\progetto.json", ".."):
        ok, _ = c.prova(f"/api/cover?path={x['path']}&n={n}".replace(" ", "%20")); assert not ok
    ok, _ = c.prova("/api/cover?path=/tmp&n=a.jpg"); assert not ok


def test_aggiungi_e_scegli_foto(home_srv, tmp_path):
    c = home_srv
    assert c.post("/api/aggiungi") == {"annullato": True}
    altro = tmp_path / "Altro"; altro.mkdir()
    dialoghi.imposta(Finti([str(altro)]))
    ok, r = c.prova("/api/aggiungi", {}); assert not ok and "progetto.json" in r["errore"]
    (altro / "progetto.json").write_text(json.dumps({"nome": "Altro", "formato_cm": [20, 20]}), encoding="utf-8")
    dialoghi.imposta(Finti([str(altro) + "/"]))
    assert c.post("/api/aggiungi")["path"] == str(altro)
    assert any(p["path"] == str(altro) for p in c.get("/api/progetti")["progetti"])
    dialoghi.imposta(Finti([str(tmp_path)]))
    assert c.post("/api/scegli-foto")["path"] == str(tmp_path)


def test_importa_zip(home_srv, tmp_path):
    c = home_srv
    assert c.post("/api/importa-zip") == {"annullato": True}
    zp = tmp_path / "Album Rossi - progetto.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("Album Rossi - progetto/progetto.json", json.dumps({"nome": "Rossi", "formato_cm": [30, 30], "foto": ""}))
        z.writestr("Album Rossi - progetto/spec.py", "from album import *\nSPREADS = []\n")
    dialoghi.imposta(Finti([str(zp), str(zp)]))
    p = c.post("/api/importa-zip")["path"]; assert os.path.basename(p) == "Album Rossi - progetto" and os.path.exists(os.path.join(p, "spec.py"))
    assert c.post("/api/importa-zip")["path"].endswith(" 2")
    vuoto = tmp_path / "vuoto.zip"
    with zipfile.ZipFile(vuoto, "w") as z: z.writestr("leggimi.txt", "x")
    dialoghi.imposta(Finti([str(vuoto)]))
    ok, r = c.prova("/api/importa-zip", {}); assert not ok and "progetto.json" in r["errore"]
    assert not os.path.exists(os.path.join(c.modulo.PROGETTI, ".importazione"))


def test_cestino_e_finder(home_srv, tmp_path, monkeypatch):
    c = home_srv; fatti = []
    monkeypatch.setattr(azioni, "cestina", lambda p: fatti.append(("cestino", p)))
    monkeypatch.setattr(azioni, "mostra", lambda p: fatti.append(("mostra", p)))
    p = c.post("/api/nuovo", {"nome": "Via", "w": 30, "h": 30})["path"]
    assert c.post("/api/cestino", {"path": p}) == {"ok": True}
    ok, r = c.prova("/api/cestino", {"path": str(tmp_path)}); assert not ok and "Cestino" in r["errore"]
    c.post("/api/finder", {"path": p})
    assert fatti == [("cestino", p), ("mostra", p)]


def test_apri_non_in_elenco(home_srv, tmp_path):
    ok, r = home_srv.prova("/api/apri", {"path": str(tmp_path)}); assert not ok and "elenco" in r["errore"]
    assert home_srv.get("/api/pronto?porta=9") == {"pronto": False, "indirizzo": None}


def test_apri_riusa_editor_gia_attivo(home_srv, editor):
    """se un editor di quel progetto risponde già (anche non lanciato da qui) si usa quello"""
    import threading
    c = home_srv; pt = c.modulo.porta_stabile(editor.progetto)
    if not c.modulo.porta_libera(pt) == pt: pytest.skip(f"porta {pt} occupata")
    srv = editor.E.crea_server(pt); threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        assert c.post("/api/apri", {"path": editor.progetto})["porta"] == pt and not c.modulo.EDITORS
        r = c.get(f"/api/pronto?porta={pt}"); assert r["pronto"] and r["indirizzo"].startswith(f"http://127.0.0.1:{pt}/avvio?c=")
    finally: srv.shutdown(); srv.server_close()


def test_esci(home_srv):
    from aiuti import attendi
    assert home_srv.post("/api/esci") == {"ok": True}
    attendi(lambda: home_srv.uscite, 30, 0.05)                           # il server esce poco dopo aver risposto (home/server.py)
    assert home_srv.uscite == [1]


class _Processo:
    """editor avviato dalla schermata (finto): poll() None = ancora aperto; terminate() può fallire se è già chiuso"""

    def __init__(self, fine=None, rotto=False): self.fine, self.rotto, self.fermato = fine, rotto, False

    def poll(self): return self.fine

    def terminate(self):
        if self.rotto: raise ProcessLookupError("già chiuso")
        self.fermato = True

    def wait(self, attesa=None): return 0                    # il riavvio dopo un aggiornamento aspetta la chiusura (desktop.finestra.chiudi_editor)


def test_apri_riusa_editor_lanciato_da_qui(home, monkeypatch):
    """apri: un editor del progetto lanciato da qui e ancora aperto si riusa; se è chiuso si cerca un editor già attivo"""
    p = home.nuovo({"nome": "Riuso", "w": 30, "h": 30})
    monkeypatch.setattr(home.subprocess, "Popen", lambda *a, **k: pytest.fail("nessun editor nuovo"))
    home.EDITORS[p] = (_Processo(), 8811)
    assert home.apri(p) == 8811
    home.EDITORS[p] = (_Processo(fine=0), 8811); monkeypatch.setattr(home, "gia_attivo", lambda path: 8822 if path == p else None)
    assert home.apri(p) == 8822


def test_editor_riavviato_in_un_processo_nuovo(home_srv, editor, monkeypatch):
    """su Windows l'editor che si riavvia (os.execv) è un processo nuovo e il figlio lanciato da qui finisce: si segue quello
    nuovo se il file di sessione della sua porta e /api/ping lo confermano (stesso progetto, stesso pid). L'editor nuovo qui è
    quello in questo processo; il processo seguito è finto (fermarlo fermerebbe i test)"""
    import subprocess

    from impaginatore import sicurezza
    from impaginatore.piattaforma import processi
    H = home_srv.modulo; seguiti = []

    class Seguito(_Processo):
        def __init__(self, pid, fine=None): super().__init__(fine); self.pid, self.uccisi = pid, 0; seguiti.append(self)
        def kill(self): self.uccisi += 1
    finito = subprocess.Popen([sys.executable, "-c", "pass"]); finito.wait()
    monkeypatch.setattr(processi, "Processo", Seguito)
    e = H.Editor(finito, editor.progetto, editor.porta)
    assert e.poll() is None and e.pid == os.getpid() and [s.pid for s in seguiti] == [os.getpid()], "segue l'editor nuovo"
    assert e.poll() is None and len(seguiti) == 1 and e.wait() == 0
    e.kill(); assert seguiti[0].uccisi == 1
    H.EDITORS[editor.progetto] = (e, editor.porta)
    assert home_srv.post("/api/esci") == {"ok": True} and seguiti[0].fermato, "«Esci» ferma l'editor nuovo"
    H.EDITORS.clear()
    # non si segue: altro progetto, nessuna sessione, stesso pid senza riavvio segnato, pid finito, porta chiusa, ping diverso,
    # processo finito (i file di sessione sono di editor partiti da tempo: non «in partenza»)
    vecchio = time.time() - H.ATTESA_RIAVVIO - 1
    assert H.Editor(finito, "/altro", editor.porta).poll() == 0 and H.Editor(finito, editor.progetto, 9).poll() == 0
    for pid in (finito.pid, 2**22 + 12345, os.getpid()):
        _sessione(9, progetto="/x", pid=pid, creato=vecchio); assert H.Editor(finito, "/x", 9).poll() == 0
    vero = sicurezza.chiedi
    for ping in ({"path": "/x", "pid": 1}, {"path": "/y", "pid": os.getpid()}, []):
        monkeypatch.setattr(sicurezza, "chiedi", lambda *a, ping=ping, **k: ping); assert H.Editor(finito, "/x", 9).poll() == 0
    monkeypatch.setattr(sicurezza, "chiedi", lambda *a, **k: {"path": "/x", "pid": os.getpid()})
    monkeypatch.setattr(processi, "Processo", lambda pid: Seguito(pid, fine=0))
    e = H.Editor(finito, "/x", 9); assert e.poll() == 0 and e.processo is finito
    e.terminate(); e.kill(); assert e.wait(1) == 0, "finito: niente da fermare"
    assert len(seguiti) > 1 and not any(s.fermato or s.uccisi for s in seguiti[1:]), "ogni volta si riprova, e un processo finito non si segue"
    monkeypatch.setattr(sicurezza, "chiedi", vero)


def _sessione(porta, **campi):
    """file di sessione di un editor sulla porta, con i campi dati al posto di quelli scritti da scrivi_sessione"""
    from impaginatore import sicurezza
    sicurezza.scrivi_sessione("editor", porta, "g")
    f = os.path.join(sicurezza.cartella_sessioni(), f"editor-{porta}.json")
    with open(f, encoding="utf-8") as fh: d = json.load(fh)
    with open(f, "w", encoding="utf-8") as fh: json.dump(dict(d, **campi), fh)


def test_editor_che_riparte_conta_come_aperto(home, monkeypatch):
    """Windows: tra la fine del figlio (os.execv) e la risposta dell'editor nuovo l'album resta aperto e «Apri» dà la stessa
    porta senza avviarne un secondo; fermato in quel momento, l'editor nuovo si ferma appena c'è. Un riavvio segnato da
    troppo tempo, o un figlio finito senza segnarlo, è un editor chiuso"""
    import subprocess

    from impaginatore import sicurezza
    from impaginatore.piattaforma import processi
    finito = subprocess.Popen([sys.executable, "-c", "pass"]); finito.wait()
    adesso, vecchio = time.time(), time.time() - home.ATTESA_RIAVVIO - 1
    p = home.nuovo({"nome": "Riparte", "w": 30, "h": 30})
    monkeypatch.setattr(home.subprocess, "Popen", lambda *a, **k: pytest.fail("nessun secondo editor"))
    monkeypatch.setattr(sicurezza, "chiedi", lambda *a, **k: (_ for _ in ()).throw(ConnectionRefusedError()))      # nessuno risponde ancora
    e = home.Editor(finito, p, 9); home.EDITORS[p] = (e, 9)
    _sessione(9, progetto=p, pid=finito.pid, riavvio=adesso)
    assert e.poll() is None and home.apri(p) == 9 and [x["aperto"] for x in home.progetti() if x["path"] == p] == [True], "il figlio ha segnato il riavvio"
    _sessione(9, progetto=p, pid=os.getpid()); assert e.poll() is None, "l'editor nuovo ha scritto la sessione e non risponde ancora"
    for campi in (dict(pid=finito.pid, riavvio=vecchio), dict(pid=finito.pid), dict(pid=finito.pid, riavvio="ieri"), dict(pid=os.getpid(), creato=vecchio),
                  dict(pid=2**22 + 12345), dict(pid=finito.pid, riavvio=adesso, progetto="/altro")):
        _sessione(9, **dict(dict(progetto=p), **campi)); assert e.poll() == 0, campi
    # fermato mentre riparte: wait aspetta l'editor nuovo; quando risponde si segue e si ferma subito
    _sessione(9, progetto=p, pid=finito.pid, riavvio=adesso)
    e.terminate(); assert e.fermato and e.poll() is None
    with pytest.raises(subprocess.TimeoutExpired): e.wait(0.3)
    seguiti = []
    monkeypatch.setattr(processi, "Processo", lambda pid: seguiti.append(_Processo()) or seguiti[-1])
    monkeypatch.setattr(sicurezza, "chiedi", lambda *a, **k: {"path": p, "pid": os.getpid()})
    _sessione(9, progetto=p, pid=os.getpid())
    assert e.wait(5) == 0 and seguiti[0].fermato and e.processo is seguiti[0]
    home.EDITORS.clear(); _sessione(9, progetto=p, pid=finito.pid)
    e = home.Editor(finito, p, 9); e.kill(); assert e.fermato and e.poll() == 0
    monkeypatch.setattr(home, "gia_attivo", lambda path: 8822)
    home.EDITORS[p] = (home.Editor(finito, p, 9), 9)
    assert home.apri(p) == 8822, "chiuso: si cerca un editor già attivo"
    home.EDITORS.clear()


def test_nuovo_con_cartella_foto_che_non_esiste(home, tmp_path):
    with pytest.raises(ValueError, match="La cartella delle foto non esiste"): home.nuovo({"nome": "X", "w": 30, "h": 30, "foto": str(tmp_path / "manca")})
    assert not os.path.exists(home.PROGETTI) or os.listdir(home.PROGETTI) == []


def test_nessuna_porta_libera(home, monkeypatch):
    monkeypatch.setattr(home, "_porta_libera", lambda pt: False)
    with pytest.raises(RuntimeError, match="nessuna porta libera"): home.porta_libera(8801)


def test_esci_e_riavvio_con_editor_gia_chiusi(home_srv, monkeypatch):
    """uscita e riavvio fermano gli editor aperti; uno già chiuso (terminate fallisce) non blocca gli altri"""
    from aiuti import attendi

    from impaginatore.piattaforma import processi
    vivo, chiuso = _Processo(), _Processo(rotto=True)
    home_srv.modulo.EDITORS.update({"/a": (chiuso, 1), "/b": (vivo, 2)})
    assert home_srv.post("/api/esci") == {"ok": True} and vivo.fermato
    attendi(lambda: home_srv.uscite == [1], 10, 0.02)
    vivo.fermato = False; lanci = []
    monkeypatch.delenv("IMPAGINATORE_SENZA_RIAVVIO")
    monkeypatch.setattr(processi, "rilancia_dopo", lambda argv, r, gettone=None: lanci.append(argv))
    monkeypatch.setattr(home_srv.modulo.threading, "Thread", lambda target, daemon: types.SimpleNamespace(start=target))
    monkeypatch.setattr(home_srv.modulo.time, "sleep", lambda s: None)
    home_srv.modulo.riavvia_programma()
    assert vivo.fermato and len(lanci) == 1 and home_srv.uscite == [1, 1]


def test_aggiorna_e_ripristina_riusciti(home_srv, monkeypatch):
    """con gli aggiornamenti attivi la pagina riceve l'esito di aggiorna e ripristina"""
    chiesti = []
    finti = types.SimpleNamespace(aggiorna=lambda: chiesti.append("aggiorna") or True, ripristina=lambda c: chiesti.append(c) or dict(n="2", caricato=True))
    monkeypatch.setattr(home_srv.modulo, "AGGIORNAMENTI", finti)
    assert home_srv.post("/api/aggiorna") == {"ok": True}
    assert home_srv.post("/api/ripristina", {"codice": "abc1234"}) == {"n": "2", "caricato": True} and chiesti == ["aggiorna", "abc1234"]


def test_apri_browser(home, monkeypatch):
    from aiuti import attendi
    aperti = []
    monkeypatch.setattr(home.webbrowser, "open", aperti.append)
    home.apri_browser("http://127.0.0.1:1/avvio?c=x", ritardo=0)
    assert attendi(lambda: aperti, 10, 0.02) == ["http://127.0.0.1:1/avvio?c=x"]


def test_porte(home):
    from impaginatore import servizio
    assert 8801 <= home.porta_stabile("/a") <= 8899 and home.porta_stabile("/a") == home.porta_stabile("/a")
    srv = servizio.ServerLocale(("127.0.0.1", 0), None); occupata = srv.server_address[1]
    try:
        assert not servizio.porta_libera(occupata)
        assert home.porta_libera(occupata) != occupata
    finally: srv.server_close()
    assert servizio.porta_libera(occupata)


def test_aggiornamenti_spenti_e_predefiniti(monkeypatch, tmp_path):
    assert isinstance(aggiornamenti.predefiniti(), aggiornamenti.NonDisponibili)
    monkeypatch.setenv("IMPAGINATORE_AGGIORNAMENTI", "")
    from impaginatore.aggiornamenti import firmati, installazione, sorgenti
    from impaginatore.piattaforma import cartelle
    monkeypatch.setattr(cartelle, "radice_checkout", lambda: None)
    a = aggiornamenti.predefiniti()
    assert isinstance(a, firmati.PacchettiFirmati) and isinstance(a.sorgente, sorgenti.SorgenteGitHub) and isinstance(a.installazione, installazione.InstallazionePython)
    assert a.stato()["disponibile"] is False and "non è configurato" in a.stato()["motivo"], "pacchetto Python: i pacchetti firmati, finché il canale non c'è spenti"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    c = aggiornamenti.predefiniti(); assert isinstance(c.installazione, installazione.InstallazioneCompilata) and "installatore" in c.stato()["motivo"]
    monkeypatch.delattr(sys, "frozen")
    monkeypatch.setattr(cartelle, "radice_checkout", lambda: "/repo")
    monkeypatch.setattr(aggiornamenti.shutil, "which", lambda n: "/usr/bin/git")
    from impaginatore.aggiornamenti.git import Git
    g = aggiornamenti.predefiniti(); assert isinstance(g, Git) and g.radice == "/repo"
    monkeypatch.setenv("IMPAGINATORE_AGGIORNAMENTI_FINTI", str(tmp_path))
    (tmp_path / "chiave-prova.txt").write_text("ab" * 32, encoding="utf-8")
    f = aggiornamenti.predefiniti()
    assert isinstance(f.sorgente, sorgenti.SorgenteFinta) and f.sorgente.cartella == str(tmp_path) and f.chiavi[0] == "ab" * 32, "prove a mano: la release in una cartella"
    import threading
    e = threading.Event(); e.set(); aggiornamenti.NonDisponibili().ciclo(e)
    with pytest.raises(NotImplementedError): aggiornamenti.Aggiornamenti().stato()
    for m in ("controlla", "versioni", "aggiorna"):
        with pytest.raises(NotImplementedError): getattr(aggiornamenti.Aggiornamenti(), m)()
    with pytest.raises(NotImplementedError): aggiornamenti.Aggiornamenti().ripristina("x")


def test_controllo_automatico_dalla_pagina(home_srv):
    """«Controlla da solo se ci sono versioni nuove» (T-207): lo stato lo dice, la pagina lo cambia con il gettone"""
    c = home_srv
    assert c.get("/api/aggiornamento")["automatico"] is True and c.post("/api/controlla")["automatico"] is True
    assert c.post("/api/aggiornamenti/automatico", {"automatico": False}) == {"automatico": False} and aggiornamenti.automatico() is False
    assert c.get("/api/aggiornamento")["automatico"] is False
    for v in ("no", 0, None):
        ok, r = c.prova("/api/aggiornamenti/automatico", {"automatico": v}); assert not ok and "vero o falso" in r["errore"]
    assert c.codice("/api/aggiornamenti/automatico", {"automatico": True}, **{"X-Impaginatore-Gettone": None}) == 401, "solo con il gettone"
    assert aggiornamenti.automatico() is False


def test_non_si_aggiorna_durante_un_esportazione(home_srv, monkeypatch):
    """il riavvio interromperebbe l'esportazione: aggiorna e ripristina aspettano"""
    from impaginatore.desktop import finestra
    chiesti = []
    monkeypatch.setattr(home_srv.modulo, "AGGIORNAMENTI", types.SimpleNamespace(aggiorna=lambda: chiesti.append(1) or True, ripristina=lambda c: chiesti.append(c)))
    monkeypatch.setattr(finestra, "esportazioni", lambda editors: 1 if editors is home_srv.modulo.EDITORS else 1 / 0)
    for u, b in (("/api/aggiorna", {}), ("/api/ripristina", {"codice": "x"})):
        ok, r = home_srv.prova(u, b); assert not ok and r["errore"] == "Un album sta esportando: aspetta che finisca, poi aggiorna"
    assert chiesti == []


def test_la_pagina_degli_album_e_pronta(home_srv, monkeypatch):
    """GET /api/progetti (la pagina degli album ha i suoi dati) segna PRONTA: la schermata di avvio lascia il posto alla finestra"""
    import threading
    monkeypatch.setattr(home_srv.modulo, "PRONTA", threading.Event())
    assert not home_srv.modulo.PRONTA.is_set()
    home_srv.get("/api/aggiornamento"); assert not home_srv.modulo.PRONTA.is_set()
    home_srv.get("/api/progetti"); assert home_srv.modulo.PRONTA.is_set()


def test_riavvio_dopo_aggiornamento(home, monkeypatch):
    from impaginatore.piattaforma import processi
    lanci, uscite = [], []
    monkeypatch.setattr(processi, "rilancia_dopo", lambda argv, r, gettone=None: lanci.append((argv, gettone)))
    monkeypatch.setattr(home, "esci", lambda: uscite.append(1))
    home.riavvia_programma(); assert lanci == [], "IMPAGINATORE_SENZA_RIAVVIO: niente riavvio"
    monkeypatch.delenv("IMPAGINATORE_SENZA_RIAVVIO")
    monkeypatch.setattr(home.threading, "Thread", lambda target, daemon: type("T", (), {"start": lambda s: target()})())
    monkeypatch.setattr(home.time, "sleep", lambda s: None)
    monkeypatch.setattr(home, "SERVER", None)
    from impaginatore.desktop import finestra
    chiusi = []; monkeypatch.setattr(finestra, "chiudi_editor", chiusi.append)
    home.riavvia_programma()
    assert lanci[0][0][1:3] == ["-m", "impaginatore"] and "--no-browser" in lanci[0][0] and uscite == [1]
    assert chiusi == [home.EDITORS], "gli editor salvano e si chiudono prima del riavvio"
    assert lanci[0][1] is None, "senza server niente gettone da passare"
    from impaginatore import servizio
    srv = servizio.ServerLocale(("127.0.0.1", 0), None); monkeypatch.setattr(home, "SERVER", srv)
    try: home.riavvia_programma()
    finally: srv.server_close()
    assert lanci[1][1] == srv.sessione.gettone, "il programma riavviato tiene il gettone: la pagina aperta resta collegata"


def test_interruttore_immagini_dell_assistente(home_srv):
    """«L'assistente può vedere le immagini» (T-205 per T-203): spento di serie; lo cambia solo la pagina, con il gettone,
    e il server MCP legge la stessa scelta (mcp/consenso.py)"""
    from impaginatore.mcp import consenso
    c = home_srv
    si = dict(consentito=True, motivo=None)                       # Studio: la licenza comprende l'assistente (T-206: altrimenti si spiega)
    assert c.get("/api/assistente") == dict(si, immagini=False) and not consenso.consentite(False)
    assert c.post("/api/assistente", {"immagini": True}) == dict(si, immagini=True) and consenso.consentite(False)
    assert c.get("/api/assistente") == dict(si, immagini=True)
    assert oct(os.stat(consenso.percorso()).st_mode & 0o777) == "0o600" or os.name == "nt"
    for v in ("true", 1, None):
        ok, r = c.prova("/api/assistente", {"immagini": v}); assert not ok and "vero o falso" in r["errore"]
    assert c.get("/api/assistente") == dict(si, immagini=True), "un valore strano non cambia la scelta"
    assert c.codice("/api/assistente", {"immagini": False}, **{"X-Impaginatore-Gettone": None}) == 401, "solo con il gettone"
    assert c.post("/api/assistente", {"immagini": False}) == dict(si, immagini=False) and not consenso.consentite(False)
