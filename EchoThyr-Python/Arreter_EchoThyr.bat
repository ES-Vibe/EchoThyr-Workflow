@echo off
REM ===================================================================
REM Arrete tous les processus Python executant main.py (EchoThyr)
REM ===================================================================

echo.
echo ========================================
echo   ARRET ECHOTHYR MONITOR (PYTHON)
echo ========================================
echo.

REM Recherche et arrete les processus Python executant main.py
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
    wmic process where "ProcessId=%%a and CommandLine like '%%main.py%%'" delete 2>nul
)

echo Processus EchoThyr arretes.
echo.
timeout /t 3
