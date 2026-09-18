#ifndef AppVersion
  #error AppVersion must be supplied by scripts/build.ps1
#endif

[Setup]
AppId={{DD97DF4D-2674-43AC-A25C-15B8DAEE49B5}
AppName=D4Sign Central Bolsas
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\D4Sign
DefaultGroupName=D4Sign Central Bolsas
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=D4Sign-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\D4Sign.exe

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\dist\D4Sign\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\D4Sign Central Bolsas"; Filename: "{app}\D4Sign.exe"
Name: "{autodesktop}\D4Sign Central Bolsas"; Filename: "{app}\D4Sign.exe"

[Run]
Filename: "{app}\D4Sign.exe"; Description: "Abrir D4Sign Central Bolsas"; Flags: nowait postinstall skipifsilent
