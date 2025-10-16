# 📅 Guide - Créer la Tâche Planifiée Windows

Ce guide vous explique comment créer manuellement la tâche planifiée Windows pour le planificateur d'orchestration automatique.

## 🎯 Objectif

Créer une tâche qui exécute l'orchestrateur automatiquement **toutes les heures**.

---

## 📋 Méthode 1: Via l'interface graphique (recommandé)

### Étape 1: Ouvrir le Planificateur de tâches

1. Appuyer sur `Windows + R`
2. Taper `taskschd.msc`
3. Appuyer sur `Entrée`

### Étape 2: Créer une tâche de base

1. Dans le panneau de droite, cliquer sur **"Créer une tâche..."** (pas "Créer une tâche de base")
2. Onglet **"Général"**:
   - **Nom:** `EMERGENCE_AutoOrchestration`
   - **Description:** `ÉMERGENCE - Orchestration automatique des agents de vérification`
   - Cocher **"Exécuter même si l'utilisateur n'est pas connecté"** (optionnel)
   - Cocher **"Exécuter avec les privilèges maximum"** (optionnel)

### Étape 3: Configurer le déclencheur

1. Aller sur l'onglet **"Déclencheurs"**
2. Cliquer sur **"Nouveau..."**
3. Configurer:
   - **Lancer la tâche:** "Selon une planification"
   - **Paramètres:** "Une seule fois"
   - **Date/heure:** Maintenant (ou une heure proche)
   - Cocher **"Répéter la tâche toutes les:"** → Sélectionner **"1 heure"**
   - **Pendant:** "Indéfiniment"
4. Cliquer sur **"OK"**

### Étape 4: Configurer l'action

1. Aller sur l'onglet **"Actions"**
2. Cliquer sur **"Nouvelle..."**
3. Configurer:
   - **Action:** "Démarrer un programme"
   - **Programme/script:**
     ```
     C:\dev\emergenceV8\.venv\Scripts\python.exe
     ```
     *(Ou le chemin de votre Python si vous n'utilisez pas le venv)*

   - **Ajouter des arguments (facultatif):**
     ```
     claude-plugins\integrity-docs-guardian\scripts\scheduler.py
     ```

   - **Commencer dans (facultatif):**
     ```
     C:\dev\emergenceV8
     ```
4. Cliquer sur **"OK"**

### Étape 5: Configurer les paramètres

1. Aller sur l'onglet **"Paramètres"**
2. Cocher:
   - ✅ **"Autoriser l'exécution de la tâche à la demande"**
   - ✅ **"Exécuter la tâche dès que possible si un démarrage planifié est manqué"**
   - ✅ **"Si la tâche échoue, recommencer toutes les:"** → "1 heure"
3. Décocher:
   - ❌ **"Arrêter la tâche si elle s'exécute plus de:"** (ou mettre 1 heure)
4. Cliquer sur **"OK"**

### Étape 6: Sauvegarder

1. Cliquer sur **"OK"** dans la fenêtre principale
2. Entrer votre mot de passe Windows si demandé

---

## 📋 Méthode 2: Via PowerShell (pour utilisateurs avancés)

```powershell
# Variables de configuration
$taskName = "EMERGENCE_AutoOrchestration"
$pythonExe = "C:\dev\emergenceV8\.venv\Scripts\python.exe"
$scriptPath = "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts\scheduler.py"
$workingDir = "C:\dev\emergenceV8"

# Créer l'action
$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $scriptPath `
    -WorkingDirectory $workingDir

# Créer le déclencheur (toutes les heures)
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

# Créer les paramètres
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -DontStopOnIdleEnd

# Créer le principal (utilisateur courant)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive

# Enregistrer la tâche
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "ÉMERGENCE - Orchestration automatique des agents de vérification"
```

---

## ✅ Vérifier que la tâche fonctionne

### Vérifier l'état de la tâche

```powershell
Get-ScheduledTask -TaskName "EMERGENCE_AutoOrchestration"
```

**Résultat attendu:**
```
TaskPath    TaskName                        State
--------    --------                        -----
\           EMERGENCE_AutoOrchestration     Ready
```

### Exécuter la tâche manuellement

```powershell
Start-ScheduledTask -TaskName "EMERGENCE_AutoOrchestration"
```

### Voir l'historique d'exécution

1. Dans le Planificateur de tâches
2. Sélectionner votre tâche
3. Onglet **"Historique"** en bas

### Vérifier les logs

Les logs du planificateur sont dans:
```
C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\logs\scheduler.log
```

Lire les logs:
```powershell
Get-Content "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\logs\scheduler.log" -Tail 50
```

---

## 🔧 Dépannage

### La tâche ne s'exécute pas

1. **Vérifier que Python est accessible:**
   ```powershell
   & "C:\dev\emergenceV8\.venv\Scripts\python.exe" --version
   ```

2. **Vérifier que le script existe:**
   ```powershell
   Test-Path "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts\scheduler.py"
   ```

3. **Exécuter le script manuellement:**
   ```powershell
   cd C:\dev\emergenceV8
   python claude-plugins\integrity-docs-guardian\scripts\scheduler.py
   ```

### La tâche s'exécute mais échoue

1. **Vérifier les logs d'erreur:**
   ```powershell
   Get-WinEvent -LogName "Microsoft-Windows-TaskScheduler/Operational" -MaxEvents 10 | Where-Object {$_.Message -like "*EMERGENCE*"}
   ```

2. **Vérifier le fichier de log du scheduler:**
   ```powershell
   Get-Content "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\logs\scheduler.log"
   ```

3. **Vérifier les permissions:**
   - La tâche doit s'exécuter avec votre compte utilisateur
   - Vérifier que vous avez accès au dossier du projet

### Désactiver temporairement la tâche

```powershell
Disable-ScheduledTask -TaskName "EMERGENCE_AutoOrchestration"
```

### Réactiver la tâche

```powershell
Enable-ScheduledTask -TaskName "EMERGENCE_AutoOrchestration"
```

### Supprimer la tâche

```powershell
Unregister-ScheduledTask -TaskName "EMERGENCE_AutoOrchestration" -Confirm:$false
```

---

## 🎯 Alternative: Sans tâche planifiée

Si vous ne voulez pas utiliser de tâche planifiée, vous pouvez:

### Option 1: Lancer le planificateur manuellement

```powershell
# En continu (toutes les heures)
python claude-plugins\integrity-docs-guardian\scripts\scheduler.py

# Garder la fenêtre PowerShell ouverte
```

### Option 2: Utiliser uniquement le hook Git

Le hook Git post-commit s'exécutera automatiquement après chaque commit sans avoir besoin de tâche planifiée.

```powershell
# Les variables sont déjà configurées
echo $env:AUTO_UPDATE_DOCS  # Devrait afficher 1
echo $env:AUTO_APPLY        # Devrait afficher 1

# Faire un commit pour tester
git commit -m "test: hook automatique"
```

---

## 📚 Ressources

- [Documentation Microsoft - Tâches planifiées](https://docs.microsoft.com/fr-fr/windows/win32/taskschd/task-scheduler-start-page)
- [QUICKSTART_AUTO.md](QUICKSTART_AUTO.md) - Guide de démarrage rapide
- [AUTO_ORCHESTRATION.md](AUTO_ORCHESTRATION.md) - Documentation complète du système

---

**Une fois la tâche créée, votre système d'orchestration automatique sera complètement opérationnel !** 🎉
