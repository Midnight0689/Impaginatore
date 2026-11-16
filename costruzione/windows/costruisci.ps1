# Costruisce e prova il pacchetto di Impaginatore per: Windows 10 e 11 a 64 bit (x64).
# Va lanciato su un PC Windows x64. Lo stesso pacchetto vale per Windows 11 sui PC ARM, che lo esegue in emulazione.
# Uso e risultato: costruzione\LEGGIMI.md
#
#   powershell -ExecutionPolicy Bypass -File costruzione\windows\costruisci.ps1 [-SenzaProva] [-Pulisci] [-Controlla]
#
#   -SenzaProva   costruisce l'installatore ma non prova il programma (senza prova non entra in una release)
#   -Pulisci      cancella prima build\compila\windows (la cache del compilatore resta)
#   -Controlla    controlla solo che il computer abbia quello che serve, senza costruire
#
# Fa gli stessi passi della pipeline (.github/workflows/pacchetti.yml): ambiente, compilazione, installatore, prova.
# Non installa niente nel sistema. La prova usa il programma compilato nella cartella di costruzione: non installa e non
# disinstalla Impaginatore su questo PC (l'installatore lo prova la pipeline, su una macchina usa e getta).
param([switch]$SenzaProva, [switch]$Pulisci, [switch]$Controlla)

$ErrorActionPreference = "Stop"
$Chiave = "windows"
$Radice = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Ambiente = Join-Path $Radice ".venv-compilazione"
$Py = Join-Path $Ambiente "Scripts\python.exe"
$Uscita = Join-Path $Radice "dist\pacchetti"

function Dico($t) { Write-Host ""; Write-Host "==> $t" }
function Fermo($t) { Write-Host ""; Write-Host "ERRORE: $t" -ForegroundColor Red; exit 1 }
function Esegui($cosa, [scriptblock]$comando) {
    & $comando
    if ($LASTEXITCODE -ne 0) { Fermo "$cosa non è andato (codice $LASTEXITCODE)" }
}

# ---- il computer è quello giusto e ha gli strumenti? Elenca tutto quello che manca in una volta sola
Dico "Controllo del computer ($Chiave)"
if ($env:OS -ne "Windows_NT") { Fermo "questo script è per Windows: usa costruzione/<sistema> del tuo computer" }
$macchina = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
if ($macchina -ne "AMD64") { Fermo "questo script è per un PC x64 (AMD64), questo è $macchina. Su Windows ARM il pacchetto non si costruisce (mancano librerie per ARM): si usa quello x64, che Windows 11 ARM esegue in emulazione" }
$mancanti = @()
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { $mancanti += "git:  https://git-scm.com/download/win" }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { $mancanti += "uv (installa Python 3.12 e le librerie):  https://docs.astral.sh/uv/getting-started/installation/" }
$iscc = @((Get-Command iscc -ErrorAction SilentlyContinue).Source, "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) { $mancanti += "Inno Setup 6 (costruisce l'installatore):  https://jrsoftware.org/isdl.php" }
if ($mancanti.Count -gt 0) {
    Write-Host ""; Write-Host "Manca qualcosa su questo computer:"
    $mancanti | ForEach-Object { Write-Host "  - $_" }
    Fermo "installa quello che manca e rilancia lo script"
}
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$msvc = if (Test-Path $vswhere) { & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath } else { $null }
if (-not $msvc) { Write-Host "Nota: non trovo il compilatore di Visual Studio (MSVC). Nuitka scarica e usa MinGW64 da solo; la pipeline usa MSVC, quindi il pacchetto può differire da quello della pipeline." }
Write-Host "Tutto quello che serve c'è."
if ($Controlla) { exit 0 }

# ---- che cosa si sta per costruire: versione, commit, modifiche non salvate
Set-Location $Radice
$riga = Select-String -Path "src\impaginatore\__init__.py" -Pattern '^__version__ = "([^"]+)"' | Select-Object -First 1
if (-not $riga) { Fermo "non trovo la versione in src\impaginatore\__init__.py" }
$Versione = $riga.Matches[0].Groups[1].Value
$commit = (& git rev-parse --short HEAD)
Dico "Impaginatore $Versione, commit $commit"
$modifiche = (& git status --porcelain --untracked-files=no)
if ($modifiche -and $env:ACCETTA_MODIFICHE -ne "1") {
    Write-Host "ATTENZIONE: ci sono modifiche non salvate in un commit. Il pacchetto non corrisponderebbe a nessun commit:"
    $modifiche | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" }
    Fermo "per un pacchetto da distribuire rimetti a posto il codice (git status). Per provare lo stesso: `$env:ACCETTA_MODIFICHE = '1'"
}
$Pacchetto = Join-Path $Uscita "Impaginatore-$Versione-$Chiave.exe"

# ---- ambiente
Dico "Ambiente di compilazione (Python 3.12, finestra, MCP, Nuitka) in .venv-compilazione"
$env:UV_PROJECT_ENVIRONMENT = $Ambiente
if (-not $env:NUITKA_CACHE_DIR) { $env:NUITKA_CACHE_DIR = Join-Path $Radice "build\cache-nuitka" }
Esegui "uv sync" { uv sync --locked --python 3.12 --extra desktop --extra mcp --extra compilazione }

# ---- compilazione e installatore
if ($Pulisci) { Dico "Pulizia di build\compila\$Chiave"; Remove-Item -Recurse -Force (Join-Path $Radice "build\compila\$Chiave") -ErrorAction SilentlyContinue }
foreach ($f in @($Pacchetto, "$Pacchetto.sha256", "$Pacchetto.componenti.json", (Join-Path $Uscita "verifica-$Chiave.json"))) { Remove-Item -Force $f -ErrorAction SilentlyContinue }
Dico "Compilazione e installatore (la prima volta 25-45 minuti; il computer resta usabile)"
$inizio = Get-Date
Esegui "compila.py" { & $Py strumenti\compila.py }
if (-not (Test-Path $Pacchetto)) { Fermo "compila.py non ha lasciato $Pacchetto" }
Write-Host ("Fatto in {0:N0} minuti." -f ((Get-Date) - $inizio).TotalMinutes)

# ---- prova: tutti i controlli e la finestra vera, sul programma compilato (senza installarlo)
if (-not $SenzaProva) {
    Dico "Prova del programma compilato (si apre una finestra per circa un minuto: non toccarla)"
    $programma = Join-Path $Radice "build\compila\$Chiave\Impaginatore\impaginatore.exe"
    & $Py strumenti\verifica_pacchetto.py $programma --finestra --architettura x86_64 --rapporto (Join-Path $Uscita "verifica-$Chiave.json")
    if ($LASTEXITCODE -ne 0) { Fermo "la prova non è passata (sopra il controllo che non va; rapporto in dist\pacchetti\verifica-$Chiave.json). Il pacchetto non va distribuito" }
}

# ---- riepilogo
Dico "Pronto"
Get-ChildItem $Uscita | Where-Object { $_.Name -like "Impaginatore-$Versione-$Chiave.exe*" -or $_.Name -eq "verifica-$Chiave.json" } | ForEach-Object { Write-Host ("  {0,8:N1} MB  {1}" -f ($_.Length / 1MB), $_.Name) }
Write-Host ("Impronta SHA-256: " + ((Get-Content "$Pacchetto.sha256" -Raw) -split " ")[0])
if ($SenzaProva) {
    Write-Host "Costruito senza prova: per una release rifai senza -SenzaProva."
} else {
    Write-Host ""
    Write-Host "Che cosa mandare a chi pubblica la release: tutta la cartella"
    Write-Host "  $Uscita"
    Write-Host "(l'installatore, il file .sha256, il file .componenti.json e verifica-$Chiave.json). Chi pubblica la aggiunge alla"
    Write-Host "release in bozza con:  python strumenti/rilascio.py aggiungi v$Versione <cartella ricevuta>"
}
