; Author: Imaad Ullah Khan Yameen
; Email: yameenimaad@gmail.com
; This code is not for sale.
; Inno Setup script (https://jrsoftware.org/isinfo.php): turns dist\AtlasA0 into Output\AtlasA0-Setup-<version>.exe
; Build:  iscc /DMyAppVersion=1.1.0 installer\atlasa0.iss      (installer\build_windows.bat does this for you)
#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif

[Setup]
AppId={{6F0B8D43-7A5E-4C3B-9E1D-A70A5A0A0001}
AppName=AtlasA0
AppVersion={#MyAppVersion}
AppPublisher=Imaad Ullah Khan Yameen
AppPublisherURL=https://github.com/Danger-Khan/Atlas_A0
AppSupportURL=mailto:yameenimaad@gmail.com
DefaultDirName={autopf}\AtlasA0
DefaultGroupName=AtlasA0
; the PolyForm Noncommercial licence is shown and must be accepted before installing
LicenseFile=..\LICENSE
OutputDir=..\Output
OutputBaseFilename=AtlasA0-Setup-{#MyAppVersion}
SetupIconFile=..\atlasa0\assets\icons\app.ico
UninstallDisplayIcon={app}\AtlasA0.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
; no administrator rights needed: the user can choose "only for me"
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\AtlasA0\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\AtlasA0"; Filename: "{app}\AtlasA0.exe"
Name: "{group}\Uninstall AtlasA0"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AtlasA0"; Filename: "{app}\AtlasA0.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AtlasA0.exe"; Description: "Start AtlasA0"; Flags: nowait postinstall skipifsilent

; Uninstall removes the program only. Your maps (Documents\AtlasA0\output) and settings are never deleted.
