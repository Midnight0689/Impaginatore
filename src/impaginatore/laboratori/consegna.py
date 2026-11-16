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

from .. import nomi

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
    if taglio < 0: raise ValueError("l'album ha meno abbondanza di quella che chiede il prodotto")
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


def _cm(v): return f"{v:g}".replace(".", ",")


def riepilogo(album, pr, info, file, spread, problemi, filigrana):
    """testo del riepilogo della consegna. pr: il prodotto del progetto (laboratori.per_progetto), info: laboratori.stato(pr),
    file: nomi dei file fatti, spread: quanti nell'album, problemi: conta del controllo {blocca, guarda}, filigrana: prova"""
    p = pr["prodotto"]; w, h = p["pagina_cm"]
    righe = [f"Consegna dell'album «{album}»", f"Preparata il {time.strftime('%d/%m/%Y alle %H:%M')} con Impaginatore", "",
             f"Laboratorio: {pr['laboratorio']}", f"Catalogo: {pr['nome_catalogo']} ({pr['catalogo']}, {pr['data']})",
             "Firma del catalogo: " + ("verificato" if info["verificato"] else "NON verificato") + f" ({info['verifica']})",
             f"Prodotto: {p['nome']} ({p['id']})"]
    if pr["stato"] == "da_confermare": righe.append("ATTENZIONE: le specifiche di questo catalogo sono DA CONFERMARE con il laboratorio prima di stampare")
    righe += ["", f"Pagina: {_cm(w)} × {_cm(h)} cm (spread aperto {_cm(round(2 * w, 2))} × {_cm(h)} cm)", f"Abbondanza: {_cm(p['abbondanza_mm'])} mm per lato, compresa nei file",
              f"Zona di sicurezza: {_cm(p['sicurezza_mm'])} mm dal bordo", f"Zona della piega: {_cm(p['piega_mm'])} mm per lato",
              f"Risoluzione: {p['ppi']} ppi · profilo colore {p['profilo_colore']} incorporato", f"File: {p['consegna']['formato'].upper()} qualità {p['consegna']['qualita']}, "
              + ("uno per spread" if p["consegna"]["file"] == "spread" else "uno per pagina") + " · " + "{} × {} px".format(*misure_px(p))]
    lim = [f"almeno {p['spread_min']}" if "spread_min" in p else "", f"al massimo {p['spread_max']}" if "spread_max" in p else ""]
    righe.append(f"Spread nell'album: {spread}" + (f" (il prodotto ne vuole {' e '.join(x for x in lim if x)})" if any(lim) else ""))
    righe.append(f"Controllo dell'album: {problemi.get('blocca', 0)} problemi che bloccano, {problemi.get('guarda', 0)} da guardare")
    if filigrana: righe.append("Prova gratuita: i file hanno la filigrana e non vanno stampati")
    if "copertina" in p: righe += ["", f"Copertina (da preparare a parte, Impaginatore non la esporta): {p['copertina']}"]
    righe += ["", f"File ({len(file)}):"] + [f"  {f}" for f in file]
    return "\n".join(righe) + "\n"
