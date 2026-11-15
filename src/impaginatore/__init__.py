"""Impaginatore: impaginare album fotografici (spread, modelli, testi, correzioni) ed esportare JPG, PDF e PSD.

Mappa del pacchetto in docs/architettura/ARCHITETTURA.md. Importare il pacchetto o i suoi moduli non legge
progetti, non apre porte e non scrive file: tutto parte da funzioni esplicite (cli.main, home.server.crea_server,
editor.server.inizializza, motore.album.carica_progetto).
"""

__version__ = "2.0.0.dev0"          # unico posto della versione: lo leggono pyproject.toml (hatch), la schermata dei progetti e l'editor
