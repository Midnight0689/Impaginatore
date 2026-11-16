#!/usr/bin/env python3
"""Release di Impaginatore (T-302, T-303): bozza nella pipeline, firma e pubblicazione sul computer di chi pubblica.

Il rilascio va in due tempi, perché la chiave privata dei rilasci non entra mai nella pipeline (sta fuori dal repository:
strumenti/aggiornamento.py, docs/architettura/AGGIORNAMENTI.md):

  1. la pipeline «Pacchetti» (.github/workflows/pacchetti.yml), su un tag v<versione>, costruisce e prova i pacchetti e
     con «bozza» crea la release di GitHub IN BOZZA: pacchetti verificati, impronte, componenti, wheel, verifiche.json;
  2. chi pubblica, sul suo computer, con «pubblica»: scarica la bozza, ricontrolla le impronte, firma il manifesto degli
     aggiornamenti con la chiave privata, lo carica con la firma e SHA256SUMS e pubblica la release.

    python strumenti/rilascio.py controlla
        cosa manca per un rilascio vero: chiavi pubbliche (licenze e aggiornamenti), repository delle release, versione
        finale, sezione della versione in CHANGELOG.md
    python strumenti/rilascio.py bozza CARTELLA_ARTEFATTI --tag v<v> --uscita DIR --note FILE --esito FILE [--esecuzione URL]
                                       [--repository PROPRIETARIO/NOME]
        (nella pipeline, senza chiavi) dagli artefatti scaricati del giro: controlla che la wheel sia della versione del
        tag, l'impronta (.sha256) e la prova (verifica-<chiave>.json) di ogni pacchetto e la prova del pacchetto Windows
        su Windows ARM; copia in DIR i pacchetti verificati (con .sha256 e .componenti.json), la wheel, SHA256SUMS e
        verifiche.json; scrive le note della bozza e l'esito (JSON: versione, prerelease, pacchetti, mancanti). Un
        pacchetto senza prova passata non entra e risulta fra i mancanti. Le note sono corte: pacchetti con dimensione e
        impronta, cosa manca, come controllare l'impronta, la guida (sul repository, alla versione del tag) e le voci del
        registro in una sezione ripiegata
    python strumenti/rilascio.py pubblica v<v> [--repo PROPRIETARIO/NOME] [--dir CHIAVI] [--id 1] [--novita-it "…"]
                                         [--novita-en "…"] [--senza CHIAVE] [--cartella DIR] [--prova] [--si]
        (sul computer di chi pubblica, con «gh» autenticato) scarica la release in bozza, ricontrolla impronte e prove,
        firma il manifesto con tutti i pacchetti, lo verifica, carica manifesto.json, manifesto.json.sig e SHA256SUMS
        completo, riscrive le note e pubblica: come pre-release se la versione è a/b/rc (non arriva agli aggiornamenti),
        altrimenti come ultima versione. Si ferma se manca qualcosa (controlla, chiave privata diversa da quella di
        CHIAVI_FIDATE, un sistema senza pacchetto: --senza CHIAVE per farne a meno di proposito). Chiede conferma prima di
        caricare (--si per non chiederla). --prova: fa tutto in --cartella ma non carica e non pubblica niente
    python strumenti/rilascio.py prepara CARTELLA_ARTEFATTI [--uscita dist/rilascio-<v>] [--dir CHIAVI] [--id 1]
                                         [--novita-it "…"] [--novita-en "…"] [--prova]
        come «pubblica», ma da una cartella di artefatti scaricati a mano e senza GitHub: copia, firma, SHA256SUMS e
        NOTE.md in --uscita (per caricarli a mano). --prova: va avanti anche se trova problemi (le note dicono in testa
        che è una prova e non va pubblicata)
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess  # nosec B404  # gh (GitHub CLI) di chi pubblica, con argomenti in lista
import sys
from pathlib import Path
from types import SimpleNamespace

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "src")); sys.path.insert(0, str(Path(__file__).resolve().parent))

import aggiornamento  # noqa: E402
import controlla_changelog  # noqa: E402

from impaginatore.aggiornamenti import firmati, lanciatore, rilascio, sorgenti  # noqa: E402
from impaginatore.licenze import chiave as chiave_licenze  # noqa: E402

SISTEMI = ("mac-arm64", "mac-x86_64", "windows", "linux", "linux-arm64")       # le chiavi di installazione.chiave_pacchetto()
ESTENSIONI = {"mac-arm64": "dmg", "mac-x86_64": "dmg", "windows": "exe", "linux": "deb", "linux-arm64": "deb"}
WINDOWS_ARM = "windows-arm64"          # la prova del pacchetto Windows x64 su Windows 11 ARM (job «windows-arm» della pipeline)
DESCRIZIONI = {"mac-arm64": "Mac con chip Apple (M1 e successivi)", "mac-x86_64": "Mac con processore Intel",
               "windows": "Windows 10 e 11 a 64 bit; anche Windows 11 sui PC con processore ARM, che lo esegue in emulazione",
               "linux": "Linux x86_64 (Ubuntu 24.04 e derivate)", "linux-arm64": "Linux arm64 (Ubuntu 24.04 e derivate)"}
GUIDA = "docs/manuale/00-installazione.md"
VERIFICHE = "verifiche.json"
SOMME = "SHA256SUMS"


def pre_release(versione):
    """versione da pre-release (a, b, rc, senza .dev)? Una pre-release di GitHub non arriva ai programmi installati: il
    controllo degli aggiornamenti legge solo l'ultima release pubblicata (releases/latest, AGGIORNAMENTI.md)"""
    k = lanciatore.chiave(versione)
    return k[3][0] in (0, 1, 2) and k[4][0] == 1


def problemi(versione, changelog=RADICE / "CHANGELOG.md", chiavi_aggiornamenti=None, chiavi_licenze=None, repository=None, pre=False):
    """motivi per cui la versione non si può pubblicare (vuoto = pronta). pre: come pre-release (beta), che gli
    aggiornamenti non vedono: basta una versione a, b o rc, il repository delle release può essere ancora vuoto e le note
    vengono da «[Non rilasciato]» se la sezione della versione non c'è"""
    out = list(firmati.problemi_per_il_rilascio(chiavi_aggiornamenti)) + list(chiave_licenze.problemi_per_il_rilascio(chiavi_licenze))
    if pre:
        if not pre_release(versione): out.append(f"la versione {versione} non è una pre-release (a, b o rc, senza .dev): una pre-release di GitHub vuole una versione così")
    else:
        if not (sorgenti.REPOSITORY if repository is None else repository): out.append("REPOSITORY in aggiornamenti/sorgenti.py è vuoto: i programmi non cercherebbero le versioni nuove")
        if lanciatore.di_sviluppo(versione): out.append(f"la versione {versione} è di sviluppo o di prova: per un rilascio serve una versione finale (src/impaginatore/__init__.py)")
    voci, errori = controlla_changelog.leggi(str(changelog))
    if errori: out.append(f"CHANGELOG.md non è in forma: {errori[0]}")
    if not pre and not any(v.get("versione", "").startswith(f"[{versione}]") for v in voci): out.append(f"CHANGELOG.md non ha la sezione «## [{versione}]»")
    return out


def trova(cartella, versione):
    """(wheel, {sistema: pacchetto}) della versione nella cartella degli artefatti"""
    tutti = [p for p in Path(cartella).rglob("*") if p.is_file()]
    ruote = [p for p in tutti if p.name == f"impaginatore-{versione}-py3-none-any.whl"]
    if len(ruote) != 1: raise SystemExit(f"Serve una e una sola wheel impaginatore-{versione}-py3-none-any.whl in {cartella} (trovate {len(ruote)}): «uv build --wheel»")
    pacchetti = {}
    for s in SISTEMI:
        trovati = [p for p in tutti if p.name == f"Impaginatore-{versione}-{s}.{ESTENSIONI[s]}"]
        if len(trovati) > 1: raise SystemExit(f"Più pacchetti {s} in {cartella}: {trovati}")
        if trovati: pacchetti[s] = trovati[0]
    altri = sorted({p.name for p in tutti if re.fullmatch(r"Impaginatore-.+\.(dmg|exe|deb)", p.name)} - {p.name for p in pacchetti.values()})
    if altri: raise SystemExit(f"Pacchetti di un'altra versione (questa è la {versione}): {altri}")
    if not pacchetti: raise SystemExit(f"Nessun pacchetto Impaginatore-{versione}-… in {cartella}")
    return ruote[0], pacchetti


def sezione_changelog(versione, changelog=RADICE / "CHANGELOG.md"):
    """le righe della sezione «## [versione]» di CHANGELOG.md (o di «[Non rilasciato]» se non c'è ancora)"""
    righe, dentro, out = changelog.read_text(encoding="utf-8").splitlines(), False, []
    for nome in (f"[{versione}]", "[Non rilasciato]"):
        for r in righe:
            if r.startswith("## "): dentro = r[3:].strip().startswith(nome)
            elif dentro: out.append(r)
        if out: return out
    return out


def impronta(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def impronta_scritta(p):
    """l'impronta del file p scritta accanto a lui (<p>.sha256, formato di sha256sum), o None"""
    s = Path(f"{p}.sha256")
    if not s.is_file(): return None
    m = re.fullmatch(r"([0-9a-f]{64})  (\S+)\s*", s.read_text(encoding="utf-8"))
    return m.group(1) if m and m.group(2) == Path(p).name else None


def leggi_json(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError): return None


def riassunto_verifica(r):
    """quello che resta, nella release, del rapporto di verifica_pacchetto.py: esito, sistema, architetture, controlli"""
    m = r.get("misure") or {}
    return dict(esito=r.get("esito"), sistema=r.get("sistema_descrizione"), macchina=m.get("macchina") or r.get("macchina"),
                eseguibile=m.get("eseguibile_architettura"), macos_minimo=m.get("macos_minimo"),
                controlli={c["nome"]: c["esito"] for c in r.get("controlli", []) if isinstance(c, dict) and "nome" in c})


def megabyte(byte):
    return f"{byte / 1e6:.1f}".replace(".", ",") + " MB"


def tabella_sistemi(pacchetti, impronte, componenti=None):
    """righe Markdown: per ogni sistema il file da scaricare (con la versione minima di macOS dei pacchetti per Mac), la
    dimensione e l'impronta SHA-256. pacchetti: {sistema: percorso}; impronte: righe «impronta  nome» di SHA256SUMS"""
    per_nome = {nome: h for h, _, nome in (r.partition("  ") for r in impronte)}
    t = ["| Sistema | File | Dimensione | SHA-256 |", "|---|---|---|---|"]
    for k in SISTEMI:
        if k not in pacchetti: continue
        p = Path(pacchetti[k]); minimo = ((componenti or {}).get(k) or {}).get("macos_minimo")
        t.append(f"| {DESCRIZIONI[k]}{f', macOS {minimo} o successivo' if minimo else ''} | `{p.name}` | {megabyte(p.stat().st_size)} | `{per_nome.get(p.name) or impronta(p)}` |")
    return t


def note(versione, impronte, problemi_trovati, mancanti, changelog=RADICE / "CHANGELOG.md", pacchetti=None, componenti=None, testa=None, guida=None):
    """note della release, corte: pacchetti con dimensione e impronta, cosa manca, come controllare l'impronta, la guida;
    le voci del registro in una sezione ripiegata. guida: indirizzo della guida di installazione (altrimenti il percorso)"""
    t = list(testa or [])
    if problemi_trovati: t += ["> **PROVA: NON PUBBLICARE.** Mancano:", *[f"> - {p}" for p in problemi_trovati], ""]
    t += [f"# Impaginatore {versione}", ""]
    if pacchetti: t += [*tabella_sistemi(pacchetti, impronte, componenti), ""]
    if mancanti: t += [f"Questa versione non ha il pacchetto per: {', '.join(mancanti)}.", ""]
    t += ["**Prima di installare** controlla l'impronta SHA-256 del file scaricato: deve essere identica a quella della tabella "
          f"(le stesse impronte, con quelle degli altri file, sono in `{SOMME}`).", "",
          "- macOS (Terminale): `shasum -a 256 <file>`",
          "- Windows (PowerShell): `Get-FileHash <file> -Algorithm SHA256`",
          f"- Linux: `sha256sum <file>`, oppure `sha256sum -c {SOMME} --ignore-missing` nella cartella dei file scaricati", "",
          f"Come si installa, sistema per sistema: {f'[guida di installazione]({guida})' if guida else f'`{GUIDA}`'}. I pacchetti non sono firmati con un "
          "certificato Apple o Microsoft: al primo avvio macOS e Windows mostrano un avviso, e la guida spiega cosa fare.", ""]
    voci = [r for r in sezione_changelog(versione, changelog) if r.strip()]
    if voci: t += ["<details>", f"<summary>Novità: le voci del registro (CHANGELOG.md, {sum(1 for r in voci if r.startswith('- '))})</summary>", "", *voci, "", "</details>", ""]
    return "\n".join(t)


def indirizzo_guida(repo, tag):
    """la guida di installazione alla versione del tag, sul repository (None se il repository non si sa)"""
    return f"https://github.com/{repo}/blob/{tag}/{GUIDA}" if repo else None


# ---------------------------------------------------------------- controlla
def cmd_controlla(a):
    from impaginatore import __version__
    p = problemi(__version__)
    for x in p: print(f"- {x}")
    print("Pronta per il rilascio." if not p else f"Versione {__version__}: {len(p)} cose da sistemare prima di un rilascio.")
    return 0 if not p else 1


# ---------------------------------------------------------------- bozza (pipeline)
def versione_del_tag(tag):
    if not (tag.startswith("v") and lanciatore.valida(tag[1:])): raise SystemExit(f"Il tag {tag} non è v<versione> (per esempio v2.0.1 o v2.0.1rc1)")
    return tag[1:]


def cmd_bozza(a):
    """i file della release in bozza dagli artefatti del giro della pipeline, senza chiavi"""
    versione = versione_del_tag(a.tag)
    ruote = list(Path(a.artefatti).rglob("impaginatore-*-py3-none-any.whl"))
    if len(ruote) != 1 or rilascio.versione_del_pacchetto(str(ruote[0])) != versione:
        raise SystemExit(f"Serve la wheel della versione {versione} del tag {a.tag} negli artefatti (trovate: {[p.name for p in ruote]})")
    wheel, trovati = trova(a.artefatti, versione)
    uscita = Path(a.uscita); uscita.mkdir(parents=True, exist_ok=True)
    if any(uscita.iterdir()): raise SystemExit(f"{uscita} non è vuota")
    verifiche, mancanti, inclusi, componenti = {}, [], {}, {}
    for k in SISTEMI:
        p = trovati.get(k)
        if p is None: mancanti.append(f"{k} (nessun pacchetto in questo giro)"); continue
        r = leggi_json(p.parent / f"verifica-{k}.json")
        if r: verifiche[k] = riassunto_verifica(r)
        if impronta_scritta(p) != impronta(p): mancanti.append(f"{k} (l'impronta {p.name}.sha256 manca o non è quella del file)"); continue
        if not r or r.get("esito") != "ok": mancanti.append(f"{k} (la prova del programma installato non è passata)"); continue
        inclusi[k] = p; componenti[k] = leggi_json(f"{p}.componenti.json") or {}
    arm = next((leggi_json(p) for p in Path(a.artefatti).rglob(f"verifica-{WINDOWS_ARM}.json")), None)
    if arm: verifiche[WINDOWS_ARM] = riassunto_verifica(arm)
    if "windows" in inclusi and (arm or {}).get("esito") != "ok": mancanti.append(f"{WINDOWS_ARM} (la prova del pacchetto Windows x64 su Windows 11 ARM non è passata)")
    copie = [Path(shutil.copy2(wheel, uscita / wheel.name))]
    for k, p in inclusi.items():
        copie.append(Path(shutil.copy2(p, uscita / p.name)))
        for altro in (Path(f"{p}.sha256"), Path(f"{p}.componenti.json")):
            if altro.is_file(): shutil.copy2(altro, uscita / altro.name)
    (uscita / VERIFICHE).write_text(json.dumps(dict(versione=versione, esecuzione=a.esecuzione, verifiche=verifiche), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    impronte = [f"{impronta(p)}  {p.name}" for p in sorted(copie, key=lambda p: p.name)]
    (uscita / SOMME).write_text("\n".join(impronte) + "\n", encoding="utf-8", newline="\n")   # \n anche su Windows, per sha256sum -c
    pre = pre_release(versione)
    testa = ["> **Bozza preparata dalla pipeline**" + (f" ([esecuzione]({a.esecuzione}))" if a.esecuzione else "") + ": non pubblicarla da qui. Si",
             f"> pubblica dal computer di chi ha la chiave dei rilasci con `python strumenti/rilascio.py pubblica {a.tag}`, che firma il",
             "> manifesto degli aggiornamenti, lo carica con SHA256SUMS completo e pubblica" + (" (come pre-release)." if pre else "."), ""]
    if mancanti: testa += ["> **Incompleta.** Mancano:", *[f"> - {m}" for m in mancanti], ""]
    Path(a.note).write_text(note(versione, impronte, [], [], pacchetti=inclusi, componenti=componenti, testa=testa, guida=indirizzo_guida(a.repository, a.tag)), encoding="utf-8")
    esito = dict(versione=versione, tag=a.tag, prerelease=pre, pacchetti=sorted(inclusi), mancanti=mancanti)
    Path(a.esito).write_text(json.dumps(esito, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Bozza {a.tag}: {', '.join(sorted(inclusi)) or 'nessun pacchetto'}" + (f"; mancano {'; '.join(mancanti)}" if mancanti else "; completa"))
    return 0


# ---------------------------------------------------------------- firma (prepara e pubblica)
def chiave_pubblica_usata(a):
    return aggiornamento.ed25519.pubblica(aggiornamento.leggi_privata(aggiornamento.cartella(a.dir), a.id)).hex()


def firma_e_somme(a, wheel, pacchetti, uscita):
    """firma il manifesto con wheel e pacchetti (già in `uscita`), lo verifica e scrive SHA256SUMS; (manifesto, impronte)"""
    pub = chiave_pubblica_usata(a)
    aggiornamento.cmd_firma(SimpleNamespace(dir=a.dir, id=a.id, pacchetto=str(uscita / wheel.name), uscita=str(uscita), novita_it=a.novita_it, novita_en=a.novita_en,
                                            python_minimo=a.python_minimo, compilato=[f"{k}={uscita / p.name}" for k, p in pacchetti.items()]))
    m = firmati.verifica((uscita / firmati.MANIFESTO).read_bytes(), (uscita / firmati.FIRMA).read_bytes(), {a.id: pub})
    tutti = sorted([uscita / wheel.name, *[uscita / p.name for p in pacchetti.values()], uscita / firmati.MANIFESTO, uscita / firmati.FIRMA], key=lambda p: p.name)
    impronte = [f"{impronta(p)}  {p.name}" for p in tutti]
    (uscita / SOMME).write_text("\n".join(impronte) + "\n", encoding="utf-8", newline="\n")   # \n anche su Windows, per sha256sum -c
    return m, impronte


def chiave_fidata(a):
    """problema se la chiave privata usata non è quella di CHIAVI_FIDATE (i programmi installati rifiuterebbero la release)"""
    if chiave_pubblica_usata(a) != firmati.CHIAVI_FIDATE.get(a.id):
        return [f"la chiave privata dei rilasci {a.id} non è quella di CHIAVI_FIDATE[{a.id}] in aggiornamenti/firmati.py: i programmi installati rifiuterebbero la release"]
    return []


def cmd_prepara(a):
    wheel_in = [p for p in Path(a.artefatti).rglob("impaginatore-*-py3-none-any.whl")]
    if len(wheel_in) != 1: raise SystemExit(f"Serve una e una sola wheel del programma in {a.artefatti} (trovate {len(wheel_in)}): «uv build --wheel»")
    versione = rilascio.versione_del_pacchetto(str(wheel_in[0]))
    trovati = problemi(versione) + chiave_fidata(a)
    if trovati and not a.prova:
        for x in trovati: print(f"- {x}", file=sys.stderr)
        raise SystemExit("La versione non è pronta per il rilascio (sopra cosa manca). Con --prova si prepara lo stesso, da non pubblicare.")
    wheel, pacchetti = trova(a.artefatti, versione)
    uscita = Path(a.uscita or RADICE / "dist" / f"rilascio-{versione}").resolve()
    if uscita.exists() and any(uscita.iterdir()): raise SystemExit(f"{uscita} non è vuota")
    uscita.mkdir(parents=True, exist_ok=True)
    for p in (wheel, *pacchetti.values()): shutil.copy2(p, uscita / p.name)
    m, impronte = firma_e_somme(a, wheel, pacchetti, uscita)
    mancanti = [s for s in SISTEMI if s not in pacchetti]
    (uscita / "NOTE.md").write_text(note(versione, impronte, trovati, mancanti, pacchetti={k: uscita / p.name for k, p in pacchetti.items()}), encoding="utf-8")
    print(f"Release {versione} in {uscita}: {', '.join(sorted(m['pacchetti']))}" + (f"; senza {', '.join(mancanti)}" if mancanti else ""))
    if trovati: print("PROVA: non pubblicare (vedi NOTE.md).")
    return 0


# ---------------------------------------------------------------- pubblica (computer di chi pubblica)
def gh(*argomenti, repo=None):
    """esegue «gh» (GitHub CLI, autenticato da chi pubblica) e restituisce quello che scrive; SystemExit se non va"""
    cmd = ["gh", *argomenti, *(["--repo", repo] if repo else [])]
    try: r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)  # nosec B603, B607  # gh di chi pubblica, argomenti in lista
    except OSError: raise SystemExit("Serve «gh» (GitHub CLI), autenticato sul repository: https://cli.github.com") from None
    if r.returncode: raise SystemExit(f"«gh {' '.join(argomenti[:2])}» non è andato: {r.stderr.strip()[-800:]}")
    return r.stdout


def controlla_scaricati(cartella, versione, senza):
    """(wheel, pacchetti, problemi) dalla bozza scaricata: impronte di SHA256SUMS e dei .sha256, prove di verifiche.json,
    sistemi mancanti (salvo quelli di --senza)"""
    wheel, pacchetti = trova(cartella, versione)
    out = []
    somme = cartella / SOMME
    righe = somme.read_text(encoding="utf-8").splitlines() if somme.is_file() else []
    if not righe: out.append(f"la bozza non ha {SOMME}")
    for r in righe:
        h, _, nome = r.partition("  ")
        if not (cartella / nome).is_file() or impronta(cartella / nome) != h: out.append(f"{nome}: l'impronta non è quella di {SOMME} della bozza")
    for k, p in pacchetti.items():
        if impronta_scritta(p) != impronta(p): out.append(f"{p.name}: l'impronta non è quella di {p.name}.sha256")
    v = (leggi_json(cartella / VERIFICHE) or {}).get("verifiche", {})
    for k in pacchetti:
        if (v.get(k) or {}).get("esito") != "ok": out.append(f"{k}: in {VERIFICHE} la prova del programma installato non risulta passata")
    if "windows" in pacchetti and WINDOWS_ARM not in senza and (v.get(WINDOWS_ARM) or {}).get("esito") != "ok":
        out.append(f"{WINDOWS_ARM}: il pacchetto Windows non risulta provato su Windows 11 ARM (--senza {WINDOWS_ARM} per pubblicarlo lo stesso)")
    for k in SISTEMI:
        if k not in pacchetti and k not in senza: out.append(f"{k}: nessun pacchetto nella bozza (--senza {k} per pubblicare senza)")
    return wheel, pacchetti, out


def cmd_pubblica(a):
    versione = versione_del_tag(a.tag); pre = pre_release(versione)
    info = json.loads(gh("release", "view", a.tag, "--json", "isDraft,isPrerelease,name,url", repo=a.repo))
    if not info.get("isDraft"): raise SystemExit(f"La release {a.tag} non è una bozza (è già pubblicata?): non la tocco")
    cartella = Path(a.cartella or RADICE / "dist" / f"pubblica-{versione}").resolve()
    if cartella.exists() and any(cartella.iterdir()): raise SystemExit(f"{cartella} non è vuota")
    gh("release", "download", a.tag, "--dir", str(cartella), repo=a.repo)
    wheel, pacchetti, trovati = controlla_scaricati(cartella, versione, set(a.senza))
    trovati = problemi(versione, pre=pre) + chiave_fidata(a) + trovati
    if trovati and not a.prova:
        for x in trovati: print(f"- {x}", file=sys.stderr)
        raise SystemExit(f"La release {a.tag} non si pubblica (sopra cosa manca). Con --prova si prepara lo stesso in {cartella}, senza caricare niente.")
    m, impronte = firma_e_somme(a, wheel, pacchetti, cartella)                # SHA256SUMS della bozza, già controllato, diventa quello completo
    componenti = {k: leggi_json(f"{p}.componenti.json") or {} for k, p in pacchetti.items()}
    mancanti = [s for s in SISTEMI if s not in pacchetti]
    (cartella / "NOTE.md").write_text(note(versione, impronte, trovati, mancanti, pacchetti=pacchetti, componenti=componenti, guida=indirizzo_guida(a.repo, a.tag)), encoding="utf-8")
    print(f"Manifesto firmato: versione {m['versione']}, pacchetti {', '.join(sorted(m['pacchetti']))}; file in {cartella}")
    if a.prova:
        print(f"PROVA: niente caricato né pubblicato. La release {a.tag} resta in bozza ({info.get('url')}).")
        return 0
    come = "pre-release (non arriva agli aggiornamenti dei programmi installati)" if pre else "ultima versione (i programmi installati la trovano al prossimo controllo)"
    if not a.si and input(f"Carico manifesto, firma e SHA256SUMS e pubblico {a.tag} come {come}? [s/N] ").strip().lower() not in ("s", "si", "sì"):
        print("Niente pubblicato: la release resta in bozza."); return 1
    gh("release", "upload", a.tag, str(cartella / firmati.MANIFESTO), str(cartella / firmati.FIRMA), str(cartella / SOMME), "--clobber", repo=a.repo)
    gh("release", "edit", a.tag, "--notes-file", str(cartella / "NOTE.md"), "--draft=false", *(["--prerelease"] if pre else ["--prerelease=false", "--latest"]), repo=a.repo)
    print(f"Pubblicata {a.tag} come {come}: {info.get('url', '')}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rilascio", description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="comando", required=True)
    sub.add_parser("controlla")
    b = sub.add_parser("bozza"); b.add_argument("artefatti"); b.add_argument("--tag", required=True); b.add_argument("--uscita", required=True)
    b.add_argument("--note", required=True); b.add_argument("--esito", required=True); b.add_argument("--esecuzione"); b.add_argument("--repository")
    for nome in ("prepara", "pubblica"):
        p = sub.add_parser(nome); p.add_argument("artefatti" if nome == "prepara" else "tag")
        p.add_argument("--dir"); p.add_argument("--id", type=int, default=1); p.add_argument("--python-minimo", default="3.11")
        p.add_argument("--novita-it", action="append", default=[]); p.add_argument("--novita-en", action="append", default=[]); p.add_argument("--prova", action="store_true")
        if nome == "prepara": p.add_argument("--uscita")
        else:
            p.add_argument("--repo"); p.add_argument("--cartella"); p.add_argument("--si", action="store_true")
            p.add_argument("--senza", action="append", default=[], choices=[*SISTEMI, WINDOWS_ARM])
    a = ap.parse_args(argv)
    try: return {"controlla": cmd_controlla, "bozza": cmd_bozza, "prepara": cmd_prepara, "pubblica": cmd_pubblica}[a.comando](a)
    except (OSError, ValueError, KeyError) as e: raise SystemExit(f"Errore: {e}") from None


if __name__ == "__main__":
    sys.exit(main())
