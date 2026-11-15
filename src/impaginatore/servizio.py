"""Base comune dei due server HTTP locali (schermata dei progetti ed editor): solo libreria standard.

ServerLocale ascolta su 127.0.0.1 e tiene il gettone di sessione del server; Gestore è la base dei gestori HTTP: ogni
richiesta passa dai controlli di sicurezza (Host, Origin, Sec-Fetch-Site, gettone, tipo e misura del corpo) prima di
arrivare a do_GET/do_POST, ogni risposta ha le intestazioni di sicurezza. Il progetto è in docs/architettura/SICUREZZA.md.
"""
import json
import logging
import secrets
import socket
import sys
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import risorse, sicurezza

log = logging.getLogger("impaginatore.server")

PAGINA_NON_AUTORIZZATA = ("<!doctype html><html lang=\"it\"><head><meta charset=\"utf-8\"><meta http-equiv=\"refresh\" content=\"5\"><title>Impaginatore</title></head>"
                          "<body style=\"margin:0;padding:48px;background:#1b1b1d;color:#d0d0d6;font:15px/1.5 -apple-system,Segoe UI,sans-serif\">"
                          "<h1 style=\"font-size:20px\">Impaginatore</h1><p>Questa scheda non è collegata al programma.</p>"
                          "<p>Apri Impaginatore dal suo collegamento (o un progetto dalla schermata dei progetti): l'indirizzo che si apre da lì "
                          "vale una volta sola e collega il browser. Se l'hai appena fatto, questa scheda si sistema da sola tra pochi secondi.</p></body></html>")


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


class Gestore(BaseHTTPRequestHandler):
    """base dei gestori HTTP. Le sottoclassi scrivono do_GET/do_POST e dicono in COOKIE/COOKIE_PREFISSI quali percorsi GET
    si aprono anche con il solo cookie (la pagina, le immagini, la navigazione): tutto il resto vuole l'intestazione
    INTESTAZIONE con il gettone. /avvio (GET, codice monouso) e /api/avvio (POST, nuovo URL di avvio) li gestisce questa base."""
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
            if not (self.command == "GET" and (p in self.COOKIE or p.startswith(self.COOKIE_PREFISSI)) and sicurezza.uguali(self._cookie(), gettone)):
                raise Rifiuto(401, "non autorizzato")
        if self.command == "POST":
            if (h.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json": raise Rifiuto(415, "il corpo deve essere JSON")
            n = h.get("Content-Length")
            if h.get("Transfer-Encoding") or n is None or not n.isdigit(): raise Rifiuto(411, "manca la lunghezza del corpo")
            if int(n) > sicurezza.MAX_CORPO: raise Rifiuto(413, "richiesta troppo grande")

    def parse_request(self):
        if not super().parse_request(): return False
        try: self.controlla()
        except Rifiuto as r:
            log.info("richiesta rifiutata (%s %s): %s %s", r.codice, r, self.command, urlparse(self.path).path)
            self.rifiuta(r.codice, str(r)); return False
        u = urlparse(self.path)
        if self.command == "GET" and u.path == "/avvio": self._avvio(parse_qs(u.query)); return False
        if self.command == "GET" and u.path == "/favicon.ico":                                     # il browser la chiede da solo: niente icona, niente errore
            self.send_response(204); self.send_header("Cache-Control", "max-age=86400"); self.end_headers(); return False
        if self.command == "POST" and u.path == "/api/avvio": self.corpo(); self.json({"indirizzo": self.server.indirizzo_avvio()}); return False
        return True

    def rifiuta(self, codice, motivo):
        if codice == 401 and self.command == "GET" and self._navigazione(): self.risposta(PAGINA_NON_AUTORIZZATA, "text/html; charset=utf-8", codice)
        else: self.json({"errore": motivo}, codice)

    def _avvio(self, q):
        if not self.server.sessione.usa((q.get("c") or [""])[0]): self.rifiuta(401, "indirizzo di avvio non valido o già usato"); return
        self.send_response(303); self.send_header("Location", "/")
        self.send_header("Set-Cookie", f"{sicurezza.nome_cookie(self.server.server_address[1])}={self.server.sessione.gettone}; Path=/; HttpOnly; SameSite=Strict")
        self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", "0"); self.end_headers()

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
        """pagina HTML delle risorse con il nonce dello script e il gettone per le fetch; CSP stretta (SICUREZZA.md)"""
        nonce = secrets.token_urlsafe(18)
        html = risorse.leggi(nome).decode("utf-8").replace("__NONCE__", nonce).replace("__GETTONE__", self.server.sessione.gettone)
        self._csp = sicurezza.csp(nonce); b = html.encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)

    def corpo(self):
        """corpo JSON della richiesta POST (un oggetto; {} se vuoto). La misura l'ha già controllata controlla()"""
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        if not isinstance(d, dict): raise ValueError("il corpo deve essere un oggetto JSON")
        return d
