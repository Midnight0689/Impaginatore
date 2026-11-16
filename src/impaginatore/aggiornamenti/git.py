"""Aggiornamenti da un checkout git (come nelle versioni 1.x): GitHub è la fonte delle versioni.

- controlla: fetch + confronto con il ramo remoto, in sola lettura (mai pull da solo)
- aggiorna: pull --ff-only, reinstalla il pacchetto nell'ambiente Python in uso (le dipendenze possono essere cambiate), riavvia
- ripristina: rimette i file di una versione precedente CREANDO una nuova versione (la storia non si perde, gli altri
  computer la ricevono come un normale aggiornamento); si può tornare solo a versioni con questo stesso layout
  (src/impaginatore): le 1.x avevano un altro installatore e un'altra struttura
Il numero di rilascio di una versione si legge da src/impaginatore/__init__.py (__version__) o, per le 1.x, dal file VERSION.
"""
import os
import re
import shutil
import subprocess
import sys
import time

from ..piattaforma import processi
from . import Aggiornamenti

INIT = "src/impaginatore/__init__.py"


class Git(Aggiornamenti):
    def __init__(self, radice, riavvia=None):
        self.radice = radice
        self.riavvia = riavvia or (lambda: None)
        self.agg = dict(da_aggiornare=False, novita=[], controllato=0, errore="", disponibile=True, attuale=None, ultima=None)

    # ---------------------------------------------------------------- git
    def _git(self, *a, t=30):
        env = processi.ambiente_figli(dict(os.environ, GIT_TERMINAL_PROMPT="0"))          # senza il gettone (VER-011): git lancia hook e programmi esterni
        return subprocess.run(["git", "-C", self.radice, *a], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t, env=env)

    def rilascio(self, rif):
        """numero di rilascio (maggiore.minore.correzione) della versione rif"""
        r = self._git("show", f"{rif}:{INIT}")
        if r.returncode == 0:
            m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', r.stdout, re.M)
            if m: return m.group(1)
        return self._git("show", f"{rif}:VERSION").stdout.strip()

    def info(self, rif):
        """numero progressivo (commit), codice breve, data e titolo di una versione (rif = HEAD oppure @{u})"""
        try:
            n = self._git("rev-list", "--count", rif).stdout.strip()
            h, d, t = (self._git("log", "-1", "--pretty=%h|%cd|%s", "--date=format:%d/%m/%Y %H:%M", rif).stdout.strip().split("|", 2) + ["", ""])[:3]
            return dict(n=int(n), codice=h, data=d, titolo=t, rel=self.rilascio(rif))
        except Exception:
            return None

    # ---------------------------------------------------------------- interfaccia
    def stato(self):
        self.agg.update(attuale=self.info("HEAD"))
        return self.agg

    def controlla(self):
        try:
            self.agg.update(attuale=self.info("HEAD"))
            f = self._git("fetch", "-q", "origin")
            if f.returncode != 0: self.agg.update(errore=(f.stderr or "")[:200], controllato=time.time()); return self.agg
            n = self._git("log", "--pretty=%s", "HEAD..@{u}").stdout.strip().splitlines()
            self.agg.update(da_aggiornare=bool(n), novita=n[:12], ultima=self.info("@{u}"), controllato=time.time(), errore="")
        except Exception as e:
            self.agg.update(errore=str(e)[:200], controllato=time.time())
        return self.agg

    def versioni(self, k=20):
        out = self._git("log", f"-{k}", "--pretty=%h|%cd|%s", "--date=format:%d/%m/%Y %H:%M").stdout.strip().splitlines()
        tot = int(self._git("rev-list", "--count", "HEAD").stdout.strip() or 0)
        return [dict(n=tot - i, codice=r.split("|", 2)[0], data=r.split("|", 2)[1], titolo=r.split("|", 2)[2], attuale=i == 0) for i, r in enumerate(out)]

    def prepara_ambiente(self):
        """reinstalla il pacchetto (modalità modificabile) nell'ambiente Python in uso: prende le dipendenze nuove.
        Restituisce "" se è andata bene, altrimenti l'ultima riga dell'errore"""
        if shutil.which("uv"): cmd = ["uv", "pip", "install", "--python", sys.executable, "-q", "-e", self.radice]
        else: cmd = [sys.executable, "-m", "pip", "install", "-q", "-e", self.radice]
        try: r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, env=processi.ambiente_figli())
        except (OSError, subprocess.SubprocessError) as e: return str(e)[:200]
        return "" if r.returncode == 0 else ((r.stderr or r.stdout).strip().splitlines() or ["errore"])[-1][:200]

    def aggiorna(self):
        """pull + ambiente + riavvio del programma (i progetti sono già salvati: l'editor salva da solo)"""
        r = self._git("pull", "--ff-only", t=120)
        if r.returncode != 0: raise ValueError("Aggiornamento non riuscito: " + (r.stderr or r.stdout)[:300])
        self.prepara_ambiente()
        self.riavvia()
        return True

    def ripristina(self, codice):
        if not re.fullmatch(r"[0-9a-f]{7,40}", codice or ""): raise ValueError("versione non valida")
        if self._git("cat-file", "-e", f"{codice}:{INIT}").returncode != 0:
            raise ValueError("Questa versione è precedente alla 2.0 (altra struttura e altro installatore): non si può ripristinare da qui")
        if self._git("status", "--porcelain", "--untracked-files=no").stdout.strip(): raise ValueError("Ci sono modifiche del programma non ancora salvate: chiedi a Claude di salvarle prima")
        n = self._git("rev-list", "--count", codice).stdout.strip()
        if self._git("read-tree", "-u", "--reset", codice).returncode != 0: raise ValueError("Ripristino non riuscito")
        self._git("-c", "user.name=Impaginatore", "-c", "user.email=impaginatore@local", "commit", "-q", "--allow-empty", "-m", f"Ripristino alla versione {n} ({codice})")
        p = self._git("push", "-q", t=60)
        err = self.prepara_ambiente()
        if err: raise ValueError("Versione ripristinata, ma l'ambiente Python non è pronto (" + err + "). Il programma resta com'è: reinstallalo per sistemarlo.")
        self.riavvia()
        return dict(n=n, caricato=p.returncode == 0)
