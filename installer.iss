; Temel Market - Inno Setup Script
; Produces a professional installer with uninstall support (Apps & Features)

#ifndef MyAppVersion
#define MyAppVersion "1.0.2"
#endif

#define MyAppName "Temel Market"
#define MyAppPublisher "Temel Market"
#define MyAppExeName "TemelMarket.exe"
#define MyAppId "{{A5B7E2C9-3E4C-49B6-9A88-2C1E0A7D31F2}"
#define MyOutputBase "TemelMarket-Setup-" + MyAppVersion
#ifndef MyDistDir
#define MyDistDir "dist_final\\TemelMarket"
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} V {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename={#MyOutputBase}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\temelmarket.ico
VersionInfoVersion={#MyAppVersion}
VersionInfoTextVersion=V {#MyAppVersion}
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaustu kisayolu olustur"; GroupDescription: "Ek gorevler:"; Flags: unchecked

[Files]
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "installer\install_webview2.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\install_webview2.ps1"""; StatusMsg: "WebView2 kontrol ediliyor..."; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
