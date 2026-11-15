"""Base comune dei due server HTTP locali (schermata dei progetti ed editor): solo libreria standard."""
import socket
import sys
from http.server import ThreadingHTTPServer


class ServerLocale(ThreadingHTTPServer):
    """server su 127.0.0.1, un thread per richiesta. Su Windows niente SO_REUSEADDR: lì permetterebbe a due programmi di
    ascoltare sulla stessa porta (su macOS e Linux serve solo a riaprire subito una porta appena chiusa)."""
    daemon_threads = True
    allow_reuse_address = not sys.platform.startswith("win")


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
