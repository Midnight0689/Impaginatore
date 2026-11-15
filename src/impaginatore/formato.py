"""Formato di salvataggio dei progetti: l'unico modulo che legge e scrive spec.py (e i file JSON del progetto).

Un progetto è una cartella con:
    progetto.json    impostazioni, correzioni, testi, guide (JSON, UTF-8)
    spec.py          impaginazione: SPREADS = [ (pagina sinistra, pagina destra), ... ] scritta con le funzioni del motore
                     (P, FULL, FREE, TEXT, ROT, STY...): è codice Python, il formato delle versioni 1.x, che resta invariato
    album_libere.py, testo.py, vib_lut.npz    copie del motore messe accanto a spec.py quando ci sono cornici libere,
                     angoli o testi (servono agli script 1.x: il programma usa sempre le sue)
    Foto/, _cache/, _backup_editor/, PSD/, Esportazioni/

Punto di estensione: un formato futuro (es. JSON puro) si aggiunge qui accanto, lasciando carica() capace di leggere spec.py.
"""
import json
import os
import re
import shutil
import sys
import time
import types

SPEC = "spec.py"
PROGETTO = "progetto.json"
_SPREAD_RE = re.compile(r"^\s*# \d+\s*$", re.M)          # ogni spread salvato comincia con «# n»


# ---------------------------------------------------------------- file
def leggi_json(path):
    with open(path, encoding="utf-8") as f: return json.load(f)


def scrivi_json(path, dati, **kw):
    """come json.dump (stessi argomenti), sempre in UTF-8"""
    with open(path, "w", encoding="utf-8") as f: json.dump(dati, f, **kw)


def scrivi_atomico(path, testo):
    """scrive il file in modo sicuro: prima in un file temporaneo, poi lo sostituisce, così un blocco a metà non lo rovina"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: f.write(testo); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


# ---------------------------------------------------------------- lettura
def carica(cartella):
    """SPREADS del spec.py della cartella del progetto. Il motore (impaginatore.motore.album) dev'essere già caricato con
    lo stesso progetto: spec.py usa i suoi nomi delle foto e la sua geometria."""
    from .motore import compat
    compat.installa()                                   # «from album import *» e «from album_libere import *» -> moduli del pacchetto
    path = os.path.join(os.path.abspath(cartella), SPEC)
    with open(path, "rb") as f: codice = compile(f.read(), path, "exec")       # niente __pycache__ nella cartella del progetto
    mod = types.ModuleType("spec"); mod.__file__ = path
    sys.path.insert(0, os.path.dirname(path))           # come nelle 1.x: uno spec scritto a mano può importare file del progetto
    bc, sys.dont_write_bytecode = sys.dont_write_bytecode, True        # ...ma senza lasciare __pycache__ nella cartella del progetto
    try: exec(codice, mod.__dict__)
    finally:
        sys.dont_write_bytecode = bc
        try: sys.path.remove(os.path.dirname(path))
        except ValueError: pass
    return mod.SPREADS


def conta_spread(cartella):
    """numero di spread di un progetto senza caricarlo (per l'elenco della home)"""
    p = os.path.join(cartella, SPEC)
    if not os.path.exists(p): return 0
    with open(p, encoding="utf-8", errors="replace") as f: return len(_SPREAD_RE.findall(f.read()))


# ---------------------------------------------------------------- scrittura
def spec_vuota(nome):
    """spec.py di un progetto nuovo"""
    return f'"""{nome}: 0 spread."""\nfrom album import *\n\nSPREADS = [\n]\n'


def is_txt(it): return it["k"] == "t" and it.get("kind") == "txt"                # livelli di testo (strumento Testo)


def ha_liberi(spreads):
    """True se l'impaginazione usa cornici libere, angoli, bordi/ombre/opacità o testi liberi: allora spec.py ha bisogno
    di album_libere.py"""
    return any(it["k"] == "f" or it.get("a") or it.get("bd") or it.get("sh") or it.get("oc", 100) < 100 or "fx" in it for sp in spreads for pg in sp for it in pg[1])


def _lead(it):
    from .motore import testo
    return testo.lead(it)


def fmt0(it, nome_foto):
    """un elemento come chiamata del motore (senza angolo e stile)"""
    if is_txt(it):
        return ("TEXT(%r, %s, %s, %s, %s, font=%r, size=%s, col=%r, al=%r, tr=%s, auto=%s" % (it["tx"], it["fx"], it["fy"], it["fw"], it["fh"], it["font"], it["size"], tuple(it["col"]), it["al"], it["tr"], bool(it.get("auto", True)))) + (f', lh={_lead(it)}' if _lead(it) != 1.2 else "") + (", caps=True" if it.get("caps") else "") + (f', zo={it["zo"]}' if it.get("zo") is not None else "") + (f', stile={it["stile"]!r}' if it.get("stile") else "") + ")"
    if it["k"] == "t":
        if "fx" in it: return f'TXTF({it["kind"]!r}, {it["fx"]}, {it["fy"]}, {it["fw"]}, {it["fh"]}, ts={it.get("ts", 1.0)}' + (f', zo={it["zo"]}' if it.get("zo") is not None else "") + ")"
        return f'TXT({it["kind"]!r}, {it["c"]}, {it["r"]}, {it["w"]}, {it["h"]})'
    n = nome_foto(it["i"]); ex = (", bw=True" if it.get("bw") else "") + (f', z={it["z"]}' if it.get("z", 1.0) != 1.0 else "") + (f', zo={it["zo"]}' if it["k"] == "f" and it.get("zo") is not None else "")
    if it["k"] == "full": return f"FULL({n!r}{ex})"
    if it["k"] == "f": return f'FREE({n!r}, {it["x"]}, {it["y"]}, {it["w"]}, {it["h"]}{ex})'
    return f'P({n!r}, {it["c"]}, {it["r"]}, {it["w"]}, {it["h"]}{ex})'


def fmt(it, nome_foto):
    """un elemento come chiamata del motore, con angolo (ROT) e stile (STY)"""
    x = fmt0(it, nome_foto)
    if it["k"] != "t" and (it.get("bd") or it.get("sh") or it.get("oc", 100) < 100): x = f'STY({x}, bd={tuple(it["bd"]) if it.get("bd") else None!r}, sh={int(it.get("sh") or 0)}, oc={int(it.get("oc", 100))})'
    return f'ROT({x}, {it["a"]})' if it["k"] != "t" and it.get("a") else x


def testo_spec(spreads, nome, nome_foto, quando=None):
    """contenuto di spec.py per l'impaginazione `spreads` ([[modo, [elementi]], [modo, [elementi]]] per spread);
    nome_foto(i) dà il nome del file (senza estensione) della foto numero i"""
    quando = time.strftime("%d/%m/%Y %H:%M") if quando is None else quando
    liberi = ha_liberi(spreads)
    lines = [f'"""{nome}: {len(spreads)} spread. Salvato dall\'editor il {quando}."""', "from album import *"]
    if liberi: lines.append("from album_libere import *     # cornici libere FREE(...) e angoli ROT(...): serve questo file, sta nella cartella del progetto")
    lines += ["", "SPREADS = ["]
    for k, sp in enumerate(spreads, 1):
        pages = [f'{pg[0]}(' + ", ".join(fmt(it, nome_foto) for it in pg[1]) + ")" for pg in sp]
        lines.append(f"    # {k}\n    ({pages[0]},\n     {pages[1]}),")
    lines.append("]")
    return "\n".join(lines) + "\n"


def copia_motore(cartella):
    """mette accanto a spec.py le copie di album_libere.py, testo.py e vib_lut.npz (formato 1.x: chi apre il progetto con
    gli script delle versioni 1.x le trova lì)"""
    from . import risorse
    mot = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motore")
    shutil.copy2(os.path.join(mot, "album_libere.py"), os.path.join(cartella, "album_libere.py"))
    shutil.copy2(os.path.join(mot, "testo.py"), os.path.join(cartella, "testo.py"))
    shutil.copy2(risorse.percorso("vib_lut.npz"), os.path.join(cartella, "vib_lut.npz"))


def salva(cartella, spreads, nome, nome_foto, quando=None):
    """scrive spec.py (in modo atomico) e, se servono, le copie del motore"""
    if ha_liberi(spreads): copia_motore(cartella)
    scrivi_atomico(os.path.join(cartella, SPEC), testo_spec(spreads, nome, nome_foto, quando))
