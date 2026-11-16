"""Chiavi di licenza «IMP1-» firmate Ed25519 e elenco firmato delle chiavi revocate: lettura e verifica, solo in locale.

Il formato è descritto in marketing/negozio/chiavi/FORMATO-CHIAVE.md; le chiavi le emette marketing/negozio/chiavi/chiavi.py
(sul computer del titolare, con la chiave privata che non sta mai nel repository). Qui c'è solo la verifica, con le chiavi
pubbliche compilate nel programma (CHIAVI_PUBBLICHE). Nessuna funzione di questo modulo usa la rete.

Testo:  IMP1- + base32 (RFC 4648, senza «=») di  payload || firma, a gruppi di 5 caratteri separati da «-».
Payload (byte):
    0      formato: 1 = licenza senza scadenza, 2 = licenza a scadenza (chiavi dei laboratori, «modello C»)
    1      id della chiave di firma (rotazione)
    2      fascia: 1 essenziale, 2 pro, 3 studio, 4 laboratorio
    3      versione maggiore
    4      computer (limite del contratto, non contato)
    5      flag: bit 0 omaggio, bit 1 beta; gli altri bit a zero
    6-9    seriale (uint32 big-endian)
    10-11  data di emissione: giorni dal 01/01/2026 (uint16 big-endian)
    12     n = lunghezza dell'intestatario (0-48)
    13…    intestatario (UTF-8)
    solo formato 2, dopo l'intestatario: 2 byte con l'ultimo giorno di validità (giorni dal 01/01/2026, compreso)
Firma: Ed25519 di DOMINIO_LICENZA + payload (64 byte in coda).
Un programma che conosce solo il formato 1 rifiuta le chiavi del formato 2: non le scambia mai per licenze perpetue.
"""
import base64
import binascii
import datetime as dt
import hashlib
import json
import re
from typing import NamedTuple

from .. import ed25519, lingua

PREFISSO = "IMP1-"
DOMINIO_LICENZA = b"IMPAGINATORE-LICENZA-v1\x00"
DOMINIO_REVOCHE = b"IMPAGINATORE-REVOCHE-v1\x00"
EPOCA = dt.date(2026, 1, 1)
FASCE = {1: "essenziale", 2: "pro", 3: "studio", 4: "laboratorio"}
FORMATI = (1, 2)
FLAG_OMAGGIO, FLAG_BETA = 1, 2
FLAG_NOTI = FLAG_OMAGGIO | FLAG_BETA
MAX_INTESTATARIO = 48
MAX_TESTO = 2048                     # una chiave vera è lunga circa 200 caratteri: oltre è un incolla sbagliato
LINK = "IMPAGINATORE://ATTIVA?CHIAVE="


class Pubblica(NamedTuple):
    """chiave pubblica di firma compilata nel programma. emesse_fino (data ISO o None): se la chiave privata viene rubata,
    l'aggiornamento successivo mette qui la data del furto e le licenze firmate con questa chiave ed emesse dopo quella
    data si rifiutano (FORMATO-CHIAVE.md, § 5)"""
    esadecimale: str
    emesse_fino: str = None


# ---------------------------------------------------------------------------------------------------------------------
# SEGNAPOSTO DA SOSTITUIRE AL RILASCIO. Al posto del testo va la chiave pubblica di produzione, 64 cifre esadecimali,
# come la stampa «python3 marketing/negozio/chiavi/chiavi.py genera-coppia». La chiave PRIVATA non entra mai nel
# repository. Con il segnaposto nessuna chiave è valida (copia di sviluppo: vale la prova gratuita). Un rilascio con il
# segnaposto non passa i test: tests/test_licenze.py::test_un_rilascio_non_parte_con_il_segnaposto (vedi LICENZE.md).
SEGNAPOSTO = "SEGNAPOSTO-CHIAVE-PUBBLICA-DI-PRODUZIONE-DA-SOSTITUIRE-AL-RILASCIO"
CHIAVI_PUBBLICHE = {1: Pubblica("280d61c82c7b8573d72e6c098a7fe9b32448c8685594bfe6eb1d00a9d6ca4fcb")}
# ---------------------------------------------------------------------------------------------------------------------


class ChiaveNonValida(ValueError):
    """la chiave non si può usare: il messaggio è per l'utente. Se nasce da una chiave della tabella (errore()), la tiene
    con i suoi parametri: chi mette il verdetto in una cache lo ricompone nella lingua del momento"""

    def __init__(self, testo, chiave=None, param=None):
        super().__init__(testo); self.chiave, self.param = chiave, param or {}


def errore(chiave, **param):
    """ChiaveNonValida con il testo della chiave nella lingua in uso"""
    return ChiaveNonValida(lingua.t(chiave, **param), chiave, param)


def problemi_per_il_rilascio(pubbliche=None):
    """elenco dei motivi per cui queste chiavi pubbliche non vanno in un rilascio (vuoto = pronte)"""
    pubbliche = CHIAVI_PUBBLICHE if pubbliche is None else pubbliche
    if not pubbliche: return ["nessuna chiave pubblica di firma"]          # non tradotto: lo legge chi prepara il rilascio, non l'utente
    out = []
    for i, p in sorted(pubbliche.items()):
        if _bytes_pubblica(p) is None: out.append(f"la chiave pubblica {i} è un segnaposto o non è valida: {p.esadecimale[:24]}…")          # non tradotto: lo legge chi prepara il rilascio
    return out


def _bytes_pubblica(p):
    """32 byte della chiave pubblica, o None se è il segnaposto o non è esadecimale di 32 byte"""
    try: b = bytes.fromhex(p.esadecimale)
    except ValueError: return None
    return b if len(b) == 32 else None


def da_testo(testo):
    """byte della chiave (payload e firma) dal testo incollato: maiuscole o minuscole, spazi, a capo e trattini non contano;
    vale anche il link impaginatore://attiva?chiave=…"""
    if not isinstance(testo, str) or not testo.strip(): raise errore("licenze.chiave_vuota")
    if len(testo) > MAX_TESTO: raise errore("licenze.chiave_troppo_lunga")
    t = re.sub(r"[\s\-]", "", testo.strip().upper())
    if t.startswith(LINK): t = t[len(LINK):]
    if not t.startswith(PREFISSO[:-1]): raise errore("licenze.chiave_non_di_impaginatore")
    corpo = t[len(PREFISSO) - 1:]
    if not re.fullmatch(r"[A-Z2-7]+", corpo): raise errore("licenze.chiave_caratteri")
    try: return base64.b32decode(corpo + "=" * (-len(corpo) % 8))
    except binascii.Error: raise errore("licenze.chiave_incompleta") from None


def in_testo(dati):
    """testo IMP1-… (gruppi di 5) dei byte della chiave"""
    b32 = base64.b32encode(dati).decode("ascii").rstrip("=")
    return PREFISSO + "-".join(b32[i:i + 5] for i in range(0, len(b32), 5))


def _data(giorni):
    return (EPOCA + dt.timedelta(days=giorni)).isoformat()


def decodifica(testo, pubbliche=None):
    """contenuto della chiave dopo la verifica della firma con le chiavi pubbliche del programma; ChiaveNonValida altrimenti.
    Non guarda revoche, versione e scadenza: sono stati della licenza, non difetti della chiave (licenze.stato)"""
    pubbliche = CHIAVI_PUBBLICHE if pubbliche is None else pubbliche
    dati = da_testo(testo)
    if len(dati) < 13 + 64: raise errore("licenze.chiave_incompleta")
    payload, firma = dati[:-64], dati[-64:]
    if payload[0] not in FORMATI: raise errore("licenze.chiave_tipo_recente")
    n = payload[12]
    coda = 2 if payload[0] == 2 else 0
    if n > MAX_INTESTATARIO or len(payload) != 13 + n + coda: raise errore("licenze.chiave_incompleta")
    p = pubbliche.get(payload[1])
    if p is None: raise errore("licenze.chiave_firma_sconosciuta", numero=payload[1])
    pub = _bytes_pubblica(p)
    if pub is None: raise errore("licenze.chiave_versione_di_sviluppo")
    if not ed25519.verifica(pub, DOMINIO_LICENZA + payload, firma):
        raise errore("licenze.chiave_firma_non_corrisponde")
    if payload[2] not in FASCE or payload[5] & ~FLAG_NOTI: raise errore("licenze.chiave_licenza_sconosciuta")
    emessa = _data(int.from_bytes(payload[10:12], "big"))
    if p.emesse_fino and emessa > p.emesse_fino:
        raise errore("licenze.chiave_firma_ritirata")
    try: intestatario = payload[13:13 + n].decode("utf-8")
    except UnicodeDecodeError: raise errore("licenze.chiave_incompleta") from None   # firmata così: solo un errore di chi l'ha emessa
    return {
        "formato": payload[0],
        "id_firma": payload[1],
        "fascia": FASCE[payload[2]],
        "versione_maggiore": payload[3],
        "computer": payload[4],
        "omaggio": bool(payload[5] & FLAG_OMAGGIO),
        "beta": bool(payload[5] & FLAG_BETA),
        "seriale": int.from_bytes(payload[6:10], "big"),
        "emessa": emessa,
        "intestatario": intestatario,
        "scade": _data(int.from_bytes(payload[13 + n:], "big")) if coda else None,
        "impronta": hashlib.sha256(dati).hexdigest()[:16],
        "testo": in_testo(dati),
    }


def canonico(corpo):
    """byte firmati di un elenco di revoche: il JSON canonico (chiavi ordinate, senza spazi) senza il campo «firma»"""
    return json.dumps({k: v for k, v in corpo.items() if k != "firma"}, sort_keys=True, separators=(",", ":")).encode("utf-8")


def revoche(corpo, pubbliche=None):
    """(seriali revocati, data dell'elenco) di un elenco firmato da chiavi.py; ValueError se il formato o la firma non vanno.
    Forma: {"formato": 1, "id_firma": n, "emessa": "…", "seriali": [interi], "firma": "<128 cifre esadecimali>"}"""
    pubbliche = CHIAVI_PUBBLICHE if pubbliche is None else pubbliche
    if not isinstance(corpo, dict) or corpo.get("formato") != 1: raise ValueError("elenco delle revoche di un formato sconosciuto")          # non tradotto: va solo nel registro (licenze.revocate)
    seriali, emessa, firma = corpo.get("seriali"), corpo.get("emessa"), corpo.get("firma")
    if not isinstance(seriali, list) or not all(isinstance(s, int) and not isinstance(s, bool) for s in seriali) or not isinstance(emessa, str) or not isinstance(firma, str):
        raise ValueError("elenco delle revoche incompleto")          # non tradotto: va solo nel registro (licenze.revocate)
    idf = corpo.get("id_firma")
    p = pubbliche.get(idf) if isinstance(idf, int) else None
    pub = _bytes_pubblica(p) if p is not None else None
    try: f = bytes.fromhex(firma)
    except ValueError: f = b""
    if pub is None or not ed25519.verifica(pub, DOMINIO_REVOCHE + canonico(corpo), f): raise ValueError("firma dell'elenco delle revoche non valida")          # non tradotto: va solo nel registro (licenze.revocate)
    return set(seriali), emessa
