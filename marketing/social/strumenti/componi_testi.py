"""Compone i testi del kit social dai sorgenti: CALENDARIO.md, CALENDARIO.csv e COPIONI.md.

Uso, dalla radice del repository:
    python3 marketing/social/strumenti/componi_testi.py              # riscrive i tre file
    python3 marketing/social/strumenti/componi_testi.py --controlla  # esce con 1 se non sono aggiornati

Sorgenti: sorgenti/uscite.txt (un blocco «=== ID» per uscita) e sorgenti/copioni.md.
Prezzi, date e link: {{chiave}} risolte da listino.py (docs/mercato/tier.json e costanti.json).
Un link ancora vuoto resta scritto {{link_…}}: il README spiega dove riempirlo. Solo libreria standard.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import listino  # noqa: E402

SOCIAL = listino.SOCIAL
SORGENTI = SOCIAL / "sorgenti"
USCITE = SORGENTI / "uscite.txt"
COPIONI_SORGENTE = SORGENTI / "copioni.md"
CALENDARIO_MD = SOCIAL / "CALENDARIO.md"
CALENDARIO_CSV = SOCIAL / "CALENDARIO.csv"
COPIONI_MD = SOCIAL / "COPIONI.md"

INIZIO_S0 = dt.date(2027, 2, 22)  # S0 = settimana del lancio (marketing/lancio/PIANO-90-GIORNI.md §5)
MARCATORE_MCP = "da pubblicare solo dopo il rilascio del server MCP"
CAMPI = ("data", "ora", "canale", "formato", "pilastro", "modello", "grafica", "cta", "link", "hashtag", "hashtag_en",
         "importante", "mcp", "titolo", "titolo_en", "note")
GIORNI = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
MESI = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre")
PILASTRI = ("Mestiere", "Le foto restano tue", "Resta tuo", "Bottega", "Assistenza e prova")

# Che cosa prevede il piano di lancio per ogni settimana (PIANO-90-GIORNI §5), riassunto per chi pubblica.
PIANO = {
    "S-3": "Proposte a podcast e riviste, accordi con 5 educator, materiali per la Convention.",
    "S-2": "Email «data» alla lista d’attesa; codici di segnalazione ai beta tester; ultimo controllo dei testi.",
    "S-1": "Versione di lancio congelata. Domenica 21: accesso anticipato di 48 ore per la lista d’attesa.",
    "S0": "Lancio martedì 23 alle 9; Convention ANFM a Padova da mercoledì 24 a sabato 27.",
    "S1": "Seguito ai contatti della Convention; «1 ora per partire» a chi ha appena comprato.",
    "S2": "Caso di studio di un beta tester; spinta sulle segnalazioni.",
    "S3": "Controllo dei piloti; primo webinar con un laboratorio.",
    "S4": "Bilancio di metà lancio. Pasqua il 28/03: niente uscite il 28 e il 29.",
    "S5": "Offerta Rosetta, con i testi rivisti dal legale; podcast e riviste; forum.",
    "S6": "Contenuti degli educator, con i loro codici di affiliazione.",
    "S7": "Promemoria onesto sulla fine del prezzo di lancio; pacchetto «inizio stagione: 5 ore».",
    "S8": "Fine del prezzo di lancio venerdì 23 aprile a mezzanotte, o prima a 300 licenze.",
}
TESTA = "> File generato da `strumenti/componi_testi.py` a partire da `{}`: non si modifica a mano."


def leggi_uscite(testo: str | None = None) -> list[dict]:
    """Legge sorgenti/uscite.txt. Errore chiaro per un campo sconosciuto o un ID ripetuto."""
    testo = USCITE.read_text(encoding="utf-8") if testo is None else testo
    uscite: list[dict] = []
    corrente: dict | None = None
    sezione = ""
    for n, riga in enumerate(testo.splitlines(), 1):
        if corrente is None and (riga.startswith("//") or not riga.strip()):
            continue
        if riga.startswith("=== "):
            corrente = {"id": riga[4:].strip(), "it": [], "en": [], "riga": n}
            if any(u["id"] == corrente["id"] for u in uscite):
                raise ValueError(f"uscite.txt:{n}: ID ripetuto {corrente['id']}")
            uscite.append(corrente)
            sezione = "campi"
        elif corrente is None:
            raise ValueError(f"uscite.txt:{n}: testo fuori da un blocco «=== ID»")
        elif riga.strip() in ("--- it", "--- en"):
            sezione = riga.strip()[4:]
        elif sezione == "campi":
            if not riga.strip():
                continue
            chiave, sep, valore = riga.partition(":")
            if not sep or chiave.strip() not in CAMPI:
                raise ValueError(f"uscite.txt:{n}: campo sconosciuto «{chiave.strip()}»")
            corrente[chiave.strip()] = valore.strip()
        else:
            corrente[sezione].append(riga)
    for u in uscite:
        for lingua in ("it", "en"):
            u[lingua] = "\n".join(u[lingua]).strip("\n")
        u["mcp"] = u.get("mcp", "") == "sì"
        u["importante"] = u.get("importante", "") == "sì"
        u["data"] = dt.date.fromisoformat(u["data"]) if u.get("data") else None
    return uscite


def settimana(data: dt.date | None) -> str:
    if data is None:
        return "—"
    n = (data - INIZIO_S0).days // 7
    return f"S{n}"


def giorno(data: dt.date | None) -> str:
    return GIORNI[data.weekday()] if data else "—"


def data_estesa(data: dt.date) -> str:
    return f"{giorno(data)} {data.day} {MESI[data.month - 1]} {data.year}"


def con_hashtag(testo: str, hashtag: str) -> str:
    """Il testo da incollare: per i post con hashtag, gli hashtag vanno in fondo, su una riga."""
    if hashtag and hashtag != "nessuno":
        return f"{testo}\n\n{hashtag}"
    return testo


def componi(u: dict, lingua: str) -> str:
    """Testo pronto da incollare nella lingua chiesta, con i valori del listino."""
    testo = u[lingua]
    if not testo:
        return ""
    hashtag = u.get("hashtag_en", "") if lingua == "en" else u.get("hashtag", "")
    return listino.sostituisci(con_hashtag(testo, hashtag), lingua)


def campo(u: dict, nome: str, lingua: str = "it") -> str:
    return listino.sostituisci(u.get(nome, ""), lingua)


def vuoti(testi: list[str]) -> list[str]:
    """Segnaposto rimasti senza valore (link e dati da decidere), in ordine di comparsa."""
    trovati: list[str] = []
    for t in testi:
        for k in listino.SEGNAPOSTO.findall(t):
            if k not in trovati:
                trovati.append(k)
    return trovati


def blocco(u: dict) -> list[str]:
    righe = []
    quando = f"{data_estesa(u['data'])}, {u.get('ora', '')}" if u["data"] else "senza data"
    righe.append(f"### {u['id']} · {quando} · {u.get('canale', '')} · {u.get('titolo', '')}")
    righe.append("")
    if u["mcp"]:
        righe.append(f"**Riserva MCP: {MARCATORE_MCP}.**")
        righe.append("")
    righe.append("| Campo | Valore |")
    righe.append("|---|---|")
    for nome, etichetta in (("formato", "Formato"), ("pilastro", "Pilastro"), ("modello", "Modello"), ("grafica", "Grafica"),
                            ("cta", "Invito all’azione"), ("link", "Link"), ("hashtag", "Hashtag"),
                            ("hashtag_en", "Hashtag in inglese"), ("note", "Note")):
        valore = campo(u, nome)
        if valore:
            righe.append(f"| {etichetta} | {valore.replace('|', '/')} |")
    testo_it = componi(u, "it")
    caratteri = f"{len(testo_it)} in italiano" + (f", {len(componi(u, 'en'))} in inglese" if u["en"] else "")
    righe.append(f"| Caratteri | {caratteri} |")
    righe.append("")
    righe.append("Testo in italiano:")
    righe.append("")
    righe.append("```text")
    righe.append(testo_it)
    righe.append("```")
    if u["en"]:
        righe.append("")
        titolo_en = campo(u, "titolo_en", "en")
        righe.append(f"Testo in inglese{f' («{titolo_en}»)' if titolo_en else ''}:")
        righe.append("")
        righe.append("```text")
        righe.append(componi(u, "en"))
        righe.append("```")
    righe.append("")
    return righe


def calendario_md(uscite: list[dict]) -> str:
    datate = sorted((u for u in uscite if u["data"]), key=lambda u: (u["data"], u.get("ora", ""), u["id"]))
    riserva = [u for u in uscite if not u["data"]]
    v = listino.valori("it")
    inizio, fine = datate[0]["data"], datate[-1]["data"]
    tutti_testi = [componi(u, lingua) for u in uscite for lingua in ("it", "en")] + [campo(u, "link") for u in uscite]
    righe = [
        "# Calendario social, 12 settimane intorno al lancio",
        "",
        TESTA.format("sorgenti/uscite.txt"),
        f"> Prezzi dal listino `{v['listino.versione']}` (`docs/mercato/tier.json`), date e link da `strumenti/costanti.json`.",
        "",
        f"Da {data_estesa(inizio)} a {data_estesa(fine)}: da tre settimane prima del lancio (S-3) alla fine del prezzo di lancio (S8),"
        " con le settimane di `marketing/lancio/PIANO-90-GIORNI.md`. "
        f"{len(datate)} uscite con data, tutte con il testo completo in italiano; "
        f"{sum(1 for u in datate if u['en'])} anche in inglese (le più importanti). "
        f"In fondo, {len(riserva)} uscite di riserva sulla bozza con Claude, {MARCATORE_MCP}.",
        "",
        "Come si legge: ogni uscita ha un ID stabile (U01…), il canale, il formato, il pilastro, il modello grafico in `modelli/`"
        " e il PNG da caricare in `grafiche/` (si rigenera con `strumenti/genera_grafiche.py`). Il testo nel riquadro si copia"
        " così com’è, hashtag compresi. Su Instagram i link non sono cliccabili: il testo dice «link nella bio» e il campo"
        " «Link» dice quale link mettere nella bio quel giorno.",
        "",
        "Regole del calendario: nessuna uscita di sabato, a Pasqua e Pasquetta (28 e 29 marzo) e il 25 aprile;"
        " di solito alle 9:00, alle 12:30 o alle 18:00 (il giorno del lancio si segue l’ora dell’email); un post per canale"
        " al giorno, più eventuali storie, salvo il giorno del lancio.",
        "",
    ]
    mancanti = vuoti(tutti_testi)
    if mancanti:
        righe.append("Segnaposto ancora vuoti, da riempire in `strumenti/costanti.json` prima di pubblicare: "
                     + ", ".join(f"`{{{{{k}}}}}`" for k in mancanti) + ".")
        righe.append("")
    righe += ["## Riepilogo", "", "| Data | Giorno | Ora | Sett. | ID | Canale | Formato | Pilastro | Titolo | EN |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for u in datate:
        righe.append(f"| {u['data'].strftime('%d/%m')} | {giorno(u['data'])} | {u.get('ora', '')} | {settimana(u['data'])} | {u['id']}"
                     f" | {u.get('canale', '')} | {u.get('formato', '')} | {u.get('pilastro', '')} | {campo(u, 'titolo')}"
                     f" | {'sì' if u['en'] else ''} |")
    righe.append("")
    righe += ["Uscite per pilastro: " + "; ".join(f"{p} {sum(1 for u in datate if u.get('pilastro') == p)}" for p in PILASTRI) + ".", ""]
    corrente = None
    for u in datate:
        s = settimana(u["data"])
        if s != corrente:
            corrente = s
            lun = INIZIO_S0 + dt.timedelta(weeks=int(s[1:]))
            dom = lun + dt.timedelta(days=6)
            righe += [f"## Settimana {s} · dal {lun.day} {MESI[lun.month - 1]} al {dom.day} {MESI[dom.month - 1]}", "",
                      f"Dal piano di lancio: {PIANO.get(s, '—')}", ""]
        righe += blocco(u)
    righe += [f"## Riserva MCP, {MARCATORE_MCP}", "",
              "Queste uscite non hanno data. Si programmano solo quando il server MCP (T-203) e la sua guida (T-403) sono"
              " rilasciati, dopo aver verificato quali dati passano a Claude. Le grafiche hanno il nome che comincia con `mcp-`"
              " e una fascia «Riserva» da togliere quel giorno.", ""]
    for u in riserva:
        righe += blocco(u)
    return "\n".join(righe).rstrip("\n") + "\n"


def calendario_csv(uscite: list[dict]) -> str:
    colonne = ("id", "data", "giorno", "ora", "settimana", "canale", "formato", "pilastro", "modello", "grafica", "cta", "link",
               "hashtag", "hashtag_en", "importante", "mcp", "titolo", "testo_it", "titolo_en", "testo_en", "note")
    uscita = io.StringIO()
    w = csv.writer(uscita, lineterminator="\n")
    w.writerow(colonne)
    ordinate = sorted(uscite, key=lambda u: (u["data"] or dt.date.max, u.get("ora", ""), u["id"]))
    for u in ordinate:
        w.writerow([
            u["id"], u["data"].isoformat() if u["data"] else "", giorno(u["data"]) if u["data"] else "", u.get("ora", ""),
            settimana(u["data"]) if u["data"] else "", u.get("canale", ""), u.get("formato", ""), u.get("pilastro", ""),
            u.get("modello", ""), u.get("grafica", ""), campo(u, "cta"), campo(u, "link"), u.get("hashtag", ""), u.get("hashtag_en", ""),
            "sì" if u["importante"] else "", MARCATORE_MCP if u["mcp"] else "", campo(u, "titolo"), componi(u, "it"),
            campo(u, "titolo_en", "en"), componi(u, "en"), campo(u, "note"),
        ])
    return uscita.getvalue()


def copioni_md() -> str:
    testo = listino.sostituisci(COPIONI_SORGENTE.read_text(encoding="utf-8"), "it")
    titolo, _, resto = testo.partition("\n")
    return f"{titolo}\n\n{TESTA.format('sorgenti/copioni.md')}\n{resto}".rstrip("\n") + "\n"


def tutti() -> dict[Path, str]:
    uscite = leggi_uscite()
    return {CALENDARIO_MD: calendario_md(uscite), CALENDARIO_CSV: calendario_csv(uscite), COPIONI_MD: copioni_md()}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--controlla", action="store_true", help="non scrive: esce con 1 se i file composti non sono aggiornati")
    a = p.parse_args()
    vecchi = []
    for percorso, contenuto in tutti().items():
        attuale = percorso.read_text(encoding="utf-8") if percorso.exists() else None
        if attuale == contenuto:
            continue
        if a.controlla:
            vecchi.append(percorso.name)
        else:
            percorso.write_text(contenuto, encoding="utf-8")
            print(f"scritto {percorso.relative_to(SOCIAL)}")
    if vecchi:
        print("da ricomporre: " + ", ".join(vecchi) + " (python3 marketing/social/strumenti/componi_testi.py)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
