@echo off
REM ===================================================================
REM Arrete tous les processus PowerShell executant EchoThyr.ps1
REM ===================================================================

echo.
echo ========================================
echo   ARRET ECHOTHYR MONITOR
echo ========================================
echo.

REM Recherche et arrete les processus PowerShell executant EchoThyr.ps1
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq powershell.exe" /FO LIST ^| find "PID:"') do (
    wmic process where "ProcessId=%%a and CommandLine like '%%EchoThyr.ps1%%'" delete 2>nul
)

echo Processus EchoThyr arretes.
echo.
timeout /t 3
