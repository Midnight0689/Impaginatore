"""Controllo automatico dei testi e delle grafiche del kit social.

Uso, dalla radice del repository:
    python3 marketing/social/strumenti/controlla_testi.py

Esce con 1 se trova errori; gli avvisi (segnaposto ancora vuoti, parti interne sospese) non bloccano.
Regole: brand/STYLEBOOK.md (parole, prezzi, tono), docs/mercato/tier.json (unica fonte dei prezzi),
marketing/social/STRATEGIA.md §6 (limiti dei canali) e §7 (cosa non fare). Solo libreria standard.

Testi pubblici controllati per intero: uscite (composte, in italiano e inglese), PROFILI.md, COPIONI.md, testo
visibile dei modelli HTML in ogni lingua. Documenti interni (STRATEGIA.md, README.md): solo importi e marchi.
In un file Markdown una parte interna si esclude fra <!-- controllo:sospeso motivo --> e <!-- controllo:ripreso -->.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import componi_testi as C  # noqa: E402
import genera_grafiche as G  # noqa: E402
import listino  # noqa: E402

SOCIAL = listino.SOCIAL
MODELLI = SOCIAL / "modelli"

# STYLEBOOK §§ 9-12 e marketing/email/strumenti/compila.py: parole che non usiamo.
VIETATE_IT = [
    r"rivoluzionari\w*", r"\bmagic[oaie]\b", r"\bmagia\b", r"in un (?:click|clic)\b", r"facilissim\w*", r"il migliore al mondo",
    r"imperdibil\w*", r"ultimi posti", r"potenziat\w* dall[’']\s?(?:ia|intelligenza)", r"l[’']\s?ia (?:crea|decide)",
    r"\bseamless\b", r"game.?changer", r"\bworkflow\b", r"\btemplate\b", r"\bsogn[oi]\b", r"\bfavol[ae]\b",
    r"il giorno più bello", r"\bemozion\w*", r"\bunic[oaie]\b", r"\b(?:il|la) prim[oa] (?:a |al mondo|in italia|programma|software)",
    r"obsolet\w*", r"supporto prioritario", r"(?<!senza )(?<!niente )(?<!nessun )\bcloud\b", r"\bIA\b", r"intelligenza artificiale",
]
VIETATE_EN = [
    r"\bmagic\w*", r"\beffortless\w*", r"\bstunning\b", r"\bunleash\w*", r"\belevate\w*", r"next.level", r"AI.powered",
    r"revolutionar\w*", r"lifetime deal", r"in seconds", r"\bseamless\w*", r"game.?changer", r"\bworkflow\b", r"\btemplates?\b",
    r"\bdream\w*", r"fairy.?tale", r"best in the world", r"\bunique\b", r"\bthe first\b", r"priority support", r"\bobsolete\b",
    r"\bAI\b",
]
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️⭐⬆↔-↪]")
SIGLE = {"ANFM", "JPG", "PDF", "PSD", "IVA", "VAT", "MCP", "FAQ", "CSV", "PNG", "HTML", "URL", "BCE", "ECB", "ICC", "RGB", "CMYK"}
MAIUSCOLE = re.compile(r"\b[A-ZÀ-Ý]{4,}\b")
BARRATO = re.compile(r"~~|<s>|<del>|line-through|invece di|anziché|instead of|prima costava|used to cost", re.I)
SCONTO_ORE = re.compile(r"rispar\w*|\bsconto\b|convien\w*|più ore compri|meno paghi|\bsave\b|saving|discount|cheaper", re.I)
MCP = re.compile(r"\bClaude\b|\bMCP\b|\bAnthropic\b")
# Nomi di concorrenti e laboratori (docs/mercato/competitor.md, prezzi.md): mai nei testi pubblici.
MARCHI = re.compile(
    r"SmartAlbums|Pixellu|\bFundy\b|DigiAlbum|AlbumTeller|AI Album Studio|Samaro|Pic-Time|AlbumStomp|Aftershoot|\bImagen\b|"
    r"Narrative Select|\bEvoto\b|ProSelect|\bZno\b|\bSaal\b|Graphi(?:studio|Designer|software)|Il Fotoalbum|Photocity|"
    r"Karizma|Maqueteer|Evolve Edits|Aurora ?Book|Recordia|Album ?Epoca|\bCewe\b", re.I)
PERCENTUALI = {"10"}  # unico sconto che i testi possono citare: il 10% del codice di segnalazione (PIANO-90-GIORNI §3.3)
GIORNI_EN = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MESI_EN = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
           "December")
GIORNI_VIETATI = {dt.date(2027, 3, 28): "Pasqua", dt.date(2027, 3, 29): "Pasquetta", dt.date(2027, 4, 25): "25 aprile"}
# Limiti per canale (STRATEGIA.md §6). Profili: (canale, tipo) → massimo di caratteri.
LIMITI_PROFILI = {
    ("instagram", "nome"): 30, ("instagram", "bio"): 150, ("facebook", "descrizione"): 255, ("youtube", "descrizione"): 1000,
    ("linkedin", "tagline"): 120, ("linkedin", "descrizione"): 2000, ("linkedin", "titolo-profilo"): 220,  # 220: [NV]
    ("tiktok", "bio"): 80, ("threads", "bio"): 150,
}
LIMITE_EVIDENZA = 15
LIMITI_USCITE = (("YouTube", 5000), ("LinkedIn", 3000), ("Threads", 500), ("TikTok", 2200), ("Instagram", 2200), ("Facebook", 63206))
MAX_HASHTAG = 5
MIN_USCITE_IT, MIN_USCITE_EN = 36, 10

errori: list[str] = []
avvisi: list[str] = []
info: list[str] = []


def errore(dove: str, msg: str) -> None:
    errori.append(f"{dove}: {msg}")


def normalizza(t: str) -> str:
    return t.replace(" ", " ").replace(" ", " ")


def senza_sospese(testo: str, dove: str) -> str:
    """Toglie le parti interne marcate e le annota fra le informazioni."""
    def via(m: re.Match) -> str:
        info.append(f"{dove}: parte interna esclusa dal controllo dei marchi ({m.group(1).strip()})")
        return ""
    testo = re.sub(r"<!--\s*controllo:sospeso(.*?)-->.*?<!--\s*controllo:ripreso\s*-->", via, testo, flags=re.S)
    if "controllo:sospeso" in testo:
        errore(dove, "«controllo:sospeso» senza «controllo:ripreso»")
    return testo


# --- controlli sul testo ------------------------------------------------------------------------------------------

def parole(testo: str, dove: str, lingua: str) -> None:
    for regola in (VIETATE_EN if lingua == "en" else VIETATE_IT):
        m = re.search(regola, testo, flags=0 if regola in (r"\bIA\b", r"\bAI\b") else re.I)
        if m:
            errore(dove, f"parola da non usare «{m.group(0)}» (STYLEBOOK)")
    if "!" in re.sub(r"<!--.*?-->|!\[", "", testo, flags=re.S):
        errore(dove, "punto esclamativo")
    m = EMOJI.search(testo)
    if m:
        errore(dove, f"emoji o simbolo «{m.group(0)}»")
    for parola in MAIUSCOLE.findall(re.sub(r"`[^`]*`", "", testo)):  # i nomi di file fra apici inversi non contano
        if parola not in SIGLE:
            errore(dove, f"parola in maiuscolo «{parola}»")


def importi(testo: str, dove: str, lingua: str = "it") -> list[float]:
    """Ogni importo in euro (e in dollari, per il confronto) deve stare nel listino o nel confronto di costanti.json."""
    t = normalizza(testo)
    ammessi = listino.importi_ammessi()
    c = listino.carica_costanti()
    confronto = {float(c[k]) for k in c if k.startswith("confronto.") and re.fullmatch(r"\d+(?:[.,]\d+)?", str(c[k]))}
    trovati: list[float] = []
    if lingua == "en":  # €1,234.50
        for m in re.finditer(r"€ ?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)", t):
            trovati.append(float(m.group(1).replace(",", "")))
    else:  # 1.234,50 €
        for m in re.finditer(r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?) ?€", t):
            trovati.append(float(m.group(1).replace(".", "").replace(",", ".")))
    dollari = [float(a or b) for a, b in re.findall(r"\$ ?(\d+)|(?<!\w)(\d+) ?\$", t)]
    for v in trovati:
        if v not in ammessi and v not in confronto:
            errore(dove, f"importo {v:g} € che non è nel listino {listino.carica_tier()['versione_listino']} né nel confronto")
    for v in dollari:
        if v not in confronto:
            errore(dove, f"importo {v:g} $ che non è nel confronto di costanti.json")
    return trovati


def c(testo: str, importo: str) -> bool:
    """Vero se l’importo compare intero (79 € sì, 179 € no)."""
    return re.search(rf"(?<![\d,.]){re.escape(importo)}(?![\d,])", testo) is not None


def prezzi(testo: str, dove: str, lingua: str, data: dt.date | None = None, frase_intera: bool = True) -> None:
    """Prezzo di lancio sempre con «fino al …, poi …», «una volta», IVA; niente barrati; ore senza sconti."""
    t = normalizza(testo)
    v = {k: normalizza(x) for k, x in listino.valori(lingua).items()}
    tier = listino.carica_tier()
    fine = dt.date.fromisoformat(listino.carica_costanti()["data.fine_lancio_iso"])
    ore = {float(p["prezzo_netto"]) for p in tier["assistenza"]["pacchetti"]}
    # Importi che sono solo prezzi di licenza (49 € è anche un’ora di assistenza: lì non si chiede «una volta»).
    solo_licenza = {float(f[k]) for f in tier["tiers"] for k in ("prezzo_netto", "prezzo_ivato", "prezzo_lancio", "prezzo_lancio_ivato")} - ore
    licenze = any(c(t, normalizza(listino.euro(x, lingua))) for x in solo_licenza)
    for f in tier["tiers"]:
        i = f["id"]
        if not re.search(rf"(?<![\d,.]){re.escape(v[f'{i}.lancio'])}(?![\d,])", t):
            continue
        licenze = True
        if data and data > fine:
            errore(dove, f"prezzo di lancio di {f['nome']} in un’uscita del {data:%d/%m}, dopo la fine del lancio")
        if frase_intera:
            if v[f"frase.{i}"] not in t:
                errore(dove, f"prezzo di lancio di {f['nome']} senza la frase «{v[f'frase.{i}']}»")
        elif v[f"{i}.listino"] not in t or v["data.fine_lancio"] not in t:
            errore(dove, f"prezzo di lancio di {f['nome']} senza il listino {v[f'{i}.listino']} e la data di fine lancio")
    if licenze:
        if not re.search(r"una volta|one-time|pay once", t, re.I):
            errore(dove, "prezzo di una licenza senza «una volta» / «one-time»")
        if not re.search(r"\bIVA\b|\bVAT\b", t):
            errore(dove, "prezzo di una licenza senza dire se l’IVA è inclusa")
    if BARRATO.search(t):
        errore(dove, f"prezzo barrato o confronto con un prezzo precedente («{BARRATO.search(t).group(0)}»)")
    for p in tier["assistenza"]["pacchetti"]:
        prezzo = normalizza(listino.euro(p["prezzo_netto"], lingua))
        for m in re.finditer(rf"(?<![\d,.]){re.escape(prezzo)}(?![\d,])", t):
            finestra = t[max(0, m.start() - 60): m.end() + 60]
            if p["ore"] > 1 and not re.search(rf"\b{p['ore']}[ -](?:ore|hours?)\b", finestra):
                if float(p["prezzo_netto"]) not in {float(f["prezzo_netto"]) for f in tier["tiers"]}:
                    errore(dove, f"{prezzo} senza dire che sono {p['ore']} ore")
    if any(re.search(rf"(?<![\d,.]){re.escape(normalizza(listino.euro(p['prezzo_netto'], lingua)))}(?![\d,])", t)
           for p in tier["assistenza"]["pacchetti"] if p["ore"] > 1):
        m = SCONTO_ORE.search(t)
        if m:
            errore(dove, f"pacchetti di ore presentati come risparmio («{m.group(0)}»)")
    if re.search(r"supporto prioritario|priority support", t, re.I):
        errore(dove, "«supporto prioritario»: le ore si vendono con la loro unità")


def marchi(testo: str, dove: str) -> None:
    for m in MARCHI.finditer(testo):
        errore(dove, f"nome di un concorrente o di un laboratorio «{m.group(0)}»")


def percentuali(testo: str, dove: str) -> None:
    for m in re.finditer(r"(\d+(?:,\d+)?)\s?%", normalizza(testo)):
        if m.group(1) not in PERCENTUALI:
            errore(dove, f"percentuale {m.group(1)}% non prevista")


def giorni_settimana(testo: str, dove: str) -> None:
    for m in re.finditer(r"\b(" + "|".join(C.GIORNI) + r")\s+(\d{1,2})\s+(" + "|".join(C.MESI) + r")(?:\s+(\d{4}))?", testo, re.I):
        anno = int(m.group(4) or 2027)
        d = dt.date(anno, C.MESI.index(m.group(3).lower()) + 1, int(m.group(2)))
        if C.GIORNI[d.weekday()] != m.group(1).lower():
            errore(dove, f"«{m.group(0)}»: il {d:%d/%m/%Y} è {C.GIORNI[d.weekday()]}")
    for m in re.finditer(r"\b(" + "|".join(GIORNI_EN) + r")\s+(\d{1,2})\s+(" + "|".join(MESI_EN) + r")(?:\s+(\d{4}))?", testo):
        anno = int(m.group(4) or 2027)
        d = dt.date(anno, MESI_EN.index(m.group(3)) + 1, int(m.group(2)))
        if GIORNI_EN[d.weekday()] != m.group(1):
            errore(dove, f"«{m.group(0)}»: {d:%d/%m/%Y} is a {GIORNI_EN[d.weekday()]}")


def segnaposto_vuoti(testo: str, dove: str) -> None:
    for k in listino.SEGNAPOSTO.findall(testo):
        avvisi.append(f"{dove}: segnaposto da riempire {{{{{k}}}}}")


def pubblico(testo: str, dove: str, lingua: str, data: dt.date | None = None, frase_intera: bool = True,
             mcp_ammesso: bool = False) -> None:
    parole(testo, dove, lingua)
    importi(testo, dove, lingua)
    prezzi(testo, dove, lingua, data, frase_intera)
    marchi(testo, dove)
    percentuali(testo, dove)
    giorni_settimana(testo, dove)
    if not mcp_ammesso and MCP.search(testo):
        errore(dove, f"«{MCP.search(testo).group(0)}» fuori dalla riserva MCP")


# --- uscite -------------------------------------------------------------------------------------------------------

def modelli_esistenti() -> set[str]:
    return {p.stem for p in MODELLI.glob("*.html")} | {p.stem for p in (MODELLI / "uscite").glob("*.html")}


def controlla_uscite() -> None:
    try:
        uscite = C.leggi_uscite()
    except ValueError as e:
        errore("sorgenti/uscite.txt", str(e))
        return
    nomi = modelli_esistenti()
    datate = [u for u in uscite if u["data"]]
    anticipato = dt.date(2027, 2, 21)
    for u in uscite:
        dove = f"uscita {u['id']}"
        try:
            testi = {lingua: C.componi(u, lingua) for lingua in ("it", "en") if u[lingua]}
            campi = " ".join(C.campo(u, k) for k in ("link", "cta", "note", "titolo"))
        except KeyError as e:
            errore(dove, str(e.args[0]))
            continue
        if not u["it"]:
            errore(dove, "manca il testo in italiano")
        if u["importante"] and not (u["en"] and u.get("titolo_en")):
            errore(dove, "uscita importante senza testo e titolo in inglese")
        if u["en"] and u.get("hashtag", "nessuno") != "nessuno" and not u.get("hashtag_en"):
            avvisi.append(f"{dove}: testo inglese con gli hashtag italiani (manca hashtag_en)")
        if u.get("pilastro") not in C.PILASTRI:
            errore(dove, f"pilastro sconosciuto «{u.get('pilastro')}»")
        for nome in re.split(r",\s*", re.sub(r"\([^)]*\)", "", u.get("modello", ""))):
            base = re.split(r"[ (]", nome.strip(), maxsplit=1)[0]
            if base and base not in ("nessuno", "da") and base not in nomi:
                errore(dove, f"modello inesistente «{base}»")
        for png in re.findall(r"grafiche/([\w./-]+?)\.png", u.get("grafica", "")):
            stem = re.sub(r"(-scuro)?(\.en)?$", "", png.split("/")[-1])
            if stem not in nomi:
                errore(dove, f"grafica «{png}.png» senza un modello che la generi")
        if u["mcp"]:
            if u["data"]:
                errore(dove, "uscita della riserva MCP con una data: si programma solo dopo il rilascio del server MCP")
            if "mcp-" not in u.get("grafica", ""):
                errore(dove, "grafica della riserva MCP senza il prefisso «mcp-»")
        else:
            d = u["data"]
            if d is None:
                errore(dove, "uscita senza data fuori dalla riserva MCP")
            elif d.weekday() == 5:
                errore(dove, f"di sabato ({d:%d/%m})")
            elif d in GIORNI_VIETATI:
                errore(dove, f"il giorno di {GIORNI_VIETATI[d]}")
            elif d.weekday() == 6 and d != anticipato:
                errore(dove, f"di domenica ({d:%d/%m}): solo l’accesso anticipato esce di domenica")
            if MCP.search(campi):
                errore(dove, f"«{MCP.search(campi).group(0)}» fuori dalla riserva MCP")
        for lingua, testo in testi.items():
            dl = f"{dove} ({lingua})"
            pubblico(testo, dl, lingua, u["data"], mcp_ammesso=u["mcp"])
            segnaposto_vuoti(testo, dl)
            canale = u.get("canale", "")
            limite = min((n for nome, n in LIMITI_USCITE if nome in canale), default=None)
            if limite and len(testo) > limite:
                errore(dl, f"{len(testo)} caratteri, il limite per {canale} è {limite}")
            hashtag = re.findall(r"(?<!\w)#\w+", testo)
            if len(hashtag) > MAX_HASHTAG:
                errore(dl, f"{len(hashtag)} hashtag, al massimo {MAX_HASHTAG}")
            if canale.startswith("Instagram") and "storia" not in u.get("formato", "") and re.search(r"https?://|\{\{(?:link_|sito)", testo):
                errore(dl, "un indirizzo in un testo di Instagram: lì i link non sono cliccabili, si scrive «link nella bio»")
        if "YouTube" in u.get("canale", "") and len(C.campo(u, "titolo")) > 100:
            errore(dove, "titolo del video oltre i 100 caratteri")
    n_it = sum(1 for u in datate if u["it"])
    n_en = sum(1 for u in datate if u["en"])
    if n_it < MIN_USCITE_IT:
        errore("calendario", f"{n_it} uscite con testo italiano, ne servono almeno {MIN_USCITE_IT}")
    if n_en < MIN_USCITE_EN:
        errore("calendario", f"{n_en} uscite anche in inglese, ne servono almeno {MIN_USCITE_EN}")
    if datate:
        giorni = (max(u["data"] for u in datate) - min(u["data"] for u in datate)).days
        info.append(f"calendario: {len(datate)} uscite con data in {giorni // 7 + 1} settimane, {n_en} anche in inglese, "
                    f"{len(uscite) - len(datate)} nella riserva MCP")
    # Il marcatore della riserva deve stare nei file composti, prima di ogni uscita MCP.
    cal = C.CALENDARIO_MD.read_text(encoding="utf-8") if C.CALENDARIO_MD.exists() else ""
    titolo = f"## Riserva MCP, {C.MARCATORE_MCP}"
    for u in uscite:
        if u["mcp"]:
            pos = cal.find(f"### {u['id']} ")
            if pos == -1 or cal.find(titolo) == -1 or cal.find(titolo) > pos:
                errore(f"CALENDARIO.md, {u['id']}", "uscita MCP fuori dalla sezione «Riserva MCP»")


# --- profili, copioni, documenti -----------------------------------------------------------------------------------

def controlla_profili() -> None:
    percorso = SOCIAL / "PROFILI.md"
    testo = senza_sospese(percorso.read_text(encoding="utf-8"), "PROFILI.md")
    campi = re.findall(r"<!--\s*campo canale=(\S+) tipo=(\S+) lingua=(\S+)\s*-->\s*```text\n(.*?)\n```", testo, flags=re.S)
    if len(campi) < 10:
        errore("PROFILI.md", f"solo {len(campi)} campi marcati")
    for canale, tipo, lingua, contenuto in campi:
        dove = f"PROFILI.md, {canale} {tipo} ({lingua})"
        if tipo == "evidenza":
            for riga in contenuto.splitlines():
                if len(riga) > LIMITE_EVIDENZA:
                    errore(dove, f"«{riga}» oltre {LIMITE_EVIDENZA} caratteri")
        elif (canale, tipo) in LIMITI_PROFILI:
            limite = LIMITI_PROFILI[(canale, tipo)]
            n = len(listino.sostituisci(contenuto, lingua))
            if n > limite:
                errore(dove, f"{n} caratteri, il limite è {limite}")
        else:
            errore(dove, "campo senza limite noto in LIMITI_PROFILI")
        pubblico(contenuto, dove, lingua)
        segnaposto_vuoti(listino.sostituisci(contenuto, lingua), dove)
    nome = re.search(r"Proposta: \*\*(\S+)\*\*", testo)
    if not nome or not 3 <= len(nome.group(1)) <= 24:
        errore("PROFILI.md", "nome utente proposto assente o fuori dai limiti (3–24 caratteri)")
    fuori = re.sub(r"```text\n.*?\n```", "", testo, flags=re.S)
    marchi(fuori, "PROFILI.md")
    if MCP.search(testo):
        errore("PROFILI.md", "Claude o MCP nei profili: si aggiungono solo dopo il rilascio del server MCP")


def controlla_copioni() -> None:
    testo = C.copioni_md()
    parti = re.split(r"^## ", testo, flags=re.M)
    pubblico(parti[0], "COPIONI.md, regole", "it")
    for parte in parti[1:]:
        dove = f"COPIONI.md, {parte.splitlines()[0][:40]}"
        pubblico(parte, dove, "it")
        durata = re.search(r"\((\d+) s\)", parte.splitlines()[0])
        if not durata or not 15 <= int(durata.group(1)) <= 45:
            errore(dove, "durata assente o fuori da 15–45 secondi")
    if len(parti) - 1 != 6:
        errore("COPIONI.md", f"{len(parti) - 1} copioni, ne servono 6")


def controlla_documenti() -> None:
    for nome in ("STRATEGIA.md", "README.md"):
        testo = senza_sospese((SOCIAL / nome).read_text(encoding="utf-8"), nome)
        importi(testo, nome)
        marchi(testo, nome)
    readme = (SOCIAL / "README.md").read_text(encoding="utf-8")
    for stem in sorted(modelli_esistenti()):
        if f"`{stem}`" not in readme and f"`uscite/{stem}`" not in readme and f" `{stem}` " not in readme:
            errore("README.md", f"il modello «{stem}» non è nell’indice dei modelli")


# --- modelli HTML ---------------------------------------------------------------------------------------------------

class TestoVisibile(HTMLParser):
    """Raccoglie il testo visibile di una lingua: salta testa, stili e gli elementi in un’altra lingua."""

    VUOTI = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self, lingua: str) -> None:
        super().__init__(convert_charrefs=True)
        self.lingua, self.pila, self.parti = lingua, [], []

    def handle_starttag(self, tag, attrs):
        if tag in self.VUOTI:
            if tag == "br":
                self.parti.append(" ")
            return
        a = dict(attrs)
        nascosto = tag in ("head", "style", "script", "title") or (a.get("lang") not in (None, self.lingua) and tag != "html")
        self.pila.append(nascosto)

    def handle_endtag(self, tag):
        if tag not in self.VUOTI and self.pila:
            self.pila.pop()
        self.parti.append(" ")

    def handle_data(self, data):
        if not any(self.pila):
            self.parti.append(data)

    def testo(self) -> str:
        return re.sub(r"\s+", " ", "".join(self.parti)).strip()


def controlla_modelli() -> None:
    for sorgente in G.modelli([]):
        html = sorgente.read_text(encoding="utf-8")
        nome = sorgente.relative_to(MODELLI).as_posix()
        mcp = G.meta(html, "mcp") == "sì"
        if mcp != sorgente.stem.startswith("mcp-"):
            errore(nome, "un modello della riserva MCP deve avere <meta name=\"mcp\" content=\"sì\"> e il nome che comincia con «mcp-»")
        if not G.meta(html, "uso"):
            errore(nome, "manca <meta name=\"uso\">")
        for lingua in G.meta(html, "lingue", "it").split():
            dove = f"{nome} ({lingua})"
            try:
                pronto, _ = G.prepara(html, sorgente, lingua, "chiaro")
            except KeyError as e:
                errore(dove, str(e.args[0]))
                continue
            p = TestoVisibile(lingua)
            p.feed(pronto)
            testo = p.testo()
            pubblico(testo, dove, lingua, frase_intera=False, mcp_ammesso=mcp)
            segnaposto_vuoti(testo, dove)
        if re.search(r"line-through|<s>|<del>", html):
            errore(nome, "prezzo barrato nel modello")


def controlla_composti() -> None:
    try:
        attesi = C.tutti()
    except (KeyError, ValueError) as e:
        errore("componi_testi.py", str(e))
        return
    for percorso, contenuto in attesi.items():
        if not percorso.exists() or percorso.read_text(encoding="utf-8") != contenuto:
            errore(percorso.name, "non aggiornato: python3 marketing/social/strumenti/componi_testi.py")


def main() -> int:
    controlla_composti()
    controlla_uscite()
    controlla_profili()
    controlla_copioni()
    controlla_documenti()
    controlla_modelli()
    vuoti = sorted({re.search(r"\{\{(.+?)\}\}", a).group(1) for a in avvisi if "segnaposto" in a})
    for riga in info:
        print(f"info    {riga}")
    altri = [a for a in avvisi if "segnaposto" not in a]
    for riga in altri:
        print(f"avviso  {riga}")
    if vuoti:
        print(f"avviso  {len([a for a in avvisi if 'segnaposto' in a])} segnaposto ancora vuoti, chiavi: {', '.join(vuoti)}")
    for riga in errori:
        print(f"ERRORE  {riga}")
    print(f"\n{len(errori)} errori, {len(altri) + (1 if vuoti else 0)} avvisi. Listino {listino.carica_tier()['versione_listino']}.")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
