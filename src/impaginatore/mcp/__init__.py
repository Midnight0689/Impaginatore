"""Server MCP (Model Context Protocol) di Impaginatore: un assistente AI (Claude Desktop, Claude Code...) lavora sugli album.

    impaginatore mcp [--consenti-immagini]          (oppure: python -m impaginatore.mcp)

Il server parla con l'assistente su stdin/stdout e con Impaginatore in funzione come client locale (collegamento.py):
le modifiche passano dagli stessi controlli della pagina e l'utente le vede nell'editor. Gli strumenti sono in
strumenti.py, la registrazione con l'SDK ufficiale «mcp» (extra facoltativo: pip install "impaginatore[mcp]") in
server.py. Senza l'SDK il resto del programma funziona come prima e questo comando spiega come installarlo.
Architettura, strumenti e modello di minaccia: docs/architettura/MCP.md.
"""
import argparse
import sys

from .. import __version__, giornale, lingua

def main(argv=None):
    ap = argparse.ArgumentParser(prog="impaginatore mcp", description=lingua.t("mcp.aiuto_descrizione"))
    ap.add_argument("--consenti-immagini", action="store_true",
                    help=lingua.t("mcp.aiuto_immagini"))
    ap.add_argument("--versione", action="version", version=f"Impaginatore {__version__}")
    args = ap.parse_args(argv)
    try:
        from . import server
    except ImportError as e:                      # extra «mcp» non installato (o SDK di un'altra versione maggiore)
        print(f"{lingua.t('mcp.senza_sdk')} ({e})", file=sys.stderr); return 2
    giornale.configura("mcp")
    server.avvia(args.consenti_immagini)
    return 0
