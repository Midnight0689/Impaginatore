#!/usr/bin/env python3
"""Prepara la cartella di una release (T-302): pacchetti dei tre sistemi, wheel, manifesto firmato, SHA256SUMS e note.

Gira sul computer di chi pubblica, MAI nella pipeline: la firma usa la chiave privata dei rilasci, che sta fuori dal
repository (strumenti/aggiornamento.py, docs/architettura/AGGIORNAMENTI.md). I pacchetti arrivano dalla pipeline
«Pacchetti» (.github/workflows/pacchetti.yml): si scaricano i suoi artefatti in una cartella e si passano qui.

    python strumenti/rilascio.py controlla
        cosa manca per un rilascio vero: chiavi pubbliche (licenze e aggiornamenti), repository delle release, versione
        finale, sezione della versione in CHANGELOG.md
    python strumenti/rilascio.py prepara CARTELLA_ARTEFATTI [--uscita dist/rilascio-<v>] [--dir CHIAVI] [--id 1]
                                         [--novita-it "…"] [--novita-en "…"] [--prova]
        cerca nella cartella (anche nelle sottocartelle) la wheel impaginatore-<v>-py3-none-any.whl e i pacchetti
        Impaginatore-<v>-<sistema>.<dmg|exe|deb>; li copia in --uscita, firma il manifesto con tutti i pacchetti, scrive
        SHA256SUMS (formato di sha256sum) e NOTE.md (da CHANGELOG.md, con le impronte). --prova: va avanti anche se
        «controlla» trova problemi (la release dice in testa che è una prova e non va pubblicata)

Si pubblica a mano: release su GitHub con tag v<v>, i file di --uscita come asset (AGGIORNAMENTI.md, «Come si pubblica»).
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "src")); sys.path.insert(0, str(Path(__file__).resolve().parent))

import aggiornamento  # noqa: E402
import controlla_changelog  # noqa: E402

from impaginatore.aggiornamenti import firmati, lanciatore, rilascio, sorgenti  # noqa: E402
from impaginatore.licenze import chiave as chiave_licenze  # noqa: E402

SISTEMI = ("mac-arm64", "mac-x86_64", "windows", "linux")
ESTENSIONI = {"mac-arm64": "dmg", "mac-x86_64": "dmg", "windows": "exe", "linux": "deb"}
GUIDA = "docs/manuale/00-installazione.md"


def problemi(versione, changelog=RADICE / "CHANGELOG.md", chiavi_aggiornamenti=None, chiavi_licenze=None, repository=None):
    """motivi per cui la versione non si può pubblicare (vuoto = pronta)"""
    out = list(firmati.problemi_per_il_rilascio(chiavi_aggiornamenti)) + list(chiave_licenze.problemi_per_il_rilascio(chiavi_licenze))
    if not (sorgenti.REPOSITORY if repository is None else repository): out.append("REPOSITORY in aggiornamenti/sorgenti.py è vuoto: i programmi non cercherebbero le versioni nuove")
    if lanciatore.di_sviluppo(versione): out.append(f"la versione {versione} è di sviluppo o di prova: per un rilascio serve una versione finale (src/impaginatore/__init__.py)")
    voci, errori = controlla_changelog.leggi(str(changelog))
    if errori: out.append(f"CHANGELOG.md non è in forma: {errori[0]}")
    if not any(v.get("versione", "").startswith(f"[{versione}]") for v in voci): out.append(f"CHANGELOG.md non ha la sezione «## [{versione}]»")
    return out


def trova(cartella, versione):
    """(wheel, {sistema: pacchetto}) della versione nella cartella degli artefatti"""
    tutti = [p for p in Path(cartella).rglob("*") if p.is_file()]
    ruote = [p for p in tutti if p.name == f"impaginatore-{versione}-py3-none-any.whl"]
    if len(ruote) != 1: raise SystemExit(f"Serve una e una sola wheel impaginatore-{versione}-py3-none-any.whl in {cartella} (trovate {len(ruote)}): «uv build --wheel»")
    pacchetti = {}
    for s in SISTEMI:
        trovati = [p for p in tutti if p.name == f"Impaginatore-{versione}-{s}.{ESTENSIONI[s]}"]
        if len(trovati) > 1: raise SystemExit(f"Più pacchetti {s} in {cartella}: {trovati}")
        if trovati: pacchetti[s] = trovati[0]
    altri = sorted({p.name for p in tutti if re.fullmatch(r"Impaginatore-.+\.(dmg|exe|deb)", p.name)} - {p.name for p in pacchetti.values()})
    if altri: raise SystemExit(f"Pacchetti di un'altra versione (questa è la {versione}): {altri}")
    if not pacchetti: raise SystemExit(f"Nessun pacchetto Impaginatore-{versione}-… in {cartella}")
    return ruote[0], pacchetti


def sezione_changelog(versione, changelog=RADICE / "CHANGELOG.md"):
    """le righe della sezione «## [versione]» di CHANGELOG.md (o di «[Non rilasciato]» se non c'è ancora)"""
    righe, dentro, out = changelog.read_text(encoding="utf-8").splitlines(), False, []
    for nome in (f"[{versione}]", "[Non rilasciato]"):
        for r in righe:
            if r.startswith("## "): dentro = r[3:].strip().startswith(nome)
            elif dentro: out.append(r)
        if out: return out
    return out


def impronta(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def note(versione, impronte, problemi_trovati, mancanti, changelog=RADICE / "CHANGELOG.md"):
    t = []
    if problemi_trovati: t += ["> **PROVA: NON PUBBLICARE.** Mancano:", *[f"> - {p}" for p in problemi_trovati], ""]
    t += [f"# Impaginatore {versione}", "", f"Come si installa, sistema per sistema, e cosa dicono gli avvisi del sistema: `{GUIDA}`.",
          "I pacchetti non sono firmati con un certificato Apple o Microsoft: al primo avvio macOS e Windows mostrano un avviso, come spiega la guida.", ""]
    if mancanti: t += [f"Questa versione non ha il pacchetto per: {', '.join(mancanti)}.", ""]
    t += ["## Novità", "", *[r for r in sezione_changelog(versione, changelog) if r.strip()], "", "## Impronte SHA-256", "",
          "Il file scaricato deve avere esattamente questa impronta (la guida spiega come controllarla):", "", "```", *impronte, "```", ""]
    return "\n".join(t)


def cmd_controlla(a):
    from impaginatore import __version__
    p = problemi(__version__)
    for x in p: print(f"- {x}")
    print("Pronta per il rilascio." if not p else f"Versione {__version__}: {len(p)} cose da sistemare prima di un rilascio.")
    return 0 if not p else 1


def cmd_prepara(a):
    wheel_in = [p for p in Path(a.artefatti).rglob("impaginatore-*-py3-none-any.whl")]
    if len(wheel_in) != 1: raise SystemExit(f"Serve una e una sola wheel del programma in {a.artefatti} (trovate {len(wheel_in)}): «uv build --wheel»")
    versione = rilascio.versione_del_pacchetto(str(wheel_in[0]))
    trovati = problemi(versione)
    if trovati and not a.prova:
        for x in trovati: print(f"- {x}", file=sys.stderr)
        raise SystemExit("La versione non è pronta per il rilascio (sopra cosa manca). Con --prova si prepara lo stesso, da non pubblicare.")
    wheel, pacchetti = trova(a.artefatti, versione)
    uscita = Path(a.uscita or RADICE / "dist" / f"rilascio-{versione}").resolve()
    if uscita.exists() and any(uscita.iterdir()): raise SystemExit(f"{uscita} non è vuota")
    uscita.mkdir(parents=True, exist_ok=True)
    copie = [Path(shutil.copy2(p, uscita / p.name)) for p in (wheel, *pacchetti.values())]
    aggiornamento.cmd_firma(SimpleNamespace(dir=a.dir, id=a.id, pacchetto=str(uscita / wheel.name), uscita=str(uscita), novita_it=a.novita_it, novita_en=a.novita_en,
                                            python_minimo=a.python_minimo, compilato=[f"{k}={uscita / p.name}" for k, p in pacchetti.items()]))
    m = json.loads((uscita / firmati.MANIFESTO).read_bytes())
    pub = (firmati.CHIAVI_FIDATE.get(a.id) if firmati.pubblica(firmati.CHIAVI_FIDATE.get(a.id)) else None) or aggiornamento.ed25519.pubblica(aggiornamento.leggi_privata(aggiornamento.cartella(a.dir), a.id)).hex()
    firmati.verifica((uscita / firmati.MANIFESTO).read_bytes(), (uscita / firmati.FIRMA).read_bytes(), {a.id: pub})
    tutti = sorted([*copie, uscita / firmati.MANIFESTO, uscita / firmati.FIRMA], key=lambda p: p.name)
    impronte = [f"{impronta(p)}  {p.name}" for p in tutti]
    (uscita / "SHA256SUMS").write_text("\n".join(impronte) + "\n", encoding="utf-8")
    mancanti = [s for s in SISTEMI if s not in pacchetti]
    (uscita / "NOTE.md").write_text(note(versione, impronte, trovati, mancanti), encoding="utf-8")
    print(f"Release {versione} in {uscita}: {', '.join(sorted(m['pacchetti']))}" + (f"; senza {', '.join(mancanti)}" if mancanti else ""))
    if trovati: print("PROVA: non pubblicare (vedi NOTE.md).")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rilascio", description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="comando", required=True)
    sub.add_parser("controlla")
    p = sub.add_parser("prepara"); p.add_argument("artefatti"); p.add_argument("--uscita"); p.add_argument("--dir"); p.add_argument("--id", type=int, default=1)
    p.add_argument("--novita-it", action="append", default=[]); p.add_argument("--novita-en", action="append", default=[]); p.add_argument("--python-minimo", default="3.11")
    p.add_argument("--prova", action="store_true")
    a = ap.parse_args(argv)
    try: return {"controlla": cmd_controlla, "prepara": cmd_prepara}[a.comando](a)
    except (OSError, ValueError, KeyError) as e: raise SystemExit(f"Errore: {e}") from None


if __name__ == "__main__":
    sys.exit(main())
