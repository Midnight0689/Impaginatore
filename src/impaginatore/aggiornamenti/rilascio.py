"""Preparare una release firmata (T-207): manifesto, firma, e una release finta in una cartella per le prove.

Lo usa strumenti/aggiornamento.py (riga di comando, sul computer di chi pubblica) e lo usano i test. Nessuna funzione di
questo modulo gira nel programma dell'utente; la chiave privata (seme di 32 byte) arriva da fuori e non si salva mai qui.

    manifesto(pacchetto, novita=…)            byte di manifesto.json di una wheel (o di uno ZIP con impaginatore/)
    firma(seme, dati)                         testo di manifesto.json.sig
    pacchetto_da_sorgente(src, versione, d)   ZIP «come una wheel» della cartella del pacchetto, con __version__ cambiata (prove)
    release_finta(cartella, pacchetto, seme)  la cartella di una SorgenteFinta: risposta dell'API, asset, chiave di prova
Come si pubblica davvero: docs/architettura/AGGIORNAMENTI.md.
"""
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import stat
import zipfile

from .. import ed25519
from . import firmati, lanciatore

_INIT = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.M)


def file_del_pacchetto(pacchetto):
    """{nome: sha256} dei file sotto impaginatore/ del pacchetto; ValueError per collegamenti, doppioni, nomi non ammessi"""
    out = {}
    with zipfile.ZipFile(pacchetto) as z:
        for zi in z.infolist():
            if not zi.filename.startswith("impaginatore/") or zi.is_dir(): continue
            if stat.S_ISLNK(zi.external_attr >> 16) or zi.filename in out or not firmati.percorso_valido(zi.filename):
                raise ValueError(f"file non ammesso nel pacchetto: {zi.filename}")          # non tradotto: strumento di chi pubblica
            out[zi.filename] = hashlib.sha256(z.read(zi)).hexdigest()
    return out


def versione_del_pacchetto(pacchetto):
    with zipfile.ZipFile(pacchetto) as z: m = _INIT.search(z.read("impaginatore/__init__.py").decode("utf-8"))
    if not m or not lanciatore.valida(m.group(1)): raise ValueError("__version__ mancante o non valida nel pacchetto")          # non tradotto: strumento di chi pubblica
    return m.group(1)


def manifesto(pacchetto, novita=None, data=None, python_minimo="3.11", id_firma=1, tipo="python", altri=None):
    """byte di manifesto.json per il pacchetto (la versione è quella scritta nel pacchetto). altri: {tipo: {nome,
    dimensione, sha256}} per i pacchetti dei programmi compilati, quando ci saranno"""
    v = versione_del_pacchetto(pacchetto)
    with open(pacchetto, "rb") as f: h = hashlib.sha256(f.read()).hexdigest()
    m = dict(formato=1, prodotto="impaginatore", id_firma=id_firma, versione=v, data=data or dt.date.today().isoformat(),
             novita=novita or {"it": [], "en": []}, python_minimo=python_minimo,
             pacchetti=dict(altri or {}, **{tipo: dict(nome=os.path.basename(pacchetto), dimensione=os.path.getsize(pacchetto), sha256=h)}),
             file=file_del_pacchetto(pacchetto))
    dati = json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    firmati.controlla_campi(json.loads(dati))                      # lo stesso controllo del programma: un manifesto storto non esce
    return dati


def firma(seme, dati):
    """testo di manifesto.json.sig: firma Ed25519 di DOMINIO + i byte esatti del manifesto"""
    return ed25519.firma(seme, firmati.DOMINIO + dati).hex() + "\n"


def pacchetto_da_sorgente(sorgente, versione, cartella):
    """ZIP impaginatore-<versione>-py3-none-any.whl in cartella con i file della cartella del pacchetto `sorgente` (senza
    __pycache__) e __version__ = versione; più un .dist-info minimo, come una wheel. Per le prove e le release finte"""
    if not lanciatore.valida(versione): raise ValueError(f"versione non valida: {versione}")          # non tradotto: strumento di chi pubblica
    os.makedirs(cartella, exist_ok=True)
    dest = os.path.join(cartella, f"impaginatore-{versione}-py3-none-any.whl")
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for radice, dirs, files in os.walk(sorgente):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for f in sorted(files):
                if f.endswith((".pyc", ".pyo")): continue
                p = os.path.join(radice, f); rel = "impaginatore/" + os.path.relpath(p, sorgente).replace(os.sep, "/")
                with open(p, "rb") as fh: b = fh.read()
                if rel == "impaginatore/__init__.py": b = _INIT.sub(f'__version__ = "{versione}"', b.decode("utf-8"), count=1).encode("utf-8")
                z.writestr(rel, b)
        z.writestr(f"impaginatore-{versione}.dist-info/METADATA", f"Metadata-Version: 2.1\nName: impaginatore\nVersion: {versione}\n")
    return dest


def risposta_api(etichetta, asset, base_url):
    """dizionario come la risposta di GET /repos/{proprietario}/{nome}/releases/latest per questi asset {nome: percorso}"""
    voci = []
    for nome, p in sorted(asset.items()):
        with open(p, "rb") as f: h = hashlib.sha256(f.read()).hexdigest()
        voci.append(dict(name=nome, size=os.path.getsize(p), state="uploaded", content_type="application/octet-stream",
                         browser_download_url=f"{base_url}/{etichetta}/{nome}", digest=f"sha256:{h}"))
    return dict(tag_name=etichetta, name=etichetta, draft=False, prerelease=False, published_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), assets=voci)


def release_finta(cartella, pacchetto, seme, novita=None, repository="prova/impaginatore", id_firma=0):
    """prepara in cartella una release per SorgenteFinta: manifesto, firma, pacchetto, releases/latest.json e la chiave
    pubblica di prova (chiave-prova.txt: con id_firma 0 la accetta una versione di sviluppo). Restituisce la versione"""
    os.makedirs(os.path.join(cartella, "releases"), exist_ok=True)
    dati = manifesto(pacchetto, novita=novita, id_firma=id_firma)
    nome = os.path.basename(pacchetto); v = versione_del_pacchetto(pacchetto)
    if os.path.abspath(pacchetto) != os.path.abspath(os.path.join(cartella, nome)): shutil.copyfile(pacchetto, os.path.join(cartella, nome))
    with open(os.path.join(cartella, firmati.MANIFESTO), "wb") as f: f.write(dati)
    with open(os.path.join(cartella, firmati.FIRMA), "w", encoding="utf-8") as f: f.write(firma(seme, dati))
    with open(os.path.join(cartella, firmati.FILE_PROVA), "w", encoding="utf-8") as f: f.write(ed25519.pubblica(seme).hex() + "\n")
    asset = {n: os.path.join(cartella, n) for n in (firmati.MANIFESTO, firmati.FIRMA, nome)}
    with open(os.path.join(cartella, "releases", "latest.json"), "w", encoding="utf-8") as f:
        json.dump(risposta_api(f"v{v}", asset, f"https://github.com/{repository}/releases/download"), f, indent=1)
    return v
