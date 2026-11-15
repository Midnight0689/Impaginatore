#!/bin/zsh
# Doppio clic: scarica da GitHub l'ultima versione dell'Impaginatore e la mette a posto (Mac secondario).
cd "$(dirname "$0")" || exit 1
ROOT="$PWD"
stop() { echo ""; echo "$1"; read -k1 "?Premi un tasto per chiudere"; exit 1; }
echo "=== Aggiornamento Impaginatore ==="
command -v git >/dev/null 2>&1 && git --version >/dev/null 2>&1 || { xcode-select --install 2>/dev/null; stop "Manca git: macOS propone di installarlo, accetta, aspetta la fine e rilancia."; }
[ -d "$ROOT/.git" ] || stop "Questa cartella non è collegata a GitHub (forse l'hai scaricata come ZIP). Scarica di nuovo il programma con git clone."
git fetch -q origin 2>&1 || stop "Non riesco a collegarmi a GitHub (internet? accesso?)."
OLD=$(git rev-parse HEAD)
git pull --ff-only -q 2>&1 || stop "Aggiornamento non riuscito: ci sono modifiche locali? Copia il messaggio sopra e mandalo a Claude."
NEW=$(git rev-parse HEAD)
if [ "$OLD" = "$NEW" ]; then echo "Già aggiornato: nessuna novità."; else
  echo "Novità:"; git log --pretty='  • %s' $OLD..$NEW
  echo "Preparo l'ambiente…"
  OUT="$(zsh "$ROOT/motore/scripts/setup.sh" 2>&1)"; RC=$?
  [ $RC -eq 0 ] || { echo "$OUT" | tail -10; stop "Ho scaricato le novità ma l'ambiente Python non è pronto. Mandami il testo qui sopra."; }
  mkdir -p "$HOME/.claude/skills"; ln -sfn "$ROOT/skill/impaginatore-stefano" "$HOME/.claude/skills/impaginatore-stefano"
  xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null; chmod +x "$ROOT"/*.command "$ROOT"/motore/scripts/*.sh 2>/dev/null
  if pgrep -f "home.py" >/dev/null; then
    echo ""; echo "Il programma è aperto: salvo i progetti e lo riavvio per usare la versione nuova."
    for p in $(seq 8801 8830); do curl -s -m 2 -X POST "http://127.0.0.1:$p/api/save" -H 'Content-Type: application/json' -d '{}' >/dev/null 2>&1; done
    pkill -f "editor.py" 2>/dev/null; pkill -f "home.py" 2>/dev/null; sleep 1
    open "$ROOT/Impaginatore.app"
  fi
  echo "Aggiornato."
fi
git log -1 --pretty='Versione: %h del %cd' --date=format:%d/%m/%Y
read -k1 "?Premi un tasto per chiudere"
