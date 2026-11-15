"""Estrazione sicura di un progetto da un file ZIP (Importa ZIP della schermata dei progetti).

Uno ZIP ricevuto da altri può essere costruito apposta. Prima di scrivere qualcosa si controlla tutto l'elenco:
    - percorsi: niente percorsi assoluti, lettere di unità (C:), «..», caratteri NUL, collegamenti simbolici (zip-slip):
      se ce n'è anche uno solo lo ZIP si rifiuta tutto
    - limiti: numero di file, dimensione totale estratta (e spazio libero sul disco), rapporto di compressione (bombe ZIP)
    - tipi: si estraggono solo i file che un progetto contiene (JSON, foto, testi; spec.py dei progetti 1.x, che si legge
      come dati e non si esegue mai); programmi, script e file nascosti si tralasciano (e si dice quanti)
Ogni file si scrive in modalità esclusiva (mai sopra un file esistente) contando i byte davvero estratti.
"""
import os
import re
import shutil
import stat
import zipfile

from .nomi import componente_valido
from .validazione import ErroreProgetto

MAX_FILE = 20000
MAX_TOTALE = 50 * 2**30                     # 50 GB: un album con migliaia di foto originali
RISERVA_DISCO = 2**30                       # spazio da lasciare libero dopo l'estrazione
MAX_RAPPORTO = 100                          # dimensione estratta / compressa di tutto lo ZIP (oltre 100 MB estratti)
MAX_RAPPORTO_FILE = 200                     # dello stesso, per un file oltre 1 MB
ESTENSIONI = (".json", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".heif", ".webp", ".txt")
SPEC = "spec.py"                            # impaginazione dei progetti 1.x: solo nella cartella del progetto
_NOTI_1X = {"album_libere.py", "testo.py", "vib_lut.npz"}           # copie del motore dei pacchetti 1.x: non servono
_UNITA = re.compile(r"^[A-Za-z]:")
_BLOCCO = 1 << 20


def _rifiuta(motivo):
    raise ErroreProgetto(f"Questo file ZIP non è sicuro da importare ({motivo}): non è stato estratto niente.")


def _parti(nome):
    """pezzi del percorso di un file nello ZIP; errore per i percorsi che potrebbero uscire dalla cartella di destinazione"""
    n = nome.replace("\\", "/")
    if "\x00" in n: _rifiuta("un nome contiene un carattere nullo")
    if n.startswith("/") or _UNITA.match(n): _rifiuta(f"percorso assoluto «{nome}»")
    parti = [p for p in n.split("/") if p not in ("", ".")]
    if ".." in parti: _rifiuta(f"percorso che esce dalla cartella «{nome}»")
    return parti


def _ammesso(parti):
    """True se il file va estratto: tipo previsto, nessun pezzo del percorso nascosto o non valido su uno dei tre sistemi"""
    if parti[0] == "__MACOSX" or any(p.startswith(".") or not componente_valido(p) for p in parti): return False
    nome = parti[-1].lower()
    if nome == SPEC: return len(parti) <= 2
    return nome.endswith(ESTENSIONI)


def _scegli(infos, avvisi):
    scelti, tralasciati, totale, compresso = [], 0, 0, 0
    for i in infos:
        parti = _parti(i.filename)
        tipo = stat.S_IFMT(i.external_attr >> 16)
        if tipo == stat.S_IFLNK: _rifiuta(f"collegamento simbolico «{i.filename}»")
        if i.is_dir() or not parti: continue
        if tipo not in (0, stat.S_IFREG) or i.flag_bits & 0x1 or not _ammesso(parti):
            if parti[-1] not in _NOTI_1X and not parti[-1].startswith(".") and parti[0] != "__MACOSX": tralasciati += 1
            continue
        if i.file_size > _BLOCCO and i.file_size > MAX_RAPPORTO_FILE * max(1, i.compress_size): _rifiuta(f"«{i.filename}» è compresso in modo anomalo")
        totale += i.file_size; compresso += i.compress_size
        scelti.append((i, parti))
    if totale > MAX_TOTALE: _rifiuta(f"estratto occuperebbe {totale // 2**30} GB")
    if totale > 100 * _BLOCCO and totale > MAX_RAPPORTO * max(1, compresso): _rifiuta("è compresso in modo anomalo")
    if tralasciati and avvisi is not None: avvisi.append(f"{tralasciati} file non previsti in un progetto (programmi, script o altro) non sono stati estratti")
    return scelti, totale


def estrai(zp, dest, avvisi=None):
    """estrae nella cartella `dest` (nuova o vuota) i file ammessi dello ZIP `zp`; restituisce i loro percorsi relativi.
    Errori: ErroreProgetto con un messaggio per l'utente (lo ZIP non sicuro non lascia niente in `dest`)"""
    try: z = zipfile.ZipFile(zp)
    except (zipfile.BadZipFile, OSError) as e: raise ErroreProgetto(f"Il file non è uno ZIP leggibile ({e})") from None
    with z:
        infos = z.infolist()
        if len(infos) > MAX_FILE: _rifiuta(f"contiene più di {MAX_FILE} file")
        scelti, totale = _scegli(infos, avvisi)
        os.makedirs(dest, exist_ok=True)
        if totale + RISERVA_DISCO > shutil.disk_usage(dest).free: raise ErroreProgetto(f"Non c'è abbastanza spazio sul disco per estrarre il progetto ({totale // 2**20} MB)")
        radice = os.path.realpath(dest); fatti = []
        try:
            for i, parti in scelti: fatti.append(_estrai_uno(z, i, parti, radice, avvisi))
        except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, NotImplementedError, EOFError) as e: raise ErroreProgetto(f"Il file ZIP è rovinato ({e})") from None
        return [f for f in fatti if f]


def _estrai_uno(z, info, parti, radice, avvisi):
    path = os.path.join(radice, *parti)
    if os.path.commonpath([radice, os.path.realpath(os.path.dirname(path))]) != radice: _rifiuta(f"percorso che esce dalla cartella «{info.filename}»")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try: fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0), 0o644)
    except FileExistsError:
        if avvisi is not None: avvisi.append(f"«{info.filename}» compare due volte: tenuto il primo")
        return None
    scritti = 0
    try:
        with os.fdopen(fd, "wb") as out, z.open(info) as src:
            while True:
                b = src.read(_BLOCCO)
                if not b: break
                scritti += len(b)
                if scritti > info.file_size: _rifiuta(f"«{info.filename}» è più grande di quanto dichiarato")
                out.write(b)
    except BaseException:
        os.remove(path); raise
    return "/".join(parti)
