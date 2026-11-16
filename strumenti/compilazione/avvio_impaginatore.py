"""Punto d'ingresso del programma compilato (strumenti/compila.py): fa quello che fa il comando «impaginatore».

Non si chiama impaginatore.py: accanto al pacchetto con lo stesso nome lo nasconderebbe durante la compilazione.
"""
import sys

from impaginatore.cli import main

if __name__ == "__main__":
    sys.exit(main())
