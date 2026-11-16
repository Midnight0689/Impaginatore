"""Strumenti del sito di vendita di Impaginatore (marketing/sito). Le pagine sono HTML scritto a mano: questo script
non le genera, copia la marca, prepara le immagini, applica configurazione e listino, controlla e fotografa.

    python3 strumenti/sito.py marca         token, font, logo, icone e favicon da brand/ (solo libreria standard)
    python3 strumenti/sito.py immagini      WebP delle schermate (o segnaposto), immagini Open Graph, icona Apple   [Pillow, Chrome]
    python3 strumenti/sito.py configura     config.json + docs/mercato/tier.json -> prezzi, link, interruttori, dati strutturati,
                                            sitemap.xml, robots.txt (riscrive solo testi e attributi marcati nelle pagine)
    python3 strumenti/sito.py controlla [--pubblicazione]
    python3 strumenti/sito.py istantanee [--pagine index.html,...] [--larghezze 360,768,1280,1920] [--temi chiaro,scuro]   [Chrome, Pillow]
    python3 strumenti/sito.py tutto         marca, immagini, configura, controlla
    python3 strumenti/sito.py pubblica DEST  copia in DEST (cartella vuota) solo i file da mettere sul server

Pillow: se manca, «uv run --with pillow python3 strumenti/sito.py immagini». Chrome: google-chrome o chromium.
Marcature nelle pagine (vedi README.md, «Come funziona la configurazione»):
    data-prezzo="pro.oggi"      testo = prezzo da tier.json          data-valore="computer.pro"   testo = numero da tier.json
    data-cfg="email.contatti"   testo = valore di config.json        data-link="acquisto.pro"     href = link o mailto: di ripiego
    data-url="prezzi.html"      href/content = indirizzo assoluto    data-se="in_vendita"         visibile solo se vero (data-se-non: se falso)
    data-fonte="mercato"        cifre di terzi, escluse dal confronto con tier.json
"""
import argparse
import datetime as dt
import html
import http.server
import json
import os
import re
import shutil
import struct
import sys
import threading
import urllib.parse
from html.parser import HTMLParser

QUI = os.path.dirname(os.path.abspath(__file__))
SITO = os.path.dirname(QUI)
RADICE = os.path.dirname(os.path.dirname(SITO))
BRAND = os.path.join(RADICE, "brand")
TIER = os.path.join(RADICE, "docs", "mercato", "tier.json")
CONCORRENTI = os.path.join(RADICE, "docs", "mercato", "competitor.json")
CONFIG = os.path.join(SITO, "config.json")
ORIGINALI = os.path.join(SITO, "img", "originali")
ANTEPRIME = os.path.join(SITO, "anteprime")
sys.path.insert(0, QUI)

# pagine pubblicate (percorso relativo alla radice del sito) e loro gemelle nell'altra lingua
PAGINE = ["index.html", "prezzi.html", "installa.html", "grazie.html", "legale.html", "404.html", "en/index.html", "en/installa.html"]
GEMELLE = {"index.html": "en/index.html", "installa.html": "en/installa.html"}
NELLA_MAPPA = ["index.html", "prezzi.html", "legale.html", "en/index.html"]   # installa.html resta fuori finché non ha i collegamenti della prima release (README.md)
ASSOLUTE = {"404.html"}            # servita dall'hosting a qualunque profondità: percorsi dalla radice del sito
ATTESI = {"installa.sh", "installa.ps1"}   # file previsti ma prodotti da altri (script d'installazione): mancano finché non esistono

# schermate della 2.0 (strumenti/schermate.py, foto sintetiche, tema chiaro, densità 2): nome stabile -> sorgente in
# img/originali, riquadro facoltativo da ritagliare dall'originale (x0, y0, x1, y1 in px), misura finale, larghezze pubblicate.
# Ogni schermata c'è in italiano (nome) e in inglese (nome-en). Vedi README.md, «Schermate».
_SCHERMATE = [
    dict(nome="editor-album", misura=(2400, 1500), larghezze=(800, 1200, 1600, 2400),
         cosa="Editor, vista Impagina: album di prova (36 foto sintetiche, 12 spread fatti da «Prepara la bozza»), spread 05–06. Finestra 1280 × 800, densità 2"),
    dict(nome="bozza", misura=(1960, 1284), larghezze=(700, 1400, 1960),
         cosa="Finestra «Prepara la bozza» con la proposta per 36 foto"),
    dict(nome="disposizione", misura=(2288, 1128), larghezze=(700, 1400, 2288),
         cosa="Spread 03–04 dopo D («Altra disposizione»), con le altre disposizioni nel pannello"),
    dict(nome="controlla", riquadro=(1100, 0, 2560, 1050), misura=(1460, 1050), larghezze=(730, 1460),
         cosa="Pannello «Controlla l'album» con «Sistema (2)», dopo due modifiche a mano (una foto più chiara, uno spazio diverso)"),
    dict(nome="esporta-psd", misura=(1120, 914), larghezze=(560, 1120),
         cosa="Finestra «Esporta», linguetta «PSD a livelli» (licenza Pro): serve Photoshop su questo computer"),
    dict(nome="nuovo-album", misura=(960, 1014), larghezze=(480, 960),
         cosa="Finestra «Nuovo album» con un prodotto del catalogo Generico (formati comuni, nessun laboratorio)"),
    dict(nome="assistente", misura=(960, 904), larghezze=(480, 960),
         cosa="Finestra «Assistente AI» della schermata Album: immagini spente (di serie)"),
]
SCHERMATE = [dict(s, nome=s["nome"] + suff, sorgente=s["nome"] + suff + ".png", stato="2.0") for s in _SCHERMATE for suff in ("", "-en")]

MESI = {"it": "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split(),
        "en": "January February March April May June July August September October November December".split()}


# ------------------------------------------------------------------------------------------------ dati

def leggi_json(p):
    with open(p, encoding="utf-8") as f: return json.load(f)


def leggi(p):
    with open(p, encoding="utf-8") as f: return f.read()


def scrivi(p, testo):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f: f.write(testo)


def oggi():
    v = os.environ.get("SITO_OGGI")              # per provare il comportamento dopo la fine del lancio
    return dt.date.fromisoformat(v) if v else dt.date.today()


def euro(v, lingua):
    intero = abs(v - round(v)) < 1e-9
    s = f"{v:,.0f}" if intero else f"{v:,.2f}"
    if lingua == "it": return s.replace(",", "§").replace(".", ",").replace("§", ".") + " €"
    return "€" + s


def data_lunga(iso, lingua):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {MESI[lingua][d.month - 1]} {d.year}"


def lancio_attivo(cfg, giorno=None):
    f = cfg.get("data_fine_lancio") or ""
    return bool(f) and dt.date.fromisoformat(f) >= (giorno or oggi())


def valori(tier, cfg):
    """chiavi data-prezzo -> importo (numero) e data-valore -> numero, tutti da tier.json"""
    attivo = lancio_attivo(cfg); iva = tier["aliquota_iva_riferimento"]
    prezzi, numeri = {}, {}
    ivato = lambda x: round(x * (1 + iva) + 1e-9, 2)
    for t in tier["tiers"]:
        i = t["id"]
        prezzi[f"{i}.listino"] = t["prezzo_netto"]; prezzi[f"{i}.lancio"] = t["prezzo_lancio"]
        prezzi[f"{i}.listino_ivato"] = t["prezzo_ivato"]; prezzi[f"{i}.lancio_ivato"] = t["prezzo_lancio_ivato"]
        prezzi[f"{i}.oggi"] = t["prezzo_lancio"] if attivo else t["prezzo_netto"]
        prezzi[f"{i}.oggi_ivato"] = t["prezzo_lancio_ivato"] if attivo else t["prezzo_ivato"]
        if not t["aggiornamenti"]["upgrade_maggiore_incluso"]:
            prezzi[f"upgrade.{i}"] = round(t["prezzo_netto"] * (100 - t["aggiornamenti"]["sconto_upgrade_maggiore_pct"]) / 100, 2)
        numeri[f"computer.{i}"] = t["funzioni"]["computer"]
        numeri[f"ore_incluse.{i}"] = t["supporto"]["ore_assistenza_incluse"]
        for k in ("modelli_autore", "modelli_personali"):
            if isinstance(t["funzioni"][k], int) and not isinstance(t["funzioni"][k], bool): numeri[f"{k}.{i}"] = t["funzioni"][k]
    for p in tier["assistenza"]["pacchetti"]:
        prezzi[f"ore.{p['id']}"] = p["prezzo_netto"]; prezzi[f"ore.{p['id']}.ivato"] = ivato(p["prezzo_netto"])
        numeri[f"ore.{p['id']}"] = p["ore"]
    for k, v in tier["upgrade_tier_netto"].items(): prezzi[f"passaggio.{k}"] = v
    pol = tier["politica_aggiornamenti"]; prova = tier["prova"]
    numeri.update({"prova.giorni": prova["giorni"], "rimborso.giorni": tier["garanzia_rimborso_giorni"], "lancio.giorni": tier["lancio"]["durata_giorni"],
                   "lancio.licenze": tier["lancio"]["max_licenze"], "ore.unita": tier["assistenza"]["unita_minima_minuti"],
                   "aggiornamenti.mesi": pol["mesi_minimi_tra_versioni_maggiori"], "aggiornamenti.finestra": pol["giorni_finestra_upgrade_gratuito"],
                   "upgrade.sconto": tier["tiers"][0]["aggiornamenti"]["sconto_upgrade_maggiore_pct"], "iva": round(iva * 100)})
    pil = tier["laboratorio"]["pilota"]
    numeri.update({"pilota.giorni": pil["giorni"], "pilota.min": pil["fotografi"][0], "pilota.max": pil["fotografi"][1], "pilota.gratuiti": pil["setup_gratuito_primi_laboratori"]})
    return prezzi, numeri


def interruttori(cfg):
    s = dict(cfg.get("interruttori", {}))
    s["lancio"] = lancio_attivo(cfg)
    s["modulo_lista"] = bool(cfg.get("modulo_lista_attesa"))
    return s


def assoluto(cfg, percorso):
    base = cfg.get("percorso_base", "/") or "/"
    if not base.endswith("/"): base += "/"
    return cfg["dominio"].rstrip("/") + base + percorso.lstrip("/")


def relativo(pagina, percorso, cfg):
    """un percorso dalla radice del sito, visto dalla pagina (relativo; dalla radice per le pagine ASSOLUTE)"""
    if re.match(r"^[a-z]+:", percorso) or percorso.startswith("#"): return percorso
    if pagina in ASSOLUTE:
        base = cfg.get("percorso_base", "/") or "/"
        return (base if base.endswith("/") else base + "/") + percorso.lstrip("/")
    return "../" * pagina.count("/") + percorso


# testi dei ripieghi mailto: (chi scrive, oggetto, corpo) per lingua
def mailto(indirizzo, oggetto, corpo):
    return "mailto:" + indirizzo + "?subject=" + urllib.parse.quote(oggetto, safe="") + "&body=" + urllib.parse.quote(corpo, safe="")


NOMI = {"essenziale": "Essenziale", "pro": "Pro", "studio": "Studio"}


def link_di(chiave, cfg, tier, lingua, pagina):
    L = cfg.get("link", {}); E = cfg.get("email", {})
    privacy = assoluto(cfg, L.get("privacy") or "legale.html#privacy") if not re.match(r"^[a-z]+:", L.get("privacy", "")) else L["privacy"]
    gruppo, _, nome = chiave.partition(".")
    if gruppo == "acquisto":
        if L.get(f"acquisto_{nome}"): return L[f"acquisto_{nome}"]
        t = next(t for t in tier["tiers"] if t["id"] == nome); n = t["funzioni"]["computer"]
        if lingua == "it":
            return mailto(E["vendite"], f"Richiesta d'acquisto: Impaginatore {NOMI[nome]}",
                          f"Ciao, vorrei acquistare Impaginatore {NOMI[nome]} (licenza per {n} computer).\n\n"
                          "Nome o ragione sociale:\nPaese:\nPartita IVA o codice fiscale:\nCodice destinatario SdI o PEC (solo per l'Italia):\n"
                          "Intestatario della licenza (il nome che comparirà nel programma):\n\nMandatemi l'importo e i dati per il bonifico.")
        return mailto(E["vendite"], f"Purchase request: Impaginatore {NOMI[nome]}",
                      f"Hi, I'd like to buy Impaginatore {NOMI[nome]} (licence for {n} computer{'s' if n > 1 else ''}).\n\n"
                      "Name or company:\nCountry:\nVAT number (businesses):\nLicence holder (the name shown in the app):\n\nPlease send me the amount and the bank transfer details.")
    if gruppo == "ore":
        if L.get(f"ore_{nome}"): return L[f"ore_{nome}"]
        p = next(p for p in tier["assistenza"]["pacchetti"] if p["id"] == nome); h = p["ore"]
        if lingua == "it":
            return mailto(E["assistenza"], f"Ore di assistenza: {h} {'ora' if h == 1 else 'ore'}",
                          f"Ciao, vorrei acquistare {h} {'ora' if h == 1 else 'ore'} di assistenza.\n\nNome o ragione sociale:\nPartita IVA o codice fiscale:\n"
                          "Di cosa hai bisogno (installazione, primo album, formati del laboratorio, Photoshop...):\n")
        return mailto(E["assistenza"], f"Support hours: {h} hour{'s' if h > 1 else ''}",
                      f"Hi, I'd like to buy {h} hour{'s' if h > 1 else ''} of support.\n\nName or company:\nVAT number (businesses):\nWhat you need help with:\n")
    if chiave == "laboratori":
        if L.get("laboratori"): return L["laboratori"]
        if lingua == "it":
            return mailto(E["laboratori"], "Edizione Laboratorio: parliamone",
                          "Ciao, vorremmo saperne di più sull'Edizione Laboratorio.\n\nLaboratorio:\nSito:\nQuanti fotografi lavorano con voi:\nCome ricevete oggi i file degli album:\n")
        return mailto(E["laboratori"], "Lab Edition: let's talk",
                      "Hi, we'd like to know more about the Lab Edition.\n\nLab:\nWebsite:\nHow many photographers work with you:\nHow you receive album files today:\n")
    if chiave == "lista":
        if lingua == "it":
            return mailto(E["lista_attesa"], "Avvisami al lancio di Impaginatore",
                          "Vorrei ricevere un'email quando Impaginatore sarà in vendita.\n\nAcconsento all'uso di questo indirizzo solo per questo scopo; "
                          f"posso chiedere di cancellarlo quando voglio.\nInformativa: {privacy}\n")
        return mailto(E["lista_attesa"], "Tell me when Impaginatore launches",
                      "I'd like an email when Impaginatore goes on sale.\n\nI agree that you use this address only for this purpose; "
                      f"I can ask you to delete it at any time.\nPrivacy notice: {privacy}\n")
    if gruppo == "email": return "mailto:" + E[nome]
    if gruppo in ("download", "script"):
        v = L.get(f"{gruppo}_{nome}") or ""
        return relativo(pagina, v, cfg) if v else relativo(pagina, "installa.html" if lingua == "it" else "en/installa.html", cfg)
    v = L.get(chiave) or ""
    if not v and chiave == "impronte": v = "installa.html" if lingua == "it" else "en/installa.html"
    if not v: v = "legale.html#" + chiave.replace("_", "-")
    return relativo(pagina, v, cfg)


def testo_cfg(chiave, cfg, lingua):
    if chiave in ("data_fine_lancio", "data_lancio"): return data_lunga(cfg[chiave], lingua) if cfg.get(chiave) else ""
    if chiave == "dominio_testo": return re.sub(r"^https?://", "", cfg["dominio"]).rstrip("/")
    if chiave == "requisiti": return cfg["requisiti"][lingua]
    if chiave == "comando_mac": return f"curl -fsSL {assoluto(cfg, cfg['link']['script_mac'])} | sh"
    if chiave == "comando_windows": return f"irm {assoluto(cfg, cfg['link']['script_windows'])} | iex"
    if chiave in ("url_script_mac", "url_script_windows"): return assoluto(cfg, cfg["link"][chiave.replace("url_", "")])
    v = cfg
    for parte in chiave.split("."): v = v[parte]
    return v


# ------------------------------------------------------------------------------------------------ HTML

ATTR = re.compile(r'([^\s=/>]+)(?:\s*=\s*"([^"]*)")?')
TAG = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)((?:\s+[^\s=/>]+(?:\s*=\s*\"[^\"]*\")?)*)\s*(/?)>")
GESTITI = ("data-prezzo", "data-valore", "data-cfg", "data-link", "data-url", "data-se", "data-se-non", "data-modulo", "data-fine-lancio")
CONTENUTO = ("data-prezzo", "data-valore", "data-cfg")


def zone_escluse(testo):
    return [m.span() for m in re.finditer(r"<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>", testo, re.S)]


def lingua_di(testo):
    m = re.search(r'<html[^>]*\blang="([a-z]+)', testo)
    return m.group(1) if m else "it"


def applica(pagina, testo, cfg, tier):
    """riscrive testi e attributi marcati; restituisce il nuovo HTML (stesso testo se è già allineato)"""
    lingua = lingua_di(testo); prezzi, numeri = valori(tier, cfg); sw = interruttori(cfg)
    escluse = zone_escluse(testo)
    fuori = lambda a: not any(s <= a < e for s, e in escluse)
    out, pos = [], 0
    for m in TAG.finditer(testo):
        if not fuori(m.start()): continue
        nome, grezzi = m.group(1).lower(), m.group(2) or ""
        if not any(g + "=" in grezzi or g + " " in grezzi or grezzi.endswith(g) for g in GESTITI): continue
        attr = [(x.group(1), x.group(2)) for x in ATTR.finditer(grezzi)]      # None = attributo senza valore (hidden)
        d = dict(attr); nuovi = dict(attr)
        contenuto = None
        if "data-prezzo" in d:
            k = d["data-prezzo"]
            if k not in prezzi: raise SystemExit(f"{pagina}: data-prezzo «{k}» sconosciuto")
            contenuto = euro(prezzi[k], lingua)
            if k.endswith(".oggi") or k.endswith(".oggi_ivato"):
                nuovi["data-listino"] = euro(prezzi[k.replace("oggi", "listino")], lingua)
        if "data-valore" in d:
            k = d["data-valore"]
            if k not in numeri: raise SystemExit(f"{pagina}: data-valore «{k}» sconosciuto")
            contenuto = str(numeri[k])
        if "data-cfg" in d: contenuto = html.escape(str(testo_cfg(d["data-cfg"], cfg, lingua)), quote=False)
        if "data-link" in d: nuovi["href"] = html.escape(link_di(d["data-link"], cfg, tier, lingua, pagina))
        if "data-url" in d:
            chiave = "content" if nome == "meta" else "href"
            nuovi[chiave] = html.escape(assoluto(cfg, d["data-url"]))
        if "data-se" in d or "data-se-non" in d:
            vero = all(sw.get(x, False) for x in d.get("data-se", "").split()) and not any(sw.get(x, False) for x in d.get("data-se-non", "").split())
            if vero: nuovi.pop("hidden", None)
            else: nuovi["hidden"] = None
        if "data-modulo" in d:
            nuovi["action"] = html.escape(cfg.get("modulo_lista_attesa") or relativo(pagina, "grazie.html", cfg) + "?per=lista")
        if "data-fine-lancio" in d:
            nuovi["data-fine-lancio"] = cfg.get("data_fine_lancio") or ""
        ordine = [a for a, _ in attr] + [a for a in nuovi if a not in d]
        parti = []
        for a in ordine:
            if a not in nuovi: continue
            v = nuovi[a]
            parti.append(a if v is None else f'{a}="{v}"')
        nuovo_tag = f"<{m.group(1)}{' ' if parti else ''}{' '.join(parti)}{m.group(3)}>"
        out.append(testo[pos:m.start()]); out.append(nuovo_tag); pos = m.end()
        if contenuto is not None and any(c in d for c in CONTENUTO):
            fine = testo.find(f"</{m.group(1)}>", m.end())
            interno = testo[m.end():fine]
            if "<" in interno: raise SystemExit(f"{pagina}: l'elemento {nuovo_tag} deve contenere solo testo")
            out.append(contenuto); pos = fine
    out.append(testo[pos:])
    nuovo = "".join(out)
    return dati_strutturati(pagina, nuovo, cfg, tier, lingua)


class Nodo:
    __slots__ = ("tag", "attr", "figli", "padre", "testo", "riga")

    def __init__(self, tag, attr=None, padre=None, riga=0):
        self.tag, self.attr, self.figli, self.padre, self.testo, self.riga = tag, dict(attr or {}), [], padre, None, riga

    def nascosto(self):
        n = self
        while n is not None:
            if "hidden" in n.attr or n.attr.get("aria-hidden") == "true" and n.tag != "svg": return True
            n = n.padre
        return False

    def antenato(self, prova):
        n = self.padre
        while n is not None:
            if prova(n): return n
            n = n.padre
        return None

    def tutti(self):
        for f in self.figli:
            yield f
            if f.tag != "#testo": yield from f.tutti()

    def testo_interno(self):
        return "".join(f.testo for f in self.tutti() if f.tag == "#testo")


VUOTI = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Costruttore(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.radice = Nodo("#documento"); self.cur = self.radice; self.dentro = None

    def handle_starttag(self, tag, attrs):
        n = Nodo(tag, attrs, self.cur, self.getpos()[0]); self.cur.figli.append(n)
        if tag not in VUOTI: self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.figli.append(Nodo(tag, attrs, self.cur, self.getpos()[0]))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag: n = n.padre
        if n is not None and n.padre is not None: self.cur = n.padre

    def handle_data(self, data):
        t = Nodo("#testo", None, self.cur, self.getpos()[0]); t.testo = data; self.cur.figli.append(t)


def albero(testo):
    c = Costruttore(); c.feed(testo); c.close()
    return c.radice


def domande(radice):
    """domande frequenti visibili: (domanda, risposta) dai <details class="domanda">"""
    out = []
    for n in radice.tutti():
        if n.tag == "details" and "domanda" in n.attr.get("class", "").split() and not n.nascosto():
            q = next((f for f in n.figli if f.tag == "summary"), None)
            r = next((f for f in n.figli if f.tag == "div"), None)
            if q and r:
                pulisci = lambda s: re.sub(r"\s+", " ", s).strip()
                out.append((pulisci(q.testo_interno()), pulisci(r.testo_interno())))
    return out


def dati_strutturati(pagina, testo, cfg, tier, lingua):
    def sostituisci(tipo, oggetto):
        nonlocal testo
        js = json.dumps(oggetto, ensure_ascii=False, indent=1).replace("</", "<\\/")
        testo = re.sub(r'(<script type="application/ld\+json" data-ld="' + tipo + r'">)(.*?)(</script>)', lambda m: m.group(1) + "\n" + js + "\n" + m.group(3), testo, flags=re.S)
    if 'data-ld="software"' in testo:
        attivo = lancio_attivo(cfg); sw = interruttori(cfg)
        offerte = []
        for t in tier["tiers"]:
            prezzo = t["prezzo_lancio"] if attivo else t["prezzo_netto"]
            o = {"@type": "Offer", "name": f"Impaginatore {t['nome']}", "price": f"{prezzo:.2f}", "priceCurrency": "EUR",
                 "availability": "https://schema.org/InStock" if sw.get("in_vendita") else "https://schema.org/PreOrder",
                 "url": assoluto(cfg, "prezzi.html" if lingua == "it" else "en/index.html#prices"),
                 "priceSpecification": {"@type": "UnitPriceSpecification", "price": prezzo, "priceCurrency": "EUR", "valueAddedTaxIncluded": False}}
            if attivo: o["priceValidUntil"] = cfg["data_fine_lancio"]
            offerte.append(o)
        desc = {"it": "Programma desktop per impaginare album fotografici di matrimonio sul proprio computer. Licenza perpetua, pagamento una tantum.",
                "en": "Desktop app for laying out wedding photo albums on your own computer. Perpetual licence, one-time payment."}[lingua]
        sostituisci("software", {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Impaginatore", "applicationCategory": "DesignApplication",
                                 "operatingSystem": "macOS, Windows, Linux", "inLanguage": lingua, "description": desc,
                                 "url": assoluto(cfg, "" if lingua == "it" else "en/"), "image": assoluto(cfg, f"img/og/og-{lingua}.jpg"), "offers": offerte})
    if 'data-ld="faq"' in testo:
        dd = domande(albero(testo))
        sostituisci("faq", {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lingua,
                            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in dd]})
    return testo


def mappa(cfg):
    righe = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    oggi_s = oggi().isoformat()
    inverse = {v: k for k, v in GEMELLE.items()}
    for p in NELLA_MAPPA:
        if not os.path.exists(os.path.join(SITO, p)): continue
        url = lambda q: assoluto(cfg, "" if q == "index.html" else "en/" if q == "en/index.html" else q)
        righe.append(f"  <url><loc>{url(p)}</loc><lastmod>{oggi_s}</lastmod>")
        it, en = (p, GEMELLE.get(p)) if not p.startswith("en/") else (inverse.get(p), p)
        if it and en and os.path.exists(os.path.join(SITO, en)):
            righe.append(f'    <xhtml:link rel="alternate" hreflang="it" href="{url(it)}"/>')
            righe.append(f'    <xhtml:link rel="alternate" hreflang="en" href="{url(en)}"/>')
        righe.append("  </url>")
    righe.append("</urlset>")
    return "\n".join(righe) + "\n"


def configura(a=None, scrivere=True):
    cfg, tier = leggi_json(CONFIG), leggi_json(TIER)
    cambiati = []
    for p in PAGINE:
        f = os.path.join(SITO, p)
        if not os.path.exists(f): continue
        vecchio = leggi(f); nuovo = applica(p, vecchio, cfg, tier)
        if nuovo != vecchio:
            cambiati.append(p)
            if scrivere: scrivi(f, nuovo)
    altri = {"sitemap.xml": mappa(cfg), "robots.txt": f"User-agent: *\nAllow: /\n\nSitemap: {assoluto(cfg, 'sitemap.xml')}\n"}
    for nome, contenuto in altri.items():
        f = os.path.join(SITO, nome)
        vecchio = leggi(f) if os.path.exists(f) else ""
        # la data di lastmod cambia ogni giorno: non conta come differenza
        if re.sub(r"<lastmod>[^<]*</lastmod>", "", vecchio) != re.sub(r"<lastmod>[^<]*</lastmod>", "", contenuto):
            cambiati.append(nome)
            if scrivere: scrivi(f, contenuto)
    if scrivere: print("configurate:", ", ".join(cambiati) if cambiati else "nessun cambiamento")
    return cambiati


# ------------------------------------------------------------------------------------------------ marca

def marca(a=None):
    copiati = []

    def copia(da, a_):
        os.makedirs(os.path.dirname(a_), exist_ok=True); shutil.copyfile(da, a_); copiati.append(os.path.relpath(a_, SITO))
    tok = leggi(os.path.join(BRAND, "tokens.css"))
    scrivi(os.path.join(SITO, "css", "token.css"), "/* Copia di brand/tokens.css fatta da strumenti/sito.py marca: non modificare qui, si rigenera. */\n" + tok)
    copiati.append("css/token.css")
    fonti = leggi(os.path.join(BRAND, "font", "font.css"))
    fonti = re.sub(r',\s*url\("[^"]+\.ttf"\)\s*format\("truetype"\)', "", fonti)            # sul web bastano i .woff2
    fonti = re.sub(r'url\("([^"/]+\.woff2)"\)', lambda m: 'url("../font/' + urllib.parse.quote(m.group(1)) + '")', fonti)
    scrivi(os.path.join(SITO, "css", "font.css"), "/* Ricavato da brand/font/font.css da strumenti/sito.py marca (solo .woff2): non modificare qui. */\n" + fonti)
    copiati.append("css/font.css")
    for f in sorted(os.listdir(os.path.join(BRAND, "font"))):
        if f.endswith(".woff2") or f.startswith("OFL-"): copia(os.path.join(BRAND, "font", f), os.path.join(SITO, "font", f))
    for f in ("impaginatore-logotipo.svg", "impaginatore-logotipo-negativo.svg", "impaginatore-simbolo.svg", "impaginatore-simbolo-negativo.svg",
              "impaginatore-verticale.svg", "impaginatore-verticale-negativo.svg"):
        copia(os.path.join(BRAND, "logo", f), os.path.join(SITO, "img", "marca", f))
    copia(os.path.join(BRAND, "icona", "favicon.svg"), os.path.join(SITO, "favicon.svg"))
    copia(os.path.join(BRAND, "icona", "icona.ico"), os.path.join(SITO, "favicon.ico"))
    copia(os.path.join(BRAND, "icona", "favicon-32.png"), os.path.join(SITO, "img", "marca", "favicon-32.png"))
    copia(os.path.join(BRAND, "icona", "icona-256.png"), os.path.join(SITO, "img", "marca", "icona-256.png"))
    # icone: i simboli del manuale di marca, tra i segni «icone:inizio» e «icone:fine» di ogni pagina
    anteprima = leggi(os.path.join(BRAND, "anteprima.html"))
    simboli = "\n".join(m.group(0) for m in re.finditer(r'<symbol id="i-[a-z-]+".*?</symbol>', anteprima, re.S))
    for p in PAGINE:
        f = os.path.join(SITO, p)
        if not os.path.exists(f): continue
        t = leggi(f)
        n = re.sub(r"(<!-- icone:inizio -->).*?(<!-- icone:fine -->)", lambda m: m.group(1) + "\n" + simboli + "\n" + m.group(2), t, flags=re.S)
        if n != t: scrivi(f, n); copiati.append(p + " (icone)")
    print("dalla marca:", len(copiati), "file")
    return copiati


# ------------------------------------------------------------------------------------------------ immagini

def immagini(a=None):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise SystemExit("serve Pillow: uv run --with pillow python3 strumenti/sito.py immagini")
    dest = os.path.join(SITO, "img", "schermate"); os.makedirs(dest, exist_ok=True)
    mono = os.path.join(BRAND, "font", "IBMPlexMono-Medium.ttf")
    fatte = []
    for s in SCHERMATE:
        W, H = s["misura"]; src = os.path.join(ORIGINALI, s["sorgente"])
        if os.path.exists(src):
            im = Image.open(src).convert("RGB")
            if s.get("riquadro"): im = im.crop(s["riquadro"])
            r_src, r_dst = im.width / im.height, W / H
            if abs(r_src - r_dst) > 0.002:            # rapporto diverso: ritaglio centrato, poi riduzione
                if r_src > r_dst: nw = round(im.height * r_dst); im = im.crop(((im.width - nw) // 2, 0, (im.width - nw) // 2 + nw, im.height))
                else: nh = round(im.width / r_dst); im = im.crop((0, (im.height - nh) // 2, im.width, (im.height - nh) // 2 + nh))
            stato = s["stato"]
        else:                                          # segnaposto con le misure esatte, finché la schermata vera non c'è
            im = Image.new("RGB", (W, H), (237, 233, 225)); d = ImageDraw.Draw(im)
            for x in range(0, W, 40): d.line([(x, 0), (x, H)], fill=(222, 218, 210), width=1)
            for y in range(0, H, 40): d.line([(0, y), (W, y)], fill=(222, 218, 210), width=1)
            d.rectangle([0, 0, W - 1, H - 1], outline=(107, 105, 100), width=4)
            f1 = ImageFont.truetype(mono, max(28, W // 32)); f2 = ImageFont.truetype(mono, max(18, W // 60))
            righe = [("SEGNAPOSTO · " + s["nome"], f1), (f"{W} × {H} px", f1)] + [(t, f2) for t in _a_capo(s["cosa"], 58)]
            y = H // 2 - sum(f.size + 18 for _, f in righe) // 2
            for t, f in righe:
                w = d.textlength(t, font=f); d.text(((W - w) / 2, y), t, font=f, fill=(84, 82, 78)); y += f.size + 18
            stato = "segnaposto"
        for w in s["larghezze"]:
            h = round(w * H / W)
            v = im.resize((w, h), Image.LANCZOS) if im.size != (w, h) else im
            p = os.path.join(dest, f"{s['nome']}-{w}.webp")
            v.save(p, "WEBP", quality=82 if "spread" in s["nome"] else 86, method=6)
            fatte.append(p)
        print(f"  {s['nome']:<20} {stato:<11} {W} × {H}  ->", ", ".join(f"{w}w" for w in s["larghezze"]))
    # icona per i dispositivi Apple (180 px) dall'icona della marca
    Image.open(os.path.join(BRAND, "icona", "icona-1024.png")).convert("RGBA").resize((180, 180), Image.LANCZOS).save(os.path.join(SITO, "img", "marca", "apple-touch-icon.png"), optimize=True)
    og(Image)
    return fatte


def _a_capo(testo, n):
    righe, r = [], ""
    for p in testo.split():
        if len(r) + len(p) + 1 > n: righe.append(r); r = p
        else: r = (r + " " + p).strip()
    return righe + ([r] if r else [])


class Servitore:
    """il sito servito su 127.0.0.1 a una porta libera (le pagine mancanti rispondono con 404.html, come un hosting)"""

    def __init__(self, cartella=SITO):
        cartella_ = cartella

        class Gestore(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *x, **k): super().__init__(*x, directory=cartella_, **k)

            def log_message(self, *x): pass

            def send_error(self, code, message=None, explain=None):
                if code == 404 and os.path.exists(os.path.join(cartella_, "404.html")):
                    corpo = open(os.path.join(cartella_, "404.html"), "rb").read()
                    self.send_response(404); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(corpo))); self.end_headers()
                    self.wfile.write(corpo); return
                super().send_error(code, message, explain)
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Gestore)

    def __enter__(self):
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/"
        return self

    def __exit__(self, *_):
        self.srv.shutdown(); self.srv.server_close()


def og(Image):
    """immagini Open Graph 1200 × 630 (JPEG), rese da strumenti/modelli/og.html con i caratteri della marca"""
    import cromo
    dest = os.path.join(SITO, "img", "og"); os.makedirs(dest, exist_ok=True)
    tmp = os.path.join(ORIGINALI, "og.png"); os.makedirs(ORIGINALI, exist_ok=True)
    with Servitore() as s, cromo.Chrome() as c:
        for lingua in ("it", "en"):
            c.vista(1200, 630, 1, tema="light")
            c.apri(s.url + f"strumenti/modelli/og.html?{lingua}")
            c.carica_immagini()
            c.foto(tmp, pagina_intera=False)
            Image.open(tmp).convert("RGB").save(os.path.join(dest, f"og-{lingua}.jpg"), "JPEG", quality=86, optimize=True, progressive=True)
            print(f"  og-{lingua}.jpg 1200 × 630")
    os.remove(tmp)


# ------------------------------------------------------------------------------------------------ controlli

def dimensioni(percorso):
    """(larghezza, altezza) di un PNG, JPEG, WebP o SVG, senza librerie esterne"""
    with open(percorso, "rb") as f: d = f.read(1 << 16)
    if d[:8] == b"\x89PNG\r\n\x1a\n": return struct.unpack(">II", d[16:24])
    if d[:4] == b"RIFF" and d[8:12] == b"WEBP":
        k = d[12:16]
        if k == b"VP8X": return 1 + int.from_bytes(d[24:27], "little"), 1 + int.from_bytes(d[27:30], "little")
        if k == b"VP8L": b = int.from_bytes(d[21:25], "little"); return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
        if k == b"VP8 ": return struct.unpack("<HH", d[26:30])[0] & 0x3FFF, struct.unpack("<HH", d[26:30])[1] & 0x3FFF
    if d[:2] == b"\xff\xd8":
        with open(percorso, "rb") as f: d = f.read()
        i = 2
        while i < len(d):
            if d[i] != 0xFF: i += 1; continue
            m = d[i + 1]
            if m in (0xC0, 0xC1, 0xC2): h, w = struct.unpack(">HH", d[i + 5:i + 9]); return w, h
            i += 2 + struct.unpack(">H", d[i + 2:i + 4])[0]
    if percorso.endswith(".svg"):
        m = re.search(rb'viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"', d)
        if m: return float(m.group(1)), float(m.group(2))
    return None


def parole_vietate():
    """dal manuale di marca, §5: (espressione regolare, parola, grave) per l'italiano e per l'inglese"""
    sb = leggi(os.path.join(BRAND, "STYLEBOOK.md"))
    it = re.search(r"\*\*Parole vietate\.\*\*(.*?)\n", sb).group(1)
    en = re.search(r"In inglese: (magic.*?)\n", sb).group(1)
    regole = {"it": [], "en": []}
    lievi = {"cloud", "emozioni"}               # ammesse in un senso preciso: si segnalano da rileggere
    for lingua, riga in (("it", it), ("en", en)):
        for voce in riga.split("·"):
            voce = re.sub(r"\(.*?\)", "", voce).strip().rstrip(".")
            if not voce or voce in ("emoji", "punti esclamativi"): continue
            forme = []
            if voce.startswith("l’IA crea/decide"): forme = ["l[’']IA crea", "l[’']IA decide"]
            elif "/" in voce: forme = [re.escape(x.strip()) for x in voce.split("/")]
            elif voce.startswith("intelligenza artificiale"): forme = ["intelligenza artificiale"]
            else: forme = [re.escape(voce).replace("’", "[’']")]
            for f in forme: regole[lingua].append((re.compile(r"(?<!\w)" + f + r"(?!\w)", re.I), voce, voce not in lievi))
    return regole


def marchi():
    nomi = set()
    for c in leggi_json(CONCORRENTI):
        for parte in re.split(r"/|\(", c["nome"]):
            parte = re.sub(r"\b(ex|by|AI Album Designer)\b.*", "", parte).strip(" )+")
            if parte and parte not in ("Album Studio", "Adobe Photography plan", "Photoshop + Lightroom", "Evolve Edits - Album Design", "outsourcing", "+ template"): nomi.add(parte)
    nomi |= {"Pixellu", "Fundy", "SmartAlbums", "Smart Albums", "Graphistudio", "Queensberry", "Aftershoot", "Evoto", "ProSelect", "Yervant", "Imagen", "Pic-Time",
             "AI Album Studio", "ilFotoalbum", "Il Fotoalbum", "Kiss Books", "QT Albums", "Vision Art", "InDesign", "PhotoSì", "Photocity", "Saal", "Zno", "Samaro",
             "Graphisoftware", "GraphiDesigner", "Maqueteer", "AlbumTeller", "AlbumStomp", "DigiAlbum", "Canva", "Affinity", "Lightroom"}
    return sorted(nomi, key=len, reverse=True)


def risorse_css(percorso):
    """url() di un foglio di stile, risolti rispetto al foglio"""
    t = leggi(percorso)
    return [(u, os.path.normpath(os.path.join(os.path.dirname(percorso), urllib.parse.unquote(u)))) for u in re.findall(r'url\("?([^")]+)"?\)', t)]


def controlla(a=None):
    pubblicazione = bool(a and getattr(a, "pubblicazione", False))
    cfg, tier = leggi_json(CONFIG), leggi_json(TIER)
    errori, avvisi = [], []
    E = lambda p, msg: errori.append(f"{p}: {msg}")
    A_ = lambda p, msg: avvisi.append(f"{p}: {msg}")
    prezzi, numeri = valori(tier, cfg); sw = interruttori(cfg)
    regole = parole_vietate(); nomi = marchi()
    pagine = {p: leggi(os.path.join(SITO, p)) for p in PAGINE if os.path.exists(os.path.join(SITO, p))}
    for p in PAGINE:
        if p not in pagine: E(p, "pagina mancante")
    alberi = {p: albero(t) for p, t in pagine.items()}
    ids = {p: {n.attr["id"] for n in r.tutti() if n.tag != "#testo" and "id" in n.attr} for p, r in alberi.items()}
    pesi = {}
    importi_ammessi = {euro(v, lg) for v in prezzi.values() for lg in ("it", "en")}

    # 0. configurazione applicata
    da_fare = configura(scrivere=False)
    if da_fare: E("config.json", "pagine non allineate a config.json o tier.json: esegui «sito.py configura» (" + ", ".join(da_fare) + ")")

    for p, t in pagine.items():
        r = alberi[p]; lingua = lingua_di(t); nodi = [n for n in r.tutti() if n.tag != "#testo"]
        # 1. struttura minima
        h1 = [n for n in nodi if n.tag == "h1"]
        if len(h1) != 1: E(p, f"{len(h1)} titoli h1 (ne serve uno)")
        livelli = [int(n.tag[1]) for n in nodi if re.fullmatch(r"h[1-6]", n.tag) and not n.nascosto()]
        for x, y in zip(livelli, livelli[1:]):
            if y > x + 1: E(p, f"titoli che saltano un livello (h{x} -> h{y})")
        visti = {}
        for n in nodi:
            if "id" in n.attr:
                if n.attr["id"] in visti: E(p, f"id ripetuto «{n.attr['id']}»")
                visti[n.attr["id"]] = 1
        for nome in ("title",):
            if not any(n.tag == nome for n in nodi): E(p, "manca <title>")
        if not any(n.tag == "meta" and n.attr.get("name") == "description" for n in nodi): E(p, "manca la descrizione")
        if not any(n.tag == "meta" and n.attr.get("name") == "viewport" for n in nodi): E(p, "manca il viewport")
        if p not in ASSOLUTE and p != "grazie.html" and not any(n.tag == "link" and n.attr.get("rel") == "canonical" for n in nodi): E(p, "manca il canonical")
        gem = GEMELLE.get(p) or {v: k for k, v in GEMELLE.items()}.get(p)
        if gem and gem in pagine:
            alt = {n.attr.get("hreflang") for n in nodi if n.tag == "link" and n.attr.get("rel") == "alternate"}
            if not {"it", "en"} <= alt: E(p, "mancano gli hreflang it/en")
        # 2. collegamenti interni e richieste esterne
        for n in nodi:
            for att in ("href", "src", "srcset", "action", "poster", "content"):
                if att not in n.attr or n.attr[att] is None: continue
                vals = [x.strip().split(" ")[0] for x in n.attr[att].split(",")] if att == "srcset" else [n.attr[att]]
                for v in vals:
                    if not v: continue
                    esterno = re.match(r"^(https?:)?//", v)
                    if att == "content":
                        continue
                    if esterno:
                        richiesta = att in ("src", "srcset", "poster") or (n.tag == "link" and n.attr.get("rel") not in ("canonical", "alternate")) or n.tag == "script"
                        if richiesta: E(p, f"richiesta verso la rete esterna: {v}")
                        elif att == "action" and not cfg.get("modulo_lista_attesa", "").startswith(v[:20]): E(p, f"modulo verso l'esterno non configurato: {v}")
                        elif att == "href" and n.tag == "a" and not v.startswith(cfg["dominio"]): A_(p, f"link in uscita: {v}")
                        continue
                    if re.match(r"^(mailto|tel|data|javascript):", v): continue
                    url = urllib.parse.urlsplit(v)
                    if not url.path:
                        if url.fragment and url.fragment not in ids[p]: E(p, f"ancora inesistente #{url.fragment}")
                        continue
                    base = SITO if url.path.startswith("/") else os.path.dirname(os.path.join(SITO, p))
                    dest = os.path.normpath(os.path.join(base, urllib.parse.unquote(url.path.lstrip("/") if url.path.startswith("/") else url.path)))
                    if url.path.endswith("/"): dest = os.path.join(dest, "index.html")
                    rel = os.path.relpath(dest, SITO)
                    if not os.path.exists(dest):
                        if rel in ATTESI: A_(p, f"{v}: previsto, non ancora nel sito (lo prepara il team prodotto)")
                        else: E(p, f"collegamento rotto: {v}")
                        continue
                    if url.fragment and rel in pagine and url.fragment not in ids[rel]: E(p, f"ancora inesistente {v}")
        # 3. immagini e grafica
        for n in nodi:
            if n.tag == "img":
                if "alt" not in n.attr: E(p, f"immagine senza alt: {n.attr.get('src')}")
                elif not (n.attr["alt"] or "").strip() and n.attr.get("role") != "presentation" and not n.antenato(lambda x: x.attr.get("aria-hidden") == "true"):
                    E(p, f"alt vuoto senza role=presentation: {n.attr.get('src')}")
                if not (n.attr.get("width") and n.attr.get("height")): E(p, f"immagine senza width/height (il layout salta): {n.attr.get('src')}")
                elif n.attr.get("src", "").startswith(("img/", "../img/", "/img/")):
                    src = n.attr["src"]; f = os.path.normpath(os.path.join(SITO if src.startswith("/") else os.path.dirname(os.path.join(SITO, p)), src.lstrip("/")))
                    dim = dimensioni(f) if os.path.exists(f) else None
                    if dim and abs(dim[0] / dim[1] - int(n.attr["width"]) / int(n.attr["height"])) > 0.01:
                        E(p, f"{src}: proporzioni del file {dim[0]}×{dim[1]} diverse da width/height {n.attr['width']}×{n.attr['height']}")
                if n.attr.get("fetchpriority") != "high" and n.attr.get("loading") != "lazy" and not n.antenato(lambda x: x.tag in ("header", "picture") and "testata" in x.attr.get("class", "")) and "logo" not in n.attr.get("class", ""):
                    A_(p, f"immagine senza loading=lazy: {n.attr.get('src')}")
            if n.tag == "svg" and n.attr.get("aria-hidden") != "true" and not (n.attr.get("role") == "img" and (n.attr.get("aria-label") or any(f.tag == "title" for f in n.figli))):
                if not n.antenato(lambda x: x.tag == "svg") and "hidden" not in n.attr:
                    E(p, "svg senza aria-hidden né role=img con etichetta")
            if n.tag in ("s", "del", "strike"): E(p, "prezzo barrato o testo cancellato: non si usa")
            if n.tag in ("input", "select", "textarea") and n.attr.get("type") not in ("hidden", "submit"):
                i = n.attr.get("id")
                if not i or not any(m.tag == "label" and m.attr.get("for") == i for m in nodi): E(p, f"campo senza etichetta: {n.attr.get('name')}")
            if n.tag == "a" and not n.testo_interno().strip() and not n.attr.get("aria-label") and not any(m.tag == "img" and m.attr.get("alt") for m in n.tutti()):
                E(p, f"link senza testo: {n.attr.get('href')}")
        # 4. testi: parole vietate, punti esclamativi, emoji, marchi, prezzi
        segmenti = []                       # (testo, dentro un prezzo marcato, dentro una cifra di mercato)
        for n in r.tutti():
            if n.tag != "#testo": continue
            if n.antenato(lambda x: x.tag in ("script", "style", "code", "pre", "title") and x.tag != "title"): continue
            prezzo = n.antenato(lambda x: "data-prezzo" in x.attr) is not None
            mercato = n.antenato(lambda x: x.attr.get("data-fonte") == "mercato") is not None
            segmenti.append((n.testo, prezzo, mercato, n.riga))
        for n in nodi:
            for att in ("alt", "title", "aria-label", "placeholder"):
                if n.attr.get(att): segmenti.append((n.attr[att], False, False, n.riga))
            if n.tag == "meta" and n.attr.get("content") and (n.attr.get("name") in ("description",) or (n.attr.get("property") or "").startswith("og:") and not n.attr.get("property").endswith(("url", "image", "locale", "type"))):
                segmenti.append((n.attr["content"], False, False, n.riga))
        visibile = " ".join(s for s, *_ in segmenti)
        for rx, voce, grave in regole.get(lingua, []):
            for m in rx.finditer(visibile):
                (E if grave else A_)(p, f"parola {'vietata' if grave else 'da rileggere'} dallo stylebook: «{m.group(0)}» … {visibile[max(0, m.start() - 50):m.end() + 50].strip()!r}")
        for s, *_ in segmenti:
            if "!" in s: E(p, f"punto esclamativo: {s.strip()[:80]!r}")
            if re.search("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]", s): E(p, f"emoji: {s.strip()[:80]!r}")
        for nome in nomi:
            if re.search(r"(?<![\w-])" + re.escape(nome) + r"(?![\w-])", t, re.I): E(p, f"marchio di un concorrente: «{nome}»")
        rx_it = re.compile(r"(\d[\d.]*(?:,\d+)?)\s?€"); rx_en = re.compile(r"€\s?(\d[\d,]*(?:\.\d+)?)")
        for s, prezzo, mercato, riga in segmenti:
            if prezzo or mercato: continue
            for m in (rx_it if lingua == "it" else rx_en).finditer(s.replace(" ", " ")):
                E(p, f"riga {riga}: cifra in euro non legata a tier.json (usa data-prezzo, o data-fonte=\"mercato\" per i prezzi di terzi): {m.group(0)!r}")
        for n in nodi:
            if "data-prezzo" in n.attr:
                atteso = euro(prezzi.get(n.attr["data-prezzo"], -1), lingua)
                if n.testo_interno() != atteso: E(p, f"prezzo «{n.attr['data-prezzo']}» = {n.testo_interno()!r}, tier.json dice {atteso!r}")
            if n.tag == "meta" and n.attr.get("content"):
                for m in (rx_it if lingua == "it" else rx_en).finditer(n.attr["content"].replace(" ", " ")):
                    if m.group(0).replace(" ", " ") not in importi_ammessi and m.group(0) not in importi_ammessi: E(p, f"cifra nei metadati non in tier.json: {m.group(0)}")
        if pubblicazione:
            for m in re.finditer(r"\{\{[^}]+\}\}", visibile): E(p, f"segnaposto ancora da riempire: {m.group(0)}")
            mostrato = " ".join(n.testo for n in r.tutti() if n.tag == "#testo" and not n.nascosto() and not n.antenato(lambda x: x.tag in ("script", "style")))
            for m in re.finditer(r"SEGNAPOSTO|PLACEHOLDER", mostrato): E(p, f"testo segnaposto visibile: {mostrato[m.start():m.start() + 90]!r}")
        # 5. peso: HTML + CSS + JS + caratteri + immagini caricate subito (prima scelta del srcset per uno schermo largo 1280 a densità 1)
        cartella = os.path.dirname(os.path.join(SITO, p))
        risolvi = lambda v: os.path.normpath(os.path.join(SITO, v.lstrip("/")) if v.startswith("/") else os.path.join(cartella, v))
        subito, dopo, fogli = len(t.encode()), 0, []
        for n in nodi:
            if n.tag == "link" and n.attr.get("rel") == "stylesheet": fogli.append(risolvi(n.attr["href"]))
            if n.tag == "script" and n.attr.get("src"): subito += os.path.getsize(risolvi(n.attr["src"]))
            if n.tag == "img" and n.attr.get("src") and not n.nascosto() and not n.attr["src"].endswith(".svg"):
                scelta = n.attr["src"]
                if n.attr.get("srcset"):
                    cand = [(int(x.strip().split()[1][:-1]), x.strip().split()[0]) for x in n.attr["srcset"].split(",")]
                    scelta = min((c for c in cand if c[0] >= 1200), default=max(cand))[1]
                f = risolvi(scelta)
                if os.path.exists(f):
                    if n.attr.get("loading") == "lazy": dopo += os.path.getsize(f)
                    else: subito += os.path.getsize(f)
            if n.tag == "img" and n.attr.get("src", "").endswith(".svg"): subito += os.path.getsize(risolvi(n.attr["src"])) if os.path.exists(risolvi(n.attr["src"])) else 0
        usa_corsivo = "italic" in "".join(leggi(f) for f in fogli if os.path.exists(f) and not f.endswith("font.css"))
        for f in fogli:
            if not os.path.exists(f): E(p, f"foglio di stile mancante: {f}"); continue
            subito += os.path.getsize(f)
            for u, ris in risorse_css(f):
                if re.match(r"^(https?:)?//", u): E(p, f"richiesta esterna nel CSS: {u}"); continue
                if not os.path.exists(ris): E(p, f"risorsa del CSS mancante: {u}"); continue
                if ris.endswith(".woff2") and ("Italic" in ris and not usa_corsivo): continue
                subito += os.path.getsize(ris)
        pesi[p] = (subito, dopo)
        if subito > 1_000_000: A_(p, f"peso al primo caricamento {subito / 1024:.0f} KB (oltre 1 MB)")
        if subito + dopo > 2_500_000: A_(p, f"peso totale {(subito + dopo) / 1024:.0f} KB (oltre 2,5 MB)")
    # 6. CSS e JS: niente richieste esterne
    for cartella in ("css", "js"):
        for f in sorted(os.listdir(os.path.join(SITO, cartella))):
            t = leggi(os.path.join(SITO, cartella, f))
            if re.search(r"@import|https?://(?!www\.w3\.org/2000/svg)", t): E(f"{cartella}/{f}", "riferimento alla rete esterna")
            if "line-through" in t and cartella == "css": E(f"{cartella}/{f}", "testo barrato: niente prezzi barrati")
    # 7. pubblicazione
    if pubblicazione:
        testo_cfg_ = json.dumps(cfg)
        if ".example" in testo_cfg_: E("config.json", "dominio o indirizzi email ancora .example")
        if "{{" in testo_cfg_: E("config.json", "titolare, partita IVA o sede ancora da riempire")
        if sw.get("in_vendita"):
            for k in ("acquisto_essenziale", "acquisto_pro", "acquisto_studio", "download_mac", "download_windows", "download_linux", "impronte"):
                if not cfg["link"].get(k) and not k.startswith("acquisto"): E("config.json", f"in vendita ma manca link.{k}")
        if cfg.get("data_fine_lancio") and not lancio_attivo(cfg): E("config.json", "la data di fine lancio è passata: svuotala")
        for s in SCHERMATE:
            if s["stato"] == "segnaposto" and not os.path.exists(os.path.join(ORIGINALI, s["sorgente"])):
                usata = [p for p, r in alberi.items() if any(n.tag == "img" and f"img/schermate/{s['nome']}-" in (n.attr.get("src") or "") and not n.nascosto() for n in r.tutti() if n.tag != "#testo")]
                if usata: E("img", f"schermata segnaposto visibile in {', '.join(usata)}: {s['nome']}")
    for p, (s, d) in pesi.items(): print(f"  peso {p:<17} {s / 1024:6.0f} KB subito, {d / 1024:6.0f} KB in differita")
    for x in avvisi: print("  avviso:", x)
    for x in errori: print("  ERRORE:", x)
    print(f"controlli: {len(errori)} errori, {len(avvisi)} avvisi ({'pubblicazione' if pubblicazione else 'sviluppo'}; listino {tier['versione_listino']}, "
          f"lancio {'attivo fino al ' + cfg['data_fine_lancio'] if lancio_attivo(cfg) else 'spento'}, in vendita: {sw.get('in_vendita')}, MCP: {sw.get('mcp_disponibile')})")
    return 1 if errori else 0


# ------------------------------------------------------------------------------------------------ istantanee

def istantanee(a):
    import cromo
    try: from PIL import Image
    except ImportError: Image = None
    pagine = a.pagine.split(",") if a.pagine else [p for p in PAGINE if os.path.exists(os.path.join(SITO, p))]
    larghezze = [int(x) for x in a.larghezze.split(",")]
    temi = a.temi.split(",")
    grezze = os.path.join(ANTEPRIME, ".grezze"); os.makedirs(grezze, exist_ok=True)
    problemi = []
    with Servitore() as s, cromo.Chrome() as c:
        c.invia("Network.enable")
        for p in pagine:
            url = s.url + ("percorso/che/non/esiste" if p == "404.html" else p)
            for w in larghezze:
                for tema in temi:
                    nome = f"{p.replace('/', '-').replace('.html', '')}-{w}-{tema}"
                    c.eventi.clear()
                    densita = 2 if w < 1000 else 1
                    c.vista(w, 900, densita, mobile=w < 1000, tema="dark" if tema == "scuro" else "light")
                    c.apri(url)
                    rotte = c.carica_immagini()
                    largo = c.valuta("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                    if largo[0] > largo[1]:
                        colpevoli = c.valuta("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1).slice(0, 5).map(e => e.tagName + '.' + e.className)")
                        problemi.append(f"{nome}: scorrimento orizzontale ({largo[0]} > {largo[1]}): {colpevoli}")
                    for e in c.eventi:
                        if e["method"] == "Network.requestWillBeSent":
                            u = e["params"]["request"]["url"]
                            if not u.startswith((s.url, "data:")): problemi.append(f"{nome}: richiesta esterna {u}")
                        if e["method"] == "Runtime.exceptionThrown": problemi.append(f"{nome}: errore JavaScript {e['params']['exceptionDetails'].get('text')}")
                        if e["method"] == "Network.loadingFailed" and not e["params"].get("canceled"): problemi.append(f"{nome}: risorsa non caricata ({e['params'].get('errorText')})")
                    if rotte: problemi.append(f"{nome}: immagini non caricate {rotte}")
                    png = c.foto(os.path.join(grezze, nome + ".png"))
                    dest = os.path.join(ANTEPRIME, nome + (".jpg" if Image else ".png"))
                    if Image: comprimi(Image, png, dest, scala=1 / densita)
                    else: shutil.copyfile(png, dest)
                    print(f"  {nome:<34} {os.path.getsize(dest) / 1024:5.0f} KB")
    for x in problemi: print("  PROBLEMA:", x)
    print(f"istantanee: {len(problemi)} problemi")
    return 1 if problemi else 0


def comprimi(Image, png, dest, scala=1, limite=700_000):
    """JPEG progressivo sotto «limite» byte; le catture a densità 2 si riducono a densità 1 (il testo resta nitido)"""
    im = Image.open(png).convert("RGB")
    if scala != 1: im = im.resize((round(im.width * scala), round(im.height * scala)), Image.LANCZOS)
    for q in (78, 70, 62, 55):
        im.save(dest, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(dest) <= limite: return
    while os.path.getsize(dest) > limite:
        im = im.resize((round(im.width * .85), round(im.height * .85)), Image.LANCZOS)
        im.save(dest, "JPEG", quality=60, optimize=True, progressive=True)


# file e cartelle che vanno sul server; tutto il resto (strumenti, anteprime, originali, documenti) resta qui
PUBBLICATI = [*PAGINE, "sitemap.xml", "robots.txt", "favicon.ico", "favicon.svg", "css", "js", "font", "img/marca", "img/schermate", "img/og"]


def pubblica(a):
    """copia in una cartella pulita solo i file da pubblicare (dopo controlla --pubblicazione)"""
    dest = os.path.abspath(a.cartella)
    if os.path.commonpath([dest, SITO]) == SITO: raise SystemExit("la cartella di destinazione deve stare fuori da marketing/sito")
    if os.path.exists(dest) and os.listdir(dest): raise SystemExit(f"{dest} non è vuota")
    n = 0
    for voce in PUBBLICATI:
        da = os.path.join(SITO, voce)
        if not os.path.exists(da): print("  manca:", voce); continue
        if os.path.isdir(da):
            shutil.copytree(da, os.path.join(dest, voce), dirs_exist_ok=True); n += sum(len(f) for _, _, f in os.walk(da))
        else:
            os.makedirs(os.path.dirname(os.path.join(dest, voce)), exist_ok=True); shutil.copyfile(da, os.path.join(dest, voce)); n += 1
    print(f"pubblicabili: {n} file in {dest}")
    return 0


def tutto(a):
    marca(); immagini(); configura(); return controlla(a)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Strumenti del sito di vendita (vedi l'intestazione di questo file)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("marca", "immagini", "configura"): sub.add_parser(n)
    for n in ("controlla", "tutto"):
        s = sub.add_parser(n); s.add_argument("--pubblicazione", action="store_true", help="rifiuta segnaposto, dominio .example, lancio scaduto")
    s = sub.add_parser("pubblica"); s.add_argument("cartella", help="cartella vuota fuori dal repository")
    s = sub.add_parser("istantanee")
    s.add_argument("--pagine", default=""); s.add_argument("--larghezze", default="360,768,1280,1920"); s.add_argument("--temi", default="chiaro,scuro")
    a = ap.parse_args(argv)
    r = {"marca": marca, "immagini": immagini, "configura": configura, "controlla": controlla, "istantanee": istantanee, "pubblica": pubblica, "tutto": tutto}[a.cmd](a)
    return r if isinstance(r, int) else 0


if __name__ == "__main__":
    sys.exit(main())
