#!/bin/zsh
# Doppio clic: prepara questo Mac per l'Impaginatore (una volta sola; si può rilanciare quando vuoi).
cd "$(dirname "$0")/../.." || exit 1
ROOT="$PWD"; APP="$ROOT/legacy/macos"
stop() { echo ""; echo "$1"; read -k1 "?Premi un tasto per chiudere"; exit 1; }
echo "=== Installazione Impaginatore ==="
case "$ROOT" in /Volumes/*|*"/AppTranslocation/"*) stop "La cartella è su un disco esterno o in una posizione temporanea. Copiala in Documenti e rilancia da lì.";; esac
echo "1/4  Ambiente Python (può volere qualche minuto la prima volta)…"
OUT="$(zsh "$APP/setup.sh" 2>&1)"; RC=$?
if [ $RC -ne 0 ]; then
  echo "$OUT" | tail -12
  if ! python3 -c 'import sys' >/dev/null 2>&1; then xcode-select --install 2>/dev/null; echo "(macOS sta proponendo di installare gli strumenti per sviluppatori: accetta, aspetta la fine e rilancia questo file)"; fi
  stop "Installazione NON riuscita. Copia il testo qui sopra e mandalo a Claude."
fi
echo "$OUT" | grep -E "^ok|ATTENZIONE" | sed 's/^/     /'
echo "2/4  Skill per Claude…"
mkdir -p "$HOME/.claude/skills"
ln -sfn "$ROOT/skill/impaginatore-stefano" "$HOME/.claude/skills/impaginatore-stefano" && echo "     skill collegata (si aggiorna insieme al programma)"
echo "3/4  Permessi dell'app…"
xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null; chmod +x "$APP"/*.command "$APP"/*.sh 2>/dev/null; echo "     ok"
echo "4/4  Controlli…"
PY="$HOME/.album-tools/venv/bin/python"
ls -d /Applications/Adobe\ Photoshop\ 20*/ >/dev/null 2>&1 && echo "     Photoshop: trovato" || echo "     ATTENZIONE: Photoshop non trovato in /Applications (serve solo per esportare i PSD)"
"$PY" - <<PYEOF
from impaginatore.motore import testo
fam = {f["fam"] for f in testo.fonts()}
for n in ("Bodoni Moda", "Avenir Next"):
    print("     font", n + ":", "trovato" if any(x.startswith(n) for x in fam) else "manca (i testi useranno un altro carattere finché non lo installi)")
PYEOF
git -C "$ROOT" log -1 --pretty='     versione: %h del %cd' --date=format:%d/%m/%Y 2>/dev/null
echo ""
echo "Fatto. Per aprire il programma: doppio clic su legacy/macos/Impaginatore.app (o 'Avvia Impaginatore.command')."
read -k1 "?Premi un tasto per chiudere"
