; Inno Setup script for Inverted Pendulum CP
; Build from Windows: Run packaging\build.bat
; Or manually: ISCC.exe packaging\windows\installer.iss

#define AppName "Inverted Pendulum CP"
#define AppVersion "0.1.0"
#define AppPublisher "MDP University Project"
#define AppExeName "InvertedPendulumCP.exe"
#define DistDir "..\..\packaging\dist\InvertedPendulumCP"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=InvertedPendulumCP_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Require MATLAB — show a warning if not detected
; (detection is best-effort via registry; MATLAB doesn't always write a key)
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Copy the entire PyInstaller output folder
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";        Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
function MatlabInstalled(): Boolean;
var
  SubKeys: TArrayOfString;
  MatlabRoot: String;
  I: Integer;
begin
  Result := False;
  // MATLAB writes version-specific subkeys: SOFTWARE\MathWorks\MATLAB\R20XXx
  if RegGetSubkeyNames(HKLM, 'SOFTWARE\MathWorks\MATLAB', SubKeys) then
    for I := 0 to GetArrayLength(SubKeys) - 1 do
      if RegQueryStringValue(HKLM, 'SOFTWARE\MathWorks\MATLAB\' + SubKeys[I], 'MATLABROOT', MatlabRoot) then
      begin
        Result := True;
        Exit;
      end;
  // Also check 32-bit registry view on 64-bit Windows
  if not Result and RegGetSubkeyNames(HKLM32, 'SOFTWARE\MathWorks\MATLAB', SubKeys) then
    for I := 0 to GetArrayLength(SubKeys) - 1 do
      if RegQueryStringValue(HKLM32, 'SOFTWARE\MathWorks\MATLAB\' + SubKeys[I], 'MATLABROOT', MatlabRoot) then
      begin
        Result := True;
        Exit;
      end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not MatlabInstalled() then
      MsgBox(
        'MATLAB does not appear to be installed on this machine.' + #13#10 +
        'Inverted Pendulum CP requires MATLAB to run simulations.' + #13#10#13#10 +
        'Please install MATLAB before launching the app.',
        mbInformation, MB_OK
      );
  end;
end;
