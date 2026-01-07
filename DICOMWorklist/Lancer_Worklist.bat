@echo off
REM ===================================================================
REM Lanceur du serveur DICOM Worklist
REM Permet de synchroniser Doctolib avec l'échographe GE
REM ===================================================================

echo.
echo ========================================
echo   DICOM WORKLIST SERVER
echo   Doctolib - Echographe GE
echo ========================================
echo.

REM Change le repertoire vers le dossier du script
cd /d "%~dp0"

REM Lance le serveur Python
python main.py

REM Si le script s'arrete, attendre avant de fermer la fenetre
echo.
echo ========================================
echo   Serveur arrete
echo ========================================
echo.
pause
