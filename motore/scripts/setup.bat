@echo off
rem Prepara l'ambiente Python degli strumenti album su Windows (una volta per PC). Si puo rilanciare quando vuoi.
rem Ambiente in %USERPROFILE%\.album-tools\venv. Esce con 0 solo se tutto funziona davvero.
setlocal
set "V=%USERPROFILE%\.album-tools\venv"
set "PYEXE="
for %%c in (py python3 python) do (
  if not defined PYEXE (
    %%c -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1 && set "PYEXE=%%c"
  )
)
if not defined PYEXE (
  echo ERRORE: manca Python 3.9 o piu recente. Installalo da python.org e spunta "Add python.exe to PATH" 1>&2
  exit /b 1
)
if exist "%V%\Scripts\python.exe" "%V%\Scripts\python.exe" -c "import sys" >nul 2>&1 || (if exist "%V%" (echo ambiente Python rovinato: lo ricreo & rmdir /s /q "%V%"))
if not exist "%V%\Scripts\python.exe" (
  if not exist "%USERPROFILE%\.album-tools" mkdir "%USERPROFILE%\.album-tools"
  %PYEXE% -m venv "%V%" || (echo ERRORE: non riesco a creare l'ambiente Python 1>&2 & exit /b 1)
)
"%V%\Scripts\python.exe" -m pip install -q --disable-pip-version-check --timeout 30 --retries 2 "pillow>=10,<14" "numpy>=1.26,<3" "opencv-python-headless>=4.8,<5" "psd-tools>=1.9,<2"
"%V%\Scripts\python.exe" -c "import PIL, numpy, cv2, psd_tools; assert hasattr(cv2,'CascadeClassifier')" >nul 2>&1 || (echo ERRORE: le librerie non si caricano o non sono state scaricate ^(c'e internet?^) 1>&2 & exit /b 1)
"%V%\Scripts\python.exe" -c "import tkinter" >nul 2>&1 || echo ATTENZIONE: manca tkinter in Python: le finestre per scegliere foto e cartelle non si apriranno. Reinstalla Python da python.org.
"%V%\Scripts\python.exe" -c "import cv2,sys; print('ok', cv2.__version__, 'python', sys.version.split()[0])"
exit /b 0
