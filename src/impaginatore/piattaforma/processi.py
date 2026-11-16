"""Processi: come partono i figli (editor, script dei PSD), come si riavvia il programma, come si stacca dal terminale.

Ogni processo figlio, nostro o di altri (finestre di sistema, file manager, Photoshop, git, il browser), riceve l'ambiente
costruito da ambiente_figli: senza il gettone del server (VER-011). Solo i nostri riavvii lo ritrovano (riesegui, che sostituisce
il processo, e rilancia_dopo, che lo rimette in modo esplicito)."""
import os
import signal
import subprocess  # nosec B404  # processi lanciati solo con argomenti in lista, mai con la shell
import sys
import threading
import time
import webbrowser

from .. import giornale
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


# ---------------------------------------------------------------- processi dati dal pid
# Windows: diritti chiesti a OpenProcess, errore «accesso negato», risposta «non ancora finito» di WaitForSingleObject
_SYNCHRONIZE, _TERMINATE, _INFORMAZIONI = 0x00100000, 0x0001, 0x1000
_ACCESSO_NEGATO, _IN_FUNZIONE = 5, 0x102


def _kernel32():
    """(kernel32, ultimo errore) di Windows, con i tipi degli argomenti: gli handle sono puntatori, a 64 bit non stanno in un int"""
    import ctypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.argtypes, k.OpenProcess.restype = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32], ctypes.c_void_p
    k.WaitForSingleObject.argtypes, k.WaitForSingleObject.restype = [ctypes.c_void_p, ctypes.c_uint32], ctypes.c_uint32
    k.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    return k, ctypes.get_last_error


def vivo(pid):
    """il processo pid c'è ancora? True anche quando non si può sapere (pid che non è un numero positivo, processo di un altro
    utente): lo dirà chi prova a parlargli. Su Windows lo si chiede con OpenProcess: lì os.kill chiuderebbe il processo"""
    if type(pid) is not int or pid <= 0: return True
    if sistema() == "windows":
        k, ultimo_errore = _kernel32()
        h = k.OpenProcess(_SYNCHRONIZE | _INFORMAZIONI, False, pid)
        if not h: return ultimo_errore() == _ACCESSO_NEGATO                  # altrimenti (87) nessun processo ha quel pid
        try: return k.WaitForSingleObject(h, 0) == _IN_FUNZIONE
        finally: k.CloseHandle(h)
    try: os.kill(pid, 0)
    except ProcessLookupError: return False
    except OSError: return True                   # c'è ma è di un altro utente
    return True


class Processo:
    """un processo in funzione che non è figlio di chi lo segue, con la parte di Popen che usano la schermata dei progetti e la
    finestra del programma (pid, poll, terminate, kill, wait). Serve su Windows, dove l'editor che si riavvia (riesegui:
    os.execv) è un processo nuovo. Lì il processo resta aperto (handle) finché lo si segue: il suo pid non passa a un altro
    programma e terminate chiude proprio lui. Il codice di uscita non si conosce: un processo finito ha returncode 0"""

    def __init__(self, pid):
        self.pid, self.returncode, self._h = pid, None, None
        if sistema() == "windows":
            self._k = _kernel32()[0]
            self._h = self._k.OpenProcess(_SYNCHRONIZE | _TERMINATE | _INFORMAZIONI, False, pid)
            if not self._h: self.returncode = 0            # già finito, o di un altro utente: non si segue

    def _finito(self, attesa):
        """il processo è finito (aspettando al massimo `attesa` secondi)?"""
        if self._h: return self._k.WaitForSingleObject(self._h, int(attesa * 1000)) != _IN_FUNZIONE
        time.sleep(attesa)
        return not vivo(self.pid)

    def poll(self):
        if self.returncode is None and self._finito(0): self.returncode = 0
        return self.returncode

    def wait(self, timeout=None):
        fine = None if timeout is None else time.monotonic() + timeout
        while self.returncode is None:
            if self._finito(0.05): self.returncode = 0
            elif fine is not None and time.monotonic() > fine: raise subprocess.TimeoutExpired(f"pid {self.pid}", timeout)
        return self.returncode

    def _ferma(self, segnale):
        if self.poll() is not None: return
        if self._h: self._k.TerminateProcess(self._h, 1); return
        try: os.kill(self.pid, segnale)
        except ProcessLookupError: self.returncode = 0

    def terminate(self): self._ferma(signal.SIGTERM)

    def kill(self): self._ferma(getattr(signal, "SIGKILL", signal.SIGTERM))           # SIGKILL non c'è su Windows (lì si usa l'handle)

    def __del__(self):
        if self._h: self._k.CloseHandle(self._h); self._h = None


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
