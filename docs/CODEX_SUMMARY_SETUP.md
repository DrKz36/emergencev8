# Setup Résumé Codex GPT - Guide d'installation

Ce guide explique comment configurer la génération automatique du résumé Guardian pour Codex GPT.

## 📋 Vue d'ensemble

Le résumé `reports/codex_summary.md` est généré automatiquement :
1. **Hooks Git** : post-commit et pre-push
2. **Task Scheduler** : toutes les 6 heures

## ✅ 1. Hooks Git (DÉJÀ CONFIGURÉ)

Les hooks Git sont déjà installés et actifs :

### Post-Commit Hook
```bash
# Après chaque commit, génère :
# - Rapport unifié Nexus
# - Résumé Codex (reports/codex_summary.md)
# - Auto-update docs (si activé)
```

### Pre-Push Hook
```bash
# Avant chaque push, génère :
# - Rapport production ProdGuardian (vérif Cloud Run)
# - Résumé Codex avec rapports frais
# - Bloque si production CRITICAL
```

**Test :**
```bash
# Faire un commit test
git add .
git commit -m "test: hooks Guardian"
# → Doit générer codex_summary.md

# Push test
git push
# → Doit regénérer codex_summary.md avec rapports frais
```

## 🕒 2. Task Scheduler (Installation manuelle requise)

### Installation automatique (RECOMMANDÉ)

**Prérequis : PowerShell avec droits Administrateur**

```powershell
# Ouvrir PowerShell en mode Administrateur
# (Clic droit > Run as Administrator)

cd C:\dev\emergenceV8

# Installer la tâche planifiée (6h par défaut)
.\scripts\setup_codex_summary_scheduler.ps1

# Ou avec intervalle personnalisé (ex: 2h)
.\scripts\setup_codex_summary_scheduler.ps1 -IntervalHours 2
```

**Ce que ça fait :**
- Crée une tâche Windows nommée `Guardian-Codex-Summary`
- Exécute `scripts/scheduled_codex_summary.ps1` toutes les N heures
- Génère rapports Guardian frais + résumé Codex
- Log dans `logs/scheduled_codex_summary.log`

### Vérification

```powershell
# Voir la tâche
Get-ScheduledTask -TaskName "Guardian-Codex-Summary"

# Lancer manuellement
Start-ScheduledTask -TaskName "Guardian-Codex-Summary"

# Voir logs
Get-Content logs/scheduled_codex_summary.log -Tail 20
```

### Désinstallation

```powershell
# Supprimer la tâche planifiée
.\scripts\setup_codex_summary_scheduler.ps1 -Disable
```

---

## 🔧 Installation manuelle Task Scheduler (Alternative)

Si vous ne pouvez pas utiliser PowerShell en admin :

### Méthode 1 : Via GUI Windows

1. Ouvrir **Task Scheduler** (Planificateur de tâches)
2. Clic droit > **Create Task** (Créer une tâche)
3. **General** :
   - Nom : `Guardian-Codex-Summary`
   - Description : `Génère résumé Guardian pour Codex GPT toutes les 6h`
   - Run whether user is logged on or not : ❌ (décoché)
   - Run with highest privileges : ❌ (décoché)

4. **Triggers** :
   - Ajouter 4 déclencheurs quotidiens :
     - 00:00 (minuit)
     - 06:00 (6h)
     - 12:00 (midi)
     - 18:00 (18h)

5. **Actions** :
   - Action : **Start a program**
   - Program : `powershell.exe`
   - Arguments : `-ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\dev\emergenceV8\scripts\scheduled_codex_summary.ps1"`
   - Start in : `C:\dev\emergenceV8`

6. **Conditions** :
   - ✅ Start only if on AC power : décoché
   - ✅ Start task as soon as possible after a scheduled start is missed

7. **Settings** :
   - ✅ Allow task to be run on demand
   - ✅ Run task as soon as possible if a scheduled start is missed
   - ❌ Stop the task if it runs longer than : décoché

8. **OK** → Tâche créée !

### Méthode 2 : Via schtasks.exe (ligne de commande)

```cmd
REM Créer déclencheur à 00:00
schtasks /create /tn "Guardian-Codex-Summary-00h" /tr "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\dev\emergenceV8\scripts\scheduled_codex_summary.ps1" /sc daily /st 00:00

REM Créer déclencheur à 06:00
schtasks /create /tn "Guardian-Codex-Summary-06h" /tr "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\dev\emergenceV8\scripts\scheduled_codex_summary.ps1" /sc daily /st 06:00

REM Créer déclencheur à 12:00
schtasks /create /tn "Guardian-Codex-Summary-12h" /tr "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\dev\emergenceV8\scripts\scheduled_codex_summary.ps1" /sc daily /st 12:00

REM Créer déclencheur à 18:00
schtasks /create /tn "Guardian-Codex-Summary-18h" /tr "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\dev\emergenceV8\scripts\scheduled_codex_summary.ps1" /sc daily /st 18:00
```

---

## 🧪 Tests

### 1. Test génération manuelle

```bash
# Générer résumé Codex
python scripts/generate_codex_summary.py

# Vérifier résultat
cat reports/codex_summary.md
```

### 2. Test hook post-commit

```bash
# Commit test
git add .
git commit -m "test: hook post-commit"

# Vérifier que codex_summary.md a été régénéré
ls -la reports/codex_summary.md
```

### 3. Test hook pre-push

```bash
# Push test
git push

# Vérifier dans le log du hook que "Codex Summary" apparaît
```

### 4. Test Task Scheduler

```powershell
# Lancer manuellement la tâche
Start-ScheduledTask -TaskName "Guardian-Codex-Summary"

# Attendre quelques secondes
Start-Sleep -Seconds 10

# Vérifier logs
Get-Content logs/scheduled_codex_summary.log -Tail 10

# Vérifier que codex_summary.md a été mis à jour
Get-Item reports/codex_summary.md | Select-Object LastWriteTime
```

---

## 📊 Résultat attendu

Après installation, le fichier `reports/codex_summary.md` sera automatiquement mis à jour :

- ✅ **Post-commit** : après chaque commit
- ✅ **Pre-push** : avant chaque push (avec rapports prod frais)
- ✅ **Toutes les 6h** : via Task Scheduler (rapports Guardian complets)

**Codex GPT peut alors lire `reports/codex_summary.md` pour avoir :**
- Vue d'ensemble des 4 Guardians
- Erreurs production détaillées (endpoint, fichier:ligne, stack trace)
- Patterns d'erreurs (endpoints/fichiers/types affectés)
- Code snippets avec contexte
- Gaps documentation
- Issues intégrité
- Actions prioritaires ("Que faire maintenant ?")

---

## 🐛 Troubleshooting

### Problème : Tâche planifiée ne s'exécute pas

```powershell
# Vérifier statut
Get-ScheduledTask -TaskName "Guardian-Codex-Summary" | Select-Object State

# Vérifier dernière exécution
Get-ScheduledTaskInfo -TaskName "Guardian-Codex-Summary" | Select-Object LastRunTime, LastTaskResult

# LastTaskResult = 0 → OK
# LastTaskResult ≠ 0 → Erreur (voir logs)
```

### Problème : Erreur dans le script

```powershell
# Lancer manuellement pour voir l'erreur
cd C:\dev\emergenceV8
.\scripts\scheduled_codex_summary.ps1
```

### Problème : Python pas trouvé

```powershell
# Vérifier que Python est dans PATH
python --version

# Si erreur, activer virtualenv d'abord :
.\.venv\Scripts\Activate.ps1
python --version
```

### Problème : Hooks Git ne s'exécutent pas

```bash
# Vérifier que les hooks sont exécutables (Git Bash)
ls -la .git/hooks/post-commit
ls -la .git/hooks/pre-push

# Si pas exécutables :
chmod +x .git/hooks/post-commit
chmod +x .git/hooks/pre-push
```

---

## 📚 Références

- Script génération : [scripts/generate_codex_summary.py](../scripts/generate_codex_summary.py)
- Script scheduler : [scripts/scheduled_codex_summary.ps1](../scripts/scheduled_codex_summary.ps1)
- Setup scheduler : [scripts/setup_codex_summary_scheduler.ps1](../scripts/setup_codex_summary_scheduler.ps1)
- Hook post-commit : [.git/hooks/post-commit](../.git/hooks/post-commit)
- Hook pre-push : [.git/hooks/pre-push](../.git/hooks/pre-push)
- Prompt Codex : [PROMPT_CODEX_RAPPORTS.md](../PROMPT_CODEX_RAPPORTS.md)
