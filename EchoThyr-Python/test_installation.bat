@echo off
REM ===================================================================
REM Script de test pour verifier l'installation Python et dependances
REM ===================================================================

echo.
echo ========================================
echo   TEST INSTALLATION PYTHON
echo ========================================
echo.

cd /d "%~dp0"

REM Test 1: Python installe
echo [1/6] Test Python installe...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ECHEC] Python n'est pas installe
    echo.
    echo Veuillez installer Python depuis:
    echo https://www.python.org/downloads/
    echo.
    echo OU via Microsoft Store: Python 3.11
    echo.
    pause
    exit /b 1
) else (
    echo [OK] Python est installe
    python --version
)

echo.
echo [2/6] Test pip (gestionnaire paquets)...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ECHEC] pip n'est pas disponible
    pause
    exit /b 1
) else (
    echo [OK] pip est disponible
)

echo.
echo [3/6] Installation dependances Python...
pip install -q pytesseract Pillow python-docx watchdog PyYAML colorlog plyer
if errorlevel 1 (
    echo [ECHEC] Installation dependances echouee
    pause
    exit /b 1
) else (
    echo [OK] Dependances installees
)

echo.
echo [4/6] Verification imports Python...
python -c "import pytesseract; import PIL; import docx; import watchdog; import yaml; import colorlog; import plyer" 2>nul
if errorlevel 1 (
    echo [ECHEC] Certains modules ne s'importent pas
    echo Reessayez: pip install -r requirements.txt
    pause
    exit /b 1
) else (
    echo [OK] Tous les modules s'importent correctement
)

echo.
echo [5/6] Verification chemins EchoThyr...
if exist "C:\EchoThyr\export\" (
    echo [OK] C:\EchoThyr\export existe
) else (
    echo [ATTENTION] C:\EchoThyr\export n'existe pas
    echo Creation du dossier...
    mkdir "C:\EchoThyr\export" 2>nul
)

if exist "C:\EchoThyr\Modele_Echo.docx" (
    echo [OK] Template Word trouve
) else (
    echo [ATTENTION] Template Word manquant: C:\EchoThyr\Modele_Echo.docx
)

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [OK] Tesseract OCR trouve
) else (
    echo [ATTENTION] Tesseract non trouve
)

echo.
echo [6/6] Test execution script Python...
echo Lancement test (Ctrl+C pour arreter)...
timeout /t 2 >nul
python -c "from src.utils.logger import get_logger; logger = get_logger(); logger.info('Test reussi!')" 2>nul
if errorlevel 1 (
    echo [ECHEC] Erreur lors du test
    echo.
    echo Details de l'erreur:
    python -c "from src.utils.logger import get_logger; logger = get_logger(); logger.info('Test reussi!')"
) else (
    echo [OK] Script Python fonctionne
)

echo.
echo ========================================
echo   TESTS TERMINES
echo ========================================
echo.
echo Vous pouvez maintenant lancer:
echo   - Lancer_EchoThyr_Python.bat
echo   - OU: python main.py
echo.
pause
