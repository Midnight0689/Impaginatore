"""Il programma compilato (pacchetti di installazione, T-302): come si riconosce e come rilancia se stesso.

Da Python (checkout, pip) i processi del programma partono con «python -m <modulo>». Compilato con Nuitka non c'è un
interprete da lanciare: sys.executable è il programma stesso, che riceve un sottocomando al posto del modulo
(SOTTOCOMANDI). Tre sottocomandi interni, con il trattino basso, servono solo ai processi che il programma lancia da sé:
_psd (i PSD con Photoshop), _dialogo (finestre di scelta di tkinter su Windows), _rilancia (riavvio dopo un
aggiornamento). Esistono anche da Python, così i test li provano come li usa il programma compilato. Un quarto, _avvio,
scrive la pagina della schermata di avvio come la mostra la finestra (versione e stato della licenza): serve alla prova
del programma installato (strumenti/verifica_pacchetto.py), che non può guardare dentro la finestra.

All'avvio del programma compilato prepara() mette sys.frozen (lo guardano desktop.finestra, che spegne gli strumenti di
sviluppo, e pywebview), dà sempre uno stdout e uno stderr (Windows senza console) e su Linux trova PyGObject del
sistema per la finestra con WebKitGTK. Come si costruisce il programma: docs/architettura/DISTRIBUZIONE.md.
"""
import os
import sys
from importlib import machinery

# modulo che da Python si lancia con «-m» -> argomenti del programma compilato al suo posto
SOTTOCOMANDI = {
    "impaginatore": [],
    "impaginatore.editor": ["editor"],
    "impaginatore.mcp": ["mcp"],
    "impaginatore.motore.genera_psd_angolo": ["_psd"],
}
INTERNI = ("_psd", "_dialogo", "_rilancia", "_avvio")

# dove le distribuzioni Linux mettono PyGObject («gi») per il Python del sistema; {v} = 3.12, la versione di questo Python
CARTELLE_GI = ("/usr/lib/python3/dist-packages", "/usr/lib/python{v}/site-packages", "/usr/lib64/python{v}/site-packages", "/usr/local/lib/python{v}/dist-packages")


def attivo():
    """True nel programma compilato: Nuitka mette __compiled__ in ogni modulo che compila (non imposta sys.frozen, lo fa
    prepara()); sys.frozen vale anche per gli altri strumenti che impacchettano Python"""
    return "__compiled__" in globals() or bool(getattr(sys, "frozen", False))


def comando(modulo, *argomenti):
    """riga di comando di un processo di questo programma: «python -m <modulo> …» da Python, il programma stesso con il
    sottocomando del modulo da compilato. Sempre lo stesso programma che sta girando, mai uno trovato nel PATH"""
    if attivo(): return [sys.executable, *SOTTOCOMANDI[modulo], *argomenti]
    return [sys.executable, "-m", modulo, *argomenti]


def interno(nome, argv):
    """esegue un sottocomando interno (INTERNI) con i suoi argomenti; restituisce il codice d'uscita"""
    if nome == "_psd":
        from .motore import genera_psd_angolo
        return genera_psd_angolo.main(argv)
    if nome == "_dialogo":
        from .piattaforma import dialoghi
        return dialoghi.scegli_con_tk(argv)
    if nome == "_rilancia":
        from .piattaforma import processi
        return processi.rilancio(argv)
    if nome == "_avvio":
        from .desktop import avvio
        sys.stdout.buffer.write(avvio.pagina().encode("utf-8")); sys.stdout.flush()
        return 0
    raise ValueError(f"sottocomando interno sconosciuto: {nome}")          # non tradotto: errore di programmazione, non arriva all'utente


class SoloGi:
    """cerca nella cartella di PyGObject del sistema solo «gi» e «cairo» (pycairo, che gi chiede per disegnare): ogni altro
    modulo resta quello compilato nel programma. I sottomoduli (gi._gi…) li trova l'import normale nel __path__ di gi"""
    NOMI = ("gi", "cairo")

    def __init__(self, cartella):
        self.cartella = cartella

    def find_spec(self, nome, percorso=None, obiettivo=None):
        if nome not in self.NOMI: return None
        return machinery.PathFinder.find_spec(nome, [self.cartella])


def cartella_gi(cartelle=CARTELLE_GI):
    """cartella del sistema con il PyGObject compilato per questa versione di Python (gi/_gi.cpython-312-….so), o None.
    Il programma compilato non contiene PyGObject né GTK né WebKitGTK (LGPL): usa quelli del sistema, come dichiara il
    pacchetto .deb. Con un Python di un'altra versione nel sistema la finestra non c'è e si apre il browser"""
    tag = sys.implementation.cache_tag                       # «cpython-312»
    v = f"{sys.version_info.major}.{sys.version_info.minor}"
    for c in cartelle:
        d = os.path.join(c.format(v=v), "gi")
        try: nomi = os.listdir(d)
        except OSError: continue
        if "__init__.py" in nomi and any(n.startswith("_gi." + tag) for n in nomi): return os.path.dirname(d)
    return None


def prepara(cartelle_gi=CARTELLE_GI):
    """all'avvio del programma compilato (cli.main): sys.frozen, flussi standard, PyGObject del sistema su Linux"""
    from .piattaforma import sistema
    sys.frozen = True
    for nome in ("stdout", "stderr"):                        # Windows senza console: print() tace già, ma chi scrive su sys.stderr no
        if getattr(sys, nome) is None: setattr(sys, nome, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115  # resta aperto finché c'è il processo
    if sistema() == "linux" and not any(isinstance(f, SoloGi) for f in sys.meta_path):
        c = cartella_gi(cartelle_gi)
        if c: sys.meta_path.append(SoloGi(c))
