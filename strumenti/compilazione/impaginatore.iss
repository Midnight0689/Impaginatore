; Installatore di Impaginatore per Windows (Inno Setup 6). Lo usa strumenti/compila.py, che passa le definizioni con /D:
; Versione, VersioneFile, Sorgente (cartella del programma compilato), Uscita, NomeFile, Icona, Autore, Licenze.
; Come e perché: docs/architettura/DISTRIBUZIONE.md. Guida per chi installa: docs/manuale/00-installazione.md.
;
; - Si installa per l'utente, senza permessi di amministratore: %LOCALAPPDATA%\Programs\Impaginatore.
; - Non è firmato (Authenticode): Windows mostra l'avviso di SmartScreen al primo avvio dell'installatore. Niente qui lo
;   aggira o lo spegne: la guida spiega cosa si vede.
; - Disinstallare toglie il programma, non gli album né le impostazioni (%APPDATA%\Impaginatore): lo dice la guida.
; - La finestra del programma usa WebView2 (c'è in Windows 10 e 11 aggiornati). Se manca, l'installatore lo dice e il
;   programma si apre nel browser: non scarica né installa niente da solo.

#ifndef Versione
  #error Manca /DVersione: l'installatore si costruisce con strumenti/compila.py
#endif

[Setup]
; identificativo dell'installazione: non cambia più (aggiornare = reinstallare sopra con lo stesso AppId)
AppId={{6C1E2B57-3F0A-4C8E-9D2B-5A7E1F4C9B30}
AppName=Impaginatore
AppVersion={#Versione}
AppVerName=Impaginatore {#Versione}
AppPublisher={#Autore}
VersionInfoVersion={#VersioneFile}
VersionInfoProductName=Impaginatore
DefaultDirName={autopf}\Impaginatore
DefaultGroupName=Impaginatore
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#Uscita}
OutputBaseFilename={#NomeFile}
SetupIconFile={#Icona}
UninstallDisplayIcon={app}\impaginatore.exe
UninstallDisplayName=Impaginatore
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=auto

[Languages]
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
it.IconaDesktop=Crea un'icona sul desktop
en.IconaDesktop=Create a desktop shortcut
it.SenzaWebView2=Su questo computer manca Microsoft Edge WebView2, che serve alla finestra del programma.%n%nImpaginatore funziona lo stesso: si apre nel browser. Per avere la finestra, installa «WebView2 Runtime» dal sito di Microsoft (la guida di installazione spiega come) e riapri Impaginatore.
en.SenzaWebView2=Microsoft Edge WebView2, which the program window needs, is missing on this computer.%n%nImpaginatore works anyway: it opens in your browser. To get the window, install «WebView2 Runtime» from Microsoft's website (the installation guide explains how) and reopen Impaginatore.
it.Avvia=Avvia Impaginatore
en.Avvia=Launch Impaginatore

[Tasks]
Name: "desktop"; Description: "{cm:IconaDesktop}"; Flags: unchecked

[Files]
Source: "{#Sorgente}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; una versione precedente: si tolgono i file del programma prima di copiare i nuovi (album e impostazioni non stanno qui)
Type: filesandordirs; Name: "{app}\*"

[Icons]
Name: "{autoprograms}\Impaginatore"; Filename: "{app}\impaginatore.exe"
Name: "{autodesktop}\Impaginatore"; Filename: "{app}\impaginatore.exe"; Tasks: desktop

[Run]
Filename: "{app}\impaginatore.exe"; Description: "{cm:Avvia}"; Flags: nowait postinstall skipifsilent

[Code]
const
  WEBVIEW2 = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function WebView2Presente(): Boolean;
var
  v: String;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + WEBVIEW2, 'pv', v) and (v <> '') and (v <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WEBVIEW2, 'pv', v) and (v <> '') and (v <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\' + WEBVIEW2, 'pv', v) and (v <> '') and (v <> '0.0.0.0'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and (not WebView2Presente()) and (not WizardSilent()) then
    MsgBox(CustomMessage('SenzaWebView2'), mbInformation, MB_OK);
end;
