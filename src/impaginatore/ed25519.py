"""Firme Ed25519 (RFC 8032) con la sola libreria standard: verifica delle chiavi di licenza e degli elenchi di revoca.

È il codice di riferimento della RFC 8032, sezione 6, lo stesso di marketing/negozio/chiavi/chiavi.py (lo strumento che
firma). Non è a tempo costante: va bene per verificare dati pubblici (chiavi di licenza, elenchi firmati) e per firmare
nelle prove, non per un servizio esposto in rete. Una verifica costa pochi millisecondi.
La stessa funzione verifica() servirà ai manifesti firmati degli aggiornamenti (aggiornamenti/firmati.py, T-207): non
serve una libreria esterna.
"""
import hashlib

_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _sha512(b):
    return hashlib.sha512(b).digest()


def _somma(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _P
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _P
    C = 2 * P[3] * Q[3] * _D % _P
    D = 2 * P[2] * Q[2] % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _per(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1: Q = _somma(Q, P)
        P = _somma(P, P)
        s >>= 1
    return Q


def _uguali(P, Q):
    return (P[0] * Q[2] - Q[0] * P[2]) % _P == 0 and (P[1] * Q[2] - Q[1] * P[2]) % _P == 0


def _recupera_x(y, segno):
    """coordinata x del punto con questa y e questo segno, o None se il punto non esiste"""
    if y >= _P: return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)
    if x2 == 0: return None if segno else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0: x = x * _I % _P
    if (x * x - x2) % _P != 0: return None
    if (x & 1) != segno: x = _P - x
    return x


_GY = 4 * pow(5, _P - 2, _P) % _P
_GX = _recupera_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)


def _comprimi(P):
    zinv = pow(P[2], _P - 2, _P)
    x, y = P[0] * zinv % _P, P[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decomprimi(s):
    y = int.from_bytes(s, "little")
    segno = y >> 255
    y &= (1 << 255) - 1
    x = _recupera_x(y, segno)
    return None if x is None else (x, y, 1, x * y % _P)


def _espandi(seme):
    h = _sha512(seme)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def _modl(b):
    return int.from_bytes(_sha512(b), "little") % _L


def pubblica(seme):
    """chiave pubblica (32 byte) del seme privato (32 byte)"""
    a, _ = _espandi(seme)
    return _comprimi(_per(a, _G))


def firma(seme, messaggio):
    """firma (64 byte) del messaggio con il seme privato. Nel programma serve solo alle prove: le chiavi le firma chiavi.py"""
    a, prefisso = _espandi(seme)
    A = _comprimi(_per(a, _G))
    r = _modl(prefisso + messaggio)
    R = _comprimi(_per(r, _G))
    s = (r + _modl(R + A + messaggio) * a) % _L
    return R + int.to_bytes(s, 32, "little")


def verifica(chiave_pubblica, messaggio, firma_):
    """True se firma_ è una firma Ed25519 valida del messaggio per questa chiave pubblica; False per ogni altra cosa
    (lunghezze sbagliate, punti che non esistono, firma alterata)"""
    if not isinstance(chiave_pubblica, bytes) or not isinstance(firma_, bytes) or len(chiave_pubblica) != 32 or len(firma_) != 64: return False
    A = _decomprimi(chiave_pubblica)
    R = _decomprimi(firma_[:32])
    if A is None or R is None: return False
    s = int.from_bytes(firma_[32:], "little")
    if s >= _L: return False
    h = _modl(firma_[:32] + chiave_pubblica + messaggio)
    return _uguali(_per(s, _G), _somma(R, _per(h, A)))
