"""Ed25519 del programma (impaginatore/ed25519.py): vettori della RFC 8032, firme rifiutate, stesso risultato di chiavi.py."""
import importlib.util
import os
import secrets

import pytest

from impaginatore import ed25519

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# RFC 8032, § 7.1: TEST 1, TEST 2, TEST 3 (seme, chiave pubblica, messaggio, firma)
VETTORI = [
    ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60", "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb", "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7", "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025", "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
]


def _chiavi_negozio():
    spec = importlib.util.spec_from_file_location("chiavi_negozio", os.path.join(RADICE, "marketing", "negozio", "chiavi", "chiavi.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("seme,pub,msg,firma", VETTORI)
def test_vettori_rfc_8032(seme, pub, msg, firma):
    s, p, m, f = bytes.fromhex(seme), bytes.fromhex(pub), bytes.fromhex(msg), bytes.fromhex(firma)
    assert ed25519.pubblica(s) == p
    assert ed25519.firma(s, m) == f
    assert ed25519.verifica(p, m, f)
    assert not ed25519.verifica(p, m + b"x", f), "messaggio cambiato"
    alterata = bytearray(f); alterata[10] ^= 1
    assert not ed25519.verifica(p, m, bytes(alterata)), "firma cambiata"
    assert not ed25519.verifica(ed25519.pubblica(bytes(32)), m, f), "chiave pubblica di un altro"


def _y_senza_punto():
    """una y per cui non esiste un punto della curva (la radice quadrata non c'è)"""
    return next(y for y in range(2, 1000) if ed25519._recupera_x(y, 0) is None)


def test_firme_e_chiavi_malformate_si_rifiutano():
    s = secrets.token_bytes(32); p = ed25519.pubblica(s); f = ed25519.firma(s, b"ciao")
    assert ed25519.verifica(p, b"ciao", f)
    for pub, firma in [(p.hex(), f), (p, f.hex()), (p[:31], f), (p, f[:63]), (p + b"\0", f)]:
        assert not ed25519.verifica(pub, b"ciao", firma), "tipi o lunghezze sbagliate"
    assert not ed25519.verifica(b"\xff" * 32, b"ciao", f), "y fuori dal campo"
    assert not ed25519.verifica(_y_senza_punto().to_bytes(32, "little"), b"ciao", f), "y senza punto sulla curva"
    assert not ed25519.verifica((1 | 1 << 255).to_bytes(32, "little"), b"ciao", f), "x = 0 con il segno 1"
    assert not ed25519.verifica((1).to_bytes(32, "little"), b"ciao", f), "punto neutro come chiave"
    assert not ed25519.verifica(p, b"ciao", b"\xff" * 32 + f[32:]), "R non è un punto"
    s_grande = (int.from_bytes(f[32:], "little") + ed25519._L).to_bytes(32, "little")
    assert not ed25519.verifica(p, b"ciao", f[:32] + s_grande), "s non ridotto (firma malleabile)"


def test_stesso_risultato_dello_strumento_del_negozio():
    """chiavi.py firma, il programma verifica: le due copie del codice della RFC devono dare gli stessi byte"""
    C = _chiavi_negozio()
    for _ in range(3):
        s = secrets.token_bytes(32); m = secrets.token_bytes(40)
        assert ed25519.pubblica(s) == C.ed25519_pubblica(s)
        assert ed25519.firma(s, m) == C.ed25519_firma(s, m)
        assert C.ed25519_verifica(ed25519.pubblica(s), m, ed25519.firma(s, m))
