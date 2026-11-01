; Inno Setup script: wraps HushKey into a normal Windows installer.
; Installers made this way are widely trusted by antivirus software, and it
; installs per-user (no admin prompt) with a Start Menu shortcut.

#ifndef MyAppVersion
  #define MyAppVersion "2.0.7"
#endif

[Setup]
AppId={{6E4C2B1A-3F7D-4D8E-9A51-5B2C8D0E4F17}
AppName=HushKey
AppVersion={#MyAppVersion}
AppVerName=HushKey {#MyAppVersion}
AppPublisher=Erick Bardales
AppCopyright=Copyright (c) 2026 Erick Bardales
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany=Erick Bardales
VersionInfoDescription=HushKey Password Manager Setup
VersionInfoProductName=HushKey
DefaultDirName={localappdata}\Programs\HushKey
DefaultGroupName=HushKey
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=HushKey-Windows
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\HushKey.ico
SetupIconFile=..\assets\HushKey.ico
; Updating: close a running HushKey first so every file really gets replaced
CloseApplications=force
RestartApplications=no
UsePreviousAppDir=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\HushKey\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; the logo as its own file, so shortcuts can't keep showing an old cached icon
Source: "..\assets\HushKey.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\HushKey"; Filename: "{app}\HushKey.exe"; IconFilename: "{app}\HushKey.ico"
Name: "{group}\Uninstall HushKey"; Filename: "{uninstallexe}"
Name: "{userdesktop}\HushKey"; Filename: "{app}\HushKey.exe"; IconFilename: "{app}\HushKey.ico"; Tasks: desktopicon

[Run]
; ask Windows to refresh its icon memory so the new logo shows right away
Filename: "{sys}\ie4uinit.exe"; Parameters: "-show"; Flags: runhidden nowait skipifdoesntexist
Filename: "{app}\HushKey.exe"; Description: "Open HushKey now"; Flags: nowait postinstall skipifsilent
