@echo off
chcp 65001 >nul
color 0C
cls

echo ============================================================
echo    🛑 ECHOTHYR WORKFLOW - ARRÊT COMPLET
echo ============================================================
echo.
echo Arrêt de tous les services DICOM...
echo.

REM Arrêter tous les processus Python liés aux services
echo [1/3] Arrêt EchoThyr-Python...
taskkill /FI "WINDOWTITLE eq EchoThyr-Python Monitor*" /T /F 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    ✅ EchoThyr-Python arrêté
) else (
    echo    ⚠️  EchoThyr-Python non trouvé ou déjà arrêté
)

echo.
echo [2/3] Arrêt DICOMStore...
taskkill /FI "WINDOWTITLE eq DICOMStore Server*" /T /F 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    ✅ DICOMStore arrêté
) else (
    echo    ⚠️  DICOMStore non trouvé ou déjà arrêté
)

echo.
echo [3/3] Arrêt DICOMWorklist...
taskkill /FI "WINDOWTITLE eq DICOMWorklist Server*" /T /F 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    ✅ DICOMWorklist arrêté
) else (
    echo    ⚠️  DICOMWorklist non trouvé ou déjà arrêté
)

echo.
echo ============================================================
echo    ✅ TOUS LES SERVICES SONT ARRÊTÉS
echo ============================================================
echo.
echo Les ports 4242 et 4243 sont maintenant libres.
echo.

pause
