' ============================================================================
' Run Unified Guardian Scheduler in Hidden Mode
' ============================================================================
' Ce script VBScript lance le unified_guardian_scheduler en arriere-plan
' sans afficher de fenetre PowerShell
' ============================================================================

Set objShell = CreateObject("WScript.Shell")

' Chemin vers le script PowerShell
scriptPath = "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler_simple.ps1"

' Commande PowerShell complete
command = "powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """"

' Executer en mode cache (0 = fenetre cachee)
objShell.Run command, 0, False

' Liberation de l'objet
Set objShell = Nothing
