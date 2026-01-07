@echo off
chcp 65001 >nul
color 0A
cls

echo ============================================================
echo    🏥 ECHOTHYR WORKFLOW - LANCEMENT COMPLET
echo ============================================================
echo.
echo Démarrage de tous les services DICOM...
echo.

REM Obtenir le chemin du script
set "SCRIPT_DIR=%~dp0"

echo [1/3] Démarrage DICOMWorklist (Port 4242)...
start "DICOMWorklist Server" cmd /k "cd /d "%SCRIPT_DIR%DICOMWorklist" && python main.py"
timeout /t 2 /nobreak >nul

echo [2/3] Démarrage DICOMStore (Port 4243)...
start "DICOMStore Server" cmd /k "cd /d "%SCRIPT_DIR%DICOMStore" && python main.py"
timeout /t 2 /nobreak >nul

echo [3/3] Démarrage EchoThyr-Python (Surveillance CR)...
start "EchoThyr-Python Monitor" cmd /k "cd /d "%SCRIPT_DIR%EchoThyr-Python" && python main.py"
timeout /t 2 /nobreak >nul

echo.
echo ============================================================
echo    ✅ TOUS LES SERVICES SONT DÉMARRÉS
echo ============================================================
echo.
echo 📋 Services actifs :
echo    - DICOMWorklist (Port 4242) - Liste patients Doctolib
echo    - DICOMStore    (Port 4243) - Archivage images DICOM
echo    - EchoThyr      (Monitoring) - Génération CR automatique
echo.
echo 💡 Chaque service s'exécute dans sa propre fenêtre
echo 🛑 Pour arrêter : Fermez chaque fenêtre ou utilisez Arreter_EchoThyr_Suite.bat
echo.
echo ============================================================
echo.

pause
