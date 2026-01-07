@echo off
REM ===================================================================
REM Lanceur Python pour EchoThyr v2.0.0
REM Double-cliquez sur ce fichier pour demarrer le monitoring
REM ===================================================================

echo.
echo ========================================
echo   LANCEMENT ECHOTHYR PYTHON v2.0.0
echo ========================================
echo.

REM Change le repertoire vers le dossier du script
cd /d "%~dp0"

REM Verifier si Python est installe
python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python n'est pas installe ou n'est pas dans le PATH
    echo.
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Verifier si les dependances sont installees
echo Verification des dependances...
python -c "import pytesseract" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Les dependances Python ne sont pas installees.
    echo Installation automatique des dependances...
    echo.
    pip install -r requirements.txt
    echo.
)

REM Lancer l'application Python
echo Demarrage de l'application...
echo.
python main.py

REM Si le script s'arrete, attendre avant de fermer la fenetre
echo.
echo ========================================
echo   Script arrete
echo ========================================
echo.
pause
