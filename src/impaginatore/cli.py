"""Comando «impaginatore».

    impaginatore [--porta 8765] [--browser | --no-browser] [--progetti CARTELLA] [--versione]
                                                                                      schermata dei progetti (nella finestra
                                                                                      del programma; nel browser se la finestra
                                                                                      non c'è o con --browser)
    impaginatore editor --progetto CARTELLA [--porta N] [--home URL]                  editor di un album (di solito lo apre la schermata)
    impaginatore mcp [--consenti-immagini]                                           server MCP per un assistente AI (stdio; extra «mcp»)

Prima di tutto il lanciatore (aggiornamenti/lanciatore.py) sceglie la copia del programma da avviare: se dopo un
aggiornamento è un'altra, parte quella al posto di questo processo, con gli stessi argomenti.
"""
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    from .aggiornamenti import lanciatore
    lanciatore.avvia(argv)
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
