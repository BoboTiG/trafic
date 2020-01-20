@echo off

set WORKSPACE=%USERPROFILE%\Desktop\trafic\trafic
set APP_NAME_SNAKE=trafic
set APP_NAME_DIST=trafic
set REPOSITORY_NAME=trafic

powershell -ExecutionPolicy Bypass .\packaging\windows\deploy.ps1 -install
rem powershell -ExecutionPolicy Bypass .\packaging\windows\deploy.ps1 -start
rem powershell -ExecutionPolicy Bypass .\packaging\windows\deploy.ps1 -tests
rem powershell -ExecutionPolicy Bypass .\packaging\windows\deploy.ps1 -check_upgrade
powershell -ExecutionPolicy Bypass .\packaging\windows\deploy.ps1 -build

pause
