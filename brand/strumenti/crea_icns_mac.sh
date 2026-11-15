#!/bin/sh
# Ricrea icona/icona.icns su macOS con gli strumenti di sistema (sips, iconutil).
# Uso: sh strumenti/crea_icns_mac.sh   (dalla cartella brand/)
# Alternativa a genera_icona.py, che scrive l'.icns con Pillow anche su Linux.
set -eu
cd "$(dirname "$0")/.."
SET=$(mktemp -d)/Impaginatore.iconset
mkdir -p "$SET"
cp icona/icona-16.png   "$SET/icon_16x16.png"
cp icona/icona-32.png   "$SET/icon_16x16@2x.png"
cp icona/icona-32.png   "$SET/icon_32x32.png"
cp icona/icona-64.png   "$SET/icon_32x32@2x.png"
cp icona/icona-128.png  "$SET/icon_128x128.png"
cp icona/icona-256.png  "$SET/icon_128x128@2x.png"
cp icona/icona-256.png  "$SET/icon_256x256.png"
cp icona/icona-512.png  "$SET/icon_256x256@2x.png"
cp icona/icona-512.png  "$SET/icon_512x512.png"
cp icona/icona-1024.png "$SET/icon_512x512@2x.png"
iconutil -c icns "$SET" -o icona/icona.icns
echo "Scritto icona/icona.icns"
# macOS 26 e successivi: per l'icona a livelli (formato .icon) apri Icon Composer
# e importa icona/livelli/fondo.svg (sfondo) e icona/livelli/segno.svg (primo piano).
