"""Nomi scelti dall'utente: il nome di un progetto (un dato, mai codice) e il nome di cartella che se ne ricava.

Il nome del progetto si salva così com'è (in progetto.json, che è JSON): qui si controlla solo che sia un testo di una riga,
senza caratteri invisibili. Il nome della cartella invece deve valere su macOS, Windows e Linux: niente caratteri vietati
da Windows, niente nomi riservati (CON, NUL, COM1...), niente punti o spazi in fondo, niente punto all'inizio (cartella
nascosta), Unicode in forma composta (NFC: «à» è un carattere solo, come lo scrive Windows; macOS lo accetta uguale) e
lunghezza limitata (sotto ci vanno ancora _cache/thumbs/<foto>, e Windows ha percorsi corti).
"""
import re
import unicodedata

LUNGHEZZA_NOME = 120                     # caratteri del nome di un progetto
LUNGHEZZA_CARTELLA = 80                  # caratteri del nome di una cartella
_VIETATI = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_RISERVATI = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {f"{p}{n}" for p in ("COM", "LPT") for n in list("123456789") + ["¹", "²", "³"]}
_INVISIBILI = ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp")          # controllo, formato (bidi, a larghezza zero), surrogati, privati, non assegnati, a capo


def invisibile(ch):
    """True per i caratteri che non si vedono o cambiano il verso del testo (a capo, tabulazioni, U+202E...)"""
    return unicodedata.category(ch) in _INVISIBILI


def nome_progetto(nome):
    """nome di un progetto pulito (spazi esterni tolti, forma NFC) o ValueError con un messaggio per l'utente"""
    nome = unicodedata.normalize("NFC", str(nome or "")).strip()
    if not nome: raise ValueError("Scrivi il nome del progetto")
    if len(nome) > LUNGHEZZA_NOME: raise ValueError(f"Il nome è troppo lungo: al massimo {LUNGHEZZA_NOME} caratteri")
    if any(invisibile(c) for c in nome): raise ValueError("Il nome contiene caratteri non ammessi (a capo, tabulazioni o caratteri invisibili)")
    return nome


def nome_cartella(nome, ripiego="Progetto"):
    """nome di cartella valido sui tre sistemi ricavato da `nome` (i caratteri vietati diventano «-»)"""
    s = unicodedata.normalize("NFC", str(nome or ""))
    s = "".join("-" if invisibile(c) else c for c in s)
    s = _VIETATI.sub("-", s).strip().lstrip(".").strip()
    s = s[:LUNGHEZZA_CARTELLA].rstrip(" .")
    if not s: return ripiego
    if s.split(".")[0].rstrip(" ").upper() in _RISERVATI: s = "_" + s          # CON, con.txt, LPT1 ... sono dispositivi su Windows
    return s


def componente_valido(parte):
    """True se `parte` (un pezzo di percorso, es. il nome di un file in uno ZIP) è accettabile su tutti e tre i sistemi:
    niente caratteri vietati o invisibili, niente punto o spazio in fondo, niente nomi riservati, al massimo 255 caratteri"""
    if not parte or parte in (".", "..") or len(parte) > 255 or parte[-1] in " ." or _VIETATI.search(parte): return False
    return not any(invisibile(c) for c in parte) and parte.split(".")[0].rstrip(" ").upper() not in _RISERVATI
