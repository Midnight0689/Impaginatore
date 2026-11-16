"""Licenze, fasce e prova gratuita (T-202): chiavi verificate su questo computer, prova di 30 giorni, sola lettura,
revoche che arrivano con il programma, cancelli delle funzioni. La coppia di firma è quella della sessione (conftest)."""
import datetime as dt
import json
import logging
import os
import re
import sys

import pytest
from PIL import Image

from impaginatore import __version__, licenze
from impaginatore.licenze import chiave as K

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIORNO = 86400
T0 = dt.datetime(2026, 11, 16, 12, 0).timestamp()
POSIX = os.name == "posix"


@pytest.fixture
def ora(monkeypatch):
    """orologio finto del modulo delle licenze: si sposta con ora.t"""
    class Ora: t = T0
    o = Ora()
    monkeypatch.setattr(licenze, "orologio", lambda: o.t)
    return o


@pytest.fixture
def revoche(monkeypatch, tmp_path):
    """file revoche.json del pacchetto, in una cartella del test: scrivi(corpo) lo cambia"""
    f = tmp_path / "revoche.json"
    monkeypatch.setattr(licenze, "FILE_REVOCHE", str(f))

    def scrivi(corpo, n=[0]):
        f.write_text(corpo if isinstance(corpo, str) else json.dumps(corpo), encoding="utf-8"); n[0] += 1
        os.utime(f, ns=(n[0] * 10**9, n[0] * 10**9))                       # ogni versione dell'elenco ha la sua data
    return scrivi


def _altera(testo, byte, valore):
    """chiave con un byte del contenuto cambiato e la firma di prima"""
    b = bytearray(K.da_testo(testo)); b[byte] = valore
    return K.in_testo(bytes(b))


# ---------------------------------------------------------------- tier.json e fasce
def test_tier_del_pacchetto_uguale_a_quello_del_listino():
    """il programma legge la copia nel pacchetto: deve restare identica a docs/mercato/tier.json"""
    with open(os.path.join(RADICE, "docs", "mercato", "tier.json"), encoding="utf-8") as f: listino = json.load(f)
    with open(licenze.FILE_TIER, encoding="utf-8") as f: pacchetto = json.load(f)
    assert pacchetto == listino, "copia docs/mercato/tier.json in src/impaginatore/licenze/tier.json"


def test_funzioni_delle_fasce():
    assert not licenze.funzioni_di("essenziale")["export_psd_livelli"] and licenze.funzioni_di("pro")["export_psd_livelli"]
    assert licenze.funzioni_di("essenziale")["modelli_personali"] == 5
    assert not licenze.funzioni_di("prova")["export_psd_livelli"] and licenze.funzioni_di("prova")["server_mcp"]
    assert licenze.funzioni_di("laboratorio")["computer"] == 2
    assert [licenze.nome_fascia(f) for f in ("essenziale", "pro", "studio", "laboratorio")] == ["Essenziale", "Pro", "Studio", "Laboratorio"]
    assert licenze.fasce_con("export_psd_livelli") == "Pro e Studio"
    assert licenze.fasce_con("export_jpg") == "Essenziale, Pro e Studio"
    assert licenze.fasce_con("uso_commerciale_multipostazione") == "Studio"
    assert licenze.fasce_con("modelli_personali", senza_limite=True) == "Pro e Studio"
    sl = licenze.funzioni_sola_lettura()
    assert {k for k, v in sl.items() if v} == {"import_export_progetto", "versioni_backup"} and set(sl) == set(licenze.funzioni_di("prova"))


# ---------------------------------------------------------------- stati
def test_licenza_attiva(licenza, ora):
    s = licenze.stato()
    assert (s["stato"], s["fascia"], s["nome_fascia"], s["sola_lettura"], s["filigrana"], s["chiave_presente"]) == ("attiva", "studio", "Studio", False, False, True)
    assert s["funzioni"] == licenze.funzioni_di("studio") and s["seriale"] == 1 and s["emessa"] == "2026-11-01" and s["scade"] is None
    assert s["messaggio"] == "Licenza Studio attiva, intestata a «Studio Prova», per 5 computer. Tutti gli aggiornamenti della versione 2 sono inclusi."
    assert "IMP1" not in json.dumps(s) and K.da_testo(licenza.chiavi.studio)[-64:].hex() not in json.dumps(s), "il testo della chiave non esce mai"
    licenza.usa(licenza.chiavi.chiave(fascia="pro", intestatario="", flag=K.FLAG_OMAGGIO, computer=2))
    s = licenze.stato()
    assert s["messaggio"] == "Licenza Pro attiva per 2 computer. Tutti gli aggiornamenti della versione 2 sono inclusi." and s["omaggio"] and not s["beta"]
    assert s["etichetta_beta"] is None and s["riga_beta"] is None, "la beta privata ha i suoi testi: tests/test_licenze_beta.py"


def test_prova_gratuita_dalla_prima_apertura(licenza, ora):
    licenza.usa(None)
    s = licenze.stato()
    assert (s["stato"], s["sola_lettura"], s["filigrana"], s["chiave_presente"]) == ("prova", False, True, False)
    assert s["funzioni"] == licenze.funzioni_di("prova") and s["prova"]["giorni_rimasti"] == 30 and s["prova"]["inizio"] == "2026-11-16"
    assert s["messaggio"] == ("Prova gratuita: mancano 30 giorni (fino al 16/12/2026). Hai le funzioni del Pro tranne il PSD a livelli; "
                              "le esportazioni JPG e PDF hanno una filigrana.")
    f = licenza.cartella / "prova.json"; assert f.exists()
    if POSIX: assert f.stat().st_mode & 0o777 == 0o600 and licenza.cartella.stat().st_mode & 0o777 == 0o700
    ora.t = T0 + 29.5 * GIORNO
    assert "oggi è l'ultimo giorno" in licenze.stato()["messaggio"]
    ora.t = T0 + 30 * GIORNO
    s = licenze.stato()
    assert (s["stato"], s["sola_lettura"], s["filigrana"]) == ("scaduta", True, False) and s["funzioni"] == licenze.funzioni_sola_lettura()
    assert s["messaggio"].startswith("La prova gratuita è finita il 16/12/2026. Gli album si aprono in sola lettura")


def test_la_prova_non_si_allunga_spostando_indietro_l_orologio(licenza, ora):
    licenza.usa(None)
    licenze.stato(); ora.t = T0 + 10 * GIORNO; licenze.stato()
    ora.t = T0 + 2 * GIORNO
    s = licenze.stato()
    assert s["prova"]["giorni_rimasti"] == 20 and s["prova"]["orologio_indietro"]
    assert s["messaggio"].endswith("L'orologio del computer è indietro rispetto all'ultimo uso: per la prova conta la data più recente.")
    ora.t = T0 + 10 * GIORNO - 3600
    assert not licenze.stato()["prova"]["orologio_indietro"], "un'ora indietro (ora legale, fuso) non si segnala"
    ora.t = T0 + 31 * GIORNO; assert licenze.stato()["stato"] == "scaduta"
    ora.t = T0 + 5 * GIORNO; s = licenze.stato()
    assert s["stato"] == "scaduta" and s["sola_lettura"] and "orologio" in s["messaggio"]
    licenza.usa(licenza.chiavi.studio)
    assert "orologio" not in licenze.stato()["messaggio"], "con una licenza l'orologio non conta"


def test_l_ultima_ora_vista_si_scrive_ogni_tanto(licenza, ora):
    licenza.usa(None); f = licenza.cartella / "prova.json"
    licenze.stato(); prima = f.read_text(encoding="utf-8")
    ora.t = T0 + 100; licenze.stato(); assert f.read_text(encoding="utf-8") == prima
    ora.t = T0 + 700; licenze.stato(); assert json.loads(f.read_text(encoding="utf-8")) == dict(formato=1, inizio=T0, visto=T0 + 700)


@pytest.mark.parametrize("contenuto", ["{", "[1, 2]", '{"inizio": "ieri", "visto": 1}', '{"inizio": 5, "visto": 1}', '{"inizio": true, "visto": true}', '{"inizio": NaN, "visto": 1}', '{"inizio": 1}'])
def test_dati_della_prova_rovinati(licenza, ora, caplog, contenuto):
    """file della prova illeggibile: la prova riparte (è il caso di chi lo cancella: LICENZE.md lo dice)"""
    licenza.usa(None); (licenza.cartella / "prova.json").write_text(contenuto, encoding="utf-8")
    with caplog.at_level(logging.WARNING, "impaginatore.licenze"): s = licenze.stato()
    assert s["stato"] == "prova" and s["prova"]["giorni_rimasti"] == 30 and "la prova riparte" in caplog.text
    assert json.loads((licenza.cartella / "prova.json").read_text(encoding="utf-8"))["inizio"] == T0


def test_cartella_della_licenza_non_scrivibile(licenza, ora, caplog):
    """prova.json che è una cartella (o un disco in sola lettura): la prova vale lo stesso, con un avviso nel registro"""
    licenza.usa(None); (licenza.cartella / "prova.json").mkdir()
    with caplog.at_level(logging.WARNING, "impaginatore.licenze"): s = licenze.stato()
    assert s["stato"] == "prova" and "dati della prova illeggibili" in caplog.text and "dati della prova non salvati" in caplog.text
    (licenza.cartella / "chiave.txt").mkdir()
    with caplog.at_level(logging.WARNING, "impaginatore.licenze"): assert licenze.chiave_salvata() is None
    assert "chiave di licenza non letta" in caplog.text
    (licenza.cartella / "chiave.txt").rmdir(); (licenza.cartella / "chiave.txt").write_text("  \n", encoding="utf-8")
    assert licenze.chiave_salvata() is None


def test_permessi_della_cartella_non_impostabili(licenza, ora, monkeypatch, caplog):
    def no(*a): raise PermissionError(1, "Operazione non permessa")
    monkeypatch.setattr(licenze.os, "chmod", no)
    with caplog.at_level(logging.WARNING, "impaginatore.licenze"): licenze.attiva(licenza.chiavi.chiave(fascia="pro"))
    assert "permessi della cartella della licenza non impostati" in caplog.text and licenze.stato()["fascia"] == "pro"


def test_cartella_nei_dati_dell_utente(licenza):
    assert licenza.cartella_vera() == os.path.join(os.environ["IMPAGINATORE_DATI"], "licenza")


# ---------------------------------------------------------------- chiavi che non valgono
def test_chiave_manomessa_vale_la_prova(licenza, ora):
    licenza.usa(_altera(licenza.chiavi.chiave(fascia="pro"), 2, 3))              # Pro trasformata in Studio: la firma non torna
    s = licenze.stato()
    assert (s["stato"], s["sola_lettura"], s["filigrana"], s["chiave_presente"]) == ("non valida", False, True, True)
    assert s["funzioni"] == licenze.funzioni_di("prova") and "il contenuto non corrisponde alla firma" in s["motivo"]
    assert s["messaggio"].startswith("La chiave salvata non vale. Questa chiave non è valida") and "Intanto vale la prova gratuita: mancano 30 giorni" in s["messaggio"]
    ora.t = T0 + 40 * GIORNO
    s = licenze.stato()
    assert s["stato"] == "non valida" and s["sola_lettura"] and s["funzioni"] == licenze.funzioni_sola_lettura()
    assert s["messaggio"] == f"La chiave salvata non vale. {s['motivo']} {licenze.msg_sola_lettura()}"


@pytest.mark.parametrize("versione,attesa", [(3, "Questa chiave è per Impaginatore 3: aggiorna il programma per usarla."),
                                             (1, "Questa chiave è per Impaginatore 1. Per Impaginatore 2 serve l'aggiornamento della licenza: trovi il prezzo scontato sul sito.")])
def test_chiave_di_un_altra_versione_maggiore(licenza, ora, versione, attesa):
    k = licenza.chiavi.chiave(versione=versione)
    licenza.usa(k); s = licenze.stato()
    assert s["stato"] == "non valida" and s["motivo"] == attesa and s["fascia"] == "studio"
    with pytest.raises(K.ChiaveNonValida, match=re.escape(attesa)): licenze.attiva(k)


def test_chiave_revocata_con_l_aggiornamento(licenza, ora, revoche):
    assert licenze.revocate() == frozenset(), "senza elenco nel pacchetto non c'è nessuna revoca"
    revoche(licenza.chiavi.revoche([1, 7]))
    s = licenze.stato()
    assert (s["stato"], s["sola_lettura"], s["messaggio"]) == ("revocata", True, licenze.msg_revocata()) and s["funzioni"] == licenze.funzioni_sola_lettura()
    assert licenze.revocate() is licenze.revocate(), "l'elenco si legge una volta per versione del file"
    with pytest.raises(K.ChiaveNonValida, match="non è più attiva"): licenze.attiva(licenza.chiavi.studio)
    revoche(licenza.chiavi.revoche([7]))                                         # togli-revoca: torna valida con il rilascio successivo
    assert licenze.stato()["stato"] == "attiva"


@pytest.mark.parametrize("caso", ["firma di un'altra chiave", "json rotto", "seriali alterati"])
def test_elenco_delle_revoche_non_valido_non_revoca_niente(licenza, ora, revoche, caplog, caso):
    c = licenza.chiavi
    corpo = {"firma di un'altra chiave": c.revoche([1], seme=bytes(32)), "json rotto": "{", "seriali alterati": dict(c.revoche([7]), seriali=[1, 7])}[caso]
    revoche(corpo)
    with caplog.at_level(logging.WARNING, "impaginatore.licenze"): assert licenze.stato()["stato"] == "attiva"
    assert "elenco delle revoche ignorato" in caplog.text


def test_licenza_a_scadenza(licenza, ora):
    """chiavi dei laboratori (formato 2): valgono fino all'ultimo giorno compreso, poi sola lettura"""
    licenza.usa(licenza.chiavi.chiave(fascia="laboratorio", intestatario="Lab Bianchi", scadenza="2026-12-31", computer=2))
    s = licenze.stato()
    assert (s["stato"], s["fascia"], s["scade"]) == ("attiva", "laboratorio", "2026-12-31") and s["funzioni"] == licenze.funzioni_di("laboratorio")
    assert s["messaggio"] == "Licenza Laboratorio attiva, intestata a «Lab Bianchi», per 2 computer. Vale fino al 31/12/2026."
    ora.t = dt.datetime(2026, 12, 31, 23, 0).timestamp(); assert licenze.stato()["stato"] == "attiva"
    ora.t = dt.datetime(2027, 1, 1, 9, 0).timestamp(); s = licenze.stato()
    assert (s["stato"], s["sola_lettura"]) == ("scaduta", True)
    assert s["messaggio"].startswith("La licenza Laboratorio intestata a «Lab Bianchi» è scaduta il 31/12/2026. Gli album si aprono in sola lettura")
    licenza.usa(licenza.chiavi.chiave(fascia="laboratorio", intestatario="", scadenza="2026-12-31"))
    assert licenze.stato()["messaggio"].startswith("La licenza Laboratorio è scaduta il 31/12/2026.")
    with pytest.raises(K.ChiaveNonValida, match="è scaduta"): licenze.attiva(licenza.chiavi.chiave(fascia="laboratorio", scadenza="2026-12-31"))


# ---------------------------------------------------------------- attivare e togliere
def test_attiva_e_togli(licenza, ora, caplog):
    licenza.usa(None); assert licenze.stato()["stato"] == "prova"
    pro = licenza.chiavi.chiave(fascia="pro", seriale=9, intestatario="Mario Rossi", computer=2)
    incollata = f"  impaginatore://attiva?chiave={pro.lower()}\n".replace("-", " - ")
    with caplog.at_level(logging.INFO, "impaginatore.licenze"): s = licenze.attiva(incollata)
    assert (s["stato"], s["fascia"], s["seriale"]) == ("attiva", "pro", 9)
    f = licenza.cartella / "chiave.txt"; assert f.read_text(encoding="utf-8") == pro + "\n", "si salva il testo pulito"
    if POSIX: assert f.stat().st_mode & 0o777 == 0o600 and licenza.cartella.stat().st_mode & 0o777 == 0o700
    assert "licenza pro attivata (seriale 9)" in caplog.text and pro not in caplog.text and "Rossi" not in caplog.text, "nel registro niente chiave né nome"
    for sbagliata in ("IMP1-AAAAA", "ciao", _altera(pro, 2, 3)):
        with pytest.raises(K.ChiaveNonValida): licenze.attiva(sbagliata)
    assert f.read_text(encoding="utf-8") == pro + "\n", "una chiave sbagliata non cancella quella buona"
    assert licenze.rimuovi()["stato"] == "prova" and not f.exists()
    assert licenze.rimuovi()["stato"] == "prova", "togliere due volte non dà errore"


def test_verifiche_in_memoria(licenza, monkeypatch):
    monkeypatch.setattr(licenze, "_VERIFICHE", {i: {} for i in range(65)})
    assert licenze.stato()["stato"] == "attiva" and len(licenze._VERIFICHE) == 1


# ---------------------------------------------------------------- formato della chiave
def test_testo_della_chiave(licenza):
    k = licenza.chiavi.studio; dati = K.da_testo(k)
    assert K.in_testo(dati) == k and K.da_testo(k.lower().replace("-", " ")) == dati and K.da_testo("impaginatore://attiva?chiave=" + k) == dati
    for testo, msg in [(None, "Incolla la chiave"), ("   ", "Incolla la chiave"), ("x" * 3000, "troppo lungo"), ("ABCDE", "non è una chiave di Impaginatore"),
                       ("IMP1-AB*CD", "caratteri che non ci vanno"), ("IMP1-A", "incompleta"), ("IMP1-AEAQC", "incompleta")]:
        with pytest.raises(K.ChiaveNonValida, match=msg): K.decodifica(testo)


def test_contenuto_e_firma(licenza):
    c = licenza.chiavi
    info = K.decodifica(c.chiave(fascia="essenziale", seriale=70000, intestatario="Studio Àlfa", computer=1, flag=K.FLAG_BETA))
    assert {k: info[k] for k in ("formato", "id_firma", "fascia", "versione_maggiore", "computer", "omaggio", "beta", "seriale", "emessa", "intestatario", "scade")} == dict(
        formato=1, id_firma=1, fascia="essenziale", versione_maggiore=2, computer=1, omaggio=False, beta=True, seriale=70000, emessa="2026-11-01", intestatario="Studio Àlfa", scade=None)
    assert K.decodifica(c.chiave(scadenza="2027-03-31"))["scade"] == "2027-03-31"
    casi = [
        (c.firma(c.payload(formato=3)), "tipo più recente"),
        (c.firma(c.payload(intestatario="x" * 49)), "incompleta"),
        (c.firma(c.payload(formato=2)), "incompleta"),                          # formato 2 senza i byte della scadenza
        (c.firma(c.payload(id_firma=9)), "che questa versione di Impaginatore non conosce \\(n. 9\\)"),
        (c.chiave(seme=bytes(32)), "non corrisponde alla firma"),
        (c.firma(c.payload(fascia=5)), "licenza che questa versione di Impaginatore non conosce"),
        (c.firma(c.payload(flag=4)), "licenza che questa versione di Impaginatore non conosce"),
        (c.firma(c.payload()[:13] + b"\xff\xfe" + c.payload()[15:]), "incompleta"),       # intestatario che non è UTF-8 (firmato così)
    ]
    for testo, msg in casi:
        with pytest.raises(K.ChiaveNonValida, match=msg): K.decodifica(testo)
    p = c.payload(); assert K.decodifica(c.firma(p[:12] + bytes([0]) + b""))["intestatario"] == ""
    sviluppo = {1: K.Pubblica(K.SEGNAPOSTO)}
    with pytest.raises(K.ChiaveNonValida, match="versione di sviluppo"): K.decodifica(c.studio, sviluppo)


def test_chiave_di_firma_ritirata(licenza):
    """furto della chiave privata: l'aggiornamento mette la data in emesse_fino e le chiavi firmate dopo non valgono più"""
    c = licenza.chiavi; ritirata = {1: K.Pubblica(c.pubblica.hex(), emesse_fino="2026-12-31")}
    assert K.decodifica(c.chiave(emessa="2026-12-31"), ritirata)["seriale"] == 1
    with pytest.raises(K.ChiaveNonValida, match="chiave di firma ritirata"): K.decodifica(c.chiave(emessa="2027-01-01"), ritirata)


def test_elenco_delle_revoche(licenza):
    c = licenza.chiavi
    assert K.revoche(c.revoche([3, 1])) == ({1, 3}, "2026-11-16T10:00:00+00:00")
    buono = c.revoche([1])
    for corpo, msg in [([], "formato sconosciuto"), (dict(buono, formato=2), "formato sconosciuto"), (dict(buono, seriali="1"), "incompleto"),
                       (dict(buono, seriali=[True]), "incompleto"), (dict(buono, emessa=1), "incompleto"), (dict(buono, firma=None), "incompleto"),
                       (dict(buono, firma="zz"), "firma"), (dict(buono, id_firma="1"), "firma"), (dict(buono, id_firma=2), "firma"),
                       (c.revoche([1], seme=bytes(32)), "firma")]:
        with pytest.raises(ValueError, match=msg): K.revoche(corpo)
    with pytest.raises(ValueError, match="firma"): K.revoche(buono, {1: K.Pubblica(K.SEGNAPOSTO)})


# ---------------------------------------------------------------- rilascio
def test_segnaposto_della_chiave_pubblica(licenza):
    assert K.problemi_per_il_rilascio({1: K.Pubblica(K.SEGNAPOSTO)}) and K.problemi_per_il_rilascio({1: K.Pubblica("ab" * 31)})
    assert K.problemi_per_il_rilascio({}) == ["nessuna chiave pubblica di firma"]
    assert K.problemi_per_il_rilascio({1: K.Pubblica(licenza.chiavi.pubblica.hex())}) == []
    assert K.problemi_per_il_rilascio() == [], "nei test la chiave della sessione prende il posto del segnaposto"


def test_un_rilascio_non_parte_con_il_segnaposto(licenza):
    """versione finale (es. 2.0.0) con il segnaposto nel codice: nessuna chiave venduta funzionerebbe. Questo test la ferma.
    Nelle versioni di sviluppo (2.0.0.dev0, 2.0.0rc1) il segnaposto è atteso: vale la prova gratuita"""
    finale = re.fullmatch(r"\d+\.\d+\.\d+", __version__) is not None
    problemi = K.problemi_per_il_rilascio(licenza.pubbliche_vere)
    assert not (finale and problemi), f"rilascio {__version__} con la chiave pubblica di prova: {problemi} (docs/architettura/LICENZE.md, «Prima del rilascio»)"
    if not finale: assert problemi, "copia di sviluppo: la chiave pubblica vera arriva al rilascio"


def test_le_licenze_non_usano_la_rete():
    """«il programma non telefona a casa»: niente moduli di rete nel codice delle licenze"""
    qui = os.path.dirname(licenze.__file__)
    for f in [os.path.join(qui, n) for n in os.listdir(qui) if n.endswith(".py")] + [os.path.join(os.path.dirname(qui), "ed25519.py")]:
        with open(f, encoding="utf-8") as h: testo = h.read()
        assert not re.search(r"^\s*(import|from)\s+(socket|ssl|http|urllib|requests|ftplib|smtplib|webbrowser)\b", testo, re.M), f


# ---------------------------------------------------------------- domande e cancelli
def test_consentita_e_limite(licenza, ora):
    st = licenze.stato()
    assert licenze.consentita("export_psd_livelli", st) and licenze.limite("modelli_personali", st) is None and licenze.consentita("computer")
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    assert licenze.limite("modelli_personali") == 5 and licenze.consentita("modelli_personali") and licenze.limite("export_psd_livelli") == 0
    assert not licenze.consentita("server_mcp")
    with pytest.raises(KeyError): licenze.consentita("volo")


def test_motivi(licenza, ora):
    licenza.usa(licenza.chiavi.chiave(fascia="essenziale"))
    assert licenze.motivo("export_psd_livelli") == "Il PSD a livelli non fa parte della licenza Essenziale: c'è nelle licenze Pro e Studio."
    assert licenze.motivo("volo").startswith("La funzione «volo» non fa parte")
    licenza.usa(None)
    assert licenze.motivo("export_psd_livelli") == "Il PSD a livelli non fa parte della prova gratuita: c'è nelle licenze Pro e Studio."
    ora.t = T0 + 31 * GIORNO
    assert licenze.motivo("editor_completo").startswith("Impaginatore è in sola lettura. La prova gratuita è finita il")


def test_cancelli(licenza, ora):
    c = licenza.chiavi; L = licenze
    assert L.controlla_esportazione("psd") is False and L.controlla_operazione({"op": "tono_fix"}) is None and L.controlla_modifica() is None
    licenza.usa(c.chiave(fascia="essenziale"))
    L.controlla_operazione({"op": "move"}); L.controlla_lettura("/api/state"); L.controlla_modelli("rinomina", 99); L.controlla_modelli("salva", 4)
    assert L.controlla_esportazione("jpg") is False
    for f in (lambda: L.controlla_operazione({"op": "tono_fix"}), lambda: L.controlla_operazione({"op": "tono_L"}), lambda: L.controlla_operazione({"op": "tono_escl"}),
              lambda: L.controlla_esportazione("psd"), lambda: L.controlla_lettura("/api/tono"), lambda: L.controlla_lettura("/api/tono_all")):
        with pytest.raises(L.NonConsentita): f()
    for azione in ("salva", "importa"):
        with pytest.raises(L.NonConsentita, match="La licenza Essenziale comprende 5 modelli personali: per salvarne un altro eliminane uno. Nelle licenze Pro e Studio sono illimitati."):
            L.controlla_modelli(azione, 5)
    licenza.usa(None)
    assert L.controlla_esportazione("jpg") is True and L.controlla_esportazione("pdf") is True
    L.controlla_modelli("salva", 1000); L.controlla_lettura("/api/tono")
    with pytest.raises(L.NonConsentita, match="prova gratuita"): L.controlla_esportazione("psd")
    ora.t = T0 + 31 * GIORNO
    L.controlla_operazione({"op": "copia"}); L.controlla_modelli("elimina", 3)
    for f in (lambda: L.controlla_operazione({"op": "move"}), lambda: L.controlla_operazione("move"), lambda: L.controlla_esportazione("pdf"),
              lambda: L.controlla_modelli("salva", 0), L.controlla_modifica):
        with pytest.raises(L.NonConsentita, match="sola lettura"): f()


# ---------------------------------------------------------------- filigrana
def test_filigrana():
    im = Image.new("RGB", (900, 500), "white"); im.paste((20, 25, 30), (450, 0, 900, 500))
    out = licenze.applica_filigrana(im)
    assert out.mode == "RGB" and out.size == im.size and im.getextrema() == ((20, 255), (25, 255), (30, 255)), "l'originale non cambia"
    chiari = out.crop((0, 0, 450, 500)).convert("L"); scuri = out.crop((450, 0, 900, 500)).convert("L")
    assert chiari.getextrema()[0] < 230 and scuri.getextrema()[1] > 60, "si vede sul bianco e sul nero"
    assert sum(chiari.histogram()[:250]) > 2000 and sum(scuri.histogram()[40:]) > 2000, "su tutta l'immagine, non in un angolo"
    piccola = licenze.applica_filigrana(Image.new("RGBA", (40, 30), (255, 255, 255, 0)))
    assert piccola.mode == "RGB" and piccola.size == (40, 30)


@pytest.mark.skipif(sys.platform == "win32", reason="permessi POSIX")
def test_file_della_licenza_solo_per_l_utente(licenza, ora):
    licenza.usa(None); os.chmod(licenza.cartella, 0o755)
    licenze.attiva(licenza.chiavi.studio)
    assert licenza.cartella.stat().st_mode & 0o777 == 0o700 and (licenza.cartella / "chiave.txt").stat().st_mode & 0o777 == 0o600
    assert not [n for n in os.listdir(licenza.cartella) if n.endswith(".tmp")], "nessun file temporaneo lasciato"
