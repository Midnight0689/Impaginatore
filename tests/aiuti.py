"""Strumenti comuni dei test: foto sintetiche, client HTTP, attese, script del motore nello stesso processo."""
import json
import os
import runpy
import sys
import time
import urllib.error
import urllib.request

from PIL import Image, ImageDraw

# le 10 foto dello scenario di parità con la 1.5.2 (stessi nomi, misure e date: i file in tests/dati/progetto_152 le usano)
FOTO_SCENARIO = [("H01", 900, 600, "2026:05:23 10:00:01"), ("H02", 900, 600, "2026:05:23 10:00:02"), ("V03", 600, 900, "2026:05:23 10:00:03"), ("V04", 600, 900, "2026:05:23 10:00:04"),
                 ("Q05", 700, 700, "2026:05:23 10:00:05"), ("H06", 1000, 560, "2026:05:23 10:00:06"), ("V07", 560, 1000, None), ("H08", 900, 600, None), ("Q09", 640, 640, "2026:05:23 10:00:09"),
                 ("V10", 600, 900, "2026:05:23 10:00:10")]


DATA_FILE = time.mktime((2026, 6, 1, 12, 0, 0, 0, 0, -1))     # data dei file sintetici (ora locale): è la data delle foto senza EXIF
P152 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dati", "progetto_152")


def progetto_152(cartella):
    """progetto.json dello scenario 1.5.2 (tests/dati/progetto_152) per l'album nella cartella data, con i percorsi
    «{PROGETTO}/Foto» e «{PROGETTO}/PSD» come li scrive il programma sul sistema che esegue i test (os.path.join: su
    Windows con «\\»)"""
    with open(os.path.join(P152, "progetto.json"), encoding="utf-8") as f: cfg = json.load(f)
    return {k: os.path.join(str(cartella), *v.split("/")[1:]) if isinstance(v, str) and v.startswith("{PROGETTO}/") else v for k, v in cfg.items()}


def crea_foto(cartella, elenco=FOTO_SCENARIO, orientamento=None, estensione=".jpg"):
    """JPEG sintetici (orizzontali, verticali, quadrati; con e senza data EXIF), tutti con data del file DATA_FILE.
    orientamento = {nome: valore EXIF 274}"""
    os.makedirs(cartella, exist_ok=True); out = []
    for k, (n, w, h, dt) in enumerate(elenco):
        im = Image.new("RGB", (w, h), (40 + 20 * k, 120, 200 - 15 * k)); d = ImageDraw.Draw(im)
        for j in range(8): d.rectangle([j * w // 8, 0, j * w // 8 + w // 16, h], fill=(200 - 20 * j, 60 + 15 * j, 90 + 10 * k))
        d.ellipse([w // 4, h // 4, 3 * w // 4, 3 * h // 4], fill=(230, 180 - 10 * k, 140)); d.line([0, h // 2, w, h // 2], fill=(255, 255, 255), width=6)
        ex = Image.Exif()
        if dt: ex.get_ifd(0x8769)[36867] = dt
        o = (orientamento or {}).get(n)
        if o: ex[274] = o
        p = os.path.join(cartella, n + estensione)
        im.save(p, "JPEG", quality=92, exif=ex.tobytes() if (dt or o) else b"")
        os.utime(p, (DATA_FILE, DATA_FILE))
        out.append(p)
    return out


class Client:
    """client JSON per i server locali (home ed editor), con il gettone della sessione del server (come la pagina)"""

    def __init__(self, porta, gettone):
        self.porta, self.gettone = porta, gettone

    def url(self, path): return f"http://127.0.0.1:{self.porta}{path}"

    def raw(self, path, body=None, timeout=120):
        h = {"Content-Type": "application/json", "X-Impaginatore-Gettone": self.gettone}
        r = urllib.request.Request(self.url(path), None if body is None else json.dumps(body).encode(), h)
        with urllib.request.urlopen(r, timeout=timeout) as f: return f.read()

    def get(self, path, timeout=120): return json.loads(self.raw(path, timeout=timeout))

    def post(self, path, body=None, timeout=120): return json.loads(self.raw(path, body if body is not None else {}, timeout=timeout))

    def codice(self, path, body=None, **intestazioni):
        """codice HTTP della risposta (GET, o POST con body), con intestazioni in più o cambiate (None = toglila)"""
        h = {"Content-Type": "application/json", "X-Impaginatore-Gettone": self.gettone}
        h.update(intestazioni); h = {k: v for k, v in h.items() if v is not None}
        r = urllib.request.Request(self.url(path), None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode()), h)
        try:
            with urllib.request.urlopen(r, timeout=120) as f: f.read(); return f.status
        except urllib.error.HTTPError as e: return e.code

    def prova(self, path, body=None):
        """(True, risposta) oppure (False, risposta d'errore) senza sollevare eccezioni HTTP"""
        try: return True, (self.post(path, body) if body is not None else self.get(path))
        except urllib.error.HTTPError as e:
            try: return False, json.load(e)
            except Exception: return False, {"errore": str(e)}


def come_script(monkeypatch, nome, *argv):
    """esegue impaginatore.motore.<nome> come «python -m» (con __name__ == "__main__") in questo processo, per gli script
    del motore che non hanno una main(). Il modulo non deve essere già importato: runpy ne eseguirebbe una seconda copia
    (RuntimeWarning «found in sys.modules», che pyproject.toml trasforma in errore). Gli script con una main() si provano
    chiamando main(argv); la riga «if __name__ == "__main__"» la provano i sottoprocessi veri (test_motore)."""
    modulo = f"impaginatore.motore.{nome}"
    assert modulo not in sys.modules, f"{modulo} è già importato: chiama la sua main() invece di eseguirlo come script"
    monkeypatch.setattr(sys, "argv", [nome, *argv])
    return runpy.run_module(modulo, run_name="__main__")


def attendi(cond, secondi=60, passo=0.1, spiega=None):
    """aspetta che cond() sia vera (un'eccezione conta come no). Se il tempo scade, il messaggio dice l'ultimo errore di
    cond e, con spiega, lo stato che spiega(): per esempio stato_processo, quando si aspetta un processo del programma"""
    t = time.time() + secondi; ultimo = None
    while time.time() < t:
        try:
            v = cond()
            if v: return v
        except Exception as e:
            ultimo = e
        time.sleep(passo)
    raise AssertionError(f"tempo scaduto (ultimo errore: {ultimo!r})" + (f"\n{spiega()}" if spiega else ""))


def coda(percorso, righe=40):
    """ultime righe di un file di registro"""
    try:
        with open(percorso, encoding="utf-8", errors="replace") as f: return "".join(f.readlines()[-righe:])
    except OSError as e: return f"({type(e).__name__}: {e})"


def stato_processo(tipo, porta, *registri):
    """perché un server del programma in un processo a parte (schermata o editor) non risponde come si aspettava: il suo file
    di sessione (senza il gettone; pid e genitore vivi o no), i file rimasti nella cartella delle sessioni (un .tmp è una
    sostituzione non riuscita), la coda dei registri dati e del registro del programma"""
    from impaginatore import sicurezza
    from impaginatore.piattaforma import processi
    s = sicurezza.leggi_sessione(tipo, porta)
    if s:
        s = {k: "..." if k == "gettone" else v for k, v in s.items()}
        s["vivi"] = {k: processi.vivo(s[k]) for k in ("pid", "genitore") if type(s.get(k)) is int}
    try: file = sorted(os.listdir(sicurezza.cartella_sessioni()))
    except OSError as e: file = repr(e)
    righe = [f"ora {time.time():.3f}; file di sessione {tipo}-{porta}: {s}", f"cartella delle sessioni: {file}"]
    for r in (*registri, os.path.join(os.environ.get("IMPAGINATORE_DATI", ""), "registro", "impaginatore.log")):
        righe += [f"--- {r}, ultime righe:", coda(r)]
    return "\n".join(righe)


def attendi_log(c, secondi=300):
    """aspetta la fine di un'esportazione dell'editor e restituisce il registro"""
    return attendi(lambda: (lambda L: L if "[finito]" in L else None)(c.get("/api/log")), secondi, 0.1)


def riduci(st):
    """parte dello stato dell'editor che non dipende dai font del sistema (i testi si misurano con i font installati)"""
    chiavi = ("k", "name", "side", "x", "y", "w", "h", "a", "bw", "z", "free", "bd", "sh", "oc", "ev", "evp", "rit", "tono", "crop", "cell", "box")
    return dict(nome=st["nome"], W=st["W"], H=st["H"], fold=st["fold"], gap=st["gap"], ppi=st["ppi"], globale=st["globale"], tolte=st["tolte"], unused=st["unused"],
                modules=st["modules"], photos=st["photos"],
                spreads=[dict(L=s["L"], R=s["R"], items=[{k: it.get(k) for k in chiavi} for it in s["items"] if it["k"] != "t"]) for s in st["spreads"]])


class Chiavi:
    """coppia di chiavi di firma delle licenze per una sessione di test (la privata nasce qui e sparisce con i test: quella di
    produzione non entra mai nel repository) e licenze IMP1- firmate con quella, nel formato di licenze/chiave.py"""

    def __init__(self, seme):
        from impaginatore import ed25519
        self.seme, self.pubblica = seme, ed25519.pubblica(seme)
        self.studio = self.chiave()

    def payload(self, fascia="studio", versione=2, computer=5, seriale=1, emessa="2026-11-01", intestatario="Studio Prova", flag=0, scadenza=None, id_firma=1, formato=None):
        import datetime as dt
        from impaginatore.licenze import chiave as K
        giorni = lambda d: (dt.date.fromisoformat(d) - K.EPOCA).days
        codice = {v: k for k, v in K.FASCE.items()}.get(fascia, fascia)
        nome = intestatario.encode("utf-8")
        coda = b"" if scadenza is None else giorni(scadenza).to_bytes(2, "big")
        formato = formato if formato is not None else (2 if scadenza is not None else 1)
        return bytes([formato, id_firma, codice, versione, computer, flag]) + seriale.to_bytes(4, "big") + giorni(emessa).to_bytes(2, "big") + bytes([len(nome)]) + nome + coda

    def firma(self, payload, seme=None):
        """testo IMP1- del payload firmato (con un altro seme: una firma che il programma non riconosce)"""
        from impaginatore import ed25519
        from impaginatore.licenze import chiave as K
        return K.in_testo(payload + ed25519.firma(seme or self.seme, K.DOMINIO_LICENZA + payload))

    def chiave(self, seme=None, **campi):
        return self.firma(self.payload(**campi), seme)

    def revoche(self, seriali, id_firma=1, seme=None, emessa="2026-11-16T10:00:00+00:00"):
        """elenco delle revoche firmato come lo scrive chiavi.py"""
        from impaginatore import ed25519
        from impaginatore.licenze import chiave as K
        corpo = {"formato": 1, "id_firma": id_firma, "emessa": emessa, "seriali": list(seriali)}
        corpo["firma"] = ed25519.firma(seme or self.seme, K.DOMINIO_REVOCHE + K.canonico(corpo)).hex()
        return corpo
