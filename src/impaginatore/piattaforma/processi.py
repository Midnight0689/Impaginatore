"""Processi: come partono i figli (editor, script dei PSD), come si riavvia il programma, come si stacca dal terminale."""
import os
import subprocess  # nosec B404  # processi lanciati solo con argomenti in lista, mai con la shell
import sys

from . import sistema


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


def opzioni_staccato():
    """argomenti per Popen di un processo che deve sopravvivere a chi lo lancia"""
    if sistema() == "windows": return dict(creationflags=0x00000008 | 0x00000200, close_fds=True)       # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    return dict(start_new_session=True)


def riesegui(argv=None):
    """sostituisce il processo con una copia di se stesso (stessi argomenti): serve all'editor per rileggere le foto"""
    argv = list(sys.orig_argv if argv is None else argv)
    if sistema() == "windows":                     # os.execv di Windows non mette tra virgolette gli argomenti con spazi
        argv = [subprocess.list2cmdline([a]) for a in argv]
    os.execv(sys.executable, argv)  # nosec B606  # riparte questo stesso Python (sys.executable) con i suoi argomenti


def rilancia_dopo(argv, ritardo=1.5, gettone=None):
    """fa ripartire il comando argv tra `ritardo` secondi, fuori da questo processo (che sta per chiudersi e liberare la porta);
    gettone: quello della sessione, che il programma rilanciato tiene (passa nell'ambiente, mai sulla riga di comando)"""
    codice = "import subprocess, sys, time; time.sleep(float(sys.argv[1])); subprocess.Popen(sys.argv[2:])"
    env = ambiente_figli()
    if gettone: env["IMPAGINATORE_GETTONE"] = gettone
    subprocess.Popen([sys.executable, "-c", codice, str(ritardo), *argv], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,  # nosec B603  # questo stesso Python con il codice fisso qui sopra; argomenti in lista, senza shell: nessun dato passa da un interprete di comandi
                     cwd=cartella_pacchetto(), env=env, **opzioni_staccato())


def stacca(registro):
    """POSIX: doppio fork + nuova sessione, uscita nel file `registro`; il processo non muore quando si chiude l'app o il terminale
    che l'ha lanciato. Restituisce False dove non si può (Windows): allora si resta in primo piano."""
    if sistema() == "windows" or not hasattr(os, "fork"): return False
    if os.fork(): os._exit(0)
    os.setsid()
    if os.fork(): os._exit(0)
    fd = os.open(registro, os.O_WRONLY | os.O_CREAT | os.O_APPEND); dn = os.open(os.devnull, os.O_RDONLY)
    os.dup2(dn, 0); os.dup2(fd, 1); os.dup2(fd, 2)
    return True
