"""Processi: come partono i figli (editor, script dei PSD), come si riavvia il programma, come si stacca dal terminale.

Ogni processo figlio, nostro o di altri (finestre di sistema, file manager, Photoshop, git, il browser), riceve l'ambiente
costruito da ambiente_figli: senza il gettone del server (VER-011). Solo i nostri riavvii lo ritrovano (riesegui, che sostituisce
il processo, e rilancia_dopo, che lo rimette in modo esplicito)."""
import os
import subprocess  # nosec B404  # processi lanciati solo con argomenti in lista, mai con la shell
import sys
import threading
import time
import webbrowser

from .. import compilato, giornale
from . import sistema

RILANCIO = "import subprocess, sys, time; time.sleep(float(sys.argv[1])); subprocess.Popen(sys.argv[2:])"


def cartella_pacchetto():
    """cartella che contiene il pacchetto impaginatore: è la cartella di lavoro dei processi figli lanciati con «python -m»
    (python mette la cartella di lavoro in testa a sys.path: dev'essere una cartella fidata, non quella di un progetto)"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ambiente_figli(env=None):
    """ambiente dei processi figli: testo sempre in UTF-8 (su Windows sarebbe cp1252) e uscita non bufferizzata nei registri.
    Senza il gettone di sessione di questo server (IMPAGINATORE_GETTONE): ogni server ha il suo (docs/architettura/SICUREZZA.md)"""
    e = dict(os.environ if env is None else env)
    e.pop("IMPAGINATORE_GETTONE", None)
    e["PYTHONUTF8"] = "1"; e["PYTHONIOENCODING"] = "utf-8"
    return e


_BROWSER = threading.Lock()


def apri_browser(url):
    """apre url nel browser predefinito. webbrowser non accetta un ambiente per il processo che lancia: il gettone si toglie
    da os.environ per il tempo del lancio e si rimette dopo (il browser non lo eredita, VER-011). Lo usa solo la schermata,
    che non si riavvia con os.execv (rilancia_dopo passa il gettone in modo esplicito)"""
    with _BROWSER:
        g = os.environ.pop("IMPAGINATORE_GETTONE", None)
        try: return webbrowser.open(url)
        finally:
            if g is not None: os.environ["IMPAGINATORE_GETTONE"] = g


def opzioni_staccato():
    """argomenti per Popen di un processo che deve sopravvivere a chi lo lancia"""
    if sistema() == "windows": return dict(creationflags=0x00000008 | 0x00000200, close_fds=True)       # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    return dict(start_new_session=True)


def riesegui(argv=None):
    """sostituisce il processo con una copia di se stesso (stessi argomenti): serve all'editor per rileggere le foto.
    Compilato: il programma stesso con gli argomenti che ha ricevuto (sys.orig_argv è quello dell'interprete)"""
    if argv is None: argv = [sys.executable, *sys.argv[1:]] if compilato.attivo() else sys.orig_argv
    argv = list(argv)
    if sistema() == "windows":                     # os.execv di Windows non mette tra virgolette gli argomenti con spazi
        argv = [subprocess.list2cmdline([a]) for a in argv]
    os.execv(sys.executable, argv)  # nosec B606  # riparte questo stesso Python (sys.executable) con i suoi argomenti


def rilancia_dopo(argv, ritardo=1.5, gettone=None):
    """fa ripartire il comando argv tra `ritardo` secondi, fuori da questo processo (che sta per chiudersi e liberare la porta);
    gettone: quello della sessione, che il programma rilanciato tiene (passa nell'ambiente, mai sulla riga di comando)"""
    env = ambiente_figli()
    if gettone: env["IMPAGINATORE_GETTONE"] = gettone
    aiutante = [sys.executable, "_rilancia"] if compilato.attivo() else [sys.executable, "-c", RILANCIO]          # compilato: lo stesso codice è rilancio()
    subprocess.Popen([*aiutante, str(ritardo), *argv], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,  # nosec B603  # questo stesso programma con il codice fisso RILANCIO (o rilancio()); argomenti in lista, senza shell: nessun dato passa da un interprete di comandi
                     cwd=cartella_pacchetto(), env=env, **opzioni_staccato())


def rilancio(argv):
    """il processo aiutante di rilancia_dopo nel programma compilato («impaginatore _rilancia <ritardo> <comando…>»): fa
    quello che fa RILANCIO da Python"""
    time.sleep(float(argv[0]))
    subprocess.Popen(argv[1:])  # nosec B603  # il comando del programma preparato da rilancia_dopo; argomenti in lista, senza shell
    return 0


def stacca(registro):
    """POSIX: doppio fork + nuova sessione, uscita nel file `registro`; il processo non muore quando si chiude l'app o il terminale
    che l'ha lanciato. Restituisce False dove non si può (Windows): allora si resta in primo piano."""
    if sistema() == "windows" or not hasattr(os, "fork"): return False
    if os.fork(): os._exit(0)
    os.setsid()
    if os.fork(): os._exit(0)
    fd = giornale.riservato(registro); dn = os.open(os.devnull, os.O_RDONLY)          # 0600: dentro ci sono percorsi e nomi (VER-013)
    os.dup2(dn, 0); os.dup2(fd, 1); os.dup2(fd, 2)
    return True
