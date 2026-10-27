#!/bin/zsh
# Doppio clic: prepara questo Mac per l'Impaginatore (una volta sola; si può rilanciare quando vuoi).
cd "$(dirname "$0")" || exit 1
ROOT="$PWD"
echo "=== Installazione Impaginatore ==="
if ! command -v python3 >/dev/null 2>&1; then
  echo "Manca Python 3. macOS sta per proporti di installare gli strumenti per sviluppatori: accetta, aspetta la fine e rilancia questo file."
  xcode-select --install 2>/dev/null; read -k1 "?Premi un tasto per chiudere"; exit 1
fi
echo "1/4  Ambiente Python (può volere qualche minuto la prima volta)…"
zsh "$ROOT/motore/scripts/setup.sh" 2>&1 | tail -3 || { echo "Qualcosa non è andato: copia questo testo e mandalo a Claude."; read -k1 "?Premi un tasto"; exit 1; }
echo "2/4  Skill per Claude…"
mkdir -p "$HOME/.claude/skills"
ln -sfn "$ROOT/skill/impaginatore-stefano" "$HOME/.claude/skills/impaginatore-stefano" && echo "     skill collegata (si aggiorna insieme al programma)"
echo "3/4  Permessi dell'app…"
xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null; chmod +x "$ROOT"/*.command 2>/dev/null; echo "     ok"
echo "4/4  Controlli…"
PY="$HOME/.album-tools/venv/bin/python"
ls -d /Applications/Adobe\ Photoshop\ 20*/ >/dev/null 2>&1 && echo "     Photoshop: trovato" || echo "     ATTENZIONE: Photoshop non trovato in /Applications (serve per esportare i PSD)"
"$PY" - <<PYEOF
import sys; sys.path.insert(0, "$ROOT/Editor Album")
import testo
fam = {f["fam"] for f in testo.fonts()}
for n in ("Bodoni Moda", "Avenir Next"):
    print("     font", n + ":", "trovato" if any(x.startswith(n) for x in fam) else "MANCA (installalo, altrimenti i testi usano un font di sistema)")
PYEOF
echo ""
echo "Fatto. Per aprire il programma: doppio clic su Impaginatore.app (o 'Avvia Impaginatore.command')."
read -k1 "?Premi un tasto per chiudere"
