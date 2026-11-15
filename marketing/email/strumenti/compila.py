"""Compila i sorgenti MJML in HTML pronto all'invio e controlla peso, link, testo alternativo e parole vietate.

Uso, dalla cartella marketing/email/:
    python3 strumenti/compila.py            # compila sorgenti/*.mjml in html/*.html e controlla
    python3 strumenti/compila.py --solo-controlli

MJML non sta nel repository: lo script usa la variabile MJML (percorso dell'eseguibile) se c'è,
altrimenti `npx -y mjml@4.18.0`, che lo scarica nella cache di npm.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CARTELLA = Path(__file__).resolve().parents[1]
SORGENTI = CARTELLA / "sorgenti"
HTML = CARTELLA / "html"
TESTO = CARTELLA / "testo"

LIMITE_GMAIL = 102 * 1024  # Gmail taglia i messaggi con HTML oltre circa 102 KB
SOGLIA_PRUDENTE = 80 * 1024  # margine per i link tracciati che il servizio aggiunge

# Parole e forme che la marca vieta (STYLEBOOK §4-5) o che i filtri antispam puniscono.
VIETATE = [
    r"!", r"\brivoluzionari", r"\bmagic", r"\bmagia\b", r"in un (solo )?click", r"facilissim", r"il migliore",
    r"imperdibil", r"ultimi posti", r"potenziat[oa] dall", r"\bseamless\b", r"game changer", r"\bworkflow\b",
    r"\btemplate\b", r"\bsogno\b", r"\bfavola\b", r"giorno più bello", r"\bunico\b", r"\bunica\b", r"(è|sono|siamo) (il|i) prim[oi]\b", r"il primo (programma|software|impaginatore)",
    r"\bobsolet", r"\bgratis!", r"\bAI-powered\b", r"\beffortless\b", r"\bstunning\b", r"\bunleash\b",
    r"\belevate\b", r"next-level", r"lifetime deal", r"in seconds", r"\b(is|are|was) the first\b", r"\bthe (first|only) (app|software|program|tool|album)",
    r"<s>|<strike>|<del>|line-through",
]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕]")


def mjml() -> list[str]:
    if os.environ.get("MJML"):
        return shlex.split(os.environ["MJML"])
    return ["npx", "-y", "mjml@4.18.0"]


def compila() -> None:
    HTML.mkdir(exist_ok=True)
    for sorgente in sorted(SORGENTI.glob("*.mjml")):
        destinazione = HTML / (sorgente.stem + ".html")
        cmd = mjml() + [str(sorgente), "-o", str(destinazione), "--config.validationLevel=strict",
                        "--config.beautify=false", "--config.minify=false"]
        r = subprocess.run(cmd, cwd=SORGENTI, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"{sorgente.name}: errore MJML\n{r.stdout}\n{r.stderr}")
        pulisci(destinazione)


def pulisci(percorso: Path) -> None:
    """Toglie i commenti dei sorgenti (non quelli condizionali per Outlook) e le righe vuote."""
    t = percorso.read_text(encoding="utf-8")
    # Restano: <!--[if …]>, <!--<![endif]--> e il <!--> dei blocchi «non Outlook».
    t = re.sub(r"<!--(?!\[if)(?!<!\[endif\])(?!>).*?-->", "", t, flags=re.S)
    t = re.sub(r"\n\s*\n+", "\n", t)
    # MJML riduce alt="" (immagine decorativa) a un attributo nudo: lo si riscrive per i client più vecchi.
    t = re.sub(r'(<img\b[^>]*?\s)alt(?=[\s>])', r'\1alt=""', t)
    percorso.write_text(t, encoding="utf-8")


def testo_visibile(html: str) -> str:
    t = re.sub(r"<(style|head)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def controlla() -> int:
    problemi = 0
    print(f"{'modello':32} {'peso':>9}  immagini  link  esito")
    for h in sorted(HTML.glob("*.html")):
        html = h.read_text(encoding="utf-8")
        peso = len(html.encode("utf-8"))
        note = []
        if peso > SOGLIA_PRUDENTE:
            note.append(f"oltre {SOGLIA_PRUDENTE // 1024} KB")
        if peso > LIMITE_GMAIL:
            note.append("OLTRE IL LIMITE DI GMAIL")
        img = re.findall(r"<img\b[^>]*>", html, flags=re.I)
        for i in img:
            if not re.search(r'\balt="', i):
                note.append("immagine senza alt")
            if not re.search(r'\bwidth="\d+', i) or not re.search(r'\bheight="\d+', i):
                note.append("immagine senza width/height")
        link = re.findall(r'<a\b[^>]*href="([^"]*)"', html, flags=re.I)
        for l in link:
            if not (l.startswith("{{") or l.startswith("mailto:{{") or l.startswith("https://")):
                note.append(f"link sospetto: {l[:60]}")
        if 'lang="' not in html[:300]:
            note.append("manca lang")
        if "display:none;max-height:0" not in html:
            note.append("manca il preheader")
        visibile = testo_visibile(html)
        for v in VIETATE:
            m = re.search(v, visibile, flags=re.I)
            if m:
                note.append(f"parola da evitare: «{visibile[max(0, m.start() - 30):m.end() + 30].strip()}»")
        if EMOJI.search(visibile):
            note.append("emoji")
        t = TESTO / (h.stem + ".txt")
        if not t.exists():
            note.append("manca la versione solo testo")
        else:
            tt = t.read_text(encoding="utf-8")
            if len(tt.strip()) < 200:
                note.append("versione solo testo vuota o troppo corta")
            for v in VIETATE:
                if v not in ("!",) and re.search(v, tt, flags=re.I):
                    note.append(f"testo: parola da evitare /{v}/")
            if "!" in tt:
                note.append("testo: punto esclamativo")
        problemi += bool(note)
        print(f"{h.stem:32} {peso / 1024:7.1f} KB  {len(img):8}  {len(link):4}  {'ok' if not note else '; '.join(dict.fromkeys(note))}")
    return 1 if problemi else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--solo-controlli", action="store_true")
    a = p.parse_args()
    if not a.solo_controlli:
        compila()
    return controlla()


if __name__ == "__main__":
    sys.exit(main())
