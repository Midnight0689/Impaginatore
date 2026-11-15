"""Strato piattaforma: ogni sistema simulato cambiando sys.platform; i comandi esterni sono intercettati (non parte
nessuna finestra, nessun Finder, nessun Photoshop)."""
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
    (cfg / "user-dirs.dirs").write_text('XDG_DESKTOP_DIR="$HOME/Scrivania"\nXDG_DOCUMENTS_DIR="$HOME/Documents"\nXDG_PICTURES_DIR="$HOME"\n', encoding="utf-8")
    assert cartelle.scrivania() == str(casa / "Scrivania")
    assert dict(cartelle.cartelle_utente())["Immagini"] == str(casa / "Pictures"), "una voce uguale alla casa vale come assente"
    media = tmp_path / "media"; (media / "DISCO").mkdir(parents=True); (media / ".nascosto").mkdir()
    assert cartelle._sottocartelle(str(media)) == [("DISCO", str(media / "DISCO"))] and cartelle._sottocartelle(str(tmp_path / "no")) == []
    assert isinstance(cartelle.volumi(), list)
    sistema("mac"); assert isinstance(cartelle.volumi(), list)
    sistema("windows"); monkeypatch.setattr(cartelle.os.path, "isdir", lambda p: p in ("C:\\", "E:\\"))
    assert cartelle.volumi() == [("C:", "C:\\"), ("E:", "E:\\")]


def test_documenti_windows(sistema, casa, monkeypatch):
    sistema("windows")
    assert cartelle.documenti() == os.path.join(str(casa), "Documents")          # ctypes.windll non c'è: ripiego


def test_progetti_predefinita(monkeypatch, tmp_path):
    assert cartelle.progetti_predefinita() == os.environ["IMPAGINATORE_PROGETTI"]
    monkeypatch.delenv("IMPAGINATORE_PROGETTI")
    r = cartelle.radice_checkout()
    if r: assert cartelle.progetti_predefinita() == os.path.join(r, "Progetti")
    monkeypatch.setattr(cartelle, "radice_checkout", lambda: None)
    assert cartelle.progetti_predefinita() == os.path.join(cartelle.documenti(), "Impaginatore", "Progetti")


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
    assert 'tell application "Adobe Photoshop 2026" to do javascript (item 1 of argv)' in cmd and cmd[-1] == '$.evalFile(new File("/tmp/a b.jsx"))'
    assert photoshop.esegui_js('alert("x")') == "ok" and reg.cmd[-1][-1] == 'alert("x")' and "with timeout of 120 seconds" in reg.cmd[-1]


def test_photoshop_mac_niente_iniezione(sistema, tmp_path, monkeypatch, reg):
    """SEC-004: percorsi e codice non diventano mai testo dello script AppleScript; il percorso nel JavaScript è una stringa JSON"""
    sistema("mac"); monkeypatch.setattr(photoshop, "CARTELLA_APPLICAZIONI", str(tmp_path))
    (tmp_path / 'Adobe Photoshop 2026 "x"' / 'Adobe Photoshop 2026 "x".app').mkdir(parents=True)
    cattivo = '/tmp/a\'b" & (do shell script "touch /tmp/PWN") & "\'); app.system("touch /tmp/PWN2"); (\'.jsx'
    photoshop.esegui_jsx(cattivo, 60); cmd = reg.cmd[-1]
    assert not any("PWN" in a for a in cmd[:-1]), "il percorso è solo nell'ultimo argomento"
    assert 'tell application "Adobe Photoshop 2026 \\"x\\"" to do javascript (item 1 of argv)' in cmd, "nome dell'applicazione quotato"
    js = cmd[-1]; assert js.startswith("$.evalFile(new File(") and js.endswith("))")
    assert json.loads(js[len("$.evalFile(new File("):-2]) == cattivo, "nel JavaScript il percorso è una sola stringa"
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
    def fuori(cmd): return not any(nome in a for a in cmd[:-1])                           # il dato è solo nell'ultimo argomento
    p = "/progetti/" + nome
    sistema("mac"); azioni.cestina(p); cmd = reg.cmd[-1]; assert cmd[-1] == p and fuori(cmd)
    for tipo in ("cartella", "zip", "foto"):
        dialoghi.Mac()._scegli(tipo, nome); cmd = reg.cmd[-1]; assert cmd[-1] == nome and fuori(cmd)
    monkeypatch.setattr(photoshop, "CARTELLA_APPLICAZIONI", str(tmp_path)); (tmp_path / "Adobe Photoshop 2026" / "Adobe Photoshop 2026.app").mkdir(parents=True)
    photoshop.esegui_jsx(p + ".jsx", 60); cmd = reg.cmd[-1]
    assert fuori(cmd) and json.loads(cmd[-1][len("$.evalFile(new File("):-2]) == p + ".jsx", "nel JavaScript il percorso è un letterale JSON"
    sistema("windows"); azioni.cestina("C:/x/" + nome); cmd = reg.cmd[-1]
    assert not any(nome in a for a in cmd) and reg.kw[-1]["env"]["IMPAGINATORE_PERCORSO"].endswith(nome)


def test_dialoghi_mac_messaggio_come_argomento(reg):
    """SEC-004: il messaggio arriva ad AppleScript come argomento (on run argv), mai nel testo dello script"""
    cattivo = 'Scegli" & (do shell script "touch /tmp/PWN") & "'
    for tipo in ("cartella", "zip", "foto"):
        dialoghi.Mac()._scegli(tipo, cattivo); cmd = reg.cmd[-1]
        assert cmd[0] == "osascript" and cmd[-1] == cattivo and cmd[2].startswith("on run argv\n") and "PWN" not in cmd[2]
    assert '"public.png"' in cmd[2] and '"public.tiff"' in cmd[2], "anche PNG e TIFF"


# ---------------------------------------------------------------- azioni
def test_mostra_per_sistema(sistema, reg, monkeypatch, tmp_path):
    sistema("mac"); azioni.mostra("/a/b.jpg"); assert reg.cmd[-1] == ["open", "-R", "/a/b.jpg"]
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
    assert cmd[0] == "osascript" and cmd[-1] == cattivo and "on run argv" in cmd and not any("PWN" in a for a in cmd[:-1]), "SEC-004: il percorso è un argomento"
    cattivo = "C:/a/b'; Remove-Item -Recurse C:/ ; '"
    sistema("windows"); azioni.cestina(cattivo); cmd = reg.cmd[-1]
    assert cmd[0] == "powershell" and "SendToRecycleBin" in cmd[-1] and "$env:IMPAGINATORE_PERCORSO" in cmd[-1] and not any("Remove-Item" in a for a in cmd)
    assert reg.kw[-1]["env"]["IMPAGINATORE_PERCORSO"] == os.path.normpath(os.path.abspath(cattivo)), "il percorso passa dall'ambiente"
    sistema("linux"); monkeypatch.setattr(azioni.shutil, "which", lambda n: "/usr/bin/gio")
    azioni.cestina("/a/b"); assert reg.cmd[-1] == ["gio", "trash", "--", "/a/b"]
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
