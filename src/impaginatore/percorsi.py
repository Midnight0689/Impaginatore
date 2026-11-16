"""Percorsi che i server accettano dalla pagina: solo dentro le cartelle consentite (radici).

Le radici di un server sono le cartelle che l'utente ha scelto con una finestra di sistema in questa sessione, la cartella
dei progetti e le cartelle dei progetti e delle loro foto (le decide ogni server). Un percorso è dentro una radice se, dopo
aver risolto collegamenti simbolici e «..», ci sta davvero: il confronto vale anche sui dischi che non distinguono le
maiuscole (macOS, Windows) e tra unità diverse di Windows (C: e D: non si contengono mai).

Le cartelle riservate (riservata) non diventano mai radici dedotte da un progetto e un progetto non vi legge foto (VER-004):
le cartelle nascoste della casa (.ssh, .config, .gnupg...), i dati e la cache dei programmi (anche i nostri, con i file
di sessione), le cartelle di sistema. L'utente può comunque sceglierle con una finestra di sistema.
"""
import os
import threading

from .piattaforma import cartelle, sistema

_SISTEMA_POSIX = ("/etc", "/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/libx32", "/boot", "/dev", "/proc", "/sys", "/run", "/snap",
                  "/var/lib", "/var/log", "/var/run", "/var/db", "/private/etc", "/private/var/db", "/private/var/log", "/private/var/run")


class FuoriDalleRadici(ValueError):
    """percorso fuori dalle cartelle consentite: i server rispondono 403"""


def reale(p):
    """percorso assoluto con collegamenti simbolici e «..» risolti (anche se non esiste ancora)"""
    return os.path.realpath(os.path.abspath(os.path.expanduser(p)))


def dentro(p, radice):
    """p è radice o sta dentro radice?"""
    try: r, cur, rr = os.stat(radice), reale(p), os.path.normcase(reale(radice))
    except (OSError, ValueError): return False           # radice che non c'è, percorso impossibile (carattere nullo...)
    q = os.path.normcase(cur)
    if q == rr or q.startswith(rr.rstrip(os.sep) + os.sep): return True
    # dischi che non distinguono le maiuscole: si risale confrontando le cartelle vere
    while True:
        try:
            if os.path.samestat(os.stat(cur), r): return True
        except (OSError, ValueError): pass
        su = os.path.dirname(cur)
        if su == cur: return False
        cur = su


def troppo_ampia(p):
    """cartelle che non diventano radici da sole (dedotte da un progetto): la radice del disco, la casa dell'utente e
    quelle che la contengono"""
    q = reale(p)
    return os.path.dirname(q) == q or dentro(cartelle.home(), q)


def _chiave(p):
    """forma confrontabile di un percorso: reale e, dove il disco non distingue le maiuscole (macOS, Windows), in minuscolo"""
    q = os.path.normcase(reale(p))
    return q.lower() if sistema() in ("mac", "windows") else q


def _riservate():
    """cartelle riservate del sistema e dei programmi, come chiavi (le nascoste della casa le guarda riservata)"""
    casa, s = cartelle.home(), sistema()
    out = [cartelle.dati_utente(), cartelle.cache(), cartelle.legacy()]
    if s == "windows":
        out += [os.environ.get(k) for k in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData", "APPDATA", "LOCALAPPDATA")] + [os.path.join(casa, "AppData")]
    else: out += list(_SISTEMA_POSIX)
    if s == "mac": out += [os.path.join(casa, "Library"), "/System", "/Library"]
    return [_chiave(p) for p in out if p]


def riservata(p):
    """p (percorso reale, collegamenti risolti) sta in una cartella riservata? Un percorso impossibile lo è sempre"""
    if not p: return False
    try: q, casa = _chiave(p), _chiave(cartelle.home())
    except (OSError, ValueError): return True

    def sotto(r): return q == r or q.startswith(r.rstrip(os.sep) + os.sep)
    if q != casa and sotto(casa) and q[len(casa.rstrip(os.sep)) + 1:].startswith("."): return True            # ~/.ssh, ~/.config ... (non ~/Lavori/.x)
    return any(sotto(r) for r in _riservate())


class Radici:
    """cartelle consentite di un server: quelle fisse (funzione che le calcola ogni volta, dal progetto) più quelle scelte
    dall'utente con le finestre di sistema durante questa sessione"""

    def __init__(self, fisse=None):
        self.fisse = fisse or (lambda: [])
        self.scelte = []
        self._lock = threading.Lock()

    def scelta(self, p):
        """l'utente ha scelto p con una finestra di sistema: p (o la sua cartella, se è un file) diventa una radice"""
        if not p: return
        d = reale(p)
        if not os.path.isdir(d): d = os.path.dirname(d)
        with self._lock:
            if d not in self.scelte: self.scelte.append(d)

    def tutte(self):
        """[radici] senza doppioni, nell'ordine: fisse (escluse quelle troppo ampie e le riservate), poi scelte"""
        out = []
        for p in [x for x in self.fisse() if x and not troppo_ampia(x) and not riservata(x)] + list(self.scelte):
            q = reale(p)
            if q not in out and os.path.isdir(q): out.append(q)
        return out

    def contiene(self, p):
        return bool(p) and any(dentro(p, r) for r in self.tutte())

    def controlla(self, p, cosa="questo percorso"):
        """p (reale) se è consentito, altrimenti FuoriDalleRadici"""
        if not isinstance(p, str) or not self.contiene(p):
            raise FuoriDalleRadici(f"Non posso usare {cosa}: sta fuori dalle cartelle del progetto e da quelle che hai scelto. Sceglilo con «Scegli…»")
        return reale(p)
