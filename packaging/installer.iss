; Inno Setup Script for Holographic VFX Standalone Application
; Targets: Windows x64 per-user installation (%LOCALAPPDATA%\Programs\HolographicVFX)

#define MyAppName "Holographic VFX"
#define MyAppVersion "0.1.1-dev"
#define MyAppPublisher "BikExists"
#define MyAppURL "https://github.com/BikExists/hologram-vfx"
#define MyAppExeName "HolographicVFX.exe"

[Setup]
AppId={{E680E744-8FB7-4C7D-9D22-C8592E87DCE4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://github.com/BikExists/hologram-vfx/issues
AppUpdatesURL=https://github.com/BikExists/hologram-vfx/releases
DefaultDirName={localappdata}\Programs\HolographicVFX
DisableProgramGroupPage=yes
; Per-user installation does not require administrative elevation
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=HolographicVFX-v0.1.1-dev-Windows-x64-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\HolographicVFX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
