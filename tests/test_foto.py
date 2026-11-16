"""Foto in ingresso (BUG-003, BUG-004, SEC-008): formati oltre il JPEG, profili colore, orientamento EXIF, foto senza data,
foto enormi, file rovinati. Le foto che non si aprono non spariscono in silenzio: vanno in album.SCARTATE con il motivo."""
import io
import json
import os
import struct
import sys
import time
import types
import urllib.parse

import pytest
from aiuti import DATA_FILE, crea_foto
from PIL import Image, ImageCms

from impaginatore.motore import album


def _scambia_primari(icc):
    """profilo ICC con i tag rXYZ e bXYZ scambiati (tabella dei tag dopo l'intestazione di 128 byte)"""
    b = bytearray(icc); n = struct.unpack(">I", b[128:132])[0]; pos = {}
    for k in range(n):
        o = 132 + 12 * k; pos[bytes(b[o:o + 4])] = o
    r, bl = pos[b"rXYZ"], pos[b"bXYZ"]
    b[r + 4:r + 12], b[bl + 4:bl + 12] = b[bl + 4:bl + 12], b[r + 4:r + 12]
    return bytes(b)


def _progetto(home, nome="Foto"):
    return home.nuovo({"nome": nome, "w": 30, "h": 30})


def test_formati_png_tiff_webp_e_avvisi(home, apri_editor):
    p = _progetto(home); fd = os.path.join(p, "Foto")
    crea_foto(fd, [("A01", 600, 400, "2026:01:01 10:00:00")])
    Image.new("RGBA", (500, 400), (255, 0, 0, 0)).save(os.path.join(fd, "B02.png"))                    # trasparente: diventa bianca
    Image.new("RGB", (400, 500), (0, 128, 255)).save(os.path.join(fd, "C03.tif"))
    Image.new("I;16", (300, 300), 40000).save(os.path.join(fd, "D04.tiff"))                           # 16 bit
    Image.new("RGB", (320, 200), (10, 200, 10)).save(os.path.join(fd, "E05.webp"))
    Image.new("CMYK", (200, 300), (0, 255, 255, 0)).save(os.path.join(fd, "F06.jpg"))                  # CMYK senza profilo
    Image.new("RGB", (200, 200)).save(os.path.join(fd, "A01.png"))                                     # stesso nome di A01.jpg
    for n, dati in (("G07.heic", b"\0" * 64), ("H08.CR3", b"\0" * 64), ("rotta.jpg", b"non sono una foto"), ("nota.txt", b"x"), (".nascosta.jpg", b"x")):
        with open(os.path.join(fd, n), "wb") as f: f.write(dati)
    os.mkdir(os.path.join(fd, "sotto.jpg"))
    c = apri_editor(p); st = c.get("/api/state")
    assert sorted(x["n"] for x in st["photos"]) == ["A01", "B02", "C03", "D04", "E05", "F06"]
    sc = {x["n"]: x["motivo"] for x in st["scartate"]}
    assert set(sc) == {"A01.png", "G07.heic", "H08.CR3", "rotta.jpg"} and "HEIC" in sc["G07.heic"] and "già" in sc["A01.png"] and "non si apre" in sc["rotta.jpg"]
    for n in ("B02", "C03", "D04", "E05", "F06"):
        with Image.open(io.BytesIO(c.raw(f"/img/thumb/{n}?w=100"))) as im: assert im.format == "JPEG" and im.mode == "RGB", n
    with Image.open(os.path.join(p, "_cache", "thumbs", "B02.png")) as im: assert im.format == "JPEG" and im.getpixel((5, 5)) == (255, 255, 255), "trasparenza su bianco"
    with Image.open(os.path.join(p, "_cache", "thumbs", "D04.tiff")) as im: assert abs(im.getpixel((5, 5))[0] - 40000 // 256) <= 2, "16 bit ridotti a 8"
    # nel selettore di foto del programma e nell'importazione: gli stessi formati
    r = c.get("/api/ls?p=" + urllib.parse.quote(fd)); assert {"B02.png", "C03.tif", "E05.webp"} <= {f["n"] for f in r["files"]} and "nota.txt" not in {f["n"] for f in r["files"]}
    assert c.raw("/api/fthumb?p=" + urllib.parse.quote(os.path.join(fd, "B02.png")))[:2] == b"\xff\xd8"
    assert c.codice("/api/fthumb?p=" + urllib.parse.quote(os.path.join(fd, "nota.txt"))) == 500


def test_foto_importate_in_un_progetto_che_legge_un_altra_cartella(home, apri_editor, tmp_path):
    """le foto importate vanno in <progetto>/Foto e all'apertura si aggiungono a foto_extra: anche PNG, TIFF e WebP"""
    cli = str(tmp_path / "Cliente"); crea_foto(cli, [("A01", 600, 400, "2026:01:01 10:00:00")])
    p = home.nuovo({"nome": "Fuori", "w": 30, "h": 30, "foto": cli}); fd = os.path.join(p, "Foto"); os.makedirs(fd, exist_ok=True)
    Image.new("RGB", (300, 200), (200, 0, 0)).save(os.path.join(fd, "B02.png")); Image.new("RGB", (200, 300)).save(os.path.join(fd, "C03.tif"))
    with open(os.path.join(fd, "nota.txt"), "w", encoding="utf-8") as f: f.write("x")
    st = apri_editor(p).get("/api/state")
    assert [x["n"] for x in st["photos"]] == ["A01", "B02", "C03"] and st["scartate"] == []


def test_profilo_colore_convertito_in_srgb():
    """BUG-004: una foto con profilo incorporato si converte in sRGB (non si buttano via i numeri come se fossero sRGB)"""
    lab = ImageCms.ImageCmsProfile(ImageCms.createProfile("LAB"))
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    im = Image.new("RGB", (4, 4), (200, 30, 30)); im.info["icc_profile"] = srgb
    assert album.in_srgb(im).getpixel((0, 0)) == pytest.approx((200, 30, 30), abs=2), "sRGB resta sRGB"
    # profilo RGB diverso: l'sRGB con primari rosso e blu scambiati. Il rosso «del file» è il blu vero
    im2 = Image.new("RGB", (4, 4), (255, 0, 0)); im2.info["icc_profile"] = _scambia_primari(srgb)
    r, g, b = album.in_srgb(im2).getpixel((0, 0)); assert b > 200 and r < 60, (r, g, b)
    im3 = Image.new("RGB", (4, 4), (1, 2, 3)); im3.info["icc_profile"] = b"rotto"
    assert album.in_srgb(im3).getpixel((0, 0)) == (1, 2, 3), "profilo illeggibile: colori come sono, con un avviso nel registro"
    assert lab and album.in_srgb(Image.new("LA", (2, 2), (0, 0))).getpixel((0, 0)) == (255, 255, 255)
    p = Image.new("P", (2, 2)); p.info["transparency"] = 0
    assert album.in_srgb(p).mode == "RGB" and album.in_srgb(Image.new("I", (2, 2), 512)).getpixel((0, 0)) == (2, 2, 2)


def test_heic_con_pillow_heif(monkeypatch):
    """HEIC/HEIF solo se c'è il pacchetto facoltativo pillow-heif (che insegna a Pillow ad aprirle)"""
    registrati = []
    monkeypatch.setitem(sys.modules, "pillow_heif", types.SimpleNamespace(register_heif_opener=lambda: registrati.append(1)))
    monkeypatch.setattr(album, "_HEIF", [])
    assert album.estensioni()[-2:] == (".heic", ".heif") and registrati == [1]
    album.estensioni(); assert registrati == [1], "una volta sola"
    monkeypatch.setitem(sys.modules, "pillow_heif", None); monkeypatch.setattr(album, "_HEIF", [])
    assert ".heic" not in album.estensioni()


@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")     # Pillow avvisa, poi la foto si scarta comunque
def test_foto_enorme_scartata(home, apri_editor, monkeypatch):
    """SEC-008: limite di pixel (IMPAGINATORE_MAX_MPIXEL): la foto troppo grande non si apre (né in elenco, né in miniatura)"""
    monkeypatch.setenv("IMPAGINATORE_MAX_MPIXEL", "0.1")                                  # 100.000 pixel
    p = _progetto(home); fd = os.path.join(p, "Foto")
    crea_foto(fd, [("Piccola", 300, 200, None), ("Grande", 400, 300, None), ("Bomba", 700, 700, None)])      # 120.000 e 490.000 (oltre il doppio: DecompressionBombError)
    c = apri_editor(p); st = c.get("/api/state")
    assert [x["n"] for x in st["photos"]] == ["Piccola"]
    assert {x["n"] for x in st["scartate"]} == {"Grande.jpg", "Bomba.jpg"} and all("troppo grande" in x["motivo"] for x in st["scartate"])
    for n in ("Grande.jpg", "Bomba.jpg"):
        ok, r = c.prova("/api/fthumb?p=" + urllib.parse.quote(os.path.join(fd, n))); assert not ok and "troppo grande" in r["errore"]
    monkeypatch.setenv("IMPAGINATORE_MAX_MPIXEL", "boh"); assert album.limite_pixel() == album.MAX_MPIXEL * 1_000_000
    monkeypatch.delenv("IMPAGINATORE_MAX_MPIXEL"); assert album.limite_pixel() == 160_000_000
    with pytest.raises(OSError): album.apri_foto(os.path.join(fd, "non-esiste.jpg"))


def test_foto_senza_data_in_ordine_di_file(home, apri_editor):
    """BUG-003: senza data di scatto conta la data del file (prima: «None.00», tutte in fondo); segnalate con sd"""
    p = _progetto(home); fd = os.path.join(p, "Foto")
    crea_foto(fd, [("A", 300, 200, "2026:06:01 10:00:00"), ("B", 300, 200, None), ("C", 300, 200, "2026:06:01 14:00:00")])
    os.utime(os.path.join(fd, "B.jpg"), (DATA_FILE - 3600, DATA_FILE - 3600))                       # 11:00 del primo giugno
    c = apri_editor(p); ph = c.get("/api/state")["photos"]
    assert [x["n"] for x in ph] == ["A", "B", "C"] and ph[1]["dt"] == "2026:06:01 11:00:00" and ph[1]["sd"] and "sd" not in ph[0]


def test_progetto_vecchio_con_date_none(home, apri_editor):
    """meta.json scritto dalle versioni fino alla 2.0 con «None.00»: all'apertura la data del file, l'ordine salvato non cambia"""
    p = _progetto(home); fd = os.path.join(p, "Foto")
    crea_foto(fd, [("X", 300, 200, None), ("Y", 300, 200, "2026:01:01 08:00:00")])
    os.makedirs(os.path.join(p, "_cache"), exist_ok=True)
    meta = [dict(n="X.jpg", dt="None.00", w=300, h=200, ar=1.5, src=os.path.join(fd, "X.jpg")), dict(n="Y.jpg", dt="2026:01:01 08:00:00.00", w=300, h=200, ar=1.5, src=os.path.join(fd, "Y.jpg"))]
    with open(os.path.join(p, "_cache", "meta.json"), "w", encoding="utf-8") as f: json.dump(meta, f)
    ph = apri_editor(p).get("/api/state")["photos"]
    assert [x["n"] for x in ph] == ["X", "Y"] and ph[0]["dt"] == time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(DATA_FILE)) and ph[0]["sd"]


def test_cartella_delle_foto_che_non_si_legge(tmp_path):
    assert album._cerca_foto(str(tmp_path / "non-esiste")) == []


def test_foto_scartate_e_troppo_grandi_in_inglese(home, apri_editor, monkeypatch):
    """i motivi delle foto che non si aprono escono nella lingua in uso; il limite di pixel e l'originale mancante pure"""
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "en")
    p = _progetto(home); fd = os.path.join(p, "Foto")
    crea_foto(fd, [("A01", 600, 400, "2026:01:01 10:00:00")]); Image.new("RGB", (200, 200)).save(os.path.join(fd, "A01.png"))
    for n, dati in (("G07.heic", b"\0" * 64), ("rotta.jpg", b"non sono una foto")):
        with open(os.path.join(fd, n), "wb") as f: f.write(dati)
    c = apri_editor(p); sc = {x["n"]: x["motivo"] for x in c.get("/api/state")["scartate"]}
    assert sc == {"A01.png": "there's already a photo called “A01”", "rotta.jpg": "the file doesn't open as a photo",
                  "G07.heic": "HEIC format isn't supported: export it as one of the formats that open (JPEG, PNG, TIFF, WebP, HEIC)"}
    monkeypatch.setenv("IMPAGINATORE_MAX_MPIXEL", "0.01")
    with pytest.raises(ValueError, match=r"^A01.jpg: photo too large \(over 0.01 million pixels; change the limit with IMPAGINATORE_MAX_MPIXEL\)$"): album.apri_foto(os.path.join(fd, "A01.jpg"))
    monkeypatch.setenv("IMPAGINATORE_LINGUA", "it")
    with pytest.raises(ValueError, match=r"^A01.jpg: foto troppo grande \(oltre 0,01 milioni di pixel"): album.apri_foto(os.path.join(fd, "A01.jpg"))
