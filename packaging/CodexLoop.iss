#ifndef AppName
  #define AppName "Codex Loop"
#endif
#ifndef AppVersion
  #define AppVersion "1.1.1"
#endif
#ifndef AppExeName
  #define AppExeName "CodexLoop.exe"
#endif
#ifndef AppPublisher
  #define AppPublisher "Codex Loop"
#endif
#ifndef AppId
  #define AppId "{{D469A7B2-486B-4E19-9C69-2E9EB1188BE3}"
#endif
#ifndef AppIdGuid
  #define AppIdGuid "{D469A7B2-486B-4E19-9C69-2E9EB1188BE3}"
#endif
#ifndef InstallerBaseName
  #define InstallerBaseName "CodexLoop-Setup"
#endif
#ifndef AppIconFile
  #define AppIconFile "codexloop.ico"
#endif
#ifndef DistFolder
  #define DistFolder "CodexLoop"
#endif
#ifndef PayloadDir
  #define PayloadDir "..\dist\" + DistFolder
#endif
#ifndef LegacyInstallFolder
  #define LegacyInstallFolder "Window Sentinel"
#endif
[Setup]
LicenseFile=..\LICENSE
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
UsePreviousAppDir=no
DisableDirPage=no
DirExistsWarning=auto
DefaultGroupName={#AppName}
UsePreviousGroup=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename={#InstallerBaseName}
SetupIconFile={#AppIconFile}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName},0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; IconIndex: 0
Name: "{userprograms}\{#AppName}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; IconIndex: 0

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Open {#AppName}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "{#AppName}"; Flags: uninsdeletevalue dontcreatekey

[Code]
procedure WriteRequiredString(const KeyName, ValueName, ValueData: String);
begin
  if not RegWriteStringValue(HKCU, KeyName, ValueName, ValueData) then
    RaiseException('Codex Loop could not repair its Windows app registration.');
end;

procedure RepairCodexLoopRegistration;
var
  UninstallKey: String;
  UninstallExe: String;
  InstallDir: String;
begin
  UninstallKey :=
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppIdGuid}_is1';
  UninstallExe := ExpandConstant('{uninstallexe}');
  InstallDir := AddBackslash(ExpandConstant('{app}'));

  { Every historical public build used this one AppId and registry view. }
  { Rewriting that exact record repairs beta entries that still reference }
  { the deleted Window Sentinel folder without scanning other products. }
  if not FileExists(UninstallExe) then
    RaiseException('Codex Loop could not create its canonical uninstaller.');

  WriteRequiredString(UninstallKey, 'DisplayName', '{#AppName}');
  WriteRequiredString(UninstallKey, 'DisplayVersion', '{#AppVersion}');
  WriteRequiredString(UninstallKey, 'Publisher', '{#AppPublisher}');
  WriteRequiredString(UninstallKey, 'InstallLocation', InstallDir);
  WriteRequiredString(
    UninstallKey,
    'DisplayIcon',
    ExpandConstant('{app}\{#AppExeName},0')
  );
  WriteRequiredString(
    UninstallKey,
    'UninstallString',
    '"' + UninstallExe + '"'
  );
  WriteRequiredString(
    UninstallKey,
    'QuietUninstallString',
    '"' + UninstallExe + '" /SILENT'
  );
  WriteRequiredString(UninstallKey, 'Inno Setup: App Path', ExpandConstant('{app}'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  StartupCommand: String;
begin
  if CurStep <> ssPostInstall then
    Exit;

  RepairCodexLoopRegistration;

  { Preserve the user's existing startup choice while repairing its executable. }
  if RegQueryStringValue(
    HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Run',
    '{#AppName}',
    StartupCommand
  ) then
    RegWriteStringValue(
      HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      '{#AppName}',
      '"' + ExpandConstant('{app}\{#AppExeName}') + '" --background'
    );

end;
