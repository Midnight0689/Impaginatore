#!/bin/zsh
# Doppio clic: avvia l'Impaginatore (schermata dei progetti) e apre il browser. Chiudi questa finestra per fermare tutto.
cd "$(dirname "$0")/../.." || exit 1
PY="$HOME/.album-tools/venv/bin/python"
[ -x "$PY" ] || { echo "Manca l'ambiente Python: fai prima doppio clic su Installa.command (una volta sola)."; read -k1; exit 1; }
lsof -ti tcp:8765 | xargs kill 2>/dev/null; sleep 1
exec "$PY" -m impaginatore --porta 8765          # apre da solo il browser
