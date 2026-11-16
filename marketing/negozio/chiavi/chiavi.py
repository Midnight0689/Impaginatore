#!/usr/bin/env python3
"""Emette e verifica le chiavi di licenza di Impaginatore, firmate Ed25519, senza piattaforme esterne.

È il percorso predefinito finché il titolare non apre un conto presso un Merchant of Record
(vedi ../GUIDA-APERTURA.md). Usa solo la libreria standard di Python (3.9 o successivo):
Ed25519 è implementato qui secondo il codice di riferimento della RFC 8032, sezione 6.
Il formato della chiave e le regole per l'app sono in FORMATO-CHIAVE.md (stessa cartella).

La chiave privata e il registro delle vendite NON stanno nel repository: vivono nella
cartella indicata da --dir, oppure dalla variabile IMPAGINATORE_NEGOZIO_DIR, oppure in
~/.impaginatore-negozio. La chiave privata va salvata anche offline (chiavetta cifrata o carta).

Comandi:
  genera-coppia   crea la coppia di chiavi di firma (una volta sola) e stampa la chiave pubblica
                  da compilare nell'app
  emetti          emette una licenza, la stampa e la scrive nel registro (--scadenza: licenza a tempo, formato 2)
  verifica        controlla una licenza e ne mostra il contenuto
  revoca          segna una licenza come revocata (rimborso) e firma revoche.json, da mettere nel prossimo rilascio
  togli-revoca    rimette attiva una licenza revocata (storno chiuso a favore del cliente, errore) e rifirma revoche.json
  revoche         rifirma revoche.json dal registro e lo scrive dove serve (--uscita, per il rilascio dell'app)
  firma-catalogo  firma il catalogo di un laboratorio (JSON, docs/architettura/CATALOGHI.md): nel programma diventa «verificato»
  stato-lancio    conta le licenze vendute a prezzo di lancio rispetto al tetto di tier.json
  autotest        prova Ed25519 con i vettori della RFC 8032 e il formato con un giro completo

Esempi:
  python3 chiavi.py genera-coppia
  python3 chiavi.py emetti --tier pro --intestatario "Studio Rossi" --riferimento "FT 2027/12" --prezzo lancio
  python3 chiavi.py verifica IMP1-AEAQE-...
  python3 chiavi.py emetti --tier laboratorio --intestatario "Lab Bianchi" --riferimento "C 2027/3" --prezzo convenzione --scadenza 2028-03-31
  python3 chiavi.py revoca --seriale 12 --motivo rimborso
  python3 chiavi.py togli-revoca --seriale 12 --motivo storno-a-favore
  python3 chiavi.py revoche --uscita src/impaginatore/licenze/revoche.json
  python3 chiavi.py firma-catalogo laboratorio-rossi.json --uscita laboratorio-rossi-firmato.json
  python3 chiavi.py stato-lancio --data-inizio 2027-02-23
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

QUI = Path(__file__).resolve().parent
RADICE_REPO = QUI.parents[2]
TIER_JSON = RADICE_REPO / "docs" / "mercato" / "tier.json"

# ----------------------------------------------------------------------------- Ed25519 (RFC 8032, §6)
# Codice di riferimento della RFC, adattato. Non è a tempo costante: va bene per firmare sul
# computer del titolare e per verificare (dati pubblici), non per un servizio esposto in rete.

_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _sha512(b: bytes) -> bytes:
    return hashlib.sha512(b).digest()


def _add(P: Tuple[int, int, int, int], Q: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _P
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _P
    C = 2 * P[3] * Q[3] * _D % _P
    D = 2 * P[2] * Q[2] % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _mul(s: int, P: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _uguali(P: Tuple[int, int, int, int], Q: Tuple[int, int, int, int]) -> bool:
    return (P[0] * Q[2] - Q[0] * P[2]) % _P == 0 and (P[1] * Q[2] - Q[1] * P[2]) % _P == 0


def _recupera_x(y: int, segno: int) -> Optional[int]:
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)
    if x2 == 0:
        return None if segno else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _I % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != segno:
        x = _P - x
    return x


_GY = 4 * pow(5, _P - 2, _P) % _P
_GX = _recupera_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)


def _comprimi(P: Tuple[int, int, int, int]) -> bytes:
    zinv = pow(P[2], _P - 2, _P)
    x, y = P[0] * zinv % _P, P[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decomprimi(s: bytes) -> Optional[Tuple[int, int, int, int]]:
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    segno = y >> 255
    y &= (1 << 255) - 1
    x = _recupera_x(y, segno)
    return None if x is None else (x, y, 1, x * y % _P)


def _espandi(seme: bytes) -> Tuple[int, bytes]:
    h = _sha512(seme)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def _modl(b: bytes) -> int:
    return int.from_bytes(_sha512(b), "little") % _L


def ed25519_pubblica(seme: bytes) -> bytes:
    a, _ = _espandi(seme)
    return _comprimi(_mul(a, _G))


def ed25519_firma(seme: bytes, msg: bytes) -> bytes:
    a, prefisso = _espandi(seme)
    A = _comprimi(_mul(a, _G))
    r = _modl(prefisso + msg)
    R = _comprimi(_mul(r, _G))
    s = (r + _modl(R + A + msg) * a) % _L
    return R + int.to_bytes(s, 32, "little")


def ed25519_verifica(pubblica: bytes, msg: bytes, firma: bytes) -> bool:
    if len(pubblica) != 32 or len(firma) != 64:
        return False
    A = _decomprimi(pubblica)
    R = _decomprimi(firma[:32])
    if A is None or R is None:
        return False
    s = int.from_bytes(firma[32:], "little")
    if s >= _L:
        return False
    h = _modl(firma[:32] + pubblica + msg)
    return _uguali(_mul(s, _G), _add(R, _mul(h, A)))


# ----------------------------------------------------------------------------- formato della chiave

PREFISSO = "IMP1-"
DOMINIO_LICENZA = b"IMPAGINATORE-LICENZA-v1\x00"
DOMINIO_REVOCHE = b"IMPAGINATORE-REVOCHE-v1\x00"
DOMINIO_CATALOGO = b"IMPAGINATORE-CATALOGO-v1\x00"
EPOCA = dt.date(2026, 1, 1)
TIER_CODICE = {"essenziale": 1, "pro": 2, "studio": 3, "laboratorio": 4}
CODICE_TIER = {v: k for k, v in TIER_CODICE.items()}
FLAG = {"omaggio": 1, "beta": 2}
MAX_INTESTATARIO = 48


class ChiaveNonValida(ValueError):
    pass


def componi(id_firma: int, tier: str, versione: int, attivazioni: int, seriale: int,
            emessa: dt.date, intestatario: str, flag: int = 0, scadenza: Optional[dt.date] = None) -> bytes:
    """payload della chiave: formato 1 senza scadenza; formato 2 se c'è la scadenza (ultimo giorno valido, compreso),
    scritta in 2 byte dopo l'intestatario. Un'app che conosce solo il formato 1 rifiuta il formato 2."""
    nome = intestatario.strip().encode("utf-8")
    if len(nome) > MAX_INTESTATARIO:
        raise ValueError(f"intestatario troppo lungo: massimo {MAX_INTESTATARIO} byte UTF-8")
    giorni = (emessa - EPOCA).days
    if not 0 <= giorni < 65536:
        raise ValueError("data di emissione fuori intervallo")
    coda = b""
    if scadenza is not None:
        fine = (scadenza - EPOCA).days
        if not giorni <= fine < 65536:
            raise ValueError("la scadenza deve essere tra la data di emissione e il 2205")
        coda = fine.to_bytes(2, "big")
    return (bytes([1 if scadenza is None else 2, id_firma, TIER_CODICE[tier], versione, attivazioni, flag])
            + seriale.to_bytes(4, "big") + giorni.to_bytes(2, "big") + bytes([len(nome)]) + nome + coda)


def in_testo(dati: bytes) -> str:
    b32 = base64.b32encode(dati).decode("ascii").rstrip("=")
    return PREFISSO + "-".join(b32[i:i + 5] for i in range(0, len(b32), 5))


def da_testo(testo: str) -> bytes:
    t = re.sub(r"[\s\-]", "", testo.strip().upper())
    t = t.replace("IMPAGINATORE://ATTIVA?CHIAVE=", "")
    if not t.startswith(PREFISSO.rstrip("-")):
        raise ChiaveNonValida("la chiave deve iniziare con IMP1-")
    corpo = t[len(PREFISSO) - 1:]
    if not re.fullmatch(r"[A-Z2-7]+", corpo):
        raise ChiaveNonValida("caratteri non ammessi nella chiave")
    try:
        return base64.b32decode(corpo + "=" * (-len(corpo) % 8))
    except Exception as e:  # noqa: BLE001
        raise ChiaveNonValida("chiave incompleta o copiata male") from e


def decodifica(testo: str, pubbliche: Dict[int, bytes]) -> Dict[str, Any]:
    """Verifica la firma e restituisce il contenuto. È la funzione che l'app può copiare."""
    dati = da_testo(testo)
    if len(dati) < 13 + 64:
        raise ChiaveNonValida("chiave troppo corta")
    payload, firma = dati[:-64], dati[-64:]
    if payload[0] not in (1, 2):
        raise ChiaveNonValida(f"formato {payload[0]} non supportato da questa versione")
    n = payload[12]
    coda = 2 if payload[0] == 2 else 0
    if len(payload) != 13 + n + coda:
        raise ChiaveNonValida("lunghezza incoerente")
    pub = pubbliche.get(payload[1])
    if pub is None:
        raise ChiaveNonValida(f"chiave di firma {payload[1]} sconosciuta")
    if not ed25519_verifica(pub, DOMINIO_LICENZA + payload, firma):
        raise ChiaveNonValida("firma non valida")
    if payload[2] not in CODICE_TIER:
        raise ChiaveNonValida("fascia sconosciuta")
    return {
        "formato": payload[0],
        "id_firma": payload[1],
        "tier": CODICE_TIER[payload[2]],
        "versione_maggiore": payload[3],
        "attivazioni": payload[4],
        "omaggio": bool(payload[5] & FLAG["omaggio"]),
        "beta": bool(payload[5] & FLAG["beta"]),
        "seriale": int.from_bytes(payload[6:10], "big"),
        "emessa": (EPOCA + dt.timedelta(days=int.from_bytes(payload[10:12], "big"))).isoformat(),
        "intestatario": payload[13:13 + n].decode("utf-8"),
        "scadenza": ((EPOCA + dt.timedelta(days=int.from_bytes(payload[13 + n:], "big"))).isoformat()
                     if coda else None),
        "impronta": hashlib.sha256(dati).hexdigest()[:16],
    }


# ----------------------------------------------------------------------------- archivio locale

CAMPI_REGISTRO = ["seriale", "emessa", "tier", "attivazioni", "versione_maggiore", "prezzo", "riferimento",
                  "intestatario", "impronta", "stato", "nota", "scadenza"]   # «scadenza» in coda: i registri di prima si leggono uguale


def cartella(arg: Optional[str]) -> Path:
    d = Path(arg or os.environ.get("IMPAGINATORE_NEGOZIO_DIR") or Path.home() / ".impaginatore-negozio")
    d = d.expanduser().resolve()
    try:
        d.relative_to(RADICE_REPO)
        raise SystemExit(f"Errore: {d} è dentro il repository. Chiave privata e registro devono stare fuori.")
    except ValueError:
        pass
    return d


def leggi_privata(d: Path, id_firma: Optional[int]) -> Tuple[int, bytes]:
    file = sorted(d.glob("chiave-privata-*.hex"))
    if not file:
        raise SystemExit(f"Nessuna chiave privata in {d}: eseguire prima 'genera-coppia'.")
    trovate = {int(f.stem.rsplit("-", 1)[1]): f for f in file}
    scelta = id_firma if id_firma is not None else max(trovate)
    if scelta not in trovate:
        raise SystemExit(f"Chiave privata {scelta} assente in {d}.")
    if os.name == "posix" and trovate[scelta].stat().st_mode & 0o077:
        print(f"Attenzione: {trovate[scelta]} è leggibile da altri utenti (chmod 600).", file=sys.stderr)
    seme = bytes.fromhex(trovate[scelta].read_text().strip())
    if len(seme) != 32:
        raise SystemExit("Chiave privata corrotta.")
    return scelta, seme


def pubbliche_locali(d: Path) -> Dict[int, bytes]:
    out = {}
    for f in d.glob("chiave-privata-*.hex"):
        out[int(f.stem.rsplit("-", 1)[1])] = ed25519_pubblica(bytes.fromhex(f.read_text().strip()))
    return out


def leggi_registro(d: Path) -> List[Dict[str, str]]:
    f = d / "registro.csv"
    if not f.exists():
        return []
    with f.open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def scrivi_registro(d: Path, righe: List[Dict[str, str]]) -> None:
    f = d / "registro.csv"
    tmp = f.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=CAMPI_REGISTRO)
        w.writeheader()
        w.writerows(righe)
    os.replace(tmp, f)
    if os.name == "posix":
        os.chmod(f, 0o600)


def listino() -> Dict[str, Any]:
    return json.loads(TIER_JSON.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- comandi

def cmd_genera_coppia(a: argparse.Namespace) -> int:
    d = cartella(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        os.chmod(d, 0o700)
    esistenti = sorted(int(f.stem.rsplit("-", 1)[1]) for f in d.glob("chiave-privata-*.hex"))
    if esistenti and not a.nuova:
        print(f"Esiste già la chiave {esistenti[-1]} in {d}. Per una rotazione usare --nuova.", file=sys.stderr)
        return 1
    id_firma = (esistenti[-1] + 1) if esistenti else 1
    if id_firma > 255:
        raise SystemExit("Troppe chiavi di firma.")
    seme = secrets.token_bytes(32)
    f = d / f"chiave-privata-{id_firma}.hex"
    fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w") as h:
        h.write(seme.hex() + "\n")
    pub = ed25519_pubblica(seme).hex()
    print(f"Chiave privata {id_firma} scritta in {f} (solo lettura per te).")
    print("FARNE SUBITO UNA COPIA OFFLINE: senza, non si possono più emettere licenze valide per le app già distribuite.")
    print("\nChiave pubblica da compilare nell'app, in src/impaginatore/licenze/chiave.py (non è un segreto):")
    print(f"  CHIAVI_PUBBLICHE = {{{id_firma}: Pubblica(\"{pub}\")}}")
    return 0


def cmd_emetti(a: argparse.Namespace) -> int:
    d = cartella(a.dir)
    lst = listino()
    tiers = {t["id"]: t for t in lst["tiers"]}
    if a.tier not in tiers and a.tier != "laboratorio":
        raise SystemExit(f"Fascia sconosciuta: {a.tier}")
    attivazioni = a.attivazioni or (tiers[a.tier]["attivazioni"] if a.tier in tiers
                                    else lst["laboratorio"]["funzioni"]["computer"])
    id_firma, seme = leggi_privata(d, a.id_firma)
    registro = leggi_registro(d)
    seriale = max([int(r["seriale"]) for r in registro] or [0]) + 1
    oggi = dt.date.fromisoformat(a.data) if a.data else dt.date.today()
    flag = (FLAG["omaggio"] if a.prezzo in ("omaggio", "beta") else 0) | (FLAG["beta"] if a.prezzo == "beta" else 0)
    scadenza = dt.date.fromisoformat(a.scadenza) if a.scadenza else None
    payload = componi(id_firma, a.tier, a.versione, attivazioni, seriale, oggi, a.intestatario, flag, scadenza)
    testo = in_testo(payload + ed25519_firma(seme, DOMINIO_LICENZA + payload))
    info = decodifica(testo, {id_firma: ed25519_pubblica(seme)})  # controllo di coerenza
    registro.append({"seriale": str(seriale), "emessa": oggi.isoformat(), "tier": a.tier,
                     "attivazioni": str(attivazioni), "versione_maggiore": str(a.versione), "prezzo": a.prezzo,
                     "riferimento": a.riferimento, "intestatario": a.intestatario.strip(),
                     "impronta": info["impronta"], "stato": "attiva", "nota": a.nota or "",
                     "scadenza": info["scadenza"] or ""})
    d.mkdir(parents=True, exist_ok=True)
    scrivi_registro(d, registro)
    if a.json:
        print(json.dumps({"chiave": testo, **info}, ensure_ascii=False, indent=2))
    else:
        print(testo)
        print(f"\nseriale {seriale} · {a.tier} · {attivazioni} computer · v{a.versione} · intestata a "
              f"«{info['intestatario']}»" + (f" · valida fino al {info['scadenza']} compreso" if info["scadenza"] else "")
              + f" · registrata in {d / 'registro.csv'}")
        print(f"link diretto: impaginatore://attiva?chiave={testo}")
    return 0


def cmd_verifica(a: argparse.Namespace) -> int:
    pub = {a.id_firma or 1: bytes.fromhex(a.pubblica)} if a.pubblica else pubbliche_locali(cartella(a.dir))
    if not pub:
        raise SystemExit("Nessuna chiave pubblica: passare --pubblica HEX oppure --dir con la chiave privata.")
    try:
        info = decodifica(a.chiave, pub)
    except ChiaveNonValida as e:
        print(f"NON VALIDA: {e}")
        return 1
    stato = ""
    if not a.pubblica:
        riga = next((r for r in leggi_registro(cartella(a.dir)) if r["impronta"] == info["impronta"]), None)
        stato = f" · registro: {riga['stato']}" if riga else " · non presente nel registro"
    print("VALIDA" + stato)
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def firma_revoche(d: Path, registro: List[Dict[str, str]], id_firma: Optional[int], uscita: Path) -> Dict[str, Any]:
    """firma l'elenco dei seriali revocati del registro e lo scrive in `uscita`. L'app lo legge solo dal proprio pacchetto
    (src/impaginatore/licenze/revoche.json): arriva con gli aggiornamenti, il programma non scarica niente (LICENZE.md)."""
    id_firma, seme = leggi_privata(d, id_firma)
    corpo = {"formato": 1, "id_firma": id_firma,
             "emessa": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
             "seriali": sorted(int(r["seriale"]) for r in registro if r["stato"] == "revocata")}
    canonico = json.dumps(corpo, sort_keys=True, separators=(",", ":")).encode("utf-8")
    corpo["firma"] = ed25519_firma(seme, DOMINIO_REVOCHE + canonico).hex()
    uscita.parent.mkdir(parents=True, exist_ok=True)
    uscita.write_text(json.dumps(corpo, indent=2) + "\n", encoding="utf-8")
    return corpo


AVVISO_RILASCIO = ("Per farlo arrivare agli utenti: «chiavi.py revoche --uscita src/impaginatore/licenze/revoche.json» "
                   "nella copia del rilascio, poi il rilascio dell'aggiornamento (FORMATO-CHIAVE.md §4).")


def _cambia_stato(a: argparse.Namespace, da: str, a_stato: str, parola: str) -> int:
    d = cartella(a.dir)
    registro = leggi_registro(d)
    riga = next((r for r in registro if r["seriale"] == str(a.seriale)), None)
    if riga is None:
        raise SystemExit(f"Seriale {a.seriale} assente dal registro.")
    if riga["stato"] != da:
        raise SystemExit(f"Il seriale {a.seriale} è «{riga['stato']}», non «{da}»: niente da fare.")
    riga["stato"] = a_stato
    riga["nota"] = (riga["nota"] + f" {parola} {dt.date.today().isoformat()}: {a.motivo}").strip()
    scrivi_registro(d, registro)
    corpo = firma_revoche(d, registro, a.id_firma, d / "revoche.json")
    print(f"Seriale {a.seriale} {parola}. Elenco firmato ({len(corpo['seriali'])} seriali) in {d / 'revoche.json'}.")
    print(AVVISO_RILASCIO)
    return 0


def cmd_revoca(a: argparse.Namespace) -> int:
    return _cambia_stato(a, "attiva", "revocata", "revocata")


def cmd_togli_revoca(a: argparse.Namespace) -> int:
    """TERMINI-VENDITA B.7: dopo uno storno chiuso a favore del cliente la stessa chiave torna valida con il rilascio
    successivo dell'elenco. Se il cliente non può aspettare il rilascio, si emette una chiave nuova."""
    return _cambia_stato(a, "revocata", "attiva", "revoca tolta")


def cmd_revoche(a: argparse.Namespace) -> int:
    d = cartella(a.dir)
    uscita = Path(a.uscita) if a.uscita else d / "revoche.json"
    corpo = firma_revoche(d, leggi_registro(d), a.id_firma, uscita)
    print(f"Elenco firmato delle revoche ({len(corpo['seriali'])} seriali) scritto in {uscita}.")
    return 0


def firma_catalogo(seme: bytes, id_firma: int, corpo: Dict[str, Any]) -> Dict[str, Any]:
    """il catalogo con «id_firma» e «firma»: Ed25519 di DOMINIO_CATALOGO + JSON canonico (chiavi ordinate, senza spazi, come
    lo rifà il programma: impaginatore.laboratori.catalogo.canonico) senza «firma». Lo schema del catalogo lo controlla il
    programma: prima di firmarlo, il catalogo si prova importandolo in Impaginatore"""
    corpo = {k: v for k, v in corpo.items() if k != "firma"}
    corpo["id_firma"] = id_firma
    canonico = json.dumps(corpo, sort_keys=True, separators=(",", ":")).encode("utf-8")
    corpo["firma"] = ed25519_firma(seme, DOMINIO_CATALOGO + canonico).hex()
    return corpo


def cmd_firma_catalogo(a: argparse.Namespace) -> int:
    src = Path(a.catalogo)
    try:
        corpo = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"Errore: catalogo non letto ({e}).")
    if not isinstance(corpo, dict) or corpo.get("formato_catalogo") != 1:
        raise SystemExit("Errore: non è un catalogo del formato 1 («formato_catalogo»: 1).")
    id_firma, seme = leggi_privata(cartella(a.dir), a.id_firma)
    uscita = Path(a.uscita) if a.uscita else src.with_name(src.stem + "-firmato.json")
    uscita.write_text(json.dumps(firma_catalogo(seme, id_firma, corpo), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Catalogo «{corpo.get('id')}» firmato con la chiave {id_firma}: {uscita}")
    return 0


def cmd_stato_lancio(a: argparse.Namespace) -> int:
    lancio = listino()["lancio"]
    inizio = dt.date.fromisoformat(a.data_inizio)
    fine = inizio + dt.timedelta(days=lancio["durata_giorni"])
    vendute = [r for r in leggi_registro(cartella(a.dir))
               if r["prezzo"] == "lancio" and r["stato"] == "attiva"]
    oggi = dt.date.today()
    print(f"Lancio dal {inizio} al {fine - dt.timedelta(days=1)} compreso ({lancio['durata_giorni']} giorni), "
          f"tetto {lancio['max_licenze']} licenze.")
    print(f"Vendute a prezzo di lancio: {len(vendute)}. Giorni rimasti: {max(0, (fine - oggi).days)}.")
    chiuso = len(vendute) >= lancio["max_licenze"] or oggi >= fine
    print("PREZZO DI LANCIO CHIUSO: da ora si vende a listino." if chiuso else "Prezzo di lancio ancora valido.")
    return 2 if chiuso else 0


def cmd_autotest(_: argparse.Namespace) -> int:
    # RFC 8032, §7.1, TEST 1 (messaggio vuoto) e TEST 2 (un byte)
    vettori = [
        ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
         "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
         "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
        ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
         "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
         "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ]
    for i, (sk, pk, msg, sig) in enumerate(vettori, 1):
        seme, m = bytes.fromhex(sk), bytes.fromhex(msg)
        assert ed25519_pubblica(seme).hex() == pk, f"vettore {i}: chiave pubblica"
        assert ed25519_firma(seme, m).hex() == sig, f"vettore {i}: firma"
        assert ed25519_verifica(bytes.fromhex(pk), m, bytes.fromhex(sig)), f"vettore {i}: verifica"
        assert not ed25519_verifica(bytes.fromhex(pk), m + b"x", bytes.fromhex(sig)), f"vettore {i}: falso positivo"
    seme = secrets.token_bytes(32)
    pub = {7: ed25519_pubblica(seme)}
    payload = componi(7, "pro", 2, 2, 42, dt.date(2027, 2, 23), "Studio Fotografico Àlfa", 0)
    testo = in_testo(payload + ed25519_firma(seme, DOMINIO_LICENZA + payload))
    info = decodifica(testo.lower().replace("-", " - "), pub)
    assert (info["tier"], info["seriale"], info["emessa"], info["intestatario"], info["scadenza"]) == \
        ("pro", 42, "2027-02-23", "Studio Fotografico Àlfa", None)
    p2 = componi(7, "laboratorio", 2, 2, 43, dt.date(2027, 2, 23), "Lab", 0, dt.date(2028, 2, 29))
    info2 = decodifica(in_testo(p2 + ed25519_firma(seme, DOMINIO_LICENZA + p2)), pub)
    assert (info2["formato"], info2["scadenza"]) == (2, "2028-02-29"), "formato 2 con scadenza"
    manomessa = bytearray(da_testo(testo))
    manomessa[2] = TIER_CODICE["studio"]
    try:
        decodifica(in_testo(bytes(manomessa)), pub)
        raise AssertionError("una chiave manomessa è stata accettata")
    except ChiaveNonValida:
        pass
    print(f"autotest superato: RFC 8032 (2 vettori), formati 1 e 2, manomissione. Esempio di chiave ({len(testo)} caratteri):")
    print(testo)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", help="cartella di chiave privata e registro (fuori dal repository)")
    sub = ap.add_subparsers(dest="comando", required=True)
    g = sub.add_parser("genera-coppia")
    g.add_argument("--nuova", action="store_true", help="crea una nuova chiave (rotazione)")
    e = sub.add_parser("emetti")
    e.add_argument("--tier", required=True, choices=["essenziale", "pro", "studio", "laboratorio"])
    e.add_argument("--intestatario", required=True, help="nome o ragione sociale mostrato nell'app (max 48 byte)")
    e.add_argument("--riferimento", required=True, help="numero di fattura o d'ordine")
    e.add_argument("--prezzo", required=True,
                   choices=["listino", "lancio", "upgrade", "rottamazione", "convenzione", "omaggio", "beta"])
    e.add_argument("--versione", type=int, default=2)
    e.add_argument("--attivazioni", type=int, help="computer, se diverso da tier.json")
    e.add_argument("--data", help="AAAA-MM-GG (predefinito: oggi)")
    e.add_argument("--nota")
    e.add_argument("--scadenza", help="AAAA-MM-GG, ultimo giorno valido compreso: licenza a tempo (formato 2, "
                   "laboratori «modello C»; le app che conoscono solo il formato 1 la rifiutano)")
    e.add_argument("--id-firma", type=int)
    e.add_argument("--json", action="store_true")
    v = sub.add_parser("verifica")
    v.add_argument("chiave")
    v.add_argument("--pubblica", help="chiave pubblica esadecimale (per verificare senza la privata)")
    v.add_argument("--id-firma", type=int)
    r = sub.add_parser("revoca")
    r.add_argument("--seriale", type=int, required=True)
    r.add_argument("--motivo", required=True, choices=["rimborso", "upgrade", "frode", "errore"])
    r.add_argument("--id-firma", type=int)
    t = sub.add_parser("togli-revoca")
    t.add_argument("--seriale", type=int, required=True)
    t.add_argument("--motivo", required=True, choices=["storno-a-favore", "errore"])
    t.add_argument("--id-firma", type=int)
    rv = sub.add_parser("revoche")
    rv.add_argument("--uscita", help="dove scrivere revoche.json (predefinito: la cartella del negozio)")
    rv.add_argument("--id-firma", type=int)
    fc = sub.add_parser("firma-catalogo")
    fc.add_argument("catalogo", help="file JSON del catalogo")
    fc.add_argument("--uscita", help="dove scrivere il catalogo firmato (predefinito: <nome>-firmato.json accanto)")
    fc.add_argument("--id-firma", type=int)
    s = sub.add_parser("stato-lancio")
    s.add_argument("--data-inizio", default="2027-02-23")
    sub.add_parser("autotest")
    a = ap.parse_args(argv)
    return {"genera-coppia": cmd_genera_coppia, "emetti": cmd_emetti, "verifica": cmd_verifica,
            "revoca": cmd_revoca, "togli-revoca": cmd_togli_revoca, "revoche": cmd_revoche, "firma-catalogo": cmd_firma_catalogo,
            "stato-lancio": cmd_stato_lancio, "autotest": cmd_autotest}[a.comando](a)


if __name__ == "__main__":
    sys.exit(main())
