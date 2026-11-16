"""Comando «impaginatore».

    impaginatore [--porta 8765] [--browser | --no-browser] [--progetti CARTELLA] [--versione]
                                                                                      schermata dei progetti (nella finestra
                                                                                      del programma; nel browser se la finestra
                                                                                      non c'è o con --browser)
    impaginatore editor --progetto CARTELLA [--porta N] [--home URL]                  editor di un album (di solito lo apre la schermata)
    impaginatore mcp [--consenti-immagini]                                           server MCP per un assistente AI (stdio; extra «mcp»)

Prima di tutto il lanciatore (aggiornamenti/lanciatore.py) sceglie la copia del programma da avviare: se dopo un
aggiornamento è un'altra, parte quella al posto di questo processo, con gli stessi argomenti. Il programma compilato
(compilato.py, T-302) si prepara ancora prima e non usa copie: si sostituisce intero.
I sottocomandi interni (_psd, _dialogo, _rilancia: compilato.INTERNI) li usano solo i processi che il programma lancia da sé.
"""
import sys

from . import compilato


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if compilato.attivo(): compilato.prepara()
    from .aggiornamenti import lanciatore
    lanciatore.avvia(argv)
    if argv[:1] and argv[0] in compilato.INTERNI: return compilato.interno(argv[0], argv[1:])
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
