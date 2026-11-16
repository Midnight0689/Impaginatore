"""Spazi fra le foto di uno spread: quali coppie di foto vicine ci sono, quali stacchi sono diversi dal riferimento e come
correggerli (UX-014). Era nella pagina (gapPairs, gapFix in risorse/index.html): qui lo usano allo stesso modo il
controllo dell'album, «Sistema» e l'assistente (MCP). Funzioni pure: lavorano su rettangoli {x, y, w, h} in pixel.

Due foto sono una coppia se una sta subito a destra (o subito sotto) dell'altra, si sovrappongono per almeno un decimo
della più piccola nell'altra direzione e fra loro non c'è una terza foto; lo stacco conta se è fra un decimo di
millimetro e il più grande fra quattro spazi standard e un centimetro. Il riferimento è lo spazio del progetto («std»),
il più frequente dello spread («freq») o una misura scelta («custom»)."""

TOLLERANZA_CM = 0.01            # circa un pixel di arrotondamento: oltre questo lo stacco è diverso dagli altri


def _ov(a0, a1, b0, b1): return min(a1, b1) - max(a0, b0)


def coppie(rett, G, ppi, modo="std", valore=0):
    """coppie di foto vicine: [{ax: "x"|"y", a, b (indici in rett), g: stacco, da, a_: bordi, at: centro, ref, ok}]"""
    mx, mn = max(G * 4, ppi / 2.54), ppi / 2.54 * 0.1; out = []
    for ia, a in enumerate(rett):
        for ib, b in enumerate(rett):
            if ia == ib: continue
            g = b["x"] - (a["x"] + a["w"])
            if mn <= g <= mx and _ov(a["y"], a["y"] + a["h"], b["y"], b["y"] + b["h"]) > min(a["h"], b["h"]) * 0.1 and not any(
                    c is not a and c is not b and c["x"] < b["x"] and c["x"] + c["w"] > a["x"] + a["w"] and _ov(c["y"], c["y"] + c["h"], max(a["y"], b["y"]), min(a["y"] + a["h"], b["y"] + b["h"])) > 0 for c in rett):
                out.append(dict(ax="x", a=ia, b=ib, g=g, da=a["x"] + a["w"], a_=b["x"], at=(max(a["y"], b["y"]) + min(a["y"] + a["h"], b["y"] + b["h"])) / 2))
            g = b["y"] - (a["y"] + a["h"])
            if mn <= g <= mx and _ov(a["x"], a["x"] + a["w"], b["x"], b["x"] + b["w"]) > min(a["w"], b["w"]) * 0.1 and not any(
                    c is not a and c is not b and c["y"] < b["y"] and c["y"] + c["h"] > a["y"] + a["h"] and _ov(c["x"], c["x"] + c["w"], max(a["x"], b["x"]), min(a["x"] + a["w"], b["x"] + b["w"])) > 0 for c in rett):
                out.append(dict(ax="y", a=ia, b=ib, g=g, da=a["y"] + a["h"], a_=b["y"], at=(max(a["x"], b["x"]) + min(a["x"] + a["w"], b["x"] + b["w"])) / 2))
    ref = riferimento(out, G, modo, valore)
    for p in out: p.update(ref=ref, ok=abs(p["g"] - ref) / ppi * 2.54 <= TOLLERANZA_CM)
    return out


def riferimento(cp, G, modo="std", valore=0):
    """a quale misura devono essere uguali gli stacchi: G, il più frequente (a parità, il più vicino a G) o valore"""
    if modo == "custom" and valore > 0: return valore
    if modo == "freq" and cp:
        n = {}
        for p in cp: k = _arrotonda(p["g"]); n[k] = n.get(k, 0) + 1
        return sorted(n.items(), key=lambda kv: (-kv[1], abs(kv[0] - G)))[0][0]
    return G


def _arrotonda(v):
    """come Math.round di JavaScript (le metà verso l'alto), perché il riferimento sia quello che vedeva la pagina"""
    import math
    return math.floor(v + 0.5)


def stato(rett, G, ppi, modo="std", valore=0):
    """{ref, n, ok, diversi}: quante coppie ci sono e quante hanno lo stacco diverso dal riferimento"""
    cp = coppie(rett, G, ppi, modo, valore)
    return dict(ref=cp[0]["ref"] if cp else G, n=len(cp), ok=sum(1 for p in cp if p["ok"]), diversi=sum(1 for p in cp if not p["ok"]))


def correggi(rett, G, ppi, modo="std", valore=0):
    """(rettangoli corretti, numero di modifiche): fino a quattro passate; in ogni passata, per ogni foto «davanti» (b) e
    asse, il suo bordo va allo stacco giusto dalla più lontana delle foto che le stanno dietro e le altre foto dietro si
    allungano fino allo stesso bordo, così i bordi restano allineati. Un bordo non si sposta per meno del 3 % della foto"""
    R = [dict(r) for r in rett]; ch = 0
    for _ in range(4):
        S0 = [dict(r) for r in R]; cp = coppie(S0, G, ppi, modo, valore)
        if all(p["ok"] for p in cp): break
        grp = {}
        for p in cp: grp.setdefault(p["b"], dict(x=[], y=[]))[p["ax"]].append(p)
        for b, m in grp.items():
            for ax, dim in (("x", "w"), ("y", "h")):
                L = m[ax]
                if not L or all(p["ok"] for p in L): continue
                ref = L[0]["ref"]; t = max(p["da"] for p in L) + ref; rb = R[b]; fine = S0[b][ax] + S0[b][dim]
                if fine - t > rb[dim] * 0.03: rb[dim] = fine - t; rb[ax] = t; ch += 1
                for p in L:
                    ra = R[p["a"]]; e = t - ref
                    if abs(ra[ax] + ra[dim] - e) > 0.5 and e - ra[ax] > ra[dim] * 0.03: ra[dim] = e - ra[ax]; ch += 1
    return R, ch
