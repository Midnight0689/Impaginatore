"""Base comune dei due server HTTP locali (schermata dei progetti ed editor): solo libreria standard.

ServerLocale ascolta su 127.0.0.1 e tiene il gettone di sessione del server; Gestore è la base dei gestori HTTP: ogni
richiesta passa dai controlli di sicurezza (Host, Origin, Sec-Fetch-Site, gettone, tipo e misura del corpo) prima di
arrivare a do_GET/do_POST, ogni risposta ha le intestazioni di sicurezza. Il progetto è in docs/architettura/SICUREZZA.md.
"""
import hashlib
import html
import json
import logging
import math
import os
import secrets
import socket
import sys
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import lingua, risorse, sicurezza

log = logging.getLogger("impaginatore.server")

def pagina_non_autorizzata():
    """pagina per chi apre l'indirizzo nudo, senza cookie (401): dice come aprire il programma, nella lingua in uso"""
    righe = "".join(f"<p>{html.escape(lingua.t(k))}</p>" for k in ("comune.non_collegata_1", "comune.non_collegata_2"))
    return (f"<!doctype html><html lang=\"{lingua.attuale()}\"><head><meta charset=\"utf-8\"><meta http-equiv=\"refresh\" content=\"5\"><title>Impaginatore</title></head>"
            "<body style=\"margin:0;padding:48px;background:#1b1b1d;color:#d0d0d6;font:15px/1.5 -apple-system,Segoe UI,sans-serif\">"
            f"<h1 style=\"font-size:20px\">Impaginatore</h1>{righe}</body></html>")


class ServerLocale(ThreadingHTTPServer):
    """server su 127.0.0.1, un thread per richiesta. Su Windows niente SO_REUSEADDR: lì permetterebbe a due programmi di
    ascoltare sulla stessa porta (su macOS e Linux serve solo a riaprire subito una porta appena chiusa).
    tipo ("home"/"editor"): scrive il file di sessione per i client locali fidati e lo toglie in server_close()."""
    daemon_threads = True
    allow_reuse_address = not sys.platform.startswith("win")

    def __init__(self, indirizzo, gestore, tipo=None, gettone=None, **info):
        super().__init__(indirizzo, gestore)
        self.sessione = sicurezza.Sessione(gettone); self.tipo = tipo
        if tipo: sicurezza.scrivi_sessione(tipo, self.server_address[1], self.sessione.gettone, **info)

    def indirizzo_avvio(self):
        """URL monouso che collega il browser a questo server (cookie) e apre la pagina"""
        return f"http://127.0.0.1:{self.server_address[1]}/avvio?c={self.sessione.codice()}"

    def server_close(self):
        super().server_close()
        if self.tipo: sicurezza.togli_sessione(self.tipo, self.server_address[1], self.sessione.gettone)


def porta_libera(porta):
    """la porta si può usare? Prova ad aprirla davvero (veloce anche su Windows, dove provare a collegarsi a una porta
    chiusa costa un paio di secondi); su macOS e Linux controlla anche che nessuno risponda, come le versioni 1.x (con
    SO_REUSEADDR il Mac lascerebbe aprire una porta già in ascolto su tutti gli indirizzi)"""
    with socket.socket() as s:
        if ServerLocale.allow_reuse_address: s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: s.bind(("127.0.0.1", porta))
        except OSError: return False
    if sys.platform.startswith("win"): return True
    with socket.socket() as s:
        s.settimeout(.2)
        return s.connect_ex(("127.0.0.1", porta)) != 0


class Rifiuto(Exception):
    """richiesta rifiutata dai controlli: codice HTTP e motivo"""

    def __init__(self, codice, motivo):
        super().__init__(motivo); self.codice = codice


STATICI = "/risorse/"                              # file statici delle pagine (risorse.statici), anche con il solo cookie


class Gestore(BaseHTTPRequestHandler):
    """base dei gestori HTTP. Le sottoclassi scrivono do_GET/do_POST e dicono in COOKIE/COOKIE_PREFISSI quali percorsi GET
    si aprono anche con il solo cookie (la pagina e le immagini, mai un percorso che dà il gettone o un URL di avvio:
    VER-006): tutto il resto vuole l'intestazione INTESTAZIONE con il gettone. /avvio (GET, codice monouso), /api/avvio
    (POST, nuovo URL di avvio) e i file statici /risorse/<nome> (GET, anche con il solo cookie) li gestisce questa base."""
    timeout = 60                                   # secondi di silenzio dopo cui si chiude la connessione (client lenti o fermi)
    COOKIE = ("/",)
    COOKIE_PREFISSI = ()
    _csp = None

    def log_message(self, *a): pass               # niente righe su stderr per ogni richiesta (i rifiuti vanno nel registro)

    # ------------------------------------------------------------ controlli
    def _origini(self):
        p = self.server.server_address[1]
        return (f"127.0.0.1:{p}", f"localhost:{p}")

    def _navigazione(self):
        m = self.headers.get("Sec-Fetch-Mode")
        return m == "navigate" if m else "text/html" in self.headers.get("Accept", "")

    def _cookie(self):
        try: c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        except cookies.CookieError: return None
        m = c.get(sicurezza.nome_cookie(self.server.server_address[1]))
        return m.value if m else None

    def controlla(self):
        """solleva Rifiuto se la richiesta non deve passare"""
        h, gettone = self.headers, self.server.sessione.gettone
        if (h.get("Host") or "").lower() not in self._origini(): raise Rifiuto(403, "indirizzo non valido")                   # DNS rebinding
        sito = h.get("Sec-Fetch-Site")
        if sito and sito not in (("same-origin", "same-site", "none") if self.command == "GET" and self._navigazione() else ("same-origin", "none")):
            raise Rifiuto(403, "richiesta da un altro sito")
        o = h.get("Origin")
        if o is not None and o.lower() not in {"http://" + x for x in self._origini()}: raise Rifiuto(403, "richiesta da un'altra origine")
        p = urlparse(self.path).path
        if self.command == "GET" and p in ("/avvio", "/favicon.ico"): return                       # il codice monouso si controlla nella risposta; l'icona non c'è
        if not sicurezza.uguali(h.get(sicurezza.INTESTAZIONE), gettone):
            if not (self.command == "GET" and (p in self.COOKIE or p.startswith(self.COOKIE_PREFISSI + (STATICI,)))
                    and sicurezza.uguali(self._cookie(), sicurezza.valore_cookie(gettone, self.server.server_address[1]))):
                raise Rifiuto(401, "non autorizzato")
        if self.command == "POST":
            if (h.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json": raise Rifiuto(415, "il corpo deve essere JSON")
            n = h.get("Content-Length")
            if h.get("Transfer-Encoding") or n is None or not (n.isascii() and n.isdigit()): raise Rifiuto(411, "manca la lunghezza del corpo")      # «²» è isdigit() ma non un numero (VER-012)
            if len(n) > 18 or int(n) > sicurezza.MAX_CORPO: raise Rifiuto(413, "richiesta troppo grande")

    def parse_request(self):
        if not super().parse_request(): return False
        try: self.controlla(); u = urlparse(self.path)
        except Rifiuto as r:
            log.info("richiesta rifiutata (%s %s): %s", r.codice, r, self.command)
            log.debug("richiesta rifiutata: percorso %s", urlparse(self.path).path)        # il percorso può contenere il nome di una foto: solo a DEBUG (VER-013)
            self.rifiuta(r.codice, str(r)); return False
        except ValueError as e:                    # richiesta malformata (percorso, intestazioni): risposta ordinata, mai una connessione chiusa (VER-012)
            log.info("richiesta non valida (%s): %s", type(e).__name__, self.command)
            self.rifiuta(400, "richiesta non valida"); return False
        if self.command == "GET" and u.path == "/avvio": self._avvio(parse_qs(u.query)); return False
        if self.command == "GET" and u.path == "/favicon.ico":                                     # il browser la chiede da solo: niente icona, niente errore
            self.send_response(204); self.send_header("Cache-Control", "max-age=86400"); self.end_headers(); return False
        if self.command == "GET" and u.path.startswith(STATICI): self.statico(u.path[len(STATICI):]); return False
        if self.command == "POST" and u.path == "/api/avvio":
            try: self.corpo()
            except ValueError as e: self.json({"errore": str(e)}, 400); return False
            self.json({"indirizzo": self.server.indirizzo_avvio()}); return False
        return True

    def rifiuta(self, codice, motivo):
        if codice == 401 and self.command == "GET" and self._navigazione(): self.risposta(pagina_non_autorizzata(), "text/html; charset=utf-8", codice)
        else: self.json({"errore": motivo}, codice)

    def _avvio(self, q):
        """codice valido: cookie (derivato, VER-006) e pagina che consegna il gettone alla scheda, poi apre /"""
        if not self.server.sessione.usa((q.get("c") or [""])[0]): self.rifiuta(401, "indirizzo di avvio non valido o già usato"); return
        porta, nonce = self.server.server_address[1], secrets.token_urlsafe(18); g = self.server.sessione.gettone
        b = sicurezza.pagina_avvio(g, nonce).encode("utf-8"); self._csp = sicurezza.csp(nonce)
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b)))
        self.send_header("Set-Cookie", f"{sicurezza.nome_cookie(porta)}={sicurezza.valore_cookie(g, porta)}; Path=/; HttpOnly; SameSite=Strict")
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)

    # ------------------------------------------------------------ risposte
    def end_headers(self):
        for k, v in sicurezza.INTESTAZIONI: self.send_header(k, v)
        self.send_header("Content-Security-Policy", self._csp or sicurezza.csp())          # pagine: quella con il nonce; il resto (JSON, immagini) niente script
        self._csp = None
        super().end_headers()

    def risposta(self, corpo, tipo, codice=200):
        """risposta semplice dei controlli e delle rotte comuni: corpo str"""
        corpo = corpo.encode("utf-8")
        self.send_response(codice); self.send_header("Content-Type", tipo); self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(corpo)

    def json(self, dati, codice=200): self.risposta(json.dumps(dati), "application/json", codice)

    def pagina(self, nome):
        """pagina HTML delle risorse con il nonce dello script, la lingua in uso e la tabella dei suoi testi in quella lingua;
        CSP stretta (SICUREZZA.md). Il gettone non c'è: la pagina lo prende dalla sessionStorage della scheda, dove l'ha
        lasciato l'URL di avvio (VER-006)"""
        nonce = secrets.token_urlsafe(18); lg, locale = lingua.per_pagina()
        testo = risorse.leggi(nome).decode("utf-8").replace("__NONCE__", nonce).replace("__LINGUA__", lg).replace("__LOCALE__", locale)
        testo = testo.replace("__TESTI__", risorse.testi_pagina(nome, lg))                  # per ultima: i testi non passano da altre sostituzioni
        self._csp = sicurezza.csp(nonce); b = testo.encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)

    def statico(self, nome):
        """file statico delle pagine (token della marca, caratteri, licenze dei caratteri): solo quelli di
        risorse.statici(), con l'impronta per non riscaricarli (304) finché non cambiano"""
        tipo = risorse.statici().get(nome)
        if tipo is None: self.json({"errore": "non trovato"}, 404); return
        b = risorse.leggi(os.path.join("statici", nome)); et = '"%s"' % hashlib.sha256(b).hexdigest()[:20]
        if self.headers.get("If-None-Match") == et:
            self.send_response(304); self.send_header("ETag", et); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", tipo); self.send_header("Content-Length", str(len(b)))
        self.send_header("ETag", et); self.send_header("Cache-Control", "no-cache"); self.end_headers(); self.wfile.write(b)

    def corpo(self):
        """corpo JSON della richiesta POST (un oggetto; {} se vuoto), letto con leggi_json. La misura l'ha già controllata controlla()"""
        d = leggi_json(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        if not isinstance(d, dict): raise ValueError("il corpo deve essere un oggetto JSON")
        return d


class RichiestaNonValida(ValueError):
    """parametro di una richiesta GET fuori misura o non numerico: i server rispondono 400"""


def _costante(v): raise ValueError(f"valore non ammesso nel JSON: {v}")


def _decimale(s):
    v = float(s)
    if not math.isfinite(v): raise ValueError(f"numero troppo grande nel JSON: {s[:20]}")
    return v


def leggi_json(dati):
    """JSON che arriva da una richiesta (corpo o parametro): niente NaN, Infinity né numeri che diventerebbero infiniti
    (1e400). Sono valori che nessun progetto può salvare: si rifiutano qui, prima di arrivare allo stato (VER-001).
    Errori: sempre ValueError"""
    try: return json.loads(dati, parse_constant=_costante, parse_float=_decimale)
    except RecursionError: raise ValueError("JSON troppo annidato") from None


def numero(q, nome, predefinito, minimo, massimo, intero=False):
    """parametro numerico di una richiesta GET (q = parse_qs): finito e riportato tra minimo e massimo (VER-014);
    un valore che non è un numero (o NaN, infinito) è una RichiestaNonValida"""
    t = (q.get(nome) or [str(predefinito)])[0]
    try: v = int(t) if intero else float(t)
    except ValueError: raise RichiestaNonValida(f"{nome}: non è un numero") from None
    if not math.isfinite(v): raise RichiestaNonValida(f"{nome}: non è un numero finito")
    return min(max(v, minimo), massimo)
