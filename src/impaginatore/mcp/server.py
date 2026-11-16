"""Server MCP su stdio con l'SDK ufficiale (pacchetto «mcp» 2.x, MIT): registra gli strumenti di strumenti.Assistente.

Qui ci sono solo nomi, descrizioni, schemi degli argomenti (dai tipi) e la forma delle risposte: testo JSON, oppure
un'immagine JPEG per i due strumenti delle immagini. Un Rifiuto diventa un risultato con is_error e il messaggio.
Su stdout passano solo i messaggi del protocollo: niente print, i registri vanno su file (giornale) e su stderr.
"""
import base64
from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations
from pydantic import Field

from .. import __version__, lingua
from . import strumenti as S

LETTURA = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
MODIFICA = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
IMMAGINE = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)   # pixel che lasciano il computer
Pagina = Literal["sinistra", "destra"]           # valori del protocollo: non cambiano con la lingua


def istruzioni():
    """istruzioni generali per l'assistente, nella lingua in uso"""
    return lingua.t("mcp.istruzioni")


def _descr(chiave, **campi):
    """descrizione di un argomento, nella lingua in uso (si legge all'avvio: cambiare lingua vale al riavvio dell'assistente)"""
    return Field(description=lingua.t(chiave), **campi)
Prodotto = Annotated[str | None, _descr("mcp.arg_prodotto", max_length=81)]


def risultato(fn, *a, **k):
    """esegue lo strumento e ne fa un CallToolResult: testo JSON, immagine, o errore (is_error) con il messaggio"""
    try: r = fn(*a, **k)
    except S.Rifiuto as e: return CallToolResult(content=[TextContent(type="text", text=str(e))], is_error=True)
    if isinstance(r, S.Immagine):
        return CallToolResult(content=[ImageContent(type="image", data=base64.b64encode(r.dati).decode("ascii"), mime_type="image/jpeg"), TextContent(type="text", text=r.testo)])
    return CallToolResult(content=[TextContent(type="text", text=S.limita(r))])


def _testi(nome):
    """titolo e descrizione di uno strumento nella lingua in uso (mcp.titolo_<nome>, mcp.descr_<nome>)"""
    return dict(title=lingua.t("mcp.titolo_" + nome), description=lingua.t("mcp.descr_" + nome))


def crea(assistente):
    """il server MCP con gli strumenti dell'assistente (non lo avvia). Titoli, descrizioni e istruzioni escono nella lingua in uso
    al momento dell'avvio: una lingua cambiata nella schermata Album vale quando l'assistente riavvia il server"""
    a = assistente
    srv = MCPServer("impaginatore", title="Impaginatore", version=__version__, instructions=istruzioni(), log_level="WARNING")
    tool = srv.tool
    Progetto = Annotated[str, _descr("mcp.arg_progetto", max_length=20)]
    Spread = Annotated[int, _descr("mcp.arg_spread", ge=1, le=100000)]
    Gruppo = Annotated[str | None, _descr("mcp.arg_gruppo", max_length=100)]
    ElencoSpread = Annotated[list[int] | None, _descr("mcp.arg_elenco_spread", max_length=1000)]

    @tool(**_testi("stato_programma"), annotations=LETTURA)
    def stato_programma() -> CallToolResult:
        return risultato(a.stato_programma)

    @tool(**_testi("elenca_progetti"), annotations=LETTURA)
    def elenca_progetti() -> CallToolResult:
        return risultato(a.elenca_progetti)

    @tool(**_testi("apri_progetto"), annotations=LETTURA)
    def apri_progetto(progetto: Annotated[str, _descr("mcp.arg_progetto_o_nome", max_length=300)]) -> CallToolResult:
        return risultato(a.apri_progetto, progetto)

    @tool(**_testi("mostra_editor"), annotations=LETTURA)
    def mostra_editor(progetto: Progetto) -> CallToolResult:
        return risultato(a.mostra_editor, progetto)

    @tool(**_testi("elenca_prodotti"), annotations=LETTURA)
    def elenca_prodotti() -> CallToolResult:
        return risultato(a.elenca_prodotti)

    @tool(**_testi("crea_progetto"), annotations=MODIFICA)
    def crea_progetto(nome: Annotated[str, Field(max_length=120)],
                      larghezza_cm: Annotated[float | None, _descr("mcp.arg_larghezza")] = None,
                      altezza_cm: Annotated[float | None, _descr("mcp.arg_altezza")] = None,
                      abbondanza_mm: float = 0.0, spazio_mm: float = 2.5, margine_mm: float = 10.0,
                      scegli_cartella_foto: Annotated[bool, _descr("mcp.arg_scegli_cartella_foto")] = False,
                      prodotto: Prodotto = None) -> CallToolResult:
        return risultato(a.crea_progetto, nome, larghezza_cm, altezza_cm, abbondanza_mm, spazio_mm, margine_mm, scegli_cartella_foto, prodotto)

    @tool(**_testi("imposta_prodotto"), annotations=MODIFICA)
    def imposta_prodotto(progetto: Progetto, prodotto: Prodotto = None) -> CallToolResult:
        return risultato(a.imposta_prodotto, progetto, prodotto)

    @tool(**_testi("aggiungi_foto"), annotations=MODIFICA)
    def aggiungi_foto(progetto: Progetto, cosa: Literal["cartella", "foto"] = "cartella") -> CallToolResult:
        return risultato(a.aggiungi_foto, progetto, cosa)

    @tool(**_testi("stato_album"), annotations=LETTURA)
    def stato_album(progetto: Progetto, da_spread: Spread = 1, quanti: Annotated[int, Field(ge=1, le=50)] = 20) -> CallToolResult:
        return risultato(a.stato_album, progetto, da_spread, quanti)

    @tool(**_testi("elenca_foto"), annotations=LETTURA)
    def elenca_foto(progetto: Progetto, filtro: Literal["tutte", "libere", "nell_album", "con_stella", "tolte"] = "tutte",
                    da: Annotated[int, Field(ge=1)] = 1, quanti: Annotated[int, Field(ge=1, le=500)] = 100) -> CallToolResult:
        return risultato(a.elenca_foto, progetto, filtro, da, quanti)

    @tool(**_testi("controlla_album"), annotations=LETTURA)
    def controlla_album(progetto: Progetto, spread: ElencoSpread = None, tono: bool | None = None) -> CallToolResult:
        return risultato(a.controlla_album, progetto, spread, tono)

    @tool(**_testi("proponi_bozza"), annotations=LETTURA)
    def proponi_bozza(progetto: Progetto, ritmo: Literal["alterna", "piene", "bianche"] = "alterna",
                      foto_per_spread: Annotated[float | None, Field(ge=1, le=8)] = None,
                      numero_spread: Annotated[int | None, _descr("mcp.arg_numero_spread", ge=1, le=1000)] = None,
                      stelle: Annotated[bool, _descr("mcp.arg_stelle")] = True, seme: Annotated[int, Field(ge=0, le=2**31 - 1)] = 0) -> CallToolResult:
        return risultato(a.proponi_bozza, progetto, ritmo, foto_per_spread, numero_spread, stelle, seme)

    @tool(**_testi("applica_bozza"), annotations=MODIFICA)
    def applica_bozza(progetto: Progetto, proposta: Annotated[str, Field(max_length=20)],
                      dopo_spread: Annotated[int | None, _descr("mcp.arg_dopo_spread", ge=0)] = None, gruppo: Gruppo = None) -> CallToolResult:
        return risultato(a.applica_bozza, progetto, proposta, dopo_spread, gruppo)

    @tool(**_testi("cambia_disposizione"), annotations=MODIFICA)
    def cambia_disposizione(progetto: Progetto, spread: Spread, pagina: Pagina | None = None, passo: Literal[1, -1] = 1, gruppo: Gruppo = None) -> CallToolResult:
        return risultato(a.cambia_disposizione, progetto, spread, pagina, passo, gruppo)

    @tool(**_testi("sostituisci_foto"), annotations=MODIFICA)
    def sostituisci_foto(progetto: Progetto, spread: Spread, pagina: Pagina, cornice: Annotated[int, _descr("mcp.arg_cornice", ge=1)],
                         foto: Annotated[str, _descr("mcp.arg_foto", max_length=1000)], adatta: bool = True, gruppo: Gruppo = None) -> CallToolResult:
        return risultato(a.sostituisci_foto, progetto, spread, pagina, cornice, foto, adatta, gruppo)

    @tool(**_testi("sistema_album"), annotations=MODIFICA)
    def sistema_album(progetto: Progetto, spread: ElencoSpread = None, spazi: bool = True, tono: bool | None = None, gruppo: Gruppo = None) -> CallToolResult:
        return risultato(a.sistema_album, progetto, spread, spazi, tono, gruppo)

    @tool(**_testi("annulla"), annotations=MODIFICA)
    def annulla(progetto: Progetto) -> CallToolResult:
        return risultato(a.annulla, progetto)

    @tool(**_testi("ripeti"), annotations=MODIFICA)
    def ripeti(progetto: Progetto) -> CallToolResult:
        return risultato(a.ripeti, progetto)

    @tool(**_testi("salva"), annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
    def salva(progetto: Progetto) -> CallToolResult:
        return risultato(a.salva, progetto)

    @tool(**_testi("esporta"), annotations=MODIFICA)
    def esporta(progetto: Progetto, formato: Literal["jpg", "pdf", "consegna"], spread: Annotated[str, _descr("mcp.arg_esporta_spread", max_length=200)] = "",
                risoluzione: Literal["stampa", "schermo"] = "stampa") -> CallToolResult:
        return risultato(a.esporta, progetto, formato, spread, risoluzione)

    @tool(**_testi("stato_esportazione"), annotations=LETTURA)
    def stato_esportazione(progetto: Progetto) -> CallToolResult:
        return risultato(a.stato_esportazione, progetto)

    @tool(**_testi("anteprima_spread"), annotations=IMMAGINE)
    def anteprima_spread(progetto: Progetto, spread: Spread, larghezza: Annotated[int, Field(ge=200, le=1200)] = 800) -> CallToolResult:
        return risultato(a.anteprima_spread, progetto, spread, larghezza)

    @tool(**_testi("miniatura_foto"), annotations=IMMAGINE)
    def miniatura_foto(progetto: Progetto, foto: Annotated[str, Field(max_length=1000)], lato: Annotated[int, Field(ge=64, le=512)] = 384) -> CallToolResult:
        return risultato(a.miniatura_foto, progetto, foto, lato)

    return srv


def avvia(immagini=False):
    """server MCP su stdio finché il client non chiude l'ingresso"""
    crea(S.Assistente(immagini)).run("stdio")
