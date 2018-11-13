﻿; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!
; >>> http://www.jrsoftware.org/ishelp/ <<<

#define MyAppName "Trafic"
#define MyAppPublisher "Schoentgen Inc"
#define MyAppURL "https://github.com/BoboTiG/trafic"
#define MyAppUpdatesURL "https://github.com/BoboTiG/trafic/releases"
#define MyAppExeName "trafic.exe"
#define MyAppVersion "0.1.0"

[Setup]
; NOTE: The value of AppId uniquely identifies this particular application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{7AE3DF21-E5B9-4438-84B6-DA8C3899FD14}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppUpdatesURL}
AppCopyright="© {#MyAppPublisher}"

; Outputs
OutputDir=../../dist
OutputBaseFilename=trafic-{#MyAppVersion}

; Startup menu entry: "Publisher/Application Name"
DefaultGroupName={#MyAppPublisher}
; Startup menu entry: "Application Name" only, i.e.: "Nuxeo Drive"
DisableProgramGroupPage=yes

; Do not require admin rights, no UAC
PrivilegesRequired=lowest

; Set the output directory to user's AppData\Local by default.
DisableDirPage=yes
DefaultDirName={param:targetdir|{localappdata}\{#MyAppName}}

; Icons
UninstallDisplayIcon={app}\{#MyAppExeName}
; 256x256px, generated from a PNG with https://convertico.com/
SetupIconFile=app_icon.ico

; Pictures
; 164x314px
;WizardImageFile=wizard.bmp
; 55x58px
WizardSmallImageFile=wizard-small.bmp

; Other
Compression=lzma
SolidCompression=yes

; Controls which files Setup will check for being in use before upgrading
CloseApplicationsFilter=*.*


[Files]
Source: "..\..\dist\trafic\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs


[UninstallDelete]
; Force the installation directory to be removed when uninstalling
Type: filesandordirs; Name: "{app}"


[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"


[Registry]
; Start at Windows boot
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletevalue


[Run]
; Launch after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall