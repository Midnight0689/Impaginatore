"""Prova della finestra vera (pywebview con WebKitGTK, sotto Xvfb). La lancia test_desktop.test_finestra_vera in un
processo a parte (pywebview vuole il thread principale e un processo suo):

    xvfb-run -a python tests/prova_finestra.py <cartella>

Avvia il programma come il comando «impaginatore» (home.server.main, senza --browser) e, da un thread, fa quello che farebbe
l'utente: aspetta la schermata dei progetti, apre un progetto nella stessa finestra (l'editor è un processo a parte),
prova a portare la finestra fuori dal programma, torna ai progetti, chiude la finestra. Il browser di sistema non si apre:
gli indirizzi che gli andrebbero si annotano. Stampa l'esito in JSON sull'ultima riga («ESITO {...}»)."""
import http.server
import json
import os
import shutil
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aiuti import crea_foto  # noqa: E402

RICHIESTE = []                                       # richieste arrivate al server che NON è del programma


class Altro(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        RICHIESTE.append(self.path); self.send_response(200); self.end_headers(); self.wfile.write(b"altro")

    def log_message(self, *a): pass


def attendi(cond, secondi=60):
    t = time.time() + secondi
    while time.time() < t:
        try:
            v = cond()
            if v: return v
        except Exception: pass
        time.sleep(.2)
    raise AssertionError("tempo scaduto")


def rispondi_al_dialogo(cartella, titoli):
    """quando compare la finestra di scelta GTK (aperta da pywebview), ne annota il titolo, va in `cartella` e preme Apri"""
    from gi.repository import GLib, Gtk

    def cerca():
        for t in Gtk.Window.list_toplevels():
            if isinstance(t, Gtk.FileChooserDialog) and t.get_visible():
                if t.get_current_folder() != cartella: t.set_current_folder(cartella); return True
                titoli.append(t.get_title()); t.response(Gtk.ResponseType.OK); return False
        return True
    GLib.timeout_add(200, cerca)


def finestre_mostrate():
    """[(titolo, larghezza)] delle finestre GTK mappate sullo schermo, lette nel thread di GTK"""
    from gi.repository import GLib, Gtk
    fatto, out = threading.Event(), []

    def leggi():
        out.extend((t.get_title(), t.get_allocated_width()) for t in Gtk.Window.list_toplevels() if t.get_mapped() and t.get_title())
        fatto.set(); return False
    GLib.idle_add(leggi); fatto.wait(10)
    return out


def gettone_nei_figli():
    """i processi del motore della finestra (figli di questo) hanno IMPAGINATORE_GETTONE nell'ambiente?"""
    out = []
    for d in os.listdir("/proc"):
        if not d.isdigit(): continue
        try:
            with open(f"/proc/{d}/stat") as f: ppid = int(f.read().rsplit(")", 1)[1].split()[1])
            if ppid != os.getpid(): continue
            with open(f"/proc/{d}/cmdline", "rb") as f: cmd = f.read().split(b"\0")[0].decode(errors="replace")
            with open(f"/proc/{d}/environ", "rb") as f: env = f.read().split(b"\0")
        except OSError: continue
        if "WebKit" in cmd: out.append(any(e.startswith(b"IMPAGINATORE_GETTONE=") for e in env))
    return out


def main(cartella):
    from impaginatore import desktop, sicurezza
    from impaginatore.desktop import finestra as F
    vero = desktop.motore

    def motore():                                        # senza motore la schermata aprirebbe il browser e non finirebbe più
        m = vero()
        if m is None:
            print("ESITO " + json.dumps({"saltato": "motore della finestra non disponibile (vedi il registro)"}), flush=True); os._exit(0)
        return m
    desktop.motore = motore
    from impaginatore.home import server as H
    from impaginatore.piattaforma import dialoghi, processi
    progetti = os.path.join(cartella, "Progetti")
    H.configura(progetti, 0)
    p = H.nuovo({"nome": "Finestra", "w": 30, "h": 30})
    for f in crea_foto(os.path.join(cartella, "foto"))[:3]: shutil.copy(f, os.path.join(p, "Foto"))
    altro = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Altro)                # un altro servizio di questo computer
    threading.Thread(target=altro.serve_forever, daemon=True).start()
    locale = f"http://127.0.0.1:{altro.server_address[1]}/"
    sito = "https://esempio.invalid/guida"
    aperti_fuori, esito = [], {}
    processi.apri_browser = aperti_fuori.append              # il browser di sistema: solo annotato
    carte = "document.querySelectorAll('#grid .riga').length"                 # righe degli album (la schermata Album è un elenco, non più a schede)

    def osserva():
        try:
            fin = attendi(lambda: F.ATTUALE[0] and F.ATTUALE[0].finestra and F.ATTUALE[0])
            w, hp = fin.finestra, fin.porta
            home = f"http://127.0.0.1:{hp}/"
            esito["home"] = attendi(lambda: w.get_current_url() == home and w.run_js(carte) == 1 and home)
            esito["gettone_home"] = w.run_js("(sessionStorage.getItem('impaginatore_gettone') || '').length")
            # dopo la schermata di avvio (480 × 300) la finestra del programma si vede davvero (mappata), e la schermata non c'è più
            try: esito["mostrate"] = attendi(lambda: (lambda v: v if [t for t, _ in v] == ["Impaginatore"] and v[0][1] > 480 else None)(finestre_mostrate()), 30)
            except AssertionError: esito["mostrate"] = finestre_mostrate()
            esito["titolo"] = w.title
            esito["gettone_ambiente"] = "IMPAGINATORE_GETTONE" in os.environ
            esito["gettone_figli"] = gettone_nei_figli()
            # finestra di scelta della schermata: quella di pywebview, sopra la finestra
            titoli = []; rispondi_al_dialogo(cartella, titoli)
            esito["scelta_home"] = dialoghi.scegli_cartella("Scegli la cartella di prova")
            esito["titolo_scelta_home"] = titoli
            # editor nella stessa finestra (processo a parte, porta sua, indirizzo di avvio monouso)
            w.run_js("openProject(LIST[0]); 0")
            esito["editor"] = attendi(lambda: (lambda u: u if u and not u.startswith(home) and u.endswith("/") else None)(w.get_current_url()), 120)
            attendi(lambda: w.run_js("S !== null && S.photos.length") == 3, 60)
            esito["gettone_editor"] = w.run_js("(sessionStorage.getItem('impaginatore_gettone') || '').length")
            # finestra di scelta dell'editor (processo a parte): la chiede alla schermata, che la apre nella finestra
            pe = int(esito["editor"].rsplit(":", 1)[1].strip("/"))
            titoli = []; rispondi_al_dialogo(cartella, titoli)
            esito["scelta_editor"] = sicurezza.chiedi(pe, "/api/pick", sicurezza.gettone_di("editor", pe), {"kind": "folder"}, timeout=60)["paths"]
            esito["titolo_scelta_editor"] = titoli
            # fuori dal programma: un altro servizio locale, un file, un sito, anche in una finestra nuova. (Non con
            # Window.load_url: pywebview azzera l'evento «loaded» prima di caricare e, se il filtro ferma il caricamento,
            # le chiamate che lo aspettano scadono. Il programma usa load_url solo verso le sue pagine)
            for i, u in enumerate((locale, "file:///etc/hostname", sito)):
                w.run_js(f"location.href = {json.dumps(u)}; 0"); time.sleep(1.5)
                esito[f"dopo_{i}"] = w.get_current_url()
            w.run_js(f"window.open({json.dumps(locale + 'blank')}, '_blank'); 0"); time.sleep(1.5)
            w.run_js(f"window.open({json.dumps(sito + '2')}, '_blank'); 0"); time.sleep(1.5)
            esito["dopo_blank"] = w.get_current_url()
            # ritorno ai progetti con il pulsante «Progetti» dell'editor
            w.run_js("vaiProgetti({preventDefault() {}}); 0")
            esito["ritorno"] = attendi(lambda: w.get_current_url() == home and w.run_js(carte) == 1 and home)
            esito["fuori"] = list(aperti_fuori)
            esito["richieste_altro"] = list(RICHIESTE)
        except Exception as e:
            esito["errore"] = repr(e)
        finally:
            F.ATTUALE[0].chiudi()

    threading.Thread(target=osserva, daemon=True).start()
    esito["rc"] = H.main(["--porta", "0", "--progetti", progetti])
    esito["editor_chiusi"] = [pr.poll() is not None for pr, _ in H.EDITORS.values()]
    esito["geometria"] = os.path.isfile(os.path.join(os.environ["IMPAGINATORE_DATI"], "finestra.json"))
    altro.shutdown()
    print("ESITO " + json.dumps(esito), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
