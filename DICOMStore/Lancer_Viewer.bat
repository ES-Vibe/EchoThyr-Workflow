@echo off
title DICOM Viewer Web
cd /d "%~dp0"
echo.
echo Demarrage du viewer DICOM...
echo Ouvrez votre navigateur sur http://localhost:8080
echo.
start http://localhost:8080
python web_viewer.py
pause
