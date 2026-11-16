"""VER-004: un progetto ricevuto come cartella (non come ZIP) non allarga le cartelle che la pagina può leggere.
Le radici dell'editor vengono solo dalle impostazioni del progetto (cartella del progetto, delle foto e quella che la
contiene, foto aggiunte, uscita dei PSD), mai dall'elenco delle foto in _cache/meta.json; una foto dell'elenco che sta
fuori da quei luoghi, o in una cartella riservata (nascoste della casa, dati dei programmi, sistema), risulta mancante
e si ricollega; «Esporta progetto» copia solo foto del progetto."""
import json
import os
from urllib.parse import quote

import pytest
from aiuti import attendi_log, crea_foto
from PIL import Image

from impaginatore import percorsi
from impaginatore.motore import album as A


def _chiudi(c): c.srv.shutdown(); c.srv.server_close(); c.E.ferma()


def _cambia(p, f, cambia):
    path = os.path.join(p, f)
    with open(path, encoding="utf-8") as x: d = json.load(x)
    d = cambia(d) or d
    with open(path, "w", encoding="utf-8") as x: json.dump(d, x)


def _segreti(casa, tmp_path):
    ssh = casa / ".ssh"; crea_foto(str(ssh), [("chiave", 40, 30, None)])
    priv = tmp_path / "Privato"; crea_foto(str(priv), [("segreta", 64, 48, None)])
    return ssh, priv


def test_radici_e_foto_dell_elenco(apri_editor, progetto, casa, tmp_path):
    ssh, priv = _segreti(casa, tmp_path)
    _chiudi(apri_editor(progetto))
    _cambia(progetto, "_cache/meta.json", lambda m: m + [dict(m[0], n="zz_a.jpg", src=str(priv / "segreta.jpg")), dict(m[0], n="zz_b.jpg", src=str(ssh / "chiave.jpg")),
                                                          dict(m[0], n="zz_c.jpg", src="Foto/zz_c.jpg"), dict(m[0], n="zz_d.jpg", src=os.path.join(progetto, "Foto", "nota.txt"))])
    c = apri_editor(progetto); st = c.get("/api/state")
    assert {"zz_a.jpg", "zz_b.jpg", "zz_c.jpg", "zz_d.jpg"} <= set(st["mancanti"]), "fuori dai luoghi del progetto: mancanti, da ricollegare"
    assert all(m["src"] == "" for m in A.M if m["n"].startswith("zz_"))
    for p in (priv, priv / "segreta.jpg", ssh, ssh / "chiave.jpg"):
        assert c.codice("/api/ls?p=" + quote(str(p))) == 403 and c.codice("/api/fthumb?p=" + quote(str(p))) == 403
    assert c.codice("/api/ls?p=" + quote(os.path.join(progetto, "Foto"))) == 200
    for f in ("zz_a.jpg", "zz_b.jpg"):
        with Image.open(os.path.join(progetto, "_cache", "thumbs", f)) as im: assert im.convert("RGB").getpixel((5, 5)) == A.GRIGIO_SEGNAPOSTO, "nessuna miniatura fatta da file di fuori"
    ok, r = c.prova("/api/reveal", {"foto": "zz_a"})
    assert not ok and "ricollega" in r["errore"]


def test_impostazioni_in_cartelle_riservate(apri_editor, progetto, casa, tmp_path):
    ssh, priv = _segreti(casa, tmp_path)
    _chiudi(apri_editor(progetto))
    _cambia(progetto, "progetto.json", lambda c: c.update(foto=str(ssh), foto_extra=[str(ssh / "chiave.jpg"), str(casa / ".config" / "x.jpg")], uscita_psd=str(casa / ".local" / "PSD")))
    c = apri_editor(progetto); E = c.E
    assert E.CFG["foto"] == os.path.join(progetto, "Foto") and E.CFG["uscita_psd"] == os.path.join(progetto, "PSD")
    assert E.CFG["foto_extra"] and not any(percorsi.riservata(x) for x in E.CFG["foto_extra"]), "restano le foto del progetto (Foto), non quelle riservate"
    assert "chiave" not in [x["n"] for x in c.get("/api/state")["photos"]]
    assert c.codice("/api/ls?p=" + quote(str(ssh))) == 403


def test_esporta_progetto_copia_solo_foto_del_progetto(apri_editor, progetto, casa, tmp_path):
    ssh, priv = _segreti(casa, tmp_path)
    _chiudi(apri_editor(progetto))
    _cambia(progetto, "_cache/meta.json", lambda m: m + [dict(m[0], n="zz_a.jpg", src=str(priv / "segreta.jpg"))])
    c = apri_editor(progetto)
    E = c.E; E.A.M[0]["src"] = os.path.join(progetto, "Foto", "nota.txt")          # anche se un src cambiasse dopo l'apertura
    with open(E.A.M[0]["src"], "w", encoding="utf-8") as f: f.write("non è una foto")
    dest = os.path.join(progetto, "uscita"); os.makedirs(dest)
    c.post("/api/prj_esporta", {"dest": str(dest), "foto": True}); log = attendi_log(c)
    pacchetto = os.path.join(dest, "Prova - progetto"); foto = set(os.listdir(os.path.join(pacchetto, "Foto")))
    assert "zz_a.jpg" not in foto and E.A.M[0]["n"] not in foto and len(foto) == len(E.A.M) - 2, foto
    segreta = (priv / "segreta.jpg").read_bytes()
    assert not [f for r, _, fs in os.walk(pacchetto) for f in fs if open(os.path.join(r, f), "rb").read() in (segreta, b"non \xc3\xa8 una foto")]
    assert any("non è nel pacchetto" in r for r in log)


def test_ricollega_ricorda_la_cartella(apri_editor, progetto, tmp_path):
    """le foto ricollegate da una cartella scelta dall'utente restano trovate alle aperture dopo (vanno in foto_extra)"""
    altrove = tmp_path / "Archivio" / "Originali"
    c = apri_editor(progetto); nomi = [m["n"] for m in A.M]
    os.makedirs(altrove); os.replace(os.path.join(progetto, "Foto", nomi[0]), altrove / nomi[0])
    _chiudi(c)
    c = apri_editor(progetto); assert nomi[0] in c.get("/api/state")["mancanti"]
    c.E.RADICI.scelta(str(altrove))                                  # come la finestra di sistema di «Ricollega foto»
    assert c.post("/api/ricollega", {"cartella": str(altrove)})["trovate"] == 1
    _chiudi(c)
    c = apri_editor(progetto)
    assert c.get("/api/state")["mancanti"] == [] and A.M[0]["src"] == str(altrove / nomi[0])
    assert c.codice("/api/fthumb?p=" + quote(str(altrove / nomi[0]))) == 200


def test_riservata(casa, tmp_path, monkeypatch):
    for p in (casa / ".ssh" / "id", casa / ".config", casa / "dati" / "sessioni", "/etc/passwd", "/proc/self", "/usr/share/x.jpg"):
        assert percorsi.riservata(str(p)), p
    for p in (casa / "Immagini" / "x.jpg", tmp_path / "Progetti", casa, "/tmp/x.jpg", casa / "Lavori" / ".nascosta" / "x.jpg"):
        assert not percorsi.riservata(str(p)), p
    assert not percorsi.riservata("") and percorsi.riservata("\0x")
    lavori = tmp_path / "Lavori"; lavori.mkdir(); os.makedirs(casa / ".ssh", exist_ok=True)
    r = percorsi.Radici(lambda: [str(casa / ".ssh"), str(lavori)])
    assert r.tutte() == [percorsi.reale(str(lavori))], "le cartelle riservate non diventano radici dal progetto"
    r.scelta(str(casa / ".ssh")); assert percorsi.reale(str(casa / ".ssh")) in r.tutte(), "ma l'utente può sceglierle con la finestra di sistema"


@pytest.mark.parametrize("sistema,attese", [("windows", ("SystemRoot", "ProgramFiles", "ProgramData")), ("mac", ("/System", "/Library"))])
def test_riservate_degli_altri_sistemi(monkeypatch, sistema, attese, tmp_path):
    for k in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"): monkeypatch.setenv(k, str(tmp_path / k))
    monkeypatch.setattr(percorsi, "sistema", lambda: sistema)
    luoghi = percorsi._riservate()
    for a in attese:
        assert any(x == percorsi._chiave(str(tmp_path / a)) or x == percorsi._chiave(a) for x in luoghi), (a, luoghi)
