"""Documenti per chi lavora sul repository (persone e agenti): non devono contraddire AGENTS.md né la configurazione
dell'ambiente dei test."""
import os
import re

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC = "uv sync --locked --extra dev --extra mcp"


def _leggi(*p):
    with open(os.path.join(RADICE, *p), encoding="utf-8") as f: return f.read()


def test_skill_segue_le_regole_del_repository():
    """la skill non chiede più di scrivere in CAMBIAMENTI.md (registro storico) né di fare push: il registro è CHANGELOG.md
    e il push si fa solo su richiesta esplicita del titolare (AGENTS.md)"""
    s = _leggi("skill", "impaginatore-stefano", "SKILL.md"); regole = _leggi("AGENTS.md")
    assert "CHANGELOG.md" in s and "AGENTS.md" in s and "`CHANGELOG.md` è l'unico registro" in regole
    for riga in s.splitlines():
        if "CAMBIAMENTI.md" in riga: assert "non si modifica più" in riga, riga
        if re.search(r"git push|\bpush\b", riga): assert "Niente `git push`" in riga and "richiesta esplicita del titolare" in riga, riga
    assert "Nessun push e nessuna modifica a `main` senza richiesta esplicita del titolare" in regole


def test_ambiente_della_suite_completa():
    """guida e LEGGIMI dicono con quali extra gira la suite completa: senza «mcp» i test del server MCP si saltano"""
    for doc in (("docs", "sviluppo", "GUIDA.md"), ("LEGGIMI.md",)):
        t = _leggi(*doc)
        assert SYNC in t and "suite completa" in t, doc
        assert "uv sync --extra" not in t, f"{doc}: senza --locked le versioni non sono quelle di uv.lock"
    assert '"--locked", "--extra", "dev", "--extra", "mcp"' in _leggi("strumenti", "controlli.py"), "i controlli usano lo stesso ambiente"
