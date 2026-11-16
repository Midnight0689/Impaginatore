"""Bozza dell'album (UX-018): le foto ancora da usare, in ordine di scatto, divise in capitoli (una pausa di più di 30
minuti fra due scatti apre un capitolo) e in spread di qualche foto, ognuno con la disposizione che rispetta meglio le
foto. La stessa funzione serve al pulsante «Prepara la bozza» e all'assistente (MCP): danno risultati coerenti.

Regole (da stile.md e dalla prova dell'analisi UX): le due pagine piene salvo pausa voluta (una pagina vuota costa
molto); ritmo fra pagine piene (immersive, «I») e bianche (con il margine, «W»); la stessa coppia di moduli mai tre volte
di fila; le panoramiche (rapporto ≥ 1,8) e, a scelta, le foto con la stella da sole su una pagina; penalità ai ritagli
oltre ×1,25. Con un seme diverso da 0 i gruppi e le scelte cambiano un poco: «Rifalla» propone un'altra combinazione.
Qui non si tocca l'album: `proposta` riceve le foto e una funzione che dà le disposizioni possibili (tpl_options
dell'editor) e restituisce gli spread da creare."""
import math
import random
import time

PAUSA_CAPITOLO = 30 * 60          # secondi fra due scatti oltre i quali comincia un capitolo
PANORAMICA = 1.8                  # rapporto dei lati da cui una foto è una panoramica
MIN_FOTO = 10                     # sotto questo numero di foto da usare la bozza non serve
RITMI = ("alterna", "piene", "bianche")
PER_SPREAD = 3.3                  # foto per spread se non si dice altro
MAX_GRUPPO = 8
VARIA = (0, -1, 1, 0, 1, -1)      # il numero di foto per spread varia attorno alla densità: il ritmo non è monotono
RITAGLIO = math.log(1.25)


def secondi(dt):
    """data di scatto «AAAA:MM:GG hh:mm:ss» in secondi, None se non si legge"""
    try: return time.mktime(time.strptime(str(dt)[:19], "%Y:%m:%d %H:%M:%S"))
    except (ValueError, OverflowError): return None


def capitoli(foto):
    """foto in ordine di scatto ([{i, dt, ...}]) divise dove fra due scatti passano più di 30 minuti; un capitolo di una
    foto sola si unisce a quello dopo (l'ultimo a quello prima)"""
    out, prima = [], None
    for f in foto:
        t = secondi(f["dt"])
        if not out or (t is not None and prima is not None and t - prima > PAUSA_CAPITOLO): out.append([])
        out[-1].append(f); prima = t if t is not None else prima
    unite = []
    for c in out:
        if unite and len(unite[-1]) == 1: unite[-1].extend(c)
        else: unite.append(c)
    if len(unite) > 1 and len(unite[-1]) == 1: unite[-2].extend(unite.pop())
    return unite


def gruppi(capitolo, per_spread, sole, scarto=0):
    """spread di un capitolo: liste di foto consecutive. Una foto «sola» (panoramica, stella) apre uno spread: lei su una
    pagina, sull'altra le foto che seguono (o un'altra foto sola, o la foto che la precede se resterebbe da sola)"""
    out, k, r = [], 0, scarto
    while k < len(capitolo):
        f = capitolo[k]; n = min(max(round(per_spread + VARIA[r % len(VARIA)]), 1), MAX_GRUPPO); r += 1
        if f["i"] in sole:
            g = [f]
            for x in capitolo[k + 1:k + max(2, n)]:
                if x["i"] in sole:
                    if len(g) == 1: g.append(x)
                    break
                g.append(x)
        else:
            g = []
            for x in capitolo[k:k + n]:
                if x["i"] in sole: break
                g.append(x)
            resto = capitolo[k + len(g):]
            if len(g) == 1 and resto and resto[0]["i"] in sole: g.append(resto[0])                 # una foto prima di una foto sola: le due pagine dello stesso spread
            elif len(resto) == 1 and resto[0]["i"] not in sole and len(g) < MAX_GRUPPO: g.append(resto[0])     # una foto sola in fondo: entra qui
        out.append(g); k += len(g)
    return out


def punteggio(t, k, ritmo, sole, precedenti):
    """quanto costa la disposizione t come k-esimo spread della bozza (più basso è meglio)"""
    p = t["cost"]
    if t["worst"] > RITAGLIO: p += 0.5 + 2 * (t["worst"] - RITAGLIO)
    mods = (t["L"]["module"], t["R"]["module"]); bianche = [t["L"]["mode"], t["R"]["mode"]].count("W")
    if "BLANK" in mods: p += 1.5
    if len(precedenti) >= 2 and precedenti[-1] == precedenti[-2] == mods: p += 1.0
    if ritmo == "piene": p += 0.4 * bianche
    elif ritmo == "bianche": p += 0.4 * (2 - bianche)
    else: p += 0.4 * (bianche if k % 2 == 0 else (0 if bianche else 1))     # spread pari pieni, dispari con una pagina bianca
    for side in "LR":
        if len(t[side]["photos"]) > 1 and any(i in sole for i in t[side]["photos"]): p += 3.0
    return p


def proposta(foto, opzioni, ritmo="alterna", per_spread=PER_SPREAD, stelle=True, seme=0):
    """foto: [{i, dt, ar, stella}] da usare, in ordine di scatto; opzioni(indici) -> {items, piu} come tpl_options.
    Restituisce {spreads: [{L, R, foto, capitolo, inizio, ora, taglia}], capitoli, foto, per_spread}"""
    rnd = random.Random(seme) if seme else None
    sole = {f["i"] for f in foto if f["ar"] >= PANORAMICA or (stelle and f.get("stella"))}
    out, precedenti = [], []
    for c, cap in enumerate(capitoli(foto)):
        ora = secondi(cap[0]["dt"])
        for j, g in enumerate(gruppi(cap, per_spread, sole, rnd.randrange(len(VARIA)) if rnd else 0)):
            coda = [g]
            while coda:
                h = coda.pop(0); t = _scegli(opzioni([f["i"] for f in h]), len(out), ritmo, sole, precedenti, rnd)
                if t is None:                                           # nessuna disposizione per questo gruppo: si divide in due
                    if len(h) > 1: coda[:0] = [h[:len(h) // 2], h[len(h) // 2:]]
                    continue
                out.append(_spread(t, h, c, j == 0 and h[0] is g[0], ora)); precedenti.append((t["L"]["module"], t["R"]["module"]))
    n = sum(len(s["foto"]) for s in out)
    return dict(spreads=out, capitoli=len({s["capitolo"] for s in out}), foto=n, per_spread=round(n / len(out), 1) if out else 0)


def _scegli(d, k, ritmo, sole, precedenti, rnd):
    """la disposizione migliore fra quelle di d che hanno tutte e due le pagine (None se non ce n'è)"""
    cand = [t for t in d["items"] + d.get("piu", []) if t.get("L") and t.get("R")]
    return min(cand, key=lambda t: punteggio(t, k, ritmo, sole, precedenti) + (rnd.uniform(0, 0.35) if rnd else 0)) if cand else None


def _spread(t, g, c, inizio, ora):
    return dict(L={k: t["L"][k] for k in ("mode", "module", "mirror", "photos")}, R={k: t["R"][k] for k in ("mode", "module", "mirror", "photos")},
                foto=[f["i"] for f in g], capitolo=c, inizio=inizio, ora=time.strftime("%H:%M", time.localtime(ora)) if inizio and ora is not None else None,
                taglia=round(math.exp(t["worst"]), 2))
