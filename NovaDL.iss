; ============================================================================
; NovaDL — Inno Setup Script v1.1
; La version se pasa desde build.bat con: ISCC /DAppVersion=1.1.0 NovaDL.iss
; ============================================================================

#define AppName      "NovaDL"
#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif
#define AppPublisher "DARK-CODE"
#define AppURL       "https://github.com/jair1c/NovaDL"
#define AppExeName   "NovaDL.exe"
#define AppMutex     "NovaDL_SingleInstance"

[Setup]
AppId={{A3F2C1B4-7E8D-4F92-B1A6-3D5E9C0F2847}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}/releases

DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes

OutputDir=installer
OutputBaseFilename=NovaDL_Setup_v{#AppVersion}

SetupIconFile=assets\icon.ico
WizardStyle=modern
WizardSizePercent=110

Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

RestartIfNeededByRun=no
AppMutex={#AppMutex}
CloseApplications=yes
CloseApplicationsFilter=*.exe

MinVersion=10.0

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "Crear acceso directo en el &Escritorio";           GroupDescription: "Accesos directos:"; Flags: unchecked
Name: "startmenuicon"; Description: "Crear acceso directo en el &Menu Inicio";          GroupDescription: "Accesos directos:"; Flags: checkedonce
Name: "startupentry";  Description: "Iniciar {#AppName} al &arrancar Windows";          GroupDescription: "Opciones adicionales:"; Flags: unchecked
Name: "associatetxt";  Description: "Asociar archivos &.txt de enlaces con {#AppName}"; GroupDescription: "Asociaciones de archivo:"; Flags: unchecked

[Files]
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\bin\*";         DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\*";           DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExeName}"; Tasks: startmenuicon
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}";       Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}";       Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: startupentry

Root: HKCR; Subkey: ".novadl";                        ValueType: string; ValueName: ""; ValueData: "NovaDL.LinkFile";  Flags: uninsdeletekey; Tasks: associatetxt
Root: HKCR; Subkey: "NovaDL.LinkFile";                ValueType: string; ValueName: ""; ValueData: "NovaDL Link File"; Flags: uninsdeletekey; Tasks: associatetxt
Root: HKCR; Subkey: "NovaDL.LinkFile\DefaultIcon";    ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; Flags: uninsdeletekey; Tasks: associatetxt
Root: HKCR; Subkey: "NovaDL.LinkFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: associatetxt

Root: HKCU; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "Version";     ValueData: "{#AppVersion}"; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName} ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\bin"
Type: filesandordirs; Name: "{app}\assets"

[Code]
function InitializeSetup(): Boolean;
var
  PrevPath: string;
  Msg: string;
begin
  Result := True;
  if RegQueryStringValue(HKCU, 'Software\DARK-CODE\NovaDL', 'InstallPath', PrevPath) then
  begin
    if DirExists(PrevPath) then
    begin
      Msg := 'Se detecto una instalacion anterior de NovaDL.' +
             ' Deseas continuar con la nueva instalacion?';
      if MsgBox(Msg, mbConfirmation, MB_YESNO) = IDNO then
        Result := False;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: string;
  Msg: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}') + '\..\' + 'novadl';
    if DirExists(DataDir) then
    begin
      Msg := 'Deseas eliminar tambien los datos de configuracion e historial de NovaDL? (' + DataDir + ')';
      if MsgBox(Msg, mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
