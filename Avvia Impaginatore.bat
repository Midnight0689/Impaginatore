@echo off
chcp 65001 >nul
rem Doppio clic: avvia l'Impaginatore (schermata dei progetti) e apre il browser. Chiudi questa finestra per fermare tutto.
set PYTHONUTF8=1
cd /d "%~dp0Editor Album"
set "PY=%USERPROFILE%\.album-tools\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Manca l'ambiente Python: fai prima doppio clic su Installa.bat ^(una volta sola^).
  pause
  exit /b 1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
start "" cmd /c "timeout /t 2 >nul & start http://127.0.0.1:8765"
"%PY%" home.py --porta 8765
pause
