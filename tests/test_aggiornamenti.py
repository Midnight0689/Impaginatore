"""Aggiornamenti da un checkout git, su repository temporanei (nessun accesso a GitHub)."""
import os
import shutil
import subprocess

import pytest

from impaginatore.aggiornamenti.git import Git

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="serve git")


def _git(d, *a):
    r = subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"))
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def _versione(d, v, titolo):
    p = d / "src" / "impaginatore"; p.mkdir(parents=True, exist_ok=True)
    (p / "__init__.py").write_text(f'"""x"""\n__version__ = "{v}"\n', encoding="utf-8")
    _git(d, "add", "-A"); _git(d, "commit", "-q", "-m", titolo)


@pytest.fixture
def repo(tmp_path):
    origine = tmp_path / "origine.git"; _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origine))
    lavoro = tmp_path / "lavoro"; _git(tmp_path, "clone", "-q", str(origine), str(lavoro))
    _git(lavoro, "checkout", "-q", "-b", "main")
    (lavoro / "VERSION").write_text("1.5.2\n", encoding="utf-8"); _git(lavoro, "add", "-A"); _git(lavoro, "commit", "-q", "-m", "1.5.2 vecchia")
    _versione(lavoro, "2.0.0", "2.0.0 prima"); _versione(lavoro, "2.0.1", "2.0.1 correzioni")
    _git(lavoro, "push", "-q", "-u", "origin", "main")
    utente = tmp_path / "utente"; _git(tmp_path, "clone", "-q", str(origine), str(utente))
    return lavoro, utente


def test_stato_versioni_e_controllo(repo):
    lavoro, utente = repo
    g = Git(str(utente))
    s = g.stato(); assert s["attuale"]["rel"] == "2.0.1" and s["attuale"]["n"] == 3 and s["attuale"]["titolo"] == "2.0.1 correzioni"
    s = g.controlla(); assert not s["da_aggiornare"] and not s["errore"] and s["controllato"]
    v = g.versioni(); assert [x["n"] for x in v] == [3, 2, 1] and v[0]["attuale"] and v[2]["titolo"] == "1.5.2 vecchia"
    assert g.rilascio("HEAD~2") == "1.5.2", "le 1.x hanno il file VERSION"
    _versione(lavoro, "2.0.2", "2.0.2 novità"); _git(lavoro, "push", "-q")
    s = g.controlla(); assert s["da_aggiornare"] and s["novita"] == ["2.0.2 novità"] and s["ultima"]["rel"] == "2.0.2"
    assert g.info("non-esiste") is None


def test_aggiorna(repo, monkeypatch):
    lavoro, utente = repo; riavvii = []
    g = Git(str(utente), lambda: riavvii.append(1))
    monkeypatch.setattr(g, "prepara_ambiente", lambda: "")
    _versione(lavoro, "2.0.2", "2.0.2 novità"); _git(lavoro, "push", "-q")
    assert g.aggiorna() is True and riavvii == [1] and g.stato()["attuale"]["rel"] == "2.0.2"
    (utente / "src" / "impaginatore" / "__init__.py").write_text("rotto", encoding="utf-8"); _git(utente, "commit", "-qam", "locale")
    _versione(lavoro, "2.0.3", "divergente"); _git(lavoro, "push", "-q")
    with pytest.raises(ValueError, match="non riuscito"): g.aggiorna()


def test_ripristina(repo, monkeypatch):
    lavoro, utente = repo; riavvii = []
    g = Git(str(utente), lambda: riavvii.append(1))
    monkeypatch.setattr(g, "prepara_ambiente", lambda: "")
    v = g.versioni()
    with pytest.raises(ValueError, match="non valida"): g.ripristina("zzz")
    with pytest.raises(ValueError, match="precedente alla 2.0"): g.ripristina(v[2]["codice"])
    r = g.ripristina(v[1]["codice"]); assert r["n"] == "2" and r["caricato"] and riavvii == [1]
    assert g.stato()["attuale"]["rel"] == "2.0.0" and g.stato()["attuale"]["titolo"].startswith("Ripristino alla versione 2")
    (utente / "src" / "impaginatore" / "__init__.py").write_text("modificato", encoding="utf-8")
    with pytest.raises(ValueError, match="modifiche"): g.ripristina(v[0]["codice"])
    _git(utente, "checkout", "-q", "--", ".")
    monkeypatch.setattr(g, "prepara_ambiente", lambda: "pip non trovato")
    with pytest.raises(ValueError, match="pip non trovato"): g.ripristina(v[0]["codice"])


def test_prepara_ambiente(repo, monkeypatch):
    _, utente = repo
    g = Git(str(utente)); comandi = []

    class R: returncode = 1; stdout = ""; stderr = "riga 1\nERRORE finale"
    monkeypatch.setattr(subprocess, "run", lambda cmd, **k: comandi.append(cmd) or R())
    monkeypatch.setattr(shutil, "which", lambda n: None)
    assert g.prepara_ambiente() == "ERRORE finale" and comandi[-1][1:4] == ["-m", "pip", "install"]
    monkeypatch.setattr(shutil, "which", lambda n: "/usr/bin/uv")
    R.returncode = 0; assert g.prepara_ambiente() == "" and comandi[-1][:3] == ["uv", "pip", "install"]
    monkeypatch.setattr(subprocess, "run", lambda cmd, **k: (_ for _ in ()).throw(OSError("manca")))
    assert g.prepara_ambiente() == "manca"


def test_senza_rete(repo):
    _, utente = repo
    _git(utente, "remote", "set-url", "origin", str(utente.parent / "sparito.git"))
    s = Git(str(utente)).controlla(); assert s["errore"] and not s["da_aggiornare"]
