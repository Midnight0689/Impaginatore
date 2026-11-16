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

from .. import __version__, giornale

SENZA_SDK = ("Il server MCP ha bisogno dell'SDK ufficiale «mcp» (versione 2), che non è installato. "
             "Installalo con: pip install \"impaginatore[mcp]\" (oppure, da una copia del codice: uv sync --extra mcp).")


def main(argv=None):
    from . import consenso
    ap = argparse.ArgumentParser(prog="impaginatore mcp", description="Server MCP per collegare un assistente AI a Impaginatore (stdio).")
    ap.add_argument("--consenti-immagini", action="store_true",
                    help="permette agli strumenti di mandare all'assistente immagini ridotte delle foto e degli spread. " + consenso.SPIEGAZIONE.split(" Per accenderle")[0])
    ap.add_argument("--versione", action="version", version=f"Impaginatore {__version__}")
    args = ap.parse_args(argv)
    try:
        from . import server
    except ImportError as e:                      # extra «mcp» non installato (o SDK di un'altra versione maggiore)
        print(f"{SENZA_SDK} ({e})", file=sys.stderr); return 2
    giornale.configura("mcp")
    server.avvia(args.consenti_immagini)
    return 0
