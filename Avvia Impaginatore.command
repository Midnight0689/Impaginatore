#!/bin/zsh
# Doppio clic: avvia l'Impaginatore (schermata dei progetti) e apre il browser. Chiudi questa finestra per fermare tutto.
cd "$(dirname "$0")/Editor Album" || exit 1
PY="$HOME/.album-tools/venv/bin/python"
[ -x "$PY" ] || { echo "Manca l'ambiente Python: fai prima doppio clic su Installa.command (una volta sola)."; read -k1; exit 1; }
lsof -ti tcp:8765 | xargs kill 2>/dev/null; sleep 1
(sleep 2; open "http://127.0.0.1:8765") &
exec "$PY" home.py --porta 8765
