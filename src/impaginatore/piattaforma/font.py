"""Font e profili colore che dipendono dal sistema.

Sul Mac il programma usa i font di sistema (Helvetica di ripiego, Didot e Avenir Next per i vecchi blocchi titolo);
su Windows e Linux ci sono equivalenti presenti di serie. Se un font manca del tutto si usa quello interno di Pillow:
il testo cambia aspetto ma il programma non si ferma.
"""
import functools
import glob
import os

from . import cartelle, sistema

_LINUX_FONT = ("/usr/share/fonts", "/usr/local/share/fonts")


def _windir():
    return os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\Windows"


def cartelle_font():
    """cartelle dove cercare i font installati (anche le sottocartelle)"""
    s = sistema()
    if s == "mac": return ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
    if s == "windows":
        return [os.path.join(_windir(), "Fonts"), os.path.join(os.environ.get("LOCALAPPDATA") or os.path.join(cartelle.home(), "AppData", "Local"), "Microsoft", "Windows", "Fonts")]
    return list(_LINUX_FONT) + [os.path.join(cartelle.home(), ".local", "share", "fonts"), os.path.join(cartelle.home(), ".fonts")]


def _primo(candidati):
    return next((c for c in candidati if os.path.isfile(c)), None)


@functools.lru_cache(maxsize=None)
def _cerca_linux(*nomi):
    for n in nomi:
        for d in _LINUX_FONT:
            trovati = sorted(glob.glob(os.path.join(d, "**", n), recursive=True))
            if trovati: return trovati[0]
    return None


def font_ripiego():
    """(file, indice) del font da usare quando quello chiesto non c'è; (None, 0) se il sistema non ne ha uno noto"""
    s = sistema()
    if s == "mac": return "/System/Library/Fonts/Helvetica.ttc", 0
    if s == "windows": return os.path.join(_windir(), "Fonts", "arial.ttf"), 0
    return _cerca_linux("DejaVuSans.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf", "FreeSans.ttf"), 0


def serif_predefinito():
    """font dei vecchi blocchi titolo (nome dell'album) quando progetto.json non ne indica uno"""
    s = sistema()
    if s == "mac": return "/System/Library/Fonts/Supplemental/Didot.ttc"
    if s == "windows": return os.path.join(_windir(), "Fonts", "georgia.ttf")
    return _cerca_linux("DejaVuSerif.ttf", "LiberationSerif-Regular.ttf", "NotoSerif-Regular.ttf") or "DejaVuSerif.ttf"


def sans_predefinito():
    """font dei vecchi blocchi titolo (sottotitolo e data)"""
    s = sistema()
    if s == "mac": return "/System/Library/Fonts/Avenir Next.ttc"
    if s == "windows": return os.path.join(_windir(), "Fonts", "segoeui.ttf")
    return _cerca_linux("DejaVuSans.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf") or "DejaVuSans.ttf"


def pil_ripiego(size):
    """font di Pillow alla misura chiesta: quello di ripiego del sistema o, se manca, quello interno di Pillow"""
    from PIL import ImageFont
    p, idx = font_ripiego()
    if sistema() == "mac": return ImageFont.truetype(p, size, index=idx)      # sul Mac c'è sempre: come nelle versioni 1.x
    try:
        if p: return ImageFont.truetype(p, size, index=idx)
    except OSError:
        pass
    return ImageFont.load_default(size)                                       # a misura da Pillow 10.1 (il pacchetto chiede la 13)


def profilo_srgb():
    """file del profilo sRGB IEC61966-2.1 del sistema (quello delle foto), o None: allora si usa quello interno di Pillow"""
    s = sistema()
    if s == "mac": c = ["/System/Library/ColorSync/Profiles/sRGB Profile.icc"]
    elif s == "windows": c = [os.path.join(_windir(), "System32", "spool", "drivers", "color", "sRGB Color Space Profile.icm")]
    else: c = []
    return _primo(c)
