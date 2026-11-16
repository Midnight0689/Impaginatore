#!/usr/bin/env python3
"""Riepilogo delle statistiche d'uso della beta privata (T-204, docs/architettura/STATISTICHE.md).

    python strumenti/statistiche_beta.py <cartella con i file .jsonl dei tester> [--uscita <cartella>] [--registro <registro.csv>]

Legge i file che i tester hanno esportato con «Esporta le statistiche…» (anche in sottocartelle), tiene solo le righe che
rispettano lo schema (statistiche/schema.py: le altre si contano e si scartano), toglie i doppioni (lo stesso file
mandato due volte) e scrive nella cartella di uscita (predefinita: quella dei file):

    riepilogo.md    per tester e in tutto: funzioni più usate, tempi mediani, percorso dal primo avvio alla prima
                    esportazione, errori più frequenti, KPI
    riepilogo.csv   una riga per tester e una per il totale («tutti»)

Un tester è il numero di serie della sua licenza beta (o, senza, il codice dell'installazione). Con --registro (il
registro.csv del negozio, che sta fuori dal repository) accanto al seriale compare l'intestatario: il riepilogo diventa
un documento con dati personali, da tenere sul computer del titolare.
"""
import argparse
import csv
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(QUI), "src"))
from impaginatore.statistiche import schema  # noqa: E402

PERCORSO = ("avvio", "primo_album", "prime_foto", "primo_spread", "prima_bozza", "primo_controllo", "prima_esportazione", "prima_consegna")
CINQUE_MINUTI = 300
CAMPI_CSV = ["tester", "intestatario", "installazioni", "sessioni", "eventi", "dal", "al", "sistema", "versione", "operazioni", "errori",
             "bozze_proposte", "bozze_accettate", "esportazioni", "esportazioni_complete", "primo_spread_s", "prima_esportazione_s"]


def leggi(cartella):
    """(righe valide senza doppioni, quante scartate, quanti file): le righe valide sono dizionari dello schema"""
    righe, viste, scartate, file = [], set(), 0, 0
    for radice, _, nomi in sorted(os.walk(cartella)):
        for nome in sorted(n for n in nomi if n.endswith(".jsonl")):
            file += 1
            with open(os.path.join(radice, nome), encoding="utf-8", errors="replace") as f:
                for testo in f:
                    testo = testo.strip()
                    if not testo or testo in viste: continue
                    viste.add(testo)
                    try:
                        r = json.loads(testo); schema.controlla_riga(r)
                    except ValueError: scartate += 1; continue
                    righe.append(r)
    righe.sort(key=lambda r: (r["t"], r["sessione"]))
    return righe, scartate, file


def chi(r):
    return f"seriale {r['serie']}" if "serie" in r else f"installazione {r['id'][:8]}"


def intestatari(registro):
    """seriale -> intestatario dal registro del negozio (facoltativo)"""
    if not registro: return {}
    with open(registro, encoding="utf-8", newline="") as f: return {f"seriale {r['seriale']}": r.get("intestatario", "") for r in csv.DictReader(f)}


def mediana(valori):
    v = [x for x in valori if x is not None]
    return statistics.median(v) if v else None


def fmt(v, unita=""):
    if v is None: return "—"
    return (f"{v:.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)) + unita


def durata(s):
    if s is None: return "—"
    s = round(s)
    return f"{s // 3600} h {s % 3600 // 60:02d} min" if s >= 3600 else f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"


def tester(righe):
    """i numeri di un tester (o di tutti)"""
    per = defaultdict(list)
    for r in righe: per[r["ev"]].append(r)
    ops = Counter(); ms = defaultdict(float); rif = Counter(); err = Counter(); ass = Counter()
    for r in per["operazioni"]:
        ops[r["op"]] += r.get("n", 0); ms[r["op"]] += r.get("ms_tot", 0); rif[r["op"]] += r.get("rifiutate", 0) + r.get("licenza", 0)
        err[r["op"]] += r.get("errori", 0); ass[r["op"]] += r.get("assistente", 0)
    traguardi = {}
    for r in per["traguardo"]: traguardi.setdefault(r["nome"], r.get("secondi_dal_primo_avvio"))
    avvio = [r for r in per["avvio"]]
    esp = per["esportazione"]
    return dict(
        installazioni=len({r["id"] for r in righe}), sessioni=len({r["sessione"] for r in righe}), eventi=len(righe),
        dal=righe[0]["t"][:10] if righe else "", al=righe[-1]["t"][:10] if righe else "",
        sistema=", ".join(sorted({f"{r.get('sistema', '?')} {r.get('sistema_versione', '')}".strip() for r in avvio})),
        versione=", ".join(sorted({r["ver"] for r in righe})),
        operazioni=sum(ops.values()), ops=ops, ms=ms, rifiutate=rif, errori_op=err, assistente=ass,
        errori=len(per["errore"]), errori_tipi=Counter((r["tipo"], r.get("dove", ""), r.get("errno", "")) for r in per["errore"]),
        bozze_proposte=len(per["bozza_proposta"]), bozze_accettate=len(per["bozza_accettata"]),
        esportazioni=len(esp), esportazioni_complete=sum(1 for r in esp if r.get("fatti") == r.get("totale") and not r.get("errori")),
        traguardi=traguardi, avviato=bool(avvio) or bool(per["consenso"]), per=per)


def percorso(gruppi):
    """per ogni passo del percorso: quanti tester ci sono arrivati e la mediana dei secondi dal primo avvio"""
    out = []
    for passo in PERCORSO:
        if passo == "avvio": arrivati = [g for g in gruppi if g["avviato"]]; sec = []
        else: arrivati = [g for g in gruppi if passo in g["traguardi"]]; sec = [g["traguardi"][passo] for g in arrivati]
        out.append((passo, len(arrivati), mediana(sec)))
    return out


def kpi(gruppi, tutti):
    per = tutti["per"]
    ps = [g["traguardi"]["primo_spread"] for g in gruppi if g["traguardi"].get("primo_spread") is not None]
    entro = sum(1 for s in ps if s <= CINQUE_MINUTI)
    modi = Counter(r["modo"] for r in per["primo_spread"])
    sess_err = len({r["sessione"] for r in per["errore"]})
    return [
        ("Tester con almeno un evento", str(len(gruppi))),
        ("Primo spread entro 5 minuti dal primo avvio (obiettivo dei KPI)", f"{entro} tester su {len(ps)} che ci sono arrivati" if ps else "—"),
        ("Tempo mediano dal primo avvio al primo spread", durata(mediana(ps))),
        ("Primo spread di un album: con la bozza / a mano / con l'assistente AI", f"{modi['bozza']} / {modi['manuale']} / {modi['assistente']}"),
        ("Tempo mediano dall'apertura dell'album al primo spread", durata(mediana([r.get("secondi") for r in per["primo_spread"]]))),
        ("Bozze accettate su proposte", f"{tutti['bozze_accettate']} su {tutti['bozze_proposte']}"),
        ("Operazioni chieste dall'assistente AI", f"{sum(tutti['assistente'].values())} su {tutti['operazioni']}"),
        ("Esportazioni complete (tutti gli spread, nessun errore)", f"{tutti['esportazioni_complete']} su {tutti['esportazioni']}"),
        ("Sessioni con almeno un errore", f"{sess_err} su {tutti['sessioni']}"),
        ("Foto caricate online", "0: le statistiche non hanno campi per le foto (schema.py)"),
    ]


def tabella(testate, righe):
    out = ["| " + " | ".join(testate) + " |", "|" + "|".join("---" for _ in testate) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in righe]
    return out


def markdown(gruppi, tutti, nomi, scartate, file):
    g_ord = sorted(gruppi.items())
    md = ["# Statistiche della beta privata", "",
          f"{file} file, {tutti['eventi']} eventi validi, {scartate} righe scartate (fuori schema o rotte), {len(gruppi)} tester, "
          f"dal {tutti['dal'] or '—'} al {tutti['al'] or '—'}.", "", "## KPI", ""]
    md += tabella(["Indicatore", "Valore"], kpi([g for _, g in g_ord], tutti))
    md += ["", "## Percorso dal primo avvio alla prima esportazione", ""]
    md += tabella(["Passo", "Tester arrivati", "Mediana dal primo avvio"], [(p, n, durata(s)) for p, n, s in percorso([g for _, g in g_ord])])
    md += ["", "## Funzioni più usate", ""]
    righe_ops = [(op, n, fmt(tutti["ms"][op] / n if n else None, " ms"), tutti["rifiutate"][op], tutti["errori_op"][op], tutti["assistente"][op])
                 for op, n in tutti["ops"].most_common(20)]
    md += tabella(["Operazione", "Volte", "Media", "Rifiutate", "Errori", "Dall'assistente"], righe_ops) if righe_ops else ["Nessuna operazione."]
    per = tutti["per"]
    md += ["", "## Tempi mediani", ""]
    tempi = [("Apertura di un album", fmt(mediana([r.get("ms") for r in per["album_aperto"]]), " ms"), len(per["album_aperto"])),
             ("Proposta di bozza", fmt(mediana([r.get("ms") for r in per["bozza_proposta"]]), " ms"), len(per["bozza_proposta"])),
             ("Controllo dell'album", fmt(mediana([r.get("ms") for r in per["controllo"]]), " ms"), len(per["controllo"])),
             ("Preparazione delle foto", fmt(mediana([r.get("ms") for r in per["preparazione"]]), " ms"), len(per["preparazione"])),
             ("Sessione del programma", durata(mediana([r.get("durata_s") for r in per["chiusura"]])), len(per["chiusura"]))]
    for f in sorted({r["formato"] for r in per["esportazione"]}):
        e = [r for r in per["esportazione"] if r["formato"] == f]
        tempi.append((f"Esportazione {f}", fmt(mediana([r.get("ms") for r in e]), " ms"), len(e)))
    md += tabella(["Cosa", "Mediana", "Quante volte"], tempi)
    md += ["", "## Errori più frequenti", ""]
    errori = [(t, d or "—", n or "—", k) for (t, d, n), k in tutti["errori_tipi"].most_common(15)]
    md += tabella(["Tipo", "Dove", "Errno", "Volte"], errori) if errori else ["Nessun errore."]
    md += ["", "## Per tester", ""]
    md += tabella(["Tester", "Sessioni", "Eventi", "Dal", "Al", "Sistema", "Operazioni", "Più usate", "Errori", "Primo spread", "Prima esportazione"],
                  [(k + (f" ({nomi[k]})" if nomi.get(k) else ""), g["sessioni"], g["eventi"], g["dal"], g["al"], g["sistema"] or "—", g["operazioni"],
                    ", ".join(f"{op} {n}" for op, n in g["ops"].most_common(3)) or "—", g["errori"],
                    durata(g["traguardi"].get("primo_spread")), durata(g["traguardi"].get("prima_esportazione"))) for k, g in g_ord])
    return "\n".join(md) + "\n"


def riga_csv(nome, intestatario, g):
    return dict({k: g[k] for k in CAMPI_CSV if k in g}, tester=nome, intestatario=intestatario,
                primo_spread_s=fmt(g["traguardi"].get("primo_spread")), prima_esportazione_s=fmt(g["traguardi"].get("prima_esportazione")))


def riepilogo(cartella, uscita=None, registro=None):
    """scrive riepilogo.md e riepilogo.csv; restituisce i loro percorsi"""
    righe, scartate, file = leggi(cartella)
    per_tester = defaultdict(list)
    for r in righe: per_tester[chi(r)].append(r)
    gruppi = {k: tester(v) for k, v in per_tester.items()}; tutti = tester(righe); nomi = intestatari(registro)
    uscita = uscita or cartella; os.makedirs(uscita, exist_ok=True)
    md, csvp = os.path.join(uscita, "riepilogo.md"), os.path.join(uscita, "riepilogo.csv")
    with open(md, "w", encoding="utf-8") as f: f.write(markdown(gruppi, tutti, nomi, scartate, file))
    with open(csvp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPI_CSV); w.writeheader()
        for k, g in sorted(gruppi.items()): w.writerow(riga_csv(k, nomi.get(k, ""), g))
        w.writerow(riga_csv("tutti", "", tutti))
    return md, csvp


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cartella", help="cartella con i file .jsonl esportati dai tester")
    ap.add_argument("--uscita", help="dove scrivere riepilogo.md e riepilogo.csv (predefinito: la cartella dei file)")
    ap.add_argument("--registro", help="registro.csv del negozio, per mostrare l'intestatario accanto al seriale")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.cartella):
        print(f"Errore: {a.cartella} non è una cartella.", file=sys.stderr); return 1
    md, csvp = riepilogo(a.cartella, a.uscita, a.registro)
    print(f"Riepilogo scritto in {md} e {csvp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
