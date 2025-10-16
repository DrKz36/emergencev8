# Guide d'utilisation en mode caché (sans fenêtre)

Ce guide explique comment exécuter le Unified Guardian Scheduler sans afficher de fenêtre PowerShell.

---

## 🎯 Pourquoi le mode caché ?

Par défaut, lorsque la tâche planifiée s'exécute, une fenêtre PowerShell s'ouvre brièvement. Le mode caché permet d'exécuter le scheduler en arrière-plan **complètement invisible**.

---

## 🚀 Méthode 1: Utilisation du script VBS (Recommandé)

### Exécution manuelle immédiate

```cmd
wscript.exe "claude-plugins\integrity-docs-guardian\scripts\run_unified_scheduler_hidden.vbs"
```

**Avantages**:
- ✅ Aucune fenêtre n'apparaît
- ✅ Exécution immédiate
- ✅ Fonctionne sans privilèges administrateur
- ✅ Les logs sont créés normalement

### Configuration de la tâche planifiée en mode caché

```powershell
# Exécuter ce script pour créer la tâche planifiée
powershell -ExecutionPolicy Bypass -File "claude-plugins\integrity-docs-guardian\scripts\setup_hidden_scheduler.ps1" -Force
```

**Note**: Nécessite des privilèges administrateur pour créer la tâche planifiée.

---

## 🔧 Méthode 2: Modification manuelle de la tâche existante

Si vous avez déjà une tâche planifiée créée, vous pouvez la modifier pour utiliser le mode caché:

### Via PowerShell

```powershell
# Supprimer l'ancienne tâche
Unregister-ScheduledTask -TaskName "EmergenceUnifiedGuardian" -Confirm:$false

# Créer la nouvelle tâche avec le script de setup caché
powershell -ExecutionPolicy Bypass -File "claude-plugins\integrity-docs-guardian\scripts\setup_hidden_scheduler.ps1" -Force
```

### Via l'interface graphique du Planificateur de tâches

1. Ouvrir le **Planificateur de tâches** Windows
2. Trouver la tâche `EmergenceUnifiedGuardian`
3. **Actions** → Modifier l'action existante:
   - Programme: `wscript.exe`
   - Arguments: `"C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts\run_unified_scheduler_hidden.vbs"`
4. **Général** → Cocher "Exécuter même si l'utilisateur n'est pas connecté"
5. **Paramètres** → Cocher "Masquer"

---

## 📊 Vérification du fonctionnement

### 1. Test immédiat

```cmd
# Lancer le script VBS
wscript.exe "claude-plugins\integrity-docs-guardian\scripts\run_unified_scheduler_hidden.vbs"

# Attendre quelques secondes, puis vérifier les logs
```

### 2. Consulter les logs

```powershell
# Voir les 20 dernières lignes du log
Get-Content "claude-plugins\integrity-docs-guardian\logs\unified_scheduler_2025-10.log" -Tail 20

# Ou en temps réel
Get-Content "claude-plugins\integrity-docs-guardian\logs\unified_scheduler_2025-10.log" -Wait -Tail 20
```

### 3. Vérifier le rapport généré

```powershell
# Lister les rapports récents
Get-ChildItem "claude-plugins\integrity-docs-guardian\reports\consolidated_report_*.json" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 3
```

---

## 📁 Fichiers du mode caché

### Script VBS
**Fichier**: `scripts/run_unified_scheduler_hidden.vbs`

```vbscript
' Lance PowerShell en mode caché sans fenêtre
Set objShell = CreateObject("WScript.Shell")
scriptPath = "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler_simple.ps1"
command = "powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """"
objShell.Run command, 0, False
```

**Paramètre clé**: `objShell.Run command, 0, False`
- `0` = Fenêtre cachée (mode invisible)
- `False` = Ne pas attendre la fin de l'exécution

### Script de setup
**Fichier**: `scripts/setup_hidden_scheduler.ps1`

Configure automatiquement la tâche planifiée pour utiliser le script VBS.

---

## 🎛️ Options de WindowStyle

Pour référence, les options de `-WindowStyle` dans PowerShell:

| Option | Description | Visible ? |
|--------|-------------|-----------|
| `Normal` | Fenêtre normale | ✅ Oui |
| `Minimized` | Fenêtre minimisée | ✅ Oui (dans barre tâches) |
| `Maximized` | Fenêtre maximisée | ✅ Oui |
| `Hidden` | Fenêtre cachée | ⚠️ Partiellement (icône flash) |

**Note**: Même avec `-WindowStyle Hidden`, PowerShell peut montrer brièvement une fenêtre. C'est pourquoi **le script VBS est la meilleure solution**.

---

## 🔍 Diagnostic

### Problème: Le script ne s'exécute pas

**Vérifications**:

1. Le script VBS existe-t-il ?
```cmd
dir "claude-plugins\integrity-docs-guardian\scripts\run_unified_scheduler_hidden.vbs"
```

2. Le script PowerShell cible existe-t-il ?
```cmd
dir "claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler_simple.ps1"
```

3. Python est-il accessible ?
```cmd
"C:\dev\emergenceV8\.venv\Scripts\python.exe" --version
```

### Problème: Pas de logs générés

**Vérifications**:

1. Le répertoire logs existe-t-il ?
```cmd
dir "claude-plugins\integrity-docs-guardian\logs"
```

2. Permissions d'écriture ?
```cmd
# Tester la création d'un fichier
echo test > "claude-plugins\integrity-docs-guardian\logs\test.txt"
```

### Problème: La tâche planifiée ne démarre pas

**Vérifications**:

```powershell
# Voir l'état de la tâche
Get-ScheduledTask -TaskName "EmergenceUnifiedGuardian"

# Voir les détails et historique
Get-ScheduledTaskInfo -TaskName "EmergenceUnifiedGuardian"

# Voir les logs d'événements Windows
Get-WinEvent -LogName "Microsoft-Windows-TaskScheduler/Operational" -MaxEvents 50 |
  Where-Object { $_.Message -like "*EmergenceUnifiedGuardian*" }
```

---

## 💡 Conseils et bonnes pratiques

### 1. Test avant production

Toujours tester le mode caché manuellement avant de configurer la tâche planifiée:

```cmd
wscript.exe "claude-plugins\integrity-docs-guardian\scripts\run_unified_scheduler_hidden.vbs"
```

### 2. Surveillance des logs

Configurer une surveillance périodique des logs:

```powershell
# Créer un alias pour voir les logs facilement
function Show-GuardianLogs {
    Get-Content "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\logs\unified_scheduler_$(Get-Date -Format 'yyyy-MM').log" -Tail 50
}

# Ajouter à votre profil PowerShell pour usage permanent
```

### 3. Notifications en cas d'erreur

Pour être notifié en cas d'erreur, vous pouvez ajouter une vérification planifiée:

```powershell
# Script de vérification (à planifier séparément)
$logFile = "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\logs\unified_scheduler_$(Get-Date -Format 'yyyy-MM').log"
$errors = Select-String -Path $logFile -Pattern "\[ERROR\]" -SimpleMatch

if ($errors.Count -gt 0) {
    # Envoyer un email, notification, etc.
    Write-Host "ATTENTION: $($errors.Count) erreur(s) détectée(s)!" -ForegroundColor Red
}
```

---

## 🎯 Comparaison des méthodes

| Méthode | Visibilité | Privilèges admin | Facilité |
|---------|------------|------------------|----------|
| PowerShell direct | ⚠️ Fenêtre flash | Non | ⭐⭐⭐ |
| PowerShell `-WindowStyle Hidden` | ⚠️ Icône flash | Non | ⭐⭐⭐ |
| **Script VBS** | ✅ **Invisible** | Non | ⭐⭐⭐⭐⭐ |
| Tâche planifiée + VBS | ✅ **Invisible** | Oui (config initiale) | ⭐⭐⭐⭐ |

**Recommandation**: Utiliser le script VBS pour une exécution complètement invisible.

---

## 📚 Références

### Commandes rapides

```powershell
# Exécuter maintenant en mode caché
wscript.exe "claude-plugins\integrity-docs-guardian\scripts\run_unified_scheduler_hidden.vbs"

# Voir les logs en direct
Get-Content "claude-plugins\integrity-docs-guardian\logs\unified_scheduler_$(Get-Date -Format 'yyyy-MM').log" -Wait -Tail 20

# Configurer la tâche planifiée en mode caché
powershell -ExecutionPolicy Bypass -File "claude-plugins\integrity-docs-guardian\scripts\setup_hidden_scheduler.ps1" -Force

# Voir l'état de la tâche
Get-ScheduledTask -TaskName "EmergenceUnifiedGuardian"
```

### Fichiers créés

- ✅ `scripts/run_unified_scheduler_hidden.vbs` - Script VBS d'exécution cachée
- ✅ `scripts/setup_hidden_scheduler.ps1` - Configuration automatique de la tâche
- ✅ `scripts/setup_unified_scheduler_simple.ps1` - Modifié avec `-WindowStyle Hidden`
- ✅ `HIDDEN_MODE_GUIDE.md` - Ce guide

---

## ✨ Résumé

Pour exécuter le Unified Guardian Scheduler **sans aucune fenêtre visible**:

1. **Test immédiat** (sans configuration):
   ```cmd
   wscript.exe "claude-plugins\integrity-docs-guardian\scripts\run_unified_scheduler_hidden.vbs"
   ```

2. **Configuration automatique** (nécessite admin):
   ```powershell
   powershell -ExecutionPolicy Bypass -File "claude-plugins\integrity-docs-guardian\scripts\setup_hidden_scheduler.ps1" -Force
   ```

3. **Vérification**:
   ```powershell
   Get-Content "claude-plugins\integrity-docs-guardian\logs\unified_scheduler_$(Get-Date -Format 'yyyy-MM').log" -Tail 20
   ```

**C'est tout !** Le système s'exécute maintenant silencieusement en arrière-plan. 🎉

---

*Guide créé le 2025-10-16 pour ÉMERGENCE Phase 3*
