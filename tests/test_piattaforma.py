"""Strato piattaforma: ogni sistema simulato cambiando sys.platform; i comandi esterni sono intercettati (non parte
nessuna finestra, nessun Finder, nessun Photoshop).

sys.platform si simula, os.path no: resta quello del computer che esegue i test (su Windows os.path.abspath("/a/b") è
«D:\\a\\b»). Dove il programma passa un percorso calcolato con os.path, l'atteso si calcola con lo stesso os.path: su macOS e
Linux è identico al percorso scritto nel test. I nomi che Windows non ammette su disco («"», a capo) si provano lì con
l'elenco del disco simulato, e restano veri file sugli altri sistemi."""
import json
import os
import subprocess
import sys
import types

import pytest

from impaginatore import piattaforma
from impaginatore.piattaforma import azioni, cartelle, dialoghi, font, photoshop, processi

SISTEMI = {"mac": "darwin", "windows": "win32", "linux": "linux"}


@pytest.fixture
def sistema(monkeypatch):
    def imposta(nome): monkeypatch.setattr(sys, "platform", SISTEMI[nome])
    return imposta


class Registro:
    """sostituisce subprocess.run / Popen e ricorda i comandi"""

    def __init__(self, rc=0, out=""):
        self.cmd = []; self.kw = []; self.rc = rc; self.out = out

    def run(self, cmd, *a, **k):
        self.cmd.append(list(cmd)); self.kw.append(k)
        o = self.out(cmd) if callable(self.out) else self.out
        return types.SimpleNamespace(returncode=self.rc, stdout=o if k.get("text") else o.encode(), stderr="" if k.get("text") else b"")

    def Popen(self, cmd, *a, **k):
        self.cmd.append(list(cmd)); return types.SimpleNamespace(pid=1)


@pytest.fixture
def reg(monkeypatch):
    r = Registro()
    monkeypatch.setattr(subprocess, "run", r.run); monkeypatch.setattr(subprocess, "Popen", r.Popen)
    return r


def test_sistema(sistema):
    for nome in SISTEMI:
        sistema(nome); assert piattaforma.sistema() == nome
    sistema("windows"); assert piattaforma.e_windows() and not piattaforma.e_mac() and not piattaforma.e_linux()
    sistema("mac"); assert piattaforma.e_mac()
    sistema("linux"); assert piattaforma.e_linux()


# ---------------------------------------------------------------- cartelle
def test_cartelle_per_sistema(sistema, casa, monkeypatch):
    monkeypatch.delenv("IMPAGINATORE_DATI"); monkeypatch.delenv("IMPAGINATORE_CACHE")
    sistema("mac")
    assert cartelle.dati_utente() == os.path.join(str(casa), "Library", "Application Support", "Impaginatore")
    assert cartelle.cache() == os.path.join(str(casa), "Library", "Caches", "Impaginatore")
    sistema("windows")
    assert cartelle.dati_utente() == os.path.join(os.environ["APPDATA"], "Impaginatore")
    assert cartelle.cache() == os.path.join(os.environ["LOCALAPPDATA"], "Impaginatore", "Cache")
    sistema("linux")
    assert cartelle.dati_utente() == os.path.join(os.environ["XDG_DATA_HOME"], "impaginatore")
    assert cartelle.cache() == os.path.join(os.environ["XDG_CACHE_HOME"], "impaginatore")
    monkeypatch.delenv("XDG_DATA_HOME")
    assert cartelle.dati_utente() == os.path.join(str(casa), ".local", "share", "impaginatore")
    monkeypatch.setenv("IMPAGINATORE_DATI", "~/altrove")
    assert cartelle.dati_utente() == os.path.join(str(casa), "altrove")


def test_migrazione_da_album_tools(casa):
    vecchio = casa / ".album-tools"; vecchio.mkdir(); (vecchio / "modelli_utente.json").write_text('[{"id": "a"}]', encoding="utf-8")
    p = cartelle.file_dati("modelli_utente.json")
    assert p.startswith(os.environ["IMPAGINATORE_DATI"]) and open(p, encoding="utf-8").read() == '[{"id": "a"}]'
    assert (vecchio / "modelli_utente.json").exists(), "l'originale resta dov'è"
    assert cartelle.file_dati("altro.json") == os.path.join(os.environ["IMPAGINATORE_DATI"], "altro.json")


def test_migrazione_cartella_non_scrivibile(casa, monkeypatch):
    vecchio = casa / ".album-tools"; vecchio.mkdir(); (vecchio / "x.json").write_text("1", encoding="utf-8")
    monkeypatch.setattr(cartelle.shutil, "copy2", lambda *a: (_ for _ in ()).throw(OSError("sola lettura")))
    assert cartelle.file_dati("x.json") == str(vecchio / "x.json")


def test_cartelle_utente_e_volumi(sistema, casa, tmp_path, monkeypatch):
    for d in ("Desktop", "Documents", "Pictures"): (casa / d).mkdir()
    sistema("mac")
    assert [n for n, _ in cartelle.cartelle_utente()] == ["Scrivania", "Documenti", "Immagini", "Home"]
    assert cartelle.scrivania() == str(casa / "Desktop") and cartelle.documenti() == str(casa / "Documents")
    sistema("linux")
    cfg = casa / ".config"; cfg.mkdir(); (casa / "Scrivania").mkdir()
    (cfg / "user-dirs.dirs").write_text('XDG_DESKTOP_DIR="$HOME//Scrivania/"\nXDG_DOCUMENTS_DIR="$HOME/Documents"\nXDG_PICTURES_DIR="$HOME"\n', encoding="utf-8")
    assert cartelle.scrivania() == str(casa / "Scrivania"), "percorso normalizzato (barre doppie e finali)"
    assert dict(cartelle.cartelle_utente())["Immagini"] == str(casa / "Pictures"), "una voce uguale alla casa vale come assente"
    for voce in ('"$HOME/"', '""'):
        (cfg / "user-dirs.dirs").write_text(f"XDG_PICTURES_DIR={voce}\n", encoding="utf-8")
        assert dict(cartelle.cartelle_utente())["Immagini"] == str(casa / "Pictures"), f"{voce}: come assente"
    media = tmp_path / "media"; (media / "DISCO").mkdir(parents=True); (media / ".nascosto").mkdir()
    assert cartelle._sottocartelle(str(media)) == [("DISCO", str(media / "DISCO"))] and cartelle._sottocartelle(str(tmp_path / "no")) == []
    assert isinstance(cartelle.volumi(), list)
    sistema("mac"); assert isinstance(cartelle.volumi(), list)
    sistema("windows"); monkeypatch.setattr(cartelle.os.path, "isdir", lambda p: p in ("C:\\", "E:\\"))
    assert cartelle.volumi() == [("C:", "C:\\"), ("E:", "E:\\")]


def test_documenti_windows(sistema, casa, monkeypatch):
    sistema("windows")
    assert cartelle.documenti() == os.path.join(str(casa), "Documents")          # ctypes.windll non c'è: ripiego
    import ctypes
    chieste = []

    def cartella_di_sistema(risposta, codice):
        def SHGetFolderPathW(hwnd, csidl, token, flags, buf):
            chieste.append(csidl); buf.value = risposta; return codice
        return types.SimpleNamespace(shell32=types.SimpleNamespace(SHGetFolderPathW=SHGetFolderPathW))
    monkeypatch.setattr(ctypes, "windll", cartella_di_sistema("D:\\OneDrive\\Documenti", 0), raising=False)
    assert cartelle.documenti() == "D:\\OneDrive\\Documenti", "la cartella Documenti che dice Windows (anche spostata su OneDrive)"
    monkeypatch.setattr(ctypes, "windll", cartella_di_sistema("", 0x80004005), raising=False)
    assert cartelle.documenti() == os.path.join(str(casa), "Documents") and chieste == [5, 5], "CSIDL_PERSONAL; se Windows non risponde: la predefinita"


def test_documenti_linux_dalle_cartelle_utente(sistema, casa):
    """su Linux la cartella Documenti è quella di ~/.config/user-dirs.dirs (con il nome nella lingua del sistema)"""
    sistema("linux"); (casa / ".config").mkdir()
    (casa / ".config" / "user-dirs.dirs").write_text('# commento\nXDG_DOCUMENTS_DIR="$HOME/Documenti"\n', encoding="utf-8")
    assert cartelle.documenti() == os.path.join(str(casa), "Documenti")


def test_progetti_predefinita(monkeypatch, tmp_path):
    assert cartelle.progetti_predefinita() == os.environ["IMPAGINATORE_PROGETTI"]
    monkeypatch.delenv("IMPAGINATORE_PROGETTI")
    r = cartelle.radice_checkout()
    if r: assert cartelle.progetti_predefinita() == os.path.join(r, "Progetti")
    monkeypatch.setattr(cartelle, "radice_checkout", lambda: None)
    assert cartelle.progetti_predefinita() == os.path.join(cartelle.documenti(), "Impaginatore", "Progetti")


def test_radice_checkout(tmp_path, monkeypatch):
    """il programma gira da un checkout (src/impaginatore con .git e pyproject.toml due cartelle sopra) o da un pacchetto installato"""
    radice = tmp_path / "repo"; pac = radice / "src" / "impaginatore" / "piattaforma"; pac.mkdir(parents=True)
    (radice / "pyproject.toml").write_text(""); (radice / ".git").mkdir()
    monkeypatch.setattr(cartelle, "__file__", str(pac / "cartelle.py"))
    assert cartelle.radice_checkout() == str(radice)
    monkeypatch.setattr(cartelle, "__file__", str(tmp_path / "site-packages" / "impaginatore" / "piattaforma" / "cartelle.py"))
    assert cartelle.radice_checkout() is None


# ---------------------------------------------------------------- font
def test_font_per_sistema(sistema, monkeypatch):
    sistema("mac")
    assert "/Library/Fonts" in font.cartelle_font() and font.font_ripiego()[0].endswith("Helvetica.ttc")
    assert font.serif_predefinito().endswith("Didot.ttc") and font.sans_predefinito().endswith("Avenir Next.ttc")
    sistema("windows"); monkeypatch.setenv("WINDIR", "C:\\Windows")
    assert font.cartelle_font()[0] == os.path.join("C:\\Windows", "Fonts") and font.font_ripiego()[0].endswith("arial.ttf")
    assert font.serif_predefinito().endswith("georgia.ttf") and font.sans_predefinito().endswith("segoeui.ttf")
    assert font.profilo_srgb() is None or font.profilo_srgb().endswith(".icm")
    sistema("linux")
    assert "/usr/share/fonts" in font.cartelle_font()
    p, idx = font.font_ripiego(); assert idx == 0 and (p is None or os.path.isfile(p))
    assert font.serif_predefinito() and font.sans_predefinito() and font.profilo_srgb() is None


def test_pil_ripiego(sistema, monkeypatch):
    sistema("linux")
    f = font.pil_ripiego(40); assert f.getlength("Ciao") > 0
    monkeypatch.setattr(font, "font_ripiego", lambda: ("/non/esiste.ttf", 0))
    assert font.pil_ripiego(40).getlength("Ciao") > 0, "font mancante: quello interno di Pillow"
    monkeypatch.setattr(font, "font_ripiego", lambda: (None, 0))
    assert font.pil_ripiego(12).getlength("Ciao") > 0


def test_font_mac_e_profili_colore(sistema, monkeypatch):
    """sul Mac il font di ripiego (Helvetica) si apre sempre, senza ripieghi; profilo sRGB del sistema dove c'è; su Linux un
    font che non c'è in nessuna cartella dà None"""
    from PIL import ImageFont
    aperti = []
    monkeypatch.setattr(ImageFont, "truetype", lambda p, size, index=0: aperti.append((p, size, index)) or "font")
    sistema("mac"); assert font.pil_ripiego(30) == "font" and aperti == [("/System/Library/Fonts/Helvetica.ttc", 30, 0)]
    monkeypatch.setattr(font.os.path, "isfile", lambda p: p.endswith(("sRGB Profile.icc", "sRGB Color Space Profile.icm")))
    assert font.profilo_srgb() == "/System/Library/ColorSync/Profiles/sRGB Profile.icc"
    sistema("windows"); monkeypatch.setenv("WINDIR", "C:\\Windows")
    assert font.profilo_srgb() == os.path.join("C:\\Windows", "System32", "spool", "drivers", "color", "sRGB Color Space Profile.icm")
    assert font._cerca_linux("NonEsiste-T104.ttf", "NemmenoQuesto-T104.otf") is None


# ---------------------------------------------------------------- photoshop
def test_photoshop_mac(sistema, tmp_path, monkeypatch, reg):
    sistema("mac"); monkeypatch.setattr(photoshop, "CARTELLA_APPLICAZIONI", str(tmp_path))
    assert photoshop.trova() is None and not photoshop.disponibile()
    assert "/Applications" in photoshop.motivo_assente()
    with pytest.raises(RuntimeError): photoshop.esegui_jsx("x.jsx")
    for v in ("2024", "2026"): (tmp_path / f"Adobe Photoshop {v}" / f"Adobe Photoshop {v}.app").mkdir(parents=True)
    assert photoshop.trova()["nome"] == "Adobe Photoshop 2026"
    reg.out = "ok"
    assert photoshop.esegui_jsx("/tmp/a b.jsx", 60) == "ok"
    cmd = reg.cmd[-1]
    assert cmd[0] == "osascript" and cmd[1:3] == ["-e", "on run argv"] and "with timeout of 60 seconds" in cmd
    assert 'tell application "Adobe Photoshop 2026" to do javascript (item 1 of argv)' in cmd and cmd[-1] == f"$.evalFile(new File({json.dumps(os.path.abspath('/tmp/a b.jsx'))}))"
    assert photoshop.esegui_js('alert("x")') == "ok" and reg.cmd[-1][-1] == 'alert("x")' and "with timeout of 120 seconds" in reg.cmd[-1]


def test_photoshop_mac_niente_iniezione(sistema, tmp_path, monkeypatch, reg):
    """SEC-004: percorsi e codice non diventano mai testo dello script AppleScript; il percorso nel JavaScript è una stringa JSON"""
    sistema("mac"); monkeypatch.setattr(photoshop, "CARTELLA_APPLICAZIONI", str(tmp_path))
    nome = 'Adobe Photoshop 2026 "x"'
    if os.name == "nt":                     # Windows non ammette «"» nei nomi: l'elenco di /Applications arriva come su macOS
        monkeypatch.setattr(photoshop.glob, "glob", lambda m: [os.path.join(str(tmp_path), nome, nome + ".app")] if "20*" in m else [])
    else: (tmp_path / nome / f"{nome}.app").mkdir(parents=True)
    cattivo = '/tmp/a\'b" & (do shell script "touch /tmp/PWN") & "\'); app.system("touch /tmp/PWN2"); (\'.jsx'
    photoshop.esegui_jsx(cattivo, 60); cmd = reg.cmd[-1]
    assert not any("PWN" in a for a in cmd[:-1]), "il percorso è solo nell'ultimo argomento"
    assert 'tell application "Adobe Photoshop 2026 \\"x\\"" to do javascript (item 1 of argv)' in cmd, "nome dell'applicazione quotato"
    js = cmd[-1]; assert js.startswith("$.evalFile(new File(") and js.endswith("))")
    assert json.loads(js[len("$.evalFile(new File("):-2]) == os.path.abspath(cattivo), "nel JavaScript il percorso è una sola stringa"
    assert photoshop.quota_applescript('a"b\\c') == '"a\\"b\\\\c"'


def test_photoshop_mac_beta(sistema, tmp_path, monkeypatch):
    sistema("mac"); monkeypatch.setattr(photoshop, "CARTELLA_APPLICAZIONI", str(tmp_path))
    (tmp_path / "Adobe Photoshop (Beta).app").mkdir(); assert photoshop.trova() is None
    (tmp_path / "Adobe Photoshop CC.app").mkdir(); assert photoshop.trova()["nome"] == "Adobe Photoshop CC"


def test_photoshop_windows(sistema, tmp_path, monkeypatch, reg):
    sistema("windows")
    for k in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"): monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    assert photoshop.trova() is None and "Programmi" in photoshop.motivo_assente()
    for v in ("Adobe Photoshop 2025", "Adobe Photoshop 2026", "Adobe Photoshop 2027 (Beta)"):
        d = tmp_path / "Adobe" / v; d.mkdir(parents=True); (d / "Photoshop.exe").write_bytes(b"")
    assert photoshop.trova()["nome"] == "Adobe Photoshop 2026"
    reg.out = "fatto"
    jsx = tmp_path / "s.jsx"; jsx.write_text("1", encoding="utf-8")
    assert photoshop.esegui_jsx(str(jsx)) == "fatto"
    assert reg.cmd[-1][0] == "cscript" and reg.cmd[-1][-1] == str(jsx)
    assert photoshop.esegui_js("app.documents.length") == "fatto"
    monkeypatch.delenv("ProgramFiles"); assert photoshop._programmi() == [r"C:\Program Files"]


def test_photoshop_linux(sistema):
    sistema("linux")
    assert photoshop.trova() is None and "Linux" in photoshop.motivo_assente()
    with pytest.raises(RuntimeError, match="Linux"): photoshop.esegui_js("1")


def test_motore_photoshop_si_ferma_senza(sistema, monkeypatch):
    from impaginatore.motore import photoshop as mps
    sistema("linux")
    with pytest.raises(SystemExit, match="Linux"): mps.app_name()
    with pytest.raises(SystemExit): mps.run_js("1")
    with pytest.raises(SystemExit): mps.run_jsx("x.jsx")
    monkeypatch.setattr(mps._ps, "trova", lambda: dict(nome="PS", percorso="x")); monkeypatch.setattr(mps._ps, "esegui_js", lambda c: "a.psd|true\nb.psd|false\nrumore")
    assert mps.open_documents() == [("a.psd", True), ("b.psd", False)]


def test_write_jsx_ascii(tmp_path):
    from impaginatore.motore import photoshop as mps
    p = tmp_path / "a.jsx"; mps.write_jsx(str(p), 'var s="àè·";')
    assert p.read_bytes() == b'var s="\\xe0\\xe8\\xb7";'


# ---------------------------------------------------------------- dialoghi
def test_dialoghi_predefiniti(sistema, monkeypatch):
    monkeypatch.delenv("IMPAGINATORE_DIALOGHI")
    sistema("mac"); assert isinstance(dialoghi.predefiniti(), dialoghi.Mac)
    sistema("windows"); assert isinstance(dialoghi.predefiniti(), (dialoghi.Tk, dialoghi.Nessuno))
    sistema("linux"); monkeypatch.delenv("DISPLAY", raising=False); monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(dialoghi.shutil, "which", lambda n: "/usr/bin/zenity" if n == "zenity" else None)
    assert isinstance(dialoghi.predefiniti(), dialoghi.Zenity)
    monkeypatch.setattr(dialoghi.shutil, "which", lambda n: "/usr/bin/kdialog" if n == "kdialog" else None)
    assert isinstance(dialoghi.predefiniti(), dialoghi.Kdialog)
    monkeypatch.setattr(dialoghi.shutil, "which", lambda n: None)
    assert isinstance(dialoghi.predefiniti(), dialoghi.Nessuno)
    monkeypatch.setenv("DISPLAY", ":99")
    assert isinstance(dialoghi.predefiniti(), (dialoghi.Tk, dialoghi.Nessuno))
    monkeypatch.setenv("IMPAGINATORE_DIALOGHI", "zenity"); assert isinstance(dialoghi.predefiniti(), dialoghi.Zenity)


@pytest.mark.parametrize("tk", [True, False])
def test_dialoghi_con_e_senza_tkinter(sistema, monkeypatch, tk):
    """Windows: le finestre di Tk se Python ha tkinter, altrimenti nessuna finestra (si scrive il percorso a mano); Linux con
    uno schermo: Tk, oppure zenity"""
    import importlib.util
    monkeypatch.delenv("IMPAGINATORE_DIALOGHI"); monkeypatch.setenv("DISPLAY", ":0")
    trova = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda n, *a: (trova("os") if tk else None) if n == "tkinter" else trova(n, *a))
    monkeypatch.setattr(dialoghi.shutil, "which", lambda n: "/usr/bin/zenity" if n == "zenity" else None)
    sistema("windows"); assert type(dialoghi.predefiniti()) is (dialoghi.Tk if tk else dialoghi.Nessuno)
    sistema("linux"); assert type(dialoghi.predefiniti()) is (dialoghi.Tk if tk else dialoghi.Zenity)


def test_dialoghi_aggancio():
    class Finti(dialoghi.Dialoghi):
        def _scegli(self, tipo, messaggio): return {"cartella": ["/a/b/"], "zip": ["/x.zip"], "foto": ["/1.jpg", "/2.jpg"]}[tipo]
    dialoghi.imposta(Finti())
    assert dialoghi.scegli_cartella() == "/a/b" and dialoghi.scegli_zip() == "/x.zip"
    assert dialoghi.scegli_percorsi() == ["/1.jpg", "/2.jpg"] and dialoghi.scegli_percorsi(cartella=True) == ["/a/b/"]
    dialoghi.imposta(None); assert isinstance(dialoghi.attuali(), dialoghi.Nessuno)
    assert dialoghi.scegli_cartella() == "" and dialoghi.scegli_zip() == "" and dialoghi.scegli_percorsi() == []
    with pytest.raises(NotImplementedError): dialoghi.Dialoghi()._scegli("zip", "")


def test_senza_barra():
    assert dialoghi.senza_barra("/a/b/") == "/a/b" and dialoghi.senza_barra("/") == "/" and dialoghi.senza_barra("C:\\") == "C:\\"
    assert dialoghi.senza_barra("C:\\Foto\\") == "C:\\Foto" and dialoghi.senza_barra("") == ""


@pytest.mark.parametrize("classe,uscita,atteso", [
    (dialoghi.Mac, "/Users/s/Foto/\n", ["/Users/s/Foto/"]),
    (dialoghi.Zenity, "/home/s/a.jpg\n/home/s/b.jpg\n", ["/home/s/a.jpg", "/home/s/b.jpg"]),
    (dialoghi.Kdialog, "/home/s/a.zip\n", ["/home/s/a.zip"]),
    (dialoghi.Tk, "/home/s/Foto\n", [os.path.normpath("/home/s/Foto")]),
])
def test_dialoghi_comandi(classe, uscita, atteso, reg):
    reg.out = uscita
    for tipo in ("cartella", "zip", "foto"):
        assert classe()._scegli(tipo, "Scegli") == atteso
    assert len(reg.cmd) == 3
    reg.rc = 1; assert classe()._scegli("foto", "Scegli") == [], "annullato"


NOMI_CATTIVI = ['a"b', "a'b", "a\\b", "$HOME $(touch /tmp/PWN) `id`", "Sposi àèìòù ñ ü", "riga\nnuova", 'x" & (do shell script "touch /tmp/PWN") & "']


@pytest.mark.parametrize("nome", NOMI_CATTIVI)
def test_dati_strani_mai_nel_testo_degli_script(sistema, reg, tmp_path, monkeypatch, nome):
    """SEC-004: virgolette, apici, barre rovesciate, $, accenti e a capo arrivano interi come argomento o variabile d'ambiente,
    mai dentro il testo di AppleScript, PowerShell o JavaScript"""
    def fuori(cmd, *dati): return not any(d in a for a in cmd[:-1] for d in (nome, *dati))          # il dato è solo nell'ultimo argomento
    p = "/progetti/" + nome; ap = os.path.abspath(p)                                      # ap == p su macOS e Linux
    sistema("mac"); azioni.cestina(p); cmd = reg.cmd[-1]; assert cmd[-1] == ap and fuori(cmd, ap)
    for tipo in ("cartella", "zip", "foto"):
        dialoghi.Mac()._scegli(tipo, nome); cmd = reg.cmd[-1]; assert cmd[-1] == nome and fuori(cmd)
    monkeypatch.setattr(photoshop, "CARTELLA_APPLICAZIONI", str(tmp_path)); (tmp_path / "Adobe Photoshop 2026" / "Adobe Photoshop 2026.app").mkdir(parents=True)
    photoshop.esegui_jsx(p + ".jsx", 60); cmd = reg.cmd[-1]
    assert fuori(cmd, ap) and json.loads(cmd[-1][len("$.evalFile(new File("):-2]) == os.path.abspath(p + ".jsx"), "nel JavaScript il percorso è un letterale JSON"
    sistema("windows"); azioni.cestina("C:/x/" + nome); cmd = reg.cmd[-1]; wp = os.path.normpath(os.path.abspath("C:/x/" + nome))
    assert not any(d in a for a in cmd for d in (nome, wp)) and reg.kw[-1]["env"]["IMPAGINATORE_PERCORSO"] == wp


def test_dialoghi_mac_messaggio_come_argomento(reg):
    """SEC-004: il messaggio arriva ad AppleScript come argomento (on run argv), mai nel testo dello script"""
    cattivo = 'Scegli" & (do shell script "touch /tmp/PWN") & "'
    for tipo in ("cartella", "zip", "foto"):
        dialoghi.Mac()._scegli(tipo, cattivo); cmd = reg.cmd[-1]
        assert cmd[0] == "osascript" and cmd[-1] == cattivo and cmd[2].startswith("on run argv\n") and "PWN" not in cmd[2]
    assert '"public.png"' in cmd[2] and '"public.tiff"' in cmd[2], "anche PNG e TIFF"


# ---------------------------------------------------------------- azioni
def test_mostra_per_sistema(sistema, reg, monkeypatch, tmp_path):
    sistema("mac"); azioni.mostra("/a/b.jpg"); assert reg.cmd[-1] == ["open", "-R", os.path.abspath("/a/b.jpg")]
    sistema("windows"); azioni.mostra("C:/a/b.jpg"); assert reg.cmd[-1][:2] == ["explorer", "/select,"]
    sistema("linux"); monkeypatch.setattr(azioni.shutil, "which", lambda n: "/usr/bin/" + n)
    azioni.mostra(str(tmp_path / "a b.jpg")); assert reg.cmd[-1][0] == "gdbus" and "a%20b.jpg" in " ".join(reg.cmd[-1])
    reg.rc = 1; azioni.mostra(str(tmp_path / "x.jpg")); assert reg.cmd[-1] == ["xdg-open", str(tmp_path)]
    azioni.mostra(str(tmp_path)); assert reg.cmd[-1] == ["xdg-open", str(tmp_path)]
    monkeypatch.setattr(azioni.shutil, "which", lambda n: None)
    with pytest.raises(OSError): azioni.mostra(str(tmp_path))


def test_cestina_per_sistema(sistema, reg, monkeypatch):
    cattivo = '/a/b" & (do shell script "touch /tmp/PWN") & "'
    sistema("mac"); azioni.cestina(cattivo); cmd = reg.cmd[-1]
    assert cmd[0] == "osascript" and cmd[-1] == os.path.abspath(cattivo) and "on run argv" in cmd and not any("PWN" in a for a in cmd[:-1]), "SEC-004: il percorso è un argomento"
    cattivo = "C:/a/b'; Remove-Item -Recurse C:/ ; '"
    sistema("windows"); azioni.cestina(cattivo); cmd = reg.cmd[-1]
    assert cmd[0] == "powershell" and "SendToRecycleBin" in cmd[-1] and "$env:IMPAGINATORE_PERCORSO" in cmd[-1] and not any("Remove-Item" in a for a in cmd)
    assert reg.kw[-1]["env"]["IMPAGINATORE_PERCORSO"] == os.path.normpath(os.path.abspath(cattivo)), "il percorso passa dall'ambiente"
    sistema("linux"); monkeypatch.setattr(azioni.shutil, "which", lambda n: "/usr/bin/gio")
    azioni.cestina("/a/b"); assert reg.cmd[-1] == ["gio", "trash", "--", os.path.abspath("/a/b")]
    reg.rc = 1; usati = []
    monkeypatch.setattr(azioni, "cestina_freedesktop", lambda p: usati.append(p))
    azioni.cestina("/a/c"); assert usati == ["/a/c"]


def test_cestino_freedesktop(tmp_path):
    cest = tmp_path / "Trash"
    for _ in range(2):
        d = tmp_path / "Progetto àè"; d.mkdir(); (d / "spec.py").write_text("x", encoding="utf-8")
        azioni.cestina_freedesktop(str(d), str(cest))
    assert sorted(os.listdir(cest / "files")) == ["Progetto àè", "Progetto àè.2"]
    info = (cest / "info" / "Progetto àè.2.trashinfo").read_text(encoding="utf-8")
    assert info.startswith("[Trash Info]\nPath=") and "Progetto%20%C3%A0%C3%A8" in info and "DeletionDate=" in info
    with pytest.raises(FileNotFoundError): azioni.cestina_freedesktop(str(tmp_path / "non-esiste"), str(cest))


def test_cestino_freedesktop_altro_disco(tmp_path, monkeypatch):
    d = tmp_path / "P"; d.mkdir()
    monkeypatch.setattr(azioni.os, "rename", lambda a, b: (_ for _ in ()).throw(OSError(18, "altro disco")))
    with pytest.raises(OSError): azioni.cestina_freedesktop(str(d), str(tmp_path / "T"))
    assert d.exists() and os.listdir(tmp_path / "T" / "info") == []


# ---------------------------------------------------------------- processi
def test_processi(sistema, monkeypatch, reg):
    e = processi.ambiente_figli({"A": "1"}); assert e == {"A": "1", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    assert os.path.isdir(os.path.join(processi.cartella_pacchetto(), "impaginatore"))
    sistema("windows"); assert processi.opzioni_staccato()["creationflags"] == 0x208 and not processi.stacca("x.log")
    sistema("linux"); assert processi.opzioni_staccato() == {"start_new_session": True}
    chiamate = []
    monkeypatch.setattr(processi.os, "execv", lambda exe, argv: chiamate.append((exe, argv)))
    processi.riesegui(["python", "-m", "impaginatore.editor", "--progetto", "/a b"])
    sistema("windows"); processi.riesegui(["python", "--progetto", "C:\\a b"])
    assert chiamate[0][1][-1] == "/a b" and chiamate[1][1][-1] == '"C:\\a b"', "su Windows execv non mette le virgolette"
    sistema("linux"); processi.rilancia_dopo(["python", "-m", "impaginatore"], 0.1)
    assert reg.cmd[-1][1] == "-c" and reg.cmd[-1][-3:] == ["python", "-m", "impaginatore"]


ORFANO = ("import subprocess, sys; p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'], stdin=subprocess.DEVNULL, "
          "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print(p.pid)")


def _orfano():
    """pid di un processo che dorme e non è figlio di chi esegue i test, come l'editor riavviato su Windows (os.execv lì
    avvia un processo nuovo): lo lancia un processo intermedio che finisce subito"""
    r = subprocess.run([sys.executable, "-c", ORFANO], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return int(r.stdout)


def test_processi_dati_dal_pid():
    """vivo e Processo su un processo che non è figlio di chi li usa, con le funzioni vere del sistema (su Windows OpenProcess)"""
    from aiuti import attendi
    assert processi.vivo(os.getpid()) and not processi.vivo(2**22 + 12345), "pid oltre quelli possibili: nessun processo"
    assert all(processi.vivo(x) for x in (None, True, 0, -1, "12")), "pid che non si può chiedere: lo dirà la richiesta"
    if os.name != "nt" and os.getuid() != 0: assert processi.vivo(1), "processo di un altro utente: c'è"
    morto = processi.Processo(2**22 + 12345); assert morto.poll() == 0 and morto.wait() == 0
    morto.terminate(); morto.kill()
    a, b = _orfano(), _orfano()
    pa, pb = processi.Processo(a), processi.Processo(b)
    try:
        assert processi.vivo(a) and pa.poll() is None and pa.pid == a
        with pytest.raises(subprocess.TimeoutExpired): pa.wait(0.2)
        pa.terminate(); assert pa.wait(20) == 0 and pa.poll() == 0
        assert attendi(lambda: not processi.vivo(a), 20), "finito anche per chi lo chiede di nuovo"
        pb.kill(); assert pb.wait(20) == 0
    finally:
        for p in (pa, pb):
            if p.poll() is None: p.kill()


def test_processo_finito_mentre_lo_si_ferma(sistema, monkeypatch):
    """macOS e Linux (simulati): il processo finisce tra poll e il segnale; nessun errore, e risulta finito"""
    sistema("linux")
    monkeypatch.setattr(processi, "vivo", lambda pid: True)
    monkeypatch.setattr(processi.os, "kill", lambda pid, segnale: (_ for _ in ()).throw(ProcessLookupError(pid)))
    p = processi.Processo(12345); assert p.poll() is None
    p.terminate(); assert p.returncode == 0


class Kernel32:
    """kernel32 finto: processi {pid: in funzione?}, errore di OpenProcess per i pid che non ci sono"""

    def __init__(self, processi, errore=87):
        self.processi, self.errore, self.aperti, self.chiusi, self.fermati, self.attese = processi, errore, [], [], [], []
        self.OpenProcess, self.WaitForSingleObject, self.TerminateProcess, self.CloseHandle = self.apri, self.aspetta, self.ferma, self.chiudi

    def apri(self, diritti, eredita, pid):
        if pid not in self.processi: return None
        self.aperti.append((diritti, eredita, pid)); return 1000 + pid

    def aspetta(self, h, ms):
        self.attese.append(ms); return 0x102 if self.processi[h - 1000] else 0

    def ferma(self, h, codice): self.fermati.append((h, codice)); self.processi[h - 1000] = False

    def chiudi(self, h): self.chiusi.append(h)


def test_processi_dati_dal_pid_su_windows(sistema, monkeypatch):
    """Windows (simulato): os.kill lì chiuderebbe il processo, si usano OpenProcess e WaitForSingleObject; il processo seguito
    resta aperto (handle) fino alla fine, e terminate/kill lo chiudono con TerminateProcess"""
    import ctypes
    k = Kernel32({7: True, 8: False, 9: True}); errore = [87]; vero = processi._kernel32
    monkeypatch.setattr(processi, "_kernel32", lambda: (k, lambda: errore[0]))
    monkeypatch.setattr(processi.os, "kill", lambda *a: pytest.fail("os.kill su Windows"))
    sistema("windows")
    assert processi.vivo(7) and not processi.vivo(8) and not processi.vivo(5), "87: nessun processo con quel pid"
    errore[0] = 5; assert processi.vivo(5), "accesso negato: c'è, di un altro utente"
    assert k.aperti[0] == (0x101000, False, 7) and k.chiusi == [1007, 1008] and k.attese == [0, 0]
    assert processi.Processo(5).poll() == 0, "non si apre: non si segue"
    p = processi.Processo(9); assert k.aperti[-1] == (0x101001, False, 9) and p.poll() is None
    with pytest.raises(subprocess.TimeoutExpired): p.wait(0.01)
    assert k.attese[-1] == 50
    p.terminate(); assert k.fermati == [(1009, 1)] and p.wait() == 0 and p.poll() == 0
    p.kill(); p.terminate(); assert k.fermati == [(1009, 1)], "già finito: niente da fermare"
    k.processi[9] = True; q = processi.Processo(9); q.kill(); assert k.fermati[-1] == (1009, 1)
    p.__del__(); p.__del__(); assert k.chiusi.count(1009) == 1, "l'handle si chiude una volta"
    dll = types.SimpleNamespace(**{n: types.SimpleNamespace() for n in ("OpenProcess", "WaitForSingleObject", "TerminateProcess", "CloseHandle")})
    caricate = []
    monkeypatch.setattr(ctypes, "WinDLL", lambda nome, use_last_error: caricate.append((nome, use_last_error)) or dll, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    kk, ultimo = vero()
    assert kk is dll and ultimo() == 5 and caricate == [("kernel32", True)]
    assert dll.OpenProcess.restype is ctypes.c_void_p and dll.WaitForSingleObject.argtypes == [ctypes.c_void_p, ctypes.c_uint32]
    assert dll.TerminateProcess.argtypes[0] is ctypes.c_void_p and dll.CloseHandle.argtypes == [ctypes.c_void_p], "handle a 64 bit"


STACCA = """import os, sys
from impaginatore.piattaforma import processi
sessione = os.getsid(0)
processi.stacca(sys.argv[1])
print("staccato", os.getsid(0) != sessione, sys.stdin.read() == "", flush=True)
"""


@pytest.mark.skipif(not hasattr(os, "fork"), reason="il doppio fork c'è solo su macOS e Linux")
def test_stacca_doppio_fork(tmp_path):
    """--daemon: il processo che l'ha lanciato finisce subito, quello che resta è in una sessione nuova, senza input e con
    l'uscita nel registro (non muore quando si chiude il terminale o l'app che l'ha lanciato)"""
    from aiuti import attendi
    registro = tmp_path / "impaginatore.log"
    r = subprocess.run([sys.executable, "-c", STACCA, str(registro)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout == "", r.stderr
    assert attendi(lambda: registro.exists() and registro.read_text()) == "staccato True True\n"


def test_porta_libera_su_windows(sistema):
    """su Windows basta aprire la porta (collegarsi a una porta chiusa lì costa secondi); una porta in uso resta occupata"""
    from impaginatore import servizio
    srv = servizio.ServerLocale(("127.0.0.1", 0), None); occupata = srv.server_address[1]
    try:
        sistema("windows"); assert not servizio.porta_libera(occupata)
    finally: srv.server_close()
    assert servizio.porta_libera(occupata)
