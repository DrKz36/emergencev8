# QUICKSTART - Phase 3: Unified Guardian Scheduler

Guide de démarrage rapide pour activer et utiliser le système unifié d'orchestration automatique.

---

## 🚀 Démarrage en 5 minutes

### Option 1: Exécution manuelle (Test)

```powershell
# 1. Ouvrir PowerShell dans le répertoire du projet
cd C:\dev\emergenceV8

# 2. Exécuter le scheduler en mode test
powershell -ExecutionPolicy Bypass -File "claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler_simple.ps1" -TestMode -Verbose

# 3. Vérifier le rapport généré
Get-Content "claude-plugins\integrity-docs-guardian\reports\consolidated_report_*.json" |
  Select-Object -Last 1 |
  Get-Content
```

### Option 2: Installation avec tâche planifiée (Production)

```powershell
# 1. Ouvrir PowerShell EN TANT QU'ADMINISTRATEUR
# Clic droit sur PowerShell > "Exécuter en tant qu'administrateur"

# 2. Naviguer vers le projet
cd C:\dev\emergenceV8

# 3. Lancer le script d'installation
powershell -ExecutionPolicy Bypass -File "claude-plugins\integrity-docs-guardian\scripts\setup_unified_scheduler_simple.ps1" -Force

# 4. La tâche planifiée est créée et s'exécutera:
#    - Au démarrage du système
#    - Toutes les 60 minutes
```

---

## 📋 Vérification rapide

### Voir l'état de la tâche planifiée

```powershell
Get-ScheduledTask -TaskName 'EmergenceUnifiedGuardian'
```

### Démarrer la tâche manuellement

```powershell
Start-ScheduledTask -TaskName 'EmergenceUnifiedGuardian'
```

### Voir les derniers logs

```powershell
Get-Content "claude-plugins\integrity-docs-guardian\logs\unified_scheduler_$(Get-Date -Format 'yyyy-MM').log" -Tail 20
```

### Voir les rapports récents

```powershell
Get-ChildItem "claude-plugins\integrity-docs-guardian\reports\consolidated_report_*.json" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 3 |
  ForEach-Object { Write-Host $_.Name -ForegroundColor Cyan }
```

---

## ⚙️ Configuration des variables d'environnement

Pour activer le mode automatique complet avec mises à jour:

```powershell
# Session courante
$env:AUTO_APPLY = "1"
$env:AUTO_UPDATE_DOCS = "1"

# Permanent (ajouter au profil PowerShell)
# Ouvrir le profil: notepad $PROFILE
# Ajouter ces lignes:
$env:AUTO_APPLY = "1"
$env:AUTO_UPDATE_DOCS = "1"
$env:AGENT_CHECK_INTERVAL = "60"
$env:PYTHONIOENCODING = "utf-8"
```

---

## 🔧 Commandes utiles

### Gestion de la tâche planifiée

```powershell
# Voir les détails
Get-ScheduledTaskInfo -TaskName 'EmergenceUnifiedGuardian'

# Désactiver temporairement
Disable-ScheduledTask -TaskName 'EmergenceUnifiedGuardian'

# Réactiver
Enable-ScheduledTask -TaskName 'EmergenceUnifiedGuardian'

# Supprimer
Unregister-ScheduledTask -TaskName 'EmergenceUnifiedGuardian' -Confirm:$false
```

### Exécution manuelle avec options

```powershell
# Mode test avec sortie détaillée
.\claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler_simple.ps1 -TestMode -Verbose

# Exécution normale
.\claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler_simple.ps1

# Force l'exécution même si des composants manquent
.\claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler_simple.ps1 -Force
```

---

## 📊 Comprendre les rapports

### Structure du rapport consolidé

```json
{
  "timestamp": "2025-10-16 18:18:16",
  "execution_mode": "test",
  "results": {
    "guardian": {
      "executed": true,
      "status": "success",
      "report_path": "path/to/guardian_report.json"
    },
    "prodguardian": {
      "executed": true,
      "status": "success",
      "report_path": "path/to/prodguardian_report.json"
    }
  },
  "summary": {
    "total_checks": 2,
    "successful_checks": 2,
    "failed_checks": 0
  }
}
```

### Statuts possibles

- **success**: Agent exécuté avec succès
- **failed**: Agent a rencontré une erreur
- **executed: false**: Agent non trouvé ou non exécuté

---

## 🐛 Dépannage rapide

### Problème: "Accès refusé" lors de la création de la tâche

**Solution**: Exécuter PowerShell en tant qu'administrateur

```powershell
# Clic droit sur PowerShell > "Exécuter en tant qu'administrateur"
```

### Problème: Agents non trouvés

**Vérification**:
```powershell
# Vérifier que les agents existent
Test-Path "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\agents\guardian_agent.py"
Test-Path "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\agents\prodguardian_agent.py"
```

**Note**: Le système fonctionne en mode dégradé si des agents manquent.

### Problème: Python non trouvé

**Vérification**:
```powershell
# Vérifier Python dans venv
Test-Path "C:\dev\emergenceV8\.venv\Scripts\python.exe"

# Ou Python système
python --version
```

**Solution**: Installer Python ou créer le venv:
```powershell
python -m venv .venv
```

### Problème: Erreurs dans les logs

**Consultation des logs**:
```powershell
# Voir tous les logs du mois
Get-Content "claude-plugins\integrity-docs-guardian\logs\unified_scheduler_$(Get-Date -Format 'yyyy-MM').log"

# Filtrer les erreurs
Get-Content "claude-plugins\integrity-docs-guardian\logs\unified_scheduler_$(Get-Date -Format 'yyyy-MM').log" |
  Select-String -Pattern "ERROR"
```

---

## 📚 Documentation complète

Pour plus d'informations détaillées, consultez:

- **[PHASE3_COMPLETE.md](./PHASE3_COMPLETE.md)** - Documentation technique complète
- **[README.md](./README.md)** - Vue d'ensemble du système
- **[PHASE1_COMPLETE.md](./PHASE1_COMPLETE.md)** - Guardian d'Intégrité
- **[PHASE2_COMPLETE.md](./PHASE2_COMPLETE.md)** - ProdGuardian

---

## 🎯 Étapes suivantes

Après avoir activé le système:

1. **Surveillance**: Vérifier les logs régulièrement
2. **Rapports**: Consulter les rapports consolidés quotidiennement
3. **Optimisation**: Ajuster l'intervalle si nécessaire
4. **Intégration**: Connecter avec d'autres outils de monitoring

---

## 💡 Conseils

- Commencer par le **mode test** pour valider la configuration
- Activer le **mode verbose** pour déboguer
- Consulter les **logs** en cas de problème
- Vérifier les **rapports consolidés** pour un aperçu global
- Ajuster l'**intervalle d'exécution** selon les besoins

---

**Système opérationnel en moins de 5 minutes!** 🚀

*Pour toute question ou problème, consultez PHASE3_COMPLETE.md*
