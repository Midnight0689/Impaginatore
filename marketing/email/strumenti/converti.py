"""Converte i modelli con segnaposto neutri ({{nome}}) nella sintassi di ciascun servizio di invio.

Sintassi neutra usata nei sorgenti (html/*.html, testo/*.txt):
    {{nome}}                                  variabile
    {{#if nome}} … {{else}} … {{/if}}          blocco condizionale (il ramo {{else}} è facoltativo)

Uso, dalla cartella marketing/email/:
    python3 strumenti/converti.py                     # tutte le varianti in html/<servizio>/ e testo/<servizio>/
    python3 strumenti/converti.py --dati invio.json   # riempie prima i dati di un invio (es. data_fine_lancio)
    python3 strumenti/converti.py --rendi dati.json --modelli rimborso-conferma --uscita /percorso
                                                      # HTML e testo finali, senza segnaposto: per l'invio a mano
                                                      # o via API; si ferma se manca un valore (costanti comprese)
    python3 strumenti/converti.py --tabella           # stampa la tabella di SEGNAPOSTO.md

Le costanti (sito, indirizzi, link fissi) si leggono da strumenti/costanti.json: se un valore è vuoto,
il segnaposto resta una variabile del servizio e lo script lo segnala.
Solo libreria standard di Python 3.9+.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

CARTELLA = Path(__file__).resolve().parents[1]
SERVIZI = ("sendgrid", "mailchimp", "brevo", "resend")

# Tipo di ciascun modello: «servizio» = transazionale (API), «campagna» = lista o sequenza automatica,
# «persona» = email da persona a persona (laboratori), da mandare a mano dalla propria casella.
MODELLI = {
    "lancio": "campagna", "lancio.en": "campagna",
    "benvenuto-chiave": "servizio", "benvenuto-chiave.en": "servizio",
    "prova-giorno-1": "campagna", "prova-giorno-7": "campagna", "prova-scadenza": "campagna",
    "rosetta": "campagna",
    "laboratori-primo-contatto": "persona", "laboratori-seguito": "persona",
    "aggiornamento": "campagna", "aggiornamento.en": "campagna",
    "rimborso-conferma": "servizio", "attivazione-problema": "servizio", "assistenza-ore": "servizio",
}

# Tabella dei segnaposto: ambito, descrizione, esempio, e nomi per servizio.
#   ambito: costante (uguale per tutti, da costanti.json) · interruttore (costante sì/no, sempre risolta)
#           destinatario (cambia per persona)
#           invio (uguale per tutti i destinatari di un invio: va riempito con --dati per le campagne)
#           speciale (link gestiti dal servizio: disiscrizione, preferenze)
#   mc: nome del merge tag Mailchimp (al massimo 10 caratteri, maiuscolo).
#   url: True se il valore è un indirizzo o un comando da non trasformare in entità HTML.
S = {}


def _s(nome, ambito, descrizione, esempio, mc=None, url=False, sg_campagna=None, brevo_contatto=None, resend_contatto=None, en=None):
    S[nome] = dict(ambito=ambito, descrizione=descrizione, esempio=esempio, mc=mc or nome.upper()[:10], url=url,
                   sg_campagna=sg_campagna, brevo_contatto=brevo_contatto, resend_contatto=resend_contatto,
                   esempio_en=en if en is not None else esempio)


# Costanti (uguali per tutti: si scrivono una volta in strumenti/costanti.json)
_s("base_immagini", "costante", "URL della cartella pubblica con immagini e font, senza barra finale", "https://impaginatore.example/email/v1", mc="BASE_IMG", url=True)
_s("sito", "costante", "URL del sito", "https://impaginatore.example", url=True)
_s("sito_testo", "costante", "Dominio da mostrare nel testo", "impaginatore.example", mc="SITO_TXT")
_s("email_supporto", "costante", "Indirizzo di assistenza (riceve anche le risposte)", "aiuto@impaginatore.example", mc="EMAIL_SUP")
_s("titolare", "costante", "Ragione sociale o nome del titolare", "Nome Cognome", mc="TITOLARE")
_s("indirizzo", "costante", "Indirizzo postale della sede", "Via Esempio 1, 00100 Roma", mc="INDIRIZZO")
_s("partita_iva", "costante", "Partita IVA", "IT00000000000", mc="PIVA")
_s("link_privacy", "costante", "Informativa privacy", "https://impaginatore.example/privacy", mc="L_PRIVACY", url=True)
_s("link_prezzi", "costante", "Pagina prezzi", "https://impaginatore.example/prezzi", mc="L_PREZZI", url=True)
_s("link_prova", "costante", "Pagina della prova gratuita (come si ottiene e come si inizia)", "https://impaginatore.example/prova", mc="L_PROVA", url=True)
_s("link_acquisto_essenziale", "costante", "Richiesta d'acquisto Essenziale (modulo o email precompilata)", "https://impaginatore.example/acquista?fascia=essenziale", mc="L_ESS", url=True)
_s("link_acquisto_pro", "costante", "Richiesta d'acquisto Pro", "https://impaginatore.example/acquista?fascia=pro", mc="L_PRO", url=True)
_s("link_acquisto_studio", "costante", "Richiesta d'acquisto Studio", "https://impaginatore.example/acquista?fascia=studio", mc="L_STUDIO", url=True)
_s("link_installa", "costante", "Pagina «Installa»: come si installa e come si aggiorna il programma, solo quello che esiste", "https://impaginatore.example/installa", mc="L_INSTALLA", url=True)
_s("link_guida_claude", "costante", "Guida al collegamento con un assistente AI (server MCP, per esempio Claude Desktop)", "https://impaginatore.example/guida/claude", mc="L_GUIDA_CL", url=True)
_s("link_manuale", "costante", "Manuale d'uso", "https://impaginatore.example/manuale", mc="L_MANUALE", url=True)
_s("link_assistenza", "costante", "Pagina dell'assistenza a ore: pacchetti, prezzi, come si prenota", "https://impaginatore.example/assistenza", mc="L_ASSIST", url=True)
_s("firma_nome", "costante", "Nome di chi firma", "Nome Cognome", mc="FIRMA")
_s("firma_ruolo", "costante", "Ruolo di chi firma", "fotografo, autore di Impaginatore", mc="FIRMA_RUOL", en="photographer, author of Impaginatore")
_s("firma_telefono", "costante", "Telefono di chi firma (email ai laboratori)", "+39 000 000 0000", mc="FIRMA_TEL")
# Interruttori: si decidono in costanti.json e si risolvono sempre in conversione (vuoto = spento).
_s("mcp_disponibile", "interruttore", "«1» quando il server MCP per Claude è rilasciato; vuoto finché non lo è: i blocchi sulla bozza con Claude spariscono", "1", mc="MCP")
# Destinatario
_s("nome", "destinatario", "Nome di battesimo; se manca, il saluto resta senza nome", "Giulia", mc="FNAME", sg_campagna="first_name", brevo_contatto="FIRSTNAME", resend_contatto="contact.first_name")
_s("email", "destinatario", "Indirizzo del destinatario", "giulia@studio.example", mc="EMAIL", sg_campagna="email", brevo_contatto="EMAIL", resend_contatto="contact.email")
_s("chiave_licenza", "destinatario", "Chiave di licenza (IMP1-…, circa 200 caratteri a gruppi di 5)", "IMP1-AEDQE-AQCAA-AAAAB-UJZDE-GXDNC-F32EP-F3DHO-DZDOC-IS2JH-TLGMX-GEDN7-3U55X-TPLPF-T7V4S-EH2KV-J72CE-UVW75-EFR6E-DT4SY-WB5WK-H7DNS-IPZZ7-FK4ZR-I3R2W-YOJFL-JOOA7-LQSAJ-2XUID-5ZZZZ-G6ZDM-EN4KH-VDGAJ-GX", mc="LICENZA")
_s("intestatario", "destinatario", "Intestatario della licenza, mostrato nell'app", "Studio Fotografico Rossi", mc="INTESTATAR")
_s("fascia", "destinatario", "Fascia acquistata: Essenziale, Pro o Studio (nei modelli inglesi: Essential, Pro o Studio)", "Pro", mc="FASCIA")
_s("computer", "destinatario", "Computer della fascia: 1, 2 o 5", "2", mc="COMPUTER")
_s("numero_richiesta", "destinatario", "Numero della richiesta d'acquisto (causale del bonifico)", "IMP-0042", mc="RICHIESTA")
_s("ore_incluse", "destinatario", "«1» se la licenza include un'ora di assistenza (Studio), vuoto altrimenti", "", mc="ORE_INCL")
_s("data_scadenza_prova", "destinatario", "Ultimo giorno della prova", "15 dicembre 2026", mc="SCAD_PROVA")
_s("importo_rimborso", "destinatario", "Importo rimborsato, come pagato (IVA compresa se dovuta)", "96,38 €", mc="RIMB_IMP")
_s("data_rimborso", "destinatario", "Data in cui è partito il bonifico di rimborso", "18 novembre 2026", mc="RIMB_DATA")
_s("se_chiave_non_valida", "destinatario", "«1» se l'app dice che la chiave non è valida (copiata a metà)", "1", mc="P_CHIAVE")
_s("se_dove_inserire", "destinatario", "«1» se il cliente non trova dove inserire la chiave nel programma", "", mc="P_DOVE")
_s("se_installazione", "destinatario", "«1» se il problema è l'installazione", "1", mc="P_INSTALL")
_s("se_altri_computer", "destinatario", "«1» se serve la licenza su più computer di quelli della fascia", "", mc="P_COMPUT")
_s("ore_acquistate", "destinatario", "Ore comprate con questo pagamento", "5", mc="ORE_ACQ")
_s("scadenza_ore", "destinatario", "Data entro cui usare le ore (12 mesi)", "18 novembre 2027", mc="ORE_SCAD")
# Invio (uguale per tutti i destinatari di un invio: per le campagne si riempie con --dati)
_s("data_fine_lancio", "invio", "Ultimo giorno del prezzo di lancio; vuoto dopo il lancio (le email mostrano il listino)", "23 aprile 2027", mc="FINE_LANC", en="23 April 2027")
_s("accesso_anticipato", "invio", "«1» per l'invio di accesso anticipato alla lista d'attesa (48 ore prima di tutti)", "", mc="ANTICIPO")
_s("data_apertura", "invio", "Giorno in cui l'acquisto si apre a tutti", "23 febbraio 2027", mc="APERTURA", en="23 February 2027")
_s("prezzo_rosetta_pro", "invio", "Prezzo netto dell'offerta Rosetta per Pro", "49 €", mc="ROS_PRO")
_s("prezzo_rosetta_studio", "invio", "Prezzo netto dell'offerta Rosetta per Studio", "99 €", mc="ROS_STUDIO")
_s("data_fine_rosetta", "invio", "Ultimo giorno dell'offerta Rosetta", "31 dicembre 2027", mc="FINE_ROS")
_s("link_rosetta", "invio", "Pagina dell'offerta Rosetta (come richiederla, FAQ di fatti)", "https://impaginatore.example/macos-28", mc="L_ROSETTA", url=True)
_s("versione", "invio", "Numero di versione", "2.1", mc="VERSIONE")
_s("data_versione", "invio", "Data di pubblicazione della versione", "2 marzo 2027", mc="DATA_VERS", en="2 March 2027")
_s("novita_1_titolo", "invio", "Novità 1: titolo breve", "Copertine con dorso calcolato", mc="NOV1_TIT", en="Covers with a calculated spine")
_s("novita_1_testo", "invio", "Novità 1: due righe, con una misura vera", "Scegli carta e numero di pagine: il dorso si calcola da solo, al decimo di millimetro.", mc="NOV1_TXT", en="Choose paper and page count: the spine width is worked out for you, to a tenth of a millimetre.")
_s("novita_2_titolo", "invio", "Novità 2: titolo", "Etichette di Lightroom", mc="NOV2_TIT", en="Lightroom labels")
_s("novita_2_testo", "invio", "Novità 2: testo", "Le foto con l’etichetta verde entrano già nella bozza; le altre restano a portata di mano.", mc="NOV2_TXT", en="Photos with the green label go straight into the draft; the others stay within reach.")
_s("novita_3_titolo", "invio", "Novità 3: titolo", "Esportazione più rapida", mc="NOV3_TIT", en="Faster export")
_s("novita_3_testo", "invio", "Novità 3: testo", "Gli spread JPG di un album da 30 pagine escono in metà del tempo di prima sullo stesso computer.", mc="NOV3_TXT", en="JPG spreads of a 30-page album export in half the previous time on the same computer.")
_s("correzioni", "invio", "Correzioni principali, una riga", "Corretta l’abbondanza dei PDF con piega di 3,0 mm su Windows.", mc="CORREZIONI", en="Fixed the bleed of PDFs with a 3.0 mm gutter on Windows.")
_s("link_note_versione", "invio", "Note di versione complete", "https://impaginatore.example/novita/2-1", mc="L_NOTE", url=True)
_s("nome_laboratorio", "invio", "Nome del laboratorio", "Laboratorio Esempio", mc="LAB")
_s("se_accordo_telefonico", "invio", "«1» se l'email segue una telefonata in cui il laboratorio ha accettato di riceverla", "1", mc="TELEFONO")
_s("formato_esempio", "invio", "Un formato vero del loro catalogo", "30 × 30 cm", mc="FORMATO")
_s("prodotto_esempio", "invio", "Una linea o copertina vera del loro catalogo", "la linea in lino", mc="PRODOTTO")
_s("link_video", "invio", "Video dimostrativo di 90 secondi", "https://impaginatore.example/video/laboratori", mc="L_VIDEO", url=True)
_s("link_album_dimostrativo", "invio", "Cartella con l'album dimostrativo esportato secondo le loro specifiche", "https://impaginatore.example/demo/laboratorio-esempio", mc="L_DEMO", url=True)
# Speciali (gestiti dal servizio)
_s("link_disiscrizione", "speciale", "Disiscrizione con un clic", "https://impaginatore.example/disiscrizione", url=True)
_s("link_preferenze", "speciale", "Preferenze di iscrizione", "https://impaginatore.example/preferenze", url=True)

SPECIALI = {
    "sendgrid": {"link_disiscrizione": "{{{unsubscribe}}}", "link_preferenze": "{{{unsubscribe_preferences}}}"},
    "mailchimp": {"link_disiscrizione": "*|UNSUB|*", "link_preferenze": "*|UPDATE_PROFILE|*"},
    "brevo": {"link_disiscrizione": "{{ unsubscribe }}", "link_preferenze": "{{ update_profile }}"},
    # Resend non ha una pagina preferenze separata documentata: entrambi portano alla disiscrizione.
    "resend": {"link_disiscrizione": "{{{RESEND_UNSUBSCRIBE_URL}}}", "link_preferenze": "{{{RESEND_UNSUBSCRIBE_URL}}}"},
}

VAR = re.compile(r"\{\{\s*(?!else\b)([a-z0-9_]+)\s*\}\}")
SE = re.compile(r"\{\{#if ([a-z0-9_]+)\}\}(.*?)(?:\{\{else\}\}(.*?))?\{\{/if\}\}", re.S)
RESIDUO = re.compile(r"\{\{[^}]*\}\}")


def nome_servizio(chiave: str, servizio: str, tipo: str) -> str:
    """Espressione che restituisce il valore della variabile nel servizio (senza graffe di stampa)."""
    v = S[chiave]
    if servizio == "sendgrid":
        return v["sg_campagna"] if tipo == "campagna" and v["sg_campagna"] else chiave
    if servizio == "mailchimp":
        return v["mc"]
    if servizio == "brevo":
        if tipo == "campagna":
            return f"contact.{v['brevo_contatto'] or chiave.upper()}"
        return f"params.{chiave}"
    if servizio == "resend":
        if tipo == "campagna":
            return v["resend_contatto"] or f"contact.{chiave}"
        return chiave.upper()
    raise ValueError(servizio)


def da_riempire(chiave: str, tipo: str) -> bool:
    """In una campagna costanti e dati d'invio non sono attributi del contatto: vanno riempiti prima
    (costanti.json, --dati). Se mancano, al loro posto resta un segno [[nome]] ben visibile."""
    return tipo == "campagna" and S[chiave]["ambito"] in ("costante", "invio")


def stampa(chiave: str, servizio: str, tipo: str, testo_semplice: bool) -> str:
    if chiave in SPECIALI[servizio]:
        return SPECIALI[servizio][chiave]
    if da_riempire(chiave, tipo):
        return f"[[{chiave}]]"
    n = nome_servizio(chiave, servizio, tipo)
    if servizio == "sendgrid":
        # Le tre graffe evitano le entità HTML negli indirizzi, nei comandi e nella versione solo testo.
        return f"{{{{{{{n}}}}}}}" if (S[chiave]["url"] or testo_semplice) else f"{{{{{n}}}}}"
    if servizio == "mailchimp":
        return f"*|{n}|*"
    if servizio == "brevo":
        return f"{{{{ {n} }}}}"
    return f"{{{{{{{n}}}}}}}"  # resend


def condizione(chiave: str, si: str, no: str | None, servizio: str, tipo: str, avvisi: list[str]) -> str:
    if da_riempire(chiave, tipo):
        return f"[[se {chiave}]]{si}" + (f"[[altrimenti]]{no}" if no is not None else "") + "[[fine]]"
    n = nome_servizio(chiave, servizio, tipo)
    if servizio == "sendgrid":
        return f"{{{{#if {n}}}}}{si}" + (f"{{{{else}}}}{no}" if no is not None else "") + "{{/if}}"
    if servizio == "mailchimp":
        return f"*|IF:{n}|*{si}" + (f"*|ELSE:|*{no}" if no is not None else "") + "*|END:IF|*"
    if servizio == "brevo":
        return f"{{% if {n} %}}{si}" + (f"{{% else %}}{no}" if no is not None else "") + "{% endif %}"
    # Resend: i modelli non documentano condizioni. Si tiene il ramo «altrimenti» (o niente) e si avvisa.
    avvisi.append(f"resend: blocco condizionale su «{chiave}» ridotto al ramo senza dato; per averlo completo usa --rendi")
    return no or ""


def riempi(testo: str, valori: dict[str, str], html_: bool) -> str:
    """Sostituisce i segnaposto per cui c'è un valore; risolve i condizionali che dipendono da quei valori."""
    def se(m):
        k, si, no = m.group(1), m.group(2), m.group(3)
        if k not in valori:
            return m.group(0)
        return si if str(valori[k]).strip() else (no or "")
    testo = SE.sub(se, testo)

    def var(m):
        k = m.group(1)
        if k not in valori:
            return m.group(0)
        v = str(valori[k])
        return html.escape(v, quote=True) if html_ else v
    return VAR.sub(var, testo)


def converti(testo: str, servizio: str, tipo: str, html_: bool, avvisi: list[str]) -> str:
    testo = SE.sub(lambda m: condizione(m.group(1), m.group(2), m.group(3), servizio, tipo, avvisi), testo)
    return VAR.sub(lambda m: stampa(m.group(1), servizio, tipo, not html_), testo)


def controlla(testo: str, origine: str) -> list[str]:
    errori = []
    for m in VAR.finditer(testo):
        if m.group(1) not in S:
            errori.append(f"{origine}: segnaposto sconosciuto «{m.group(1)}»")
    for m in SE.finditer(testo):
        if m.group(1) not in S:
            errori.append(f"{origine}: condizione su segnaposto sconosciuto «{m.group(1)}»")
    return errori


def sorgenti():
    for nome in MODELLI:
        h, t = CARTELLA / "html" / f"{nome}.html", CARTELLA / "testo" / f"{nome}.txt"
        if h.exists():
            yield nome, h, t


def per_lingua(valori: dict, nome_modello: str) -> dict:
    """Per i modelli inglesi (*.en) le chiavi «nome.en» sostituiscono «nome»; poi le «.en» si tolgono."""
    en = nome_modello.endswith(".en")
    base = {k: v for k, v in valori.items() if not k.endswith(".en")}
    if en:
        base.update({k[:-3]: v for k, v in valori.items() if k.endswith(".en")})
    return base


def esempi(nome_modello: str) -> dict[str, str]:
    chiave = "esempio_en" if nome_modello.endswith(".en") else "esempio"
    return {k: v[chiave] for k, v in S.items()}


def carica_json(percorso: Path) -> dict:
    dati = json.loads(percorso.read_text(encoding="utf-8"))
    return {k: v for k, v in dati.items() if not k.startswith("_")}


def tabella() -> str:
    righe = [
        "| Segnaposto | Ambito | Cosa contiene | SendGrid | Mailchimp | Brevo | Resend |",
        "|---|---|---|---|---|---|---|",
    ]
    for k, v in S.items():
        def cella(servizio):
            if k in SPECIALI[servizio]:
                return f"`{SPECIALI[servizio][k]}`"
            if v["ambito"] == "interruttore":
                return "risolto da converti.py"
            if v["ambito"] in ("costante", "invio"):
                if servizio == "mailchimp":
                    return "riempito da converti.py"
                return f"`{stampa(k, servizio, 'servizio', False)}` · campagne: riempito da converti.py"
            if servizio == "brevo":
                serv, camp = stampa(k, "brevo", "servizio", False), stampa(k, "brevo", "campagna", False)
                return f"`{serv}`" if serv == camp else f"`{serv}` · campagne `{camp}`"
            if servizio == "resend":
                tpl, bc = stampa(k, "resend", "servizio", False), stampa(k, "resend", "campagna", False)
                return f"`{tpl}` · broadcast `{bc}`"
            if servizio == "sendgrid":
                a, b = stampa(k, "sendgrid", "servizio", False), stampa(k, "sendgrid", "campagna", False)
                return f"`{a}`" if a == b else f"`{a}` · campagne `{b}`"
            return f"`{stampa(k, servizio, 'servizio', False)}`"
        descr = v["descrizione"].replace("|", "\\|")
        righe.append(f"| `{{{{{k}}}}}` | {v['ambito']} | {descr} | {cella('sendgrid')} | {cella('mailchimp')} | {cella('brevo')} | {cella('resend')} |")
    return "\n".join(righe)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dati", type=Path, help="JSON con i dati di un invio (ambito «invio»), riempiti prima della conversione")
    p.add_argument("--rendi", type=Path, help="JSON con tutti i valori: produce HTML e testo finali, senza segnaposto")
    p.add_argument("--uscita", type=Path, help="cartella di uscita per --rendi")
    p.add_argument("--servizi", default=",".join(SERVIZI))
    p.add_argument("--modelli", help="solo questi modelli, separati da virgola (es. laboratori-primo-contatto)")
    p.add_argument("--tabella", action="store_true")
    p.add_argument("--costanti", type=Path, default=CARTELLA / "strumenti" / "costanti.json")
    a = p.parse_args()

    if a.tabella:
        print(tabella())
        return 0

    scelti = set(a.modelli.split(",")) if a.modelli else set()
    costanti_file = a.costanti
    grezze = carica_json(costanti_file) if costanti_file.exists() else {}
    costanti = {k: v for k, v in grezze.items() if str(v).strip()}  # le chiavi «x.en» valgono per i modelli inglesi
    # Gli interruttori valgono sempre: vuoti o assenti significano «spento».
    costanti.update({k: str(grezze.get(k, "")).strip() for k, v in S.items() if v["ambito"] == "interruttore"})
    dati = carica_json(a.dati) if a.dati else {}
    errori, avvisi = [], []

    for nome, h, t in sorgenti():
        testi = {"html": h.read_text(encoding="utf-8"), "txt": t.read_text(encoding="utf-8") if t.exists() else None}
        for formato, contenuto in testi.items():
            if contenuto is not None:
                errori += controlla(contenuto, f"{nome}.{formato}")
    if errori:
        print("\n".join(errori), file=sys.stderr)
        return 1

    if a.rendi:
        # Nessun valore d'esempio: ciò che manca (costanti comprese) blocca la resa, per non spedire dati finti.
        rendi = carica_json(a.rendi)
        uscita = a.uscita or (CARTELLA / "rese")
        uscita.mkdir(parents=True, exist_ok=True)
        for nome, h, t in sorgenti():
            if scelti and nome not in scelti:
                continue
            valori = per_lingua({**costanti, **dati, **rendi}, nome)
            for formato, sorgente in (("html", h), ("txt", t)):
                if not sorgente.exists():
                    continue
                reso = riempi(sorgente.read_text(encoding="utf-8"), valori, formato == "html")
                mancano = sorted(set(RESIDUO.findall(reso)))
                if mancano:
                    errori.append(f"{nome}.{formato}: valori mancanti {mancano[:8]}")
                    continue
                (uscita / f"{nome}.{formato}").write_text(reso, encoding="utf-8")
        if errori:
            print("\n".join(errori), file=sys.stderr)
            return 1
        print(f"rese in {uscita}")
        return 0

    mancanti_costanti = sorted(k for k, v in S.items() if v["ambito"] == "costante" and k not in costanti)
    if mancanti_costanti:
        avvisi.append(f"costanti senza valore in {costanti_file.name} (email di servizio: parametri dell'API; campagne: segni [[nome]]): " + ", ".join(mancanti_costanti))
    for servizio in a.servizi.split(","):
        for nome, h, t in sorgenti():
            if scelti and nome not in scelti:
                continue
            tipo = MODELLI[nome]
            if tipo == "persona":
                continue  # le email ai laboratori partono a mano dalla propria casella: si usa --rendi
            for formato, sorgente, cartella in (("html", h, "html"), ("txt", t, "testo")):
                if not sorgente.exists():
                    continue
                testo = riempi(sorgente.read_text(encoding="utf-8"), per_lingua({**costanti, **dati}, nome), formato == "html")
                if tipo == "campagna":
                    restano = sorted({m.group(1) for m in VAR.finditer(testo) if da_riempire(m.group(1), tipo)}
                                     | {m.group(1) for m in SE.finditer(testo) if da_riempire(m.group(1), tipo)})
                    if restano and formato == "html":
                        avvisi.append(f"{servizio}/{nome}: NON PRONTA, restano [[{'|'.join(restano)}]]: riempi costanti.json e passa --dati")
                avvisi_locali: list[str] = []
                testo = converti(testo, servizio, tipo, formato == "html", avvisi_locali)
                if formato == "html":
                    avvisi += [f"{x} ({nome})" for x in sorted(set(avvisi_locali))]
                residui = [r for r in RESIDUO.findall(testo) if not _valido(r, servizio)]
                if residui:
                    errori.append(f"{servizio}/{nome}.{formato}: segnaposto non convertiti {residui[:5]}")
                destinazione = CARTELLA / cartella / servizio / f"{nome}.{formato}"
                destinazione.parent.mkdir(parents=True, exist_ok=True)
                destinazione.write_text(testo, encoding="utf-8")
        print(f"{servizio}: varianti scritte in html/{servizio}/ e testo/{servizio}/")
    for x in dict.fromkeys(avvisi):
        print("avviso:", x, file=sys.stderr)
    if errori:
        print("\n".join(errori), file=sys.stderr)
        return 1
    return 0


def _valido(segno: str, servizio: str) -> bool:
    """Le graffe rimaste devono essere sintassi del servizio, non segnaposto neutri dimenticati."""
    if servizio in ("sendgrid", "resend"):
        return True  # Handlebars e Resend usano le graffe: il controllo è fatto prima, da controlla()
    if servizio == "brevo":
        return segno.startswith("{{ ") and segno.endswith(" }}")
    return False  # Mailchimp non usa graffe


if __name__ == "__main__":
    sys.exit(main())
