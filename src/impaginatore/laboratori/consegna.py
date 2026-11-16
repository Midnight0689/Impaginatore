"""Consegna al laboratorio (UX-013, T-208): dagli spread del motore ai file che il prodotto chiede.

Il motore disegna lo spread con l'abbondanza del progetto e alla sua risoluzione; qui si toglie l'abbondanza in più, si
porta l'immagine alla risoluzione del prodotto e, se il prodotto vuole un file per pagina, la si divide sulla piega (ogni
pagina tiene la sua abbondanza anche dal lato della piega, presa dall'altra pagina). I nomi dei file vengono dal modello
del prodotto; il riepilogo è un testo da leggere (e da mandare al laboratorio insieme ai file).
Nessuna funzione di questo modulo usa la rete: la consegna è una cartella sul computer dell'utente.
"""
import os
import re
import time

from .. import lingua, nomi

RIEPILOGO = "Riepilogo consegna.txt"
_SEGNAPOSTO = re.compile(r"\{(album|n|pagina|prodotto)\}")


def _pezzo(v):
    """un valore dentro il nome di un file: niente caratteri vietati, al massimo 40 caratteri"""
    return nomi.nome_cartella(v, "Album")[:40].rstrip(" .")         # nome_cartella non comincia mai con spazi o punti: resta qualcosa


def nome_file(prod, album, n, pagina=None):
    """nome del file dello spread n (pagina: numero della pagina se il prodotto vuole un file per pagina), con l'estensione.
    I segnaposti si sostituiscono uno per uno: il modello del laboratorio non passa mai da str.format"""
    c = prod["consegna"]; cifre = c["cifre"]
    valori = dict(album=_pezzo(album), prodotto=_pezzo(prod["nome"]), n=f"{n:0{cifre}d}", pagina=f"{(pagina if pagina is not None else 2 * n - 1):0{cifre}d}")
    s = _SEGNAPOSTO.sub(lambda m: valori[m.group(1)], c["nome"])
    return nomi.nome_cartella(s, f"Spread {n:0{cifre}d}", 240) + "." + c["formato"]          # 80 di modello + 4 segnaposti da 40: sotto i 255 di ogni sistema


def misure_px(prod):
    """(larghezza, altezza) in pixel di un file della consegna"""
    w, h = prod["pagina_cm"]; b = prod["abbondanza_mm"] / 10; p = prod["ppi"]
    px = lambda cm: max(1, round(cm / 2.54 * p))
    larghezza = 2 * w + 2 * b if prod["consegna"]["file"] == "spread" else w + 2 * b
    return px(larghezza), px(h + 2 * b)


def immagini(im, ppi, abbondanza_px, prod):
    """[(pagina, immagine)] dello spread `im` disegnato dal motore (abbondanza_px per lato, a ppi): pagina None per lo spread
    intero, 0 e 1 per la sinistra e la destra. ValueError se l'album ha meno abbondanza di quella del prodotto"""
    from PIL import Image
    ab = round(prod["abbondanza_mm"] / 25.4 * ppi); taglio = abbondanza_px - ab
    if taglio < 0: raise ValueError(lingua.t("laboratori.meno_abbondanza"))
    if taglio: im = im.crop((taglio, taglio, im.width - taglio, im.height - taglio))
    misura = misure_px(prod)
    porta = lambda x: x if x.size == misura else x.resize(misura, Image.LANCZOS)
    if prod["consegna"]["file"] == "spread": return [(None, porta(im))]
    piega = im.width // 2
    return [(0, porta(im.crop((0, 0, piega + ab, im.height)))), (1, porta(im.crop((piega - ab, 0, im.width, im.height))))]


def cartella_nuova(base, nome):
    """cartella nuova (mai una che c'è già) dentro base: «<nome> <data ora>», poi « (2)», « (3)»..."""
    p = os.path.join(base, f"{nomi.nome_cartella(nome, 'Consegna')[:60].rstrip(' .')} {time.strftime('%Y-%m-%d %H.%M')}"); q, k = p, 2
    while True:
        try: os.makedirs(q); return q
        except FileExistsError: q = f"{p} ({k})"; k += 1


def _cm(v): return lingua.num(v)


def riepilogo(album, pr, info, file, spread, problemi, filigrana):
    """testo del riepilogo della consegna, nella lingua in uso (da leggere, e da mandare al laboratorio con i file). pr: il prodotto
    del progetto (laboratori.per_progetto), info: laboratori.stato(pr), file: nomi dei file fatti, spread: quanti nell'album,
    problemi: conta del controllo {blocca, guarda}, filigrana: prova"""
    t = lingua.t
    p = pr["prodotto"]; w, h = p["pagina_cm"]; ora = time.time()
    righe = [t("laboratori.riepilogo_titolo", album=album), t("laboratori.riepilogo_preparata", data=lingua.data(ora), ora=lingua.ora(ora)), "",
             t("laboratori.riepilogo_laboratorio", nome=pr["laboratorio"]), t("laboratori.riepilogo_catalogo", nome=pr["nome_catalogo"], id=pr["catalogo"], data=pr["data"]),
             t("laboratori.riepilogo_firma_verificata" if info["verificato"] else "laboratori.riepilogo_firma_non_verificata", motivo=info["verifica"]),
             t("laboratori.riepilogo_prodotto", nome=p["nome"], id=p["id"])]
    if pr["stato"] == "da_confermare": righe.append(t("laboratori.riepilogo_da_confermare"))
    c = p["consegna"]
    righe += ["", t("laboratori.riepilogo_pagina", w=_cm(w), h=_cm(h), doppia=_cm(round(2 * w, 2))), t("laboratori.riepilogo_abbondanza", mm=_cm(p["abbondanza_mm"])),
              t("laboratori.riepilogo_sicurezza", mm=_cm(p["sicurezza_mm"])), t("laboratori.riepilogo_piega", mm=_cm(p["piega_mm"])),
              t("laboratori.riepilogo_risoluzione", ppi=str(p["ppi"]), profilo=p["profilo_colore"]),
              t("laboratori.riepilogo_file_" + ("spread" if c["file"] == "spread" else "pagine"), formato=c["formato"].upper(), qualita=str(c["qualita"]), px="{} × {}".format(*misure_px(p)))]
    lim = ([t("laboratori.riepilogo_almeno", n=str(p["spread_min"]))] if "spread_min" in p else []) + ([t("laboratori.riepilogo_al_massimo", n=str(p["spread_max"]))] if "spread_max" in p else [])
    righe.append(t("laboratori.riepilogo_spread_limiti", n=str(spread), limiti=lingua.elenco(lim)) if lim else t("laboratori.riepilogo_spread", n=str(spread)))
    righe.append(t("laboratori.riepilogo_controllo", blocca=lingua.tn("laboratori.riepilogo_bloccano", problemi.get("blocca", 0)), guarda=str(problemi.get("guarda", 0))))
    if filigrana: righe.append(t("laboratori.riepilogo_filigrana"))
    if "copertina" in p: righe += ["", t("laboratori.riepilogo_copertina", testo=p["copertina"])]
    righe += ["", t("laboratori.riepilogo_elenco_file", n=str(len(file)))] + [f"  {f}" for f in file]
    return "\n".join(righe) + "\n"
