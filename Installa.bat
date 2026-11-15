@echo off
chcp 65001 >nul
rem Doppio clic: prepara questo PC Windows per l'Impaginatore (una volta sola; si puo rilanciare quando vuoi).
cd /d "%~dp0"
echo === Installazione Impaginatore (Windows) ===
echo %CD% | findstr /i "Temp AppData\Local\Temp" >nul && (echo La cartella e' in una posizione temporanea ^(forse apri lo ZIP senza estrarlo^). Estrai tutto in Documenti e rilancia da li. & pause & exit /b 1)
echo 1/2  Ambiente Python ^(puo volere qualche minuto la prima volta^)...
call "%~dp0motore\scripts\setup.bat"
if errorlevel 1 (
  echo.
  echo Installazione NON riuscita. Copia il testo qui sopra e mandalo a Claude o a Stefano.
  pause
  exit /b 1
)
echo 2/2  Controlli...
powershell -NoProfile -Command "$f = Get-ChildItem 'C:\Windows\Fonts','$env:LOCALAPPDATA\Microsoft\Windows\Fonts' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name; foreach ($n in 'Bodoni','Avenir') { if ($f -match $n) { Write-Host \"     font $n : trovato\" } else { Write-Host \"     font $n : manca (i testi useranno un altro carattere finche non lo installi)\" } }"
echo.
echo Fatto. Per aprire il programma: doppio clic su "Avvia Impaginatore.bat".
echo Nota: i PSD per Photoshop per ora si generano solo dal Mac; su Windows si esportano JPG e PDF.
pause
