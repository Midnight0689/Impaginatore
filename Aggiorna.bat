@echo off
chcp 65001 >nul
rem Doppio clic: scarica da GitHub l'ultima versione dell'Impaginatore e la mette a posto.
cd /d "%~dp0"
echo === Aggiornamento Impaginatore ===
where git >nul 2>&1 || (echo Manca Git: installalo da git-scm.com e rilancia. & pause & exit /b 1)
if not exist ".git" (echo Questa cartella non e' collegata a GitHub ^(forse l'hai scaricata come ZIP^). Scarica di nuovo il programma con git clone. & pause & exit /b 1)
git fetch -q origin || (echo Non riesco a collegarmi a GitHub ^(internet? accesso?^). & pause & exit /b 1)
git pull --ff-only -q || (echo Aggiornamento non riuscito: ci sono modifiche locali? Copia il messaggio sopra e mandalo a Claude. & pause & exit /b 1)
echo Preparo l'ambiente...
call "%~dp0motore\scripts\setup.bat" || (echo Ho scaricato le novita' ma l'ambiente Python non e' pronto. Mandami il testo qui sopra. & pause & exit /b 1)
git log -1 --pretty="Versione: %%h del %%cd" --date=format:%%d/%%m/%%Y
echo Aggiornato. Riavvia il programma con "Avvia Impaginatore.bat".
pause
