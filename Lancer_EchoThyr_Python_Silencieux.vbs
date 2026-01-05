' ===================================================================
' Lanceur silencieux pour EchoThyr Python (sans fenetre visible)
' Utile pour le demarrage automatique au demarrage de Windows
' ===================================================================

Set objShell = CreateObject("WScript.Shell")

' Chemin vers le script Python
scriptPath = objShell.CurrentDirectory & "\main.py"

' Lance Python en mode cache (fenetre invisible)
objShell.Run "python """ & scriptPath & """", 0, False

' Message de confirmation (optionnel - commentez la ligne suivante si vous ne voulez pas de popup)
WScript.Echo "EchoThyr Python v2.0.0 demarre en arriere-plan"
