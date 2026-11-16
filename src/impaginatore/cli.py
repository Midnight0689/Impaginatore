"""Comando «impaginatore».

    impaginatore [--porta 8765] [--browser | --no-browser] [--progetti CARTELLA] [--versione]
                                                                                      schermata dei progetti (nella finestra
                                                                                      del programma; nel browser se la finestra
                                                                                      non c'è o con --browser)
    impaginatore editor --progetto CARTELLA [--porta N] [--home URL]                  editor di un album (di solito lo apre la schermata)
    impaginatore mcp [--consenti-immagini]                                           server MCP per un assistente AI (stdio; extra «mcp»)
"""
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["editor"]:
        from .editor import server
        return server.main(argv[1:])
    if argv[:1] == ["mcp"]:
        from . import mcp
        return mcp.main(argv[1:])
    from .home import server
    return server.main(argv)


if __name__ == "__main__":
    sys.exit(main())
