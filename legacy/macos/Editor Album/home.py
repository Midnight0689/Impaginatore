"""Ponte per Impaginatore.app (applet compilata delle versioni 1.x, che qui su Linux non si può ricompilare).

L'applet lancia  cd "<cartella dell'app>/Editor Album" && ~/.album-tools/venv/bin/python home.py --porta 8765 --daemon :
questo file passa gli stessi argomenti al programma vero (pacchetto impaginatore, installato in quell'ambiente da setup.sh).
"""
import sys

try:
    from impaginatore.cli import main
except ImportError:
    sys.exit("Impaginatore non è installato nell'ambiente Python: fai doppio clic su legacy/macos/Installa.command")

sys.exit(main(sys.argv[1:]))
