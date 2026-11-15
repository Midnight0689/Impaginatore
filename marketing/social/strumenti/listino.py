"""Valori dei testi e delle grafiche: prezzi da docs/mercato/tier.json, date e link da costanti.json.

Fonte unica dei numeri del kit social. Gli altri script importano `valori(lingua)` e `sostituisci(testo, lingua)`.
Solo libreria standard.

Chiavi (si scrivono nei sorgenti come {{chiave}} e nelle grafiche come data-valore="chiave"):
    essenziale.listino  essenziale.lancio  essenziale.listino_ivato  essenziale.lancio_ivato  essenziale.computer
    pro.…  studio.…                               (stessi suffissi)
    frase.essenziale  frase.pro  frase.studio     «79 € fino al 23 aprile, poi 99 €»
    ore.1  ore.5  ore.10                          prezzi dei pacchetti di assistenza
    passaggio.essenziale_pro  passaggio.pro_studio  passaggio.essenziale_studio
    prova.giorni  rimborso.giorni  lancio.giorni  lancio.max_licenze  listino.versione
    più le chiavi di costanti.json (date, link, offerta Rosetta)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]
SOCIAL = RADICE / "marketing" / "social"
TIER = RADICE / "docs" / "mercato" / "tier.json"
COSTANTI = SOCIAL / "strumenti" / "costanti.json"
FASCE = ("essenziale", "pro", "studio")
SEGNAPOSTO = re.compile(r"\{\{\s*([a-z0-9_.]+)\s*\}\}")


def carica_tier() -> dict:
    return json.loads(TIER.read_text(encoding="utf-8"))


def carica_costanti() -> dict:
    return {k: v for k, v in json.loads(COSTANTI.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def euro(valore: float, lingua: str = "it") -> str:
    """49 → «49 €» in italiano, «€49» in inglese; i decimali solo se servono (96,38 €)."""
    intero = float(valore).is_integer()
    if lingua == "en":
        cifra = f"{valore:,.0f}" if intero else f"{valore:,.2f}"
        return f"€{cifra}"
    cifra = f"{valore:,.0f}" if intero else f"{valore:,.2f}"
    cifra = cifra.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{cifra} €"


def valori(lingua: str = "it") -> dict[str, str]:
    """Tutte le chiavi risolte per la lingua: i prezzi dal listino, il resto da costanti.json."""
    t = carica_tier()
    c = carica_costanti()
    v: dict[str, str] = {}
    for k, val in c.items():
        if k.endswith(".en"):
            continue
        v[k] = c.get(f"{k}.en", val) if lingua == "en" else val
    fine = v["data.fine_lancio"]
    for f in t["tiers"]:
        i = f["id"]
        v[f"{i}.listino"] = euro(f["prezzo_netto"], lingua)
        v[f"{i}.lancio"] = euro(f["prezzo_lancio"], lingua)
        v[f"{i}.listino_ivato"] = euro(f["prezzo_ivato"], lingua)
        v[f"{i}.lancio_ivato"] = euro(f["prezzo_lancio_ivato"], lingua)
        v[f"{i}.computer"] = str(f["attivazioni"])
        v[f"{i}.nome"] = f["nome"]
        modelli = f["funzioni"]["modelli_autore"]
        v[f"{i}.modelli_autore"] = str(modelli) if modelli is not True else ("tutti" if lingua == "it" else "all")
        if lingua == "en":
            v[f"frase.{i}"] = f"{v[f'{i}.lancio']} until {fine}, then {v[f'{i}.listino']}"
        else:
            v[f"frase.{i}"] = f"{v[f'{i}.lancio']} fino al {fine}, poi {v[f'{i}.listino']}"
    for p in t["assistenza"]["pacchetti"]:
        v[f"ore.{p['ore']}"] = euro(p["prezzo_netto"], lingua)
    for k, val in t["upgrade_tier_netto"].items():
        v[f"passaggio.{k}"] = euro(val, lingua)
    v["prova.giorni"] = str(t["prova"]["giorni"])
    v["rimborso.giorni"] = str(t["garanzia_rimborso_giorni"])
    v["lancio.giorni"] = str(t["lancio"]["durata_giorni"])
    v["lancio.max_licenze"] = str(t["lancio"]["max_licenze"])
    v["listino.versione"] = t["versione_listino"]
    # Confronto per categoria (mai per marchio): quanti mesi di un abbonamento da circa 20 € valgono una licenza.
    mese = float(c["confronto.abbonamento_mese"])
    for f in t["tiers"]:
        v[f"confronto.mesi_{f['id']}"] = str(round(f["prezzo_netto"] / mese))
        v[f"confronto.mesi_{f['id']}_lancio"] = str(round(f["prezzo_lancio"] / mese))
    # Prezzi dell'offerta Rosetta: non sono nel listino; vuoti finché il titolare non li approva.
    for k in ("prezzo_rosetta_pro", "prezzo_rosetta_studio"):
        if v.get(k):
            v[k] = euro(float(v[k]), lingua)
    return v


def importi_ammessi() -> dict[float, str]:
    """Ogni importo in euro che un testo può contenere, con la sua origine (per il controllo automatico)."""
    t = carica_tier()
    c = carica_costanti()
    ammessi: dict[float, str] = {}
    for f in t["tiers"]:
        ammessi[float(f["prezzo_netto"])] = f"{f['nome']} listino"
        ammessi[float(f["prezzo_lancio"])] = f"{f['nome']} lancio"
        ammessi[float(f["prezzo_ivato"])] = f"{f['nome']} listino con IVA"
        ammessi[float(f["prezzo_lancio_ivato"])] = f"{f['nome']} lancio con IVA"
    for p in t["assistenza"]["pacchetti"]:
        ammessi[float(p["prezzo_netto"])] = f"assistenza {p['ore']} ore"
    for k, val in t["upgrade_tier_netto"].items():
        ammessi.setdefault(float(val), f"passaggio {k}")
    for k in ("prezzo_rosetta_pro", "prezzo_rosetta_studio"):
        if c.get(k):
            ammessi.setdefault(float(c[k]), k)
    return ammessi


def sostituisci(testo: str, lingua: str = "it", lascia: bool = True) -> str:
    """Sostituisce i {{segnaposto}} noti. Quelli vuoti (link non ancora decisi) restano com'erano se `lascia`.

    Una chiave sconosciuta è un errore: un refuso non deve arrivare in un post.
    """
    v = valori(lingua)

    def sost(m: re.Match) -> str:
        k = m.group(1)
        if k not in v:
            raise KeyError(f"segnaposto sconosciuto: {{{{{k}}}}}")
        if v[k]:
            return v[k]
        if lascia:
            return m.group(0)
        raise KeyError(f"segnaposto senza valore: {{{{{k}}}}}")

    return SEGNAPOSTO.sub(sost, testo)


if __name__ == "__main__":
    for lingua in ("it", "en"):
        print(lingua, {k: x for k, x in valori(lingua).items() if not k.startswith("link") and x})
