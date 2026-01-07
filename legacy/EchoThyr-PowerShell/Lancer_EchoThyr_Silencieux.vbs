' ===================================================================
' Lanceur silencieux pour EchoThyr (sans fenetre visible)
' Utile pour le demarrage automatique au demarrage de Windows
' ===================================================================

Set objShell = CreateObject("WScript.Shell")

' Chemin vers le script PowerShell
scriptPath = objShell.CurrentDirectory & "\EchoThyr.ps1"

' Lance PowerShell en mode cache (fenetre invisible)
objShell.Run "powershell.exe -ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File """ & scriptPath & """", 0, False

' Message de confirmation (optionnel - commentez la ligne suivante si vous ne voulez pas de popup)
WScript.Echo "EchoThyr Monitor demarre en arriere-plan"
