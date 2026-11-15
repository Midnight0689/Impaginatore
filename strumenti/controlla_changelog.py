#!/usr/bin/env python3
"""Controlla la forma di CHANGELOG.md (regole in AGENTS.md) e, con --json, lo stampa come elenco di voci.

    python strumenti/controlla_changelog.py [--json] [percorso]

Esce con 1 se una voce non rispetta la forma o se un identificativo è ripetuto.
"""
import json
import re
import sys

TIPI = {"AGG": "Aggiunto", "MOD": "Modificato", "COR": "Corretto", "SIC": "Sicurezza", "RIM": "Rimosso", "DOC": "Documenti e contenuti"}
AREE = {"pacchetto", "aggiornamenti", "motore", "editor", "progetti", "piattaforma", "desktop", "licenze", "mcp", "test", "ci", "installer", "documenti", "brand", "mercato", "sito"}
VOCE = re.compile(r"^- `(?P<id>(?P<tipo>[A-Z]{3})-\d{3,})` \*\*(?P<area>[a-z]+)\*\* — (?P<testo>.+?) _File:_ (?P<file>`[^`]+`(?:, `[^`]+`)*)\.(?: _Rif:_ (?P<rif>`[^`]+`(?:, `[^`]+`)*)\.)?$")


def leggi(percorso):
    voci, errori, visti = [], [], set()
    versione = sezione = None
    with open(percorso, encoding="utf-8") as f:
        for n, riga in enumerate(f, 1):
            riga = riga.rstrip("\n")
            if riga.startswith("## "):
                versione, sezione = riga[3:].strip(), None
            elif riga.startswith("### "):
                sezione = riga[4:].strip()
                if sezione not in TIPI.values():
                    errori.append(f"riga {n}: sezione sconosciuta «{sezione}»")
            elif riga.startswith("- "):
                m = VOCE.match(riga)
                if not m:
                    errori.append(f"riga {n}: voce fuori forma")
                    continue
                d = m.groupdict()
                if d["tipo"] not in TIPI:
                    errori.append(f"riga {n}: tipo sconosciuto {d['tipo']}")
                elif TIPI[d["tipo"]] != sezione:
                    errori.append(f"riga {n}: {d['id']} sta sotto «{sezione}» invece di «{TIPI[d['tipo']]}»")
                if d["area"] not in AREE:
                    errori.append(f"riga {n}: area sconosciuta {d['area']}")
                if d["id"] in visti:
                    errori.append(f"riga {n}: identificativo ripetuto {d['id']}")
                visti.add(d["id"])
                voci.append({"id": d["id"], "tipo": d["tipo"], "area": d["area"], "versione": versione, "testo": d["testo"].rstrip(), "file": re.findall(r"`([^`]+)`", d["file"]), "rif": re.findall(r"`([^`]+)`", d["rif"] or "")})
    return voci, errori


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    voci, errori = leggi(args[0] if args else "CHANGELOG.md")
    if "--json" in argv:
        print(json.dumps(voci, ensure_ascii=False, indent=1))
    for e in errori:
        print(e, file=sys.stderr)
    if not errori and "--json" not in argv:
        print(f"registro in ordine: {len(voci)} voci")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
