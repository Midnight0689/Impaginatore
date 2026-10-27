#!/bin/zsh
# Prepara l'ambiente Python degli strumenti album (una volta per Mac). Idempotente.
# Ambiente in ~/.album-tools/venv; stampa il percorso del python da usare.
set -e
V="$HOME/.album-tools/venv"
if [ ! -x "$V/bin/python" ]; then
  python3 -m venv "$V"
fi
"$V/bin/pip" install -q --upgrade pip >/dev/null 2>&1 || true
# opencv 5 non ha più CascadeClassifier: restare su 4.x
"$V/bin/pip" install -q pillow numpy "opencv-python-headless<5" psd-tools 2>&1 | grep -v -i notice || true
"$V/bin/python" -c "import PIL, numpy, cv2, psd_tools; assert hasattr(cv2,'CascadeClassifier'); print('ok', cv2.__version__)"
ls -d /Applications/Adobe\ Photoshop\ 20*/ 2>/dev/null | head -1 || echo "ATTENZIONE: Photoshop non trovato in /Applications"
echo "$V/bin/python"
