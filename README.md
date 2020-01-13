# Trafic

A Python desktop application that displays a systray icon with a counter about data metrics from all network adaptators. Codename: Mayonnaise.

Tested OK on:
- Debian GNU/Linux 10 (buster)
- macOS 10.14.6 (Mojave)
- Microsoft Windows 7 (SP1) and 10

## Installers

### Windows

```batch
set WORKSPACE=%USERPROFILE%\Desktop
powershell -ExecutionPolicy Bypass .\installer\windows\deploy.ps1 -install
powershell -ExecutionPolicy Bypass .\installer\windows\deploy.ps1 -build
```
