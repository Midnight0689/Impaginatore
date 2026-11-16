"""T-203: il server MCP con il protocollo vero (SDK ufficiale «mcp»): elenco degli strumenti, schemi, risposte, errori;
poi il comando «impaginatore mcp» avviato come processo e usato da un client stdio, come fanno Claude Desktop e Claude Code."""
import asyncio
import base64
import io
import json
import os
import subprocess
import sys

import pytest
from PIL import Image

pytest.importorskip("mcp", reason="extra «mcp» non installato (uv sync --extra mcp)")

from mcp import Client, StdioServerParameters  # noqa: E402

from impaginatore import cli  # noqa: E402
from impaginatore import mcp as M  # noqa: E402
from impaginatore.mcp import consenso, server  # noqa: E402
from impaginatore.mcp import strumenti as S  # noqa: E402
from impaginatore.piattaforma import processi  # noqa: E402

LETTURA = {"stato_programma", "elenca_progetti", "apri_progetto", "mostra_editor", "stato_album", "elenca_foto", "controlla_album", "proponi_bozza", "stato_esportazione",
           "anteprima_spread", "miniatura_foto", "elenca_prodotti"}
MODIFICA = {"crea_progetto", "aggiungi_foto", "applica_bozza", "cambia_disposizione", "sostituisci_foto", "sistema_album", "annulla", "ripeti", "salva", "esporta",
            "imposta_prodotto"}


def sessione(srv, *chiamate):
    """apre il client sul server (in memoria o processo), elenca gli strumenti e fa le chiamate: (strumenti, [risultati])"""
    async def va():
        async with Client(srv, read_timeout_seconds=120) as c:
            t = (await c.list_tools()).tools
            return t, [await c.call_tool(n, a) for n, a in chiamate]
    return asyncio.run(va())


def contenuto(r):
    assert r.is_error is False, r.content[0].text
    return json.loads(r.content[0].text)


def errore(r):
    assert r.is_error is True
    return r.content[0].text


def stdio(*args):
    """«impaginatore mcp» come lo avvia un assistente: questo Python, ambiente del test (casa finta, misura della copertura)"""
    return StdioServerParameters(command=sys.executable, args=["-m", "impaginatore", "mcp", *args], env=dict(os.environ), cwd=processi.cartella_pacchetto())


def test_strumenti_e_schemi():
    t, _ = sessione(server.crea(S.Assistente()))
    nomi = {x.name for x in t}
    assert nomi == LETTURA | MODIFICA and len(t) == 23
    for x in t:
        a = x.annotations
        assert x.description and x.title and a.open_world_hint is (x.name in ("anteprima_spread", "miniatura_foto")), x.name
        assert a.read_only_hint is (x.name in LETTURA) and a.destructive_hint is False, x.name
        assert x.input_schema["type"] == "object"
    sch = {x.name: x.input_schema for x in t}
    assert sch["esporta"]["properties"]["formato"]["enum"] == ["jpg", "pdf", "consegna"], "il PSD non c'è"
    assert sch["crea_progetto"]["required"] == ["nome"] and sch["imposta_prodotto"]["required"] == ["progetto"], "col prodotto le misure non servono"
    assert sch["cambia_disposizione"]["properties"]["spread"]["minimum"] == 1 and sch["miniatura_foto"]["properties"]["lato"]["maximum"] == 512
    assert not any("percorso" in p or "path" in p for s in sch.values() for p in s["properties"]), "nessuno strumento prende un percorso"


def test_risposte_ed_errori_dal_protocollo(editor):
    p = S.id_progetto(editor.progetto)
    editor.post("/api/op", {"op": "newspreadsel", "names": ["H01", "H02"], "pos": 0})
    _, r = sessione(server.crea(S.Assistente()), ("stato_programma", {}), ("stato_album", {"progetto": p}), ("cambia_disposizione", {"progetto": p, "spread": 0}),
                    ("stato_album", {"progetto": "p0000000000"}), ("anteprima_spread", {"progetto": p, "spread": 1}), ("esporta", {"progetto": p, "formato": "psd"}),
                    ("annulla", {"progetto": p}))
    assert contenuto(r[0])["licenza"]["fascia"] == "Studio"
    assert contenuto(r[1])["spread"][0]["numero"] == 1
    assert "greater than or equal to 1" in errore(r[2]), "gli schemi valgono prima dello strumento"
    assert errore(r[3]) == S.MSG_NON_APERTO
    assert errore(r[4]) == consenso.SPIEGAZIONE and len(r[4].content) == 1, "nessun pixel senza il consenso"
    assert "formato" in errore(r[5])
    assert contenuto(r[6])["annullato"]["nome"] == "Nuovo spread"


def test_immagine_dal_protocollo(editor):
    p = S.id_progetto(editor.progetto)
    editor.post("/api/op", {"op": "newspreadsel", "names": ["H01", "H02"], "pos": 0})
    _, r = sessione(server.crea(S.Assistente(immagini=True)), ("anteprima_spread", {"progetto": p, "spread": 1, "larghezza": 300}), ("miniatura_foto", {"progetto": p, "foto": "H01", "lato": 100}))
    for x, lato in zip(r, (300, 100)):
        assert x.is_error is False and x.content[0].type == "image" and x.content[0].mime_type == "image/jpeg" and x.content[1].type == "text"
        assert max(Image.open(io.BytesIO(base64.b64decode(x.content[0].data))).size) <= lato


def test_argomenti_arrivano_agli_strumenti():
    """ogni strumento del protocollo chiama il metodo giusto con gli argomenti al posto giusto (e i valori di serie)"""
    chiamate = []

    class Registra:
        def __getattr__(self, nome):
            return lambda *a: (chiamate.append((nome, a)), {"ok": nome})[1]
    p = "p0123456789"
    attese = [
        ("stato_programma", {}, ()), ("elenca_progetti", {}, ()), ("apri_progetto", {"progetto": "Nozze"}, ("Nozze",)), ("mostra_editor", {"progetto": p}, (p,)),
        ("crea_progetto", {"nome": "N", "larghezza_cm": 60, "altezza_cm": 22.5}, ("N", 60, 22.5, 0.0, 2.5, 10.0, False, None)),
        ("crea_progetto", {"nome": "N", "larghezza_cm": 60, "altezza_cm": 22.5, "abbondanza_mm": 3, "spazio_mm": 2, "margine_mm": 8, "scegli_cartella_foto": True}, ("N", 60, 22.5, 3, 2, 8, True, None)),
        ("crea_progetto", {"nome": "N", "prodotto": "generico/quadrato-30"}, ("N", None, None, 0.0, 2.5, 10.0, False, "generico/quadrato-30")),
        ("elenca_prodotti", {}, ()), ("imposta_prodotto", {"progetto": p, "prodotto": "lab/album-30"}, (p, "lab/album-30")), ("imposta_prodotto", {"progetto": p}, (p, None)),
        ("aggiungi_foto", {"progetto": p}, (p, "cartella")), ("stato_album", {"progetto": p, "da_spread": 3, "quanti": 2}, (p, 3, 2)),
        ("elenca_foto", {"progetto": p, "filtro": "libere", "da": 5, "quanti": 7}, (p, "libere", 5, 7)), ("controlla_album", {"progetto": p, "spread": [2], "tono": False}, (p, [2], False)),
        ("proponi_bozza", {"progetto": p, "ritmo": "piene", "foto_per_spread": 2.5, "numero_spread": 9, "stelle": False, "seme": 4}, (p, "piene", 2.5, 9, False, 4)),
        ("applica_bozza", {"progetto": p, "proposta": "b1", "dopo_spread": 0, "gruppo": "g"}, (p, "b1", 0, "g")),
        ("cambia_disposizione", {"progetto": p, "spread": 2, "pagina": "destra", "passo": -1, "gruppo": "g"}, (p, 2, "destra", -1, "g")),
        ("sostituisci_foto", {"progetto": p, "spread": 2, "pagina": "sinistra", "cornice": 3, "foto": "H01", "adatta": False, "gruppo": "g"}, (p, 2, "sinistra", 3, "H01", False, "g")),
        ("sistema_album", {"progetto": p, "spread": [1], "spazi": False, "tono": True, "gruppo": "g"}, (p, [1], False, True, "g")),
        ("annulla", {"progetto": p}, (p,)), ("ripeti", {"progetto": p}, (p,)), ("salva", {"progetto": p}, (p,)),
        ("esporta", {"progetto": p, "formato": "pdf", "spread": "1-3", "risoluzione": "schermo"}, (p, "pdf", "1-3", "schermo")), ("stato_esportazione", {"progetto": p}, (p,)),
        ("anteprima_spread", {"progetto": p, "spread": 2, "larghezza": 640}, (p, 2, 640)), ("miniatura_foto", {"progetto": p, "foto": "H01", "lato": 200}, (p, "H01", 200)),
    ]
    _, r = sessione(server.crea(Registra()), *[(n, a) for n, a, _ in attese])
    assert [x.is_error for x in r] == [False] * len(attese)
    assert chiamate == [(n, att) for n, _, att in attese]
    assert {n for n, _, _ in attese} == LETTURA | MODIFICA


def test_risposta_lunga_accorciata(monkeypatch):
    monkeypatch.setattr(S, "MAX_TESTO", 300)
    r = server.risultato(lambda: dict(foto=[dict(n="x" * 20)] * 50))
    assert len(r.content[0].text) <= 300 and "troncato" in json.loads(r.content[0].text)


def test_comando_stdio(editor, home_srv):
    """«impaginatore mcp» come processo, con il client stdio dell'SDK: trova il programma dai file di sessione, lavora
    sull'album aperto in questo processo (l'utente lo vede), e senza «--consenti-immagini» non manda immagini"""
    E = editor.E; p = S.id_progetto(editor.progetto)
    t, r = sessione(stdio(), ("stato_programma", {}), ("elenca_progetti", {}), ("proponi_bozza", {"progetto": p}), ("anteprima_spread", {"progetto": p, "spread": 1}))
    assert len(t) == 23
    st = contenuto(r[0])
    assert st["licenza"]["stato"] == "prova" and st["programma_in_funzione"] is True and st["progetti_aperti"] == [{"progetto": p, "cartella": "Prova"}]
    assert contenuto(r[1])["progetti"][0]["progetto"] == p and editor.progetto not in r[1].content[0].text
    pr = contenuto(r[2])
    assert pr["foto"] == 10 and errore(r[3]) == consenso.SPIEGAZIONE
    # un altro processo, con le immagini: la proposta vive nel processo che l'ha fatta
    async def seconda():
        async with Client(stdio("--consenti-immagini"), read_timeout_seconds=120) as c:
            vecchia = await c.call_tool("applica_bozza", {"progetto": p, "proposta": pr["proposta"]})
            nuova = json.loads((await c.call_tool("proponi_bozza", {"progetto": p})).content[0].text)
            altre = [await c.call_tool(n, a) for n, a in (("applica_bozza", {"progetto": p, "proposta": nuova["proposta"]}), ("stato_programma", {}),
                                                          ("anteprima_spread", {"progetto": p, "spread": 1, "larghezza": 200}))]
            return vecchia, nuova, altre
    vecchia, nuova, (ap, st, im) = asyncio.run(seconda())
    assert "Proposta sconosciuta" in errore(vecchia)
    assert contenuto(ap)["aggiunti"]["foto"] == 10 and len(E.SP) == nuova["spread"] and E.LASTC.startswith("assistente-"), "la modifica è nell'editor dell'utente"
    assert contenuto(st)["immagini"] == {"consentite": True} and im.content[0].type == "image"


def test_comando_senza_sdk(monkeypatch, capsys):
    import impaginatore.mcp
    monkeypatch.delattr(impaginatore.mcp, "server")
    monkeypatch.setitem(sys.modules, "impaginatore.mcp.server", None)
    assert cli.main(["mcp"]) == 2
    err = capsys.readouterr().err
    assert "pip install \"impaginatore[mcp]\"" in err and "uv sync --extra mcp" in err


def test_comando(monkeypatch, capsys):
    import impaginatore.mcp.__main__ as principale                      # importato (non eseguito) non avvia niente
    assert principale.main is M.main
    avvii = []; monkeypatch.setattr(server, "avvia", avvii.append)
    assert cli.main(["mcp"]) == 0 and M.main(["--consenti-immagini"]) == 0 and avvii == [False, True]
    with pytest.raises(SystemExit): M.main(["--help"])
    aiuto = capsys.readouterr().out
    assert "--consenti-immagini" in aiuto and "fuori dal tuo" in aiuto and "Per accenderle" not in aiuto
    r = subprocess.run([sys.executable, "-m", "impaginatore.mcp", "--versione"], capture_output=True, text=True, encoding="utf-8", cwd=processi.cartella_pacchetto(), timeout=60)
    assert r.returncode == 0 and r.stdout.startswith("Impaginatore ")
