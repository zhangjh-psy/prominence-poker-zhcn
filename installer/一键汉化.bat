@echo off
chcp 65001 >nul 2>&1
setlocal
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0patch.ps1" %*
if errorlevel 1 (
  echo.
  echo Installer exited with an error.
  pause >nul
)
