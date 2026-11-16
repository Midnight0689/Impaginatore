#!/usr/bin/env bash
# Parte comune degli script di costruzione di Impaginatore per macOS e Linux (costruzione/LEGGIMI.md).
# Non si lancia da sola: la leggono costruzione/<sistema>/costruisci.sh, che prima fissano
#   CHIAVE         mac-arm64 | mac-x86_64 | linux | linux-arm64  (il nome del pacchetto, come in strumenti/compila.py)
#   SISTEMA        Darwin | Linux                                 (uname -s atteso)
#   MACCHINA       arm64 | x86_64 | aarch64                       (uname -m atteso)
#   ARCHITETTURA   arm64 | x86_64                                 (quella che deve avere l'eseguibile)
# e, sui Mac, MACOS_MINIMO (uguale a compila.MACOS_MINIMO) e PIATTAFORMA_UV.
# Fa gli stessi passi della pipeline (.github/workflows/pacchetti.yml): ambiente, compilazione, pacchetto, prova.
# Non installa niente nel sistema e non chiede la password: se manca uno strumento dice quale e come metterlo.
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AMBIENTE="$RADICE/.venv-compilazione"
PY="$AMBIENTE/bin/python"
USCITA="$RADICE/dist/pacchetti"

dico()   { printf '\n==> %s\n' "$*"; }
fermo()  { printf '\nERRORE: %s\n' "$*" >&2; exit 1; }
manca()  { MANCANTI+=("$1"); }

uso() {
  cat <<FINE
Uso: costruzione/$CHIAVE/costruisci.sh [opzioni]

  --senza-prova   costruisce il pacchetto ma non prova il programma (senza prova non entra in una release)
  --pulisci       cancella prima build/compila/$CHIAVE (la cache del compilatore resta)
  --controlla     controlla solo che il computer abbia quello che serve, senza costruire
  -h, --aiuto     questo testo

Risultato in dist/pacchetti: il pacchetto, la sua impronta (.sha256), l'elenco dei componenti e il rapporto della prova.
FINE
}

leggi_opzioni() {
  PROVA=1; PULISCI=0; SOLO_CONTROLLO=0
  for o in "$@"; do
    case "$o" in
      --senza-prova) PROVA=0 ;;
      --pulisci) PULISCI=1 ;;
      --controlla) SOLO_CONTROLLO=1 ;;
      -h|--aiuto|--help) uso; exit 0 ;;
      *) uso >&2; fermo "opzione sconosciuta: $o" ;;
    esac
  done
}

# il computer è quello giusto e ha gli strumenti? Elenca tutto quello che manca in una volta sola
controlla_computer() {
  dico "Controllo del computer ($CHIAVE)"
  [ "$(uname -s)" = "$SISTEMA" ] || fermo "questo script è per $SISTEMA, qui c'è $(uname -s): usa costruzione/<sistema> del tuo computer"
  local m; m="$(uname -m)"
  if [ "$m" != "$MACCHINA" ]; then
    fermo "questo script è per un computer $MACCHINA, questo è $m. Il pacchetto $CHIAVE si costruisce solo su un computer $MACCHINA (Nuitka non compila per un'altra architettura)"
  fi
  MANCANTI=()
  if [ "$SISTEMA" = Darwin ]; then
    # un Terminale aperto «con Rosetta» su un Mac con chip Apple direbbe x86_64 qui sopra; questo lo dice chiaro
    [ "$(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)" = 1 ] && fermo "il Terminale gira con Rosetta: Applicazioni › Utility › Terminale › Ottieni informazioni › togli «Apri con Rosetta»"
    xcode-select -p >/dev/null 2>&1 || manca "strumenti a riga di comando di Xcode (compilatore C):  xcode-select --install"
    for s in codesign hdiutil ditto otool lipo; do command -v "$s" >/dev/null || manca "$s (arriva con macOS e con gli strumenti di Xcode)"; done
    local v; v="$(sw_vers -productVersion)"
    [ "$(printf '%s\n%s\n' "$MACOS_MINIMO" "$v" | sort -V | head -1)" = "$MACOS_MINIMO" ] || fermo "serve macOS $MACOS_MINIMO o successivo per costruire, qui c'è $v"
    if [ "$CHIAVE" = mac-x86_64 ]; then    # cryptography non ha ruote per i Mac Intel: uv la costruisce con Rust e OpenSSL 3
      command -v brew >/dev/null || manca "Homebrew (per OpenSSL 3 e Rust):  https://brew.sh"
      command -v cargo >/dev/null || manca "Rust:  brew install rust"
      { command -v brew >/dev/null && brew list --versions openssl@3 >/dev/null 2>&1; } || manca "OpenSSL 3:  brew install openssl@3"
    fi
  else
    command -v gcc >/dev/null || manca "compilatore C:  sudo apt install build-essential"
    command -v dpkg-deb >/dev/null || manca "dpkg-deb:  sudo apt install dpkg"
    if [ "$PROVA" = 1 ]; then    # la finestra è quella del sistema: serve per provare il programma, non per compilarlo
      /usr/bin/python3 -c "import gi; gi.require_version('Gtk','3.0'); gi.require_version('WebKit2','4.1')" 2>/dev/null \
        || manca "finestra del sistema (GTK e WebKit):  sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1"
      if [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
        command -v xvfb-run >/dev/null || manca "schermo finto per la prova senza schermo:  sudo apt install xvfb xauth x11-apps"
      fi
    fi
  fi
  command -v git >/dev/null || manca "git"
  command -v uv >/dev/null || manca "uv (installa Python 3.12 e le librerie):  https://docs.astral.sh/uv/getting-started/installation/"
  if [ "${#MANCANTI[@]}" -gt 0 ]; then
    printf '\nManca qualcosa su questo computer:\n' >&2
    printf '  - %s\n' "${MANCANTI[@]}" >&2
    fermo "installa quello che manca e rilancia lo script"
  fi
  command -v ccache >/dev/null || echo "Nota: senza ccache la seconda compilazione non è più veloce della prima (facoltativo: $([ "$SISTEMA" = Darwin ] && echo 'brew install ccache' || echo 'sudo apt install ccache'))."
  echo "Tutto quello che serve c'è."
}

# che cosa si sta per costruire: versione, commit, modifiche non salvate
dichiara_sorgente() {
  cd "$RADICE"
  VERSIONE="$(sed -n 's/^__version__ = "\([^"]*\)".*/\1/p' src/impaginatore/__init__.py)"
  [ -n "$VERSIONE" ] || fermo "non trovo la versione in src/impaginatore/__init__.py"
  local commit dove
  commit="$(git rev-parse --short HEAD)"
  dove="$(git describe --tags --exact-match 2>/dev/null || git rev-parse --abbrev-ref HEAD)"
  dico "Impaginatore $VERSIONE, commit $commit ($dove)"
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "ATTENZIONE: ci sono modifiche non salvate in un commit. Il pacchetto non corrisponderà a nessun commit:"
    git status --short --untracked-files=no | head -10
    [ "${ACCETTA_MODIFICHE:-0}" = 1 ] || fermo "per un pacchetto da distribuire rimetti a posto il codice (git status). Per provare lo stesso: ACCETTA_MODIFICHE=1"
  fi
  PACCHETTO="$USCITA/Impaginatore-$VERSIONE-$CHIAVE.$([ "$SISTEMA" = Darwin ] && echo dmg || echo deb)"
}

prepara_ambiente() {
  dico "Ambiente di compilazione (Python 3.12, finestra, MCP, Nuitka) in .venv-compilazione"
  export UV_PROJECT_ENVIRONMENT="$AMBIENTE"
  export NUITKA_CACHE_DIR="${NUITKA_CACHE_DIR:-$RADICE/build/cache-nuitka}"
  local piattaforma=()
  if [ "$SISTEMA" = Darwin ]; then
    # versione minima di macOS: uv sceglie le ruote per lei e compila.py la confronta con compila.MACOS_MINIMO
    export MACOSX_DEPLOYMENT_TARGET="$MACOS_MINIMO"
    piattaforma=(--python-platform "$PIATTAFORMA_UV")
    if [ "$CHIAVE" = mac-x86_64 ]; then
      OPENSSL_DIR="$(brew --prefix openssl@3)"; export OPENSSL_DIR OPENSSL_STATIC=1
    fi
  fi
  uv sync --locked --python 3.12 --extra desktop --extra mcp --extra compilazione ${piattaforma[@]+"${piattaforma[@]}"}
}

compila() {
  [ "$PULISCI" = 1 ] && { dico "Pulizia di build/compila/$CHIAVE"; rm -rf "$RADICE/build/compila/$CHIAVE"; }
  rm -f "$PACCHETTO" "$PACCHETTO.sha256" "$PACCHETTO.componenti.json" "$USCITA/verifica-$CHIAVE.json"
  dico "Compilazione e pacchetto (la prima volta 15–40 minuti; il computer resta usabile)"
  local inizio; inizio=$(date +%s)
  "$PY" strumenti/compila.py
  [ -f "$PACCHETTO" ] || fermo "compila.py non ha lasciato $PACCHETTO"
  echo "Fatto in $(( ($(date +%s) - inizio) / 60 )) minuti."
}

# la prova che fa la pipeline: tutti i controlli e la finestra vera. Sui Mac dal DMG montato, come lo vedrà chi installa
prova() {
  local programma prima=() esito=0
  if [ "$SISTEMA" = Darwin ]; then
    MONTATO="$(mktemp -d "${TMPDIR:-/tmp}/impaginatore-dmg.XXXXXX")"
    trap 'hdiutil detach "$MONTATO" >/dev/null 2>&1 || true; rmdir "$MONTATO" 2>/dev/null || true' EXIT
    dico "Prova del programma dal DMG (si apre una finestra per circa un minuto: non toccarla)"
    hdiutil attach -nobrowse -readonly -mountpoint "$MONTATO" "$PACCHETTO" >/dev/null
    codesign --verify --deep --strict "$MONTATO/Impaginatore.app"
    programma="$MONTATO/Impaginatore.app/Contents/MacOS/impaginatore-app"
    echo "Architettura: $(lipo -archs "$programma"); macOS minimo: $(plutil -extract LSMinimumSystemVersion raw "$MONTATO/Impaginatore.app/Contents/Info.plist")"
  else
    dico "Prova del programma compilato (si apre una finestra per circa un minuto: non toccarla)"
    programma="$RADICE/build/compila/$CHIAVE/Impaginatore/impaginatore-app"
    [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && prima=(xvfb-run -a -s "-screen 0 1280x800x24")
  fi
  ${prima[@]+"${prima[@]}"} "$PY" strumenti/verifica_pacchetto.py "$programma" --finestra --architettura "$ARCHITETTURA" \
    --rapporto "$USCITA/verifica-$CHIAVE.json" ${RIEPILOGO:+--riepilogo "$RIEPILOGO"} || esito=$?
  [ "$esito" = 0 ] || fermo "la prova non è passata (sopra il controllo che non va; rapporto in dist/pacchetti/verifica-$CHIAVE.json). Il pacchetto non va distribuito"
}

riepilogo() {
  dico "Pronto"
  local f
  for f in "$PACCHETTO" "$PACCHETTO.sha256" "$PACCHETTO.componenti.json" "$USCITA/verifica-$CHIAVE.json"; do
    # senza prova il rapporto non c'è: si elenca solo quello che esiste
    [ -f "$f" ] && printf '  %10s byte  %s\n' "$(wc -c < "$f" | tr -d ' ')" "$(basename "$f")"
  done
  echo "Impronta SHA-256: $(cut -d' ' -f1 "$PACCHETTO.sha256")"
  if [ "$PROVA" = 1 ]; then
    cat <<FINE

Che cosa mandare a chi pubblica la release: tutta la cartella
  $USCITA
(il pacchetto, il file .sha256, il file .componenti.json e verifica-$CHIAVE.json). Chi pubblica la aggiunge alla release
in bozza con:  python strumenti/rilascio.py aggiungi v$VERSIONE <cartella ricevuta>
FINE
  else
    echo "Costruito senza prova: per una release rifai senza --senza-prova."
  fi
}

costruisci() {
  leggi_opzioni "$@"
  controlla_computer
  [ "$SOLO_CONTROLLO" = 1 ] && exit 0
  dichiara_sorgente
  prepara_ambiente
  compila
  [ "$PROVA" = 1 ] && prova
  riepilogo
}
