#!/usr/bin/env python3
"""Prepara e controlla le release firmate degli aggiornamenti (T-207). Come si pubblica: docs/architettura/AGGIORNAMENTI.md.

Gira sul computer di chi pubblica, con il programma installato nell'ambiente (uv run). La chiave privata dei rilasci
NON sta nel repository: vive nella cartella indicata da --dir, oppure da IMPAGINATORE_NEGOZIO_DIR, oppure in
~/.impaginatore-negozio (la stessa delle chiavi di licenza, in un file a parte). Va salvata anche offline.

Comandi:
  genera-coppia   crea la chiave dei rilasci (una volta sola) e stampa la pubblica da compilare in aggiornamenti/firmati.py
  firma           scrive manifesto.json e manifesto.json.sig accanto al pacchetto (la wheel costruita con «uv build»);
                  --compilato chiave=file aggiunge al manifesto i pacchetti del programma compilato (strumenti/compila.py)
  verifica        controlla firma, campi e impronte di una cartella con manifesto, firma e pacchetti
  finta           prepara una release finta per le prove (IMPAGINATORE_AGGIORNAMENTI_FINTI), con una chiave di prova

Esempi:
  uv run python strumenti/aggiornamento.py genera-coppia
  uv build --wheel
  uv run python strumenti/aggiornamento.py firma dist/impaginatore-2.0.1-py3-none-any.whl --novita-it "Esportazione più veloce" --novita-en "Faster export"
  uv run python strumenti/aggiornamento.py verifica dist --pubblica <64 cifre>
  uv run python strumenti/aggiornamento.py finta /tmp/release-finta --versione 2.0.1
"""
import argparse
import json
import os
import secrets
import stat
import sys
from pathlib import Path

from impaginatore import ed25519
from impaginatore.aggiornamenti import firmati, rilascio

RADICE_REPO = Path(__file__).resolve().parent.parent
FILE = "aggiornamenti-privata-{}.hex"


def cartella(arg):
    d = Path(arg or os.environ.get("IMPAGINATORE_NEGOZIO_DIR") or Path.home() / ".impaginatore-negozio").expanduser().resolve()
    if d == RADICE_REPO or RADICE_REPO in d.parents: raise SystemExit(f"Errore: {d} è dentro il repository. La chiave privata deve stare fuori.")
    return d


def leggi_privata(d, id_firma):
    f = d / FILE.format(id_firma)
    if not f.exists(): raise SystemExit(f"Nessuna chiave dei rilasci {id_firma} in {d}: eseguire prima «genera-coppia».")
    if os.name == "posix" and f.stat().st_mode & 0o077: print(f"Attenzione: {f} è leggibile da altri utenti (chmod 600).", file=sys.stderr)
    seme = bytes.fromhex(f.read_text().strip())
    if len(seme) != 32: raise SystemExit("Chiave privata corrotta.")
    return seme


def cmd_genera_coppia(a):
    d = cartella(a.dir); d.mkdir(parents=True, exist_ok=True)
    if os.name == "posix": os.chmod(d, 0o700)
    f = d / FILE.format(a.id)
    if f.exists(): print(f"Esiste già la chiave dei rilasci {a.id} in {d}: per una rotazione usare --id {a.id + 1}.", file=sys.stderr); return 1
    seme = secrets.token_bytes(32)
    fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w") as h: h.write(seme.hex() + "\n")
    print(f"Chiave privata dei rilasci {a.id} scritta in {f} (solo lettura per te).")
    print("FARNE SUBITO UNA COPIA OFFLINE: senza, le copie già installate non accettano più aggiornamenti.")
    print("\nChiave pubblica da compilare in src/impaginatore/aggiornamenti/firmati.py (non è un segreto):")
    print(f'  CHIAVI_FIDATE = {{{a.id}: "{ed25519.pubblica(seme).hex()}"}}')
    return 0


CHIAVI_COMPILATI = ("mac-arm64", "mac-x86_64", "windows", "linux", "linux-arm64")      # installazione.chiave_pacchetto()


def compilati(voci):
    """{chiave: {nome, dimensione, sha256}} dai --compilato chiave=file (una chiave di CHIAVI_COMPILATI)"""
    out = {}
    for v in voci:
        k, _, f = v.partition("=")
        if k not in CHIAVI_COMPILATI or not f: raise ValueError(f"--compilato vuole chiave=file ({', '.join(CHIAVI_COMPILATI)}): {v}")
        p = Path(f).resolve()
        out[k] = dict(nome=p.name, dimensione=p.stat().st_size, sha256=firmati.sha256_file(str(p)))
    return out


def cmd_firma(a):
    seme = leggi_privata(cartella(a.dir), a.id)
    pacchetto = Path(a.pacchetto).resolve(); uscita = Path(a.uscita or pacchetto.parent).resolve()
    dati = rilascio.manifesto(str(pacchetto), novita={"it": a.novita_it, "en": a.novita_en}, python_minimo=a.python_minimo, id_firma=a.id, altri=compilati(a.compilato))
    uscita.mkdir(parents=True, exist_ok=True)
    (uscita / firmati.MANIFESTO).write_bytes(dati)
    (uscita / firmati.FIRMA).write_text(rilascio.firma(seme, dati), encoding="utf-8")
    m = json.loads(dati)
    print(f"Versione {m['versione']}: {len(m['file'])} file, pacchetto {m['pacchetti']['python']['nome']} ({m['pacchetti']['python']['dimensione']} byte).")
    altri = [p["nome"] for k, p in sorted(m["pacchetti"].items()) if k != "python"]
    print(f"Da caricare nella release v{m['versione']} su GitHub: {', '.join([pacchetto.name, *altri])}, {firmati.MANIFESTO}, {firmati.FIRMA} (in {uscita}).")
    return 0


def cmd_verifica(a):
    d = Path(a.cartella)
    m = firmati.verifica((d / firmati.MANIFESTO).read_bytes(), (d / firmati.FIRMA).read_bytes(), {a.id: a.pubblica})
    for k, p in sorted(m["pacchetti"].items()):
        f = d / p["nome"]
        if not f.exists() or f.stat().st_size != p["dimensione"] or firmati.sha256_file(str(f)) != p["sha256"]: raise SystemExit(f"Il pacchetto {f} ({k}) non è quello del manifesto.")
    if rilascio.file_del_pacchetto(str(d / m["pacchetti"]["python"]["nome"])) != m["file"]: raise SystemExit("I file del pacchetto non sono quelli del manifesto.")
    print(f"Firma e impronte valide: versione {m['versione']}, {len(m['file'])} file, pacchetti {', '.join(sorted(m['pacchetti']))}.")
    return 0


def cmd_finta(a):
    d = Path(a.cartella).resolve()
    seme = bytes.fromhex(a.seme) if a.seme else secrets.token_bytes(32)
    pk = rilascio.pacchetto_da_sorgente(str(RADICE_REPO / "src" / "impaginatore"), a.versione, str(d))
    v = rilascio.release_finta(str(d), pk, seme, novita={"it": a.novita_it or [f"Versione di prova {a.versione}"], "en": a.novita_en or [f"Test version {a.versione}"]})
    print(f"Release finta {v} in {d}. Per provarla: IMPAGINATORE_AGGIORNAMENTI_FINTI={d} uv run impaginatore")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aggiornamento", description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="comando", required=True)
    g = sub.add_parser("genera-coppia"); g.add_argument("--dir"); g.add_argument("--id", type=int, default=1)
    f = sub.add_parser("firma"); f.add_argument("pacchetto"); f.add_argument("--dir"); f.add_argument("--id", type=int, default=1); f.add_argument("--uscita")
    f.add_argument("--novita-it", action="append", default=[]); f.add_argument("--novita-en", action="append", default=[]); f.add_argument("--python-minimo", default="3.11")
    f.add_argument("--compilato", action="append", default=[], metavar="CHIAVE=FILE", help="pacchetto del programma compilato (si può ripetere)")
    v = sub.add_parser("verifica"); v.add_argument("cartella"); v.add_argument("--pubblica", required=True); v.add_argument("--id", type=int, default=1)
    t = sub.add_parser("finta"); t.add_argument("cartella"); t.add_argument("--versione", required=True); t.add_argument("--seme", help="32 byte in esadecimale (di serie: a caso)")
    t.add_argument("--novita-it", action="append", default=[]); t.add_argument("--novita-en", action="append", default=[])
    a = ap.parse_args(argv)
    try: return {"genera-coppia": cmd_genera_coppia, "firma": cmd_firma, "verifica": cmd_verifica, "finta": cmd_finta}[a.comando](a)
    except (OSError, ValueError, KeyError) as e: raise SystemExit(f"Errore: {e}") from None


if __name__ == "__main__":
    sys.exit(main())
