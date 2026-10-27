#!/bin/zsh
# Doppio clic: scarica da GitHub l'ultima versione dell'Impaginatore e la mette a posto (Mac secondario).
cd "$(dirname "$0")" || exit 1
ROOT="$PWD"
echo "=== Aggiornamento Impaginatore ==="
command -v git >/dev/null 2>&1 || { echo "Manca git: macOS propone di installarlo, accetta e rilancia."; xcode-select --install 2>/dev/null; read -k1 "?Premi un tasto"; exit 1; }
git fetch -q origin 2>&1 || { echo "Non riesco a collegarmi a GitHub (internet? accesso?)."; read -k1 "?Premi un tasto"; exit 1; }
OLD=$(git rev-parse HEAD); git pull --ff-only -q 2>&1 || { echo "Aggiornamento non riuscito: ci sono modifiche locali? Scrivimi il messaggio sopra."; read -k1 "?Premi un tasto"; exit 1; }
NEW=$(git rev-parse HEAD)
if [ "$OLD" = "$NEW" ]; then echo "Già aggiornato: nessuna novità."; else
  echo "Novità:"; git log --pretty='  • %s' $OLD..$NEW
  zsh "$ROOT/motore/scripts/setup.sh" >/dev/null 2>&1
  ln -sfn "$ROOT/skill/impaginatore-stefano" "$HOME/.claude/skills/impaginatore-stefano"
  xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null; chmod +x "$ROOT"/*.command 2>/dev/null
  if pgrep -f "home.py" >/dev/null; then
    echo ""; echo "Il programma è aperto: lo riavvio per usare la versione nuova."
    pkill -f "editor.py" 2>/dev/null; pkill -f "home.py" 2>/dev/null; sleep 1
    open "$ROOT/Impaginatore.app"
  fi
  echo "Aggiornato."
fi
read -k1 "?Premi un tasto per chiudere"
