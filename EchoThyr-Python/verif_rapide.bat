@echo off
echo.
echo Verification rapide Python...
echo.
python --version
if errorlevel 1 (
    echo.
    echo Python n'est pas encore installe ou pas dans le PATH
    echo Fermez cette fenetre et relancez apres installation
) else (
    echo.
    echo Python est bien installe !
    echo.
    echo Installation des dependances...
    pip install --quiet pytesseract Pillow python-docx PyYAML colorlog plyer watchdog
    echo.
    echo Tout est pret ! Vous pouvez lancer:
    echo   Lancer_EchoThyr_Python.bat
)
echo.
pause
