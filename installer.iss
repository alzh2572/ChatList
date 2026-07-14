; Установщик ChatList. Версия передаётся при сборке:
;   iscc /DAppVersion=<версия> installer.iss
; Версия берётся из version.py через build.ps1

#ifndef AppVersion
  #define AppVersion "dev"
#endif

#define AppName "ChatList"
#define AppExeName AppName + "-" + AppVersion + ".exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=ChatList
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename={#AppName}-{#AppVersion}-setup
SetupIconFile=app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\chatlist.db"

[Code]
function InitializeUninstall(): Boolean;
begin
  Result := MsgBox(
    'Удалить программу ChatList и все её файлы из папки установки?' + #13#10 +
    'Будут удалены: исполняемый файл, журналы (logs) и база данных (chatlist.db).',
    mbConfirmation, MB_YESNO) = IDYES;
end;
