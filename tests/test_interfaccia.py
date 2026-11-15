"""Le pagine si aprono davvero in un browser (Chrome/Chromium senza schermo) e mostrano i dati del server."""
import os
import shutil
import subprocess

import pytest

CHROME = next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(n)), None)
pytestmark = [pytest.mark.browser, pytest.mark.skipif(not CHROME, reason="serve Chrome o Chromium")]


def dom(url, tmp_path):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run", f"--user-data-dir={tmp_path / 'chrome'}",
                        "--virtual-time-budget=8000", "--dump-dom", url], capture_output=True, text=True, encoding="utf-8", timeout=120)
    return r.stdout


def test_home_nel_browser(home_srv, tmp_path):
    home_srv.post("/api/nuovo", {"nome": "Album Verdi", "w": 30, "h": 30})
    assert "Album Verdi" in dom(home_srv.url("/"), tmp_path)


def test_editor_nel_browser(editor, tmp_path):
    st = editor.get("/api/state"); names = [p["n"] for p in st["photos"]]
    t = editor.post("/api/templates", {"photos": names[:2]})["items"][0]
    editor.post("/api/op", dict(cid="b", rev=st["rev"], op="newspread", pos=0, L=t["L"], R=t["R"]))
    html = dom(editor.url("/"), tmp_path)
    assert "/img/spread/0" in html or "/img/thumb/" in html, html[:2000]
    assert os.path.exists(os.path.join(editor.progetto, "album.json"))
