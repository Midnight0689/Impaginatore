#!/bin/zsh
# Prepara l'ambiente Python degli strumenti album (una volta per Mac). Idempotente: si può rilanciare quando vuoi.
# Ambiente in ~/.album-tools/venv (lo usa Impaginatore.app), con dentro il programma (pacchetto impaginatore, modalità
# modificabile: si aggiorna con git pull). Esce con 0 solo se tutto funziona davvero; altrimenti scrive cosa non va.
V="$HOME/.album-tools/venv"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
fail() { echo "ERRORE: $1" >&2; exit 1; }

# 1. serve un Python 3.11+ che funzioni (il «python3» finto di macOS senza strumenti sviluppatori non conta; quello degli
#    strumenti sviluppatori è 3.9: troppo vecchio, serve quello di python.org o di Homebrew)
SYS=""
for c in python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then SYS="$c"; break; fi
done
[ -n "$SYS" ] || fail "manca Python 3.11 o più recente (installalo da python.org)"

# 2. ambiente: se esiste ma è rotto (Python aggiornato, cartella a metà) lo rifaccio da zero
if [ -e "$V" ] && ! "$V/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
  echo "ambiente Python rovinato: lo ricreo"; rm -rf "$V"
fi
if [ ! -x "$V/bin/python" ]; then
  mkdir -p "$HOME/.album-tools" || fail "non riesco a creare ~/.album-tools"
  "$SYS" -m venv "$V" || { rm -rf "$V"; fail "non riesco a creare l'ambiente Python"; }
fi

# 3. programma e librerie (versioni compatibili in pyproject.toml: opencv 5 non ha più CascadeClassifier, si resta su 4.x)
LOG="$(mktemp -t albumsetup)"
"$V/bin/pip" install -q --disable-pip-version-check --timeout 30 --retries 2 -e "$ROOT" >"$LOG" 2>&1
RC=$?
if ! "$V/bin/python" -c "import PIL, numpy, cv2, psd_tools, impaginatore; assert hasattr(cv2,'CascadeClassifier')" >/dev/null 2>&1; then
  echo "--- ultime righe dell'installazione ---" >&2; tail -8 "$LOG" >&2; rm -f "$LOG"
  if [ $RC -ne 0 ]; then fail "non sono riuscito a scaricare le librerie (c'è internet?)"; else fail "le librerie non si caricano"; fi
fi
rm -f "$LOG"
echo "ok $("$V/bin/python" -c 'import cv2,sys,impaginatore; print("impaginatore", impaginatore.__version__, "opencv", cv2.__version__, "python", sys.version.split()[0])')"
ls -d /Applications/Adobe\ Photoshop\ 20*/ 2>/dev/null | head -1 || echo "ATTENZIONE: Photoshop non trovato in /Applications (serve solo per i PSD)"
echo "$V/bin/python"
