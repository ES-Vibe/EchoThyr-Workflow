' ============================================================
' ECHOTHYR WORKFLOW - Lancement silencieux de tous les services
' ============================================================

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Obtenir le chemin du script
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Message de démarrage (optionnel, peut être commenté)
' objShell.Popup "Démarrage EchoThyr Suite...", 2, "EchoThyr Workflow", 64

' Lancer DICOMWorklist (arrière-plan)
objShell.Run "cmd /c cd /d """ & strScriptPath & "\DICOMWorklist"" && python main.py", 0, False
WScript.Sleep 2000

' Lancer DICOMStore (arrière-plan)
objShell.Run "cmd /c cd /d """ & strScriptPath & "\DICOMStore"" && python main.py", 0, False
WScript.Sleep 2000

' Lancer EchoThyr-Python (arrière-plan)
objShell.Run "cmd /c cd /d """ & strScriptPath & "\EchoThyr-Python"" && python main.py", 0, False
WScript.Sleep 2000

' Message de confirmation
objShell.Popup "✅ EchoThyr Suite démarrée avec succès !" & vbCrLf & vbCrLf & _
               "Services actifs :" & vbCrLf & _
               "- DICOMWorklist (Port 4242)" & vbCrLf & _
               "- DICOMStore (Port 4243)" & vbCrLf & _
               "- EchoThyr-Python (Monitoring)" & vbCrLf & vbCrLf & _
               "Pour arrêter : Arreter_EchoThyr_Suite.bat", _
               5, "EchoThyr Workflow", 64

Set objShell = Nothing
Set objFSO = Nothing
