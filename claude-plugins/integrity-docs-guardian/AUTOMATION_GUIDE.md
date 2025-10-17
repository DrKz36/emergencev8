# 🤖 Guide d'Automatisation ÉMERGENCE Guardian

## Vue d'ensemble

Ce guide explique comment activer et utiliser l'automatisation complète des agents Guardian pour :
- ✅ Vérifications automatiques avant chaque commit
- ✅ Génération automatique de rapports après chaque commit
- ✅ Vérification de la production avant chaque push
- ✅ Mise à jour automatique de la documentation
- ✅ Monitoring continu en arrière-plan

---

## 🚀 Démarrage Rapide (5 minutes)

### 1. Activer l'automatisation

```bash
# Exécute le script de configuration
python claude-plugins/integrity-docs-guardian/scripts/setup_automation.py
```

Ce script va :
- ✅ Vérifier que tous les hooks Git sont en place
- ✅ Guider la configuration des variables d'environnement
- ✅ Tester que tous les agents fonctionnent
- ✅ Afficher un guide d'utilisation

### 2. Configurer les variables d'environnement (optionnel)

Pour activer les fonctionnalités avancées :

**Windows (PowerShell) :**
```powershell
# Session actuelle
$env:AUTO_UPDATE_DOCS='1'
$env:AUTO_APPLY='1'

# Permanent (ajoute à ton profil PowerShell)
[System.Environment]::SetEnvironmentVariable('AUTO_UPDATE_DOCS','1','User')
[System.Environment]::SetEnvironmentVariable('AUTO_APPLY','1','User')
```

**Linux/Mac (Bash/Zsh) :**
```bash
# Ajoute à ~/.bashrc ou ~/.zshrc
export AUTO_UPDATE_DOCS=1
export AUTO_APPLY=1

# Puis recharge
source ~/.bashrc  # ou source ~/.zshrc
```

### 3. Test du système

```bash
# Fais un commit de test
git add .
git commit -m "test: validation de l'automatisation Guardian"

# Les hooks devraient s'exécuter automatiquement et afficher:
# - 🔍 Pre-Commit: Vérifications Anima + Neo
# - 🎯 Post-Commit: Feedback détaillé + rapports
```

---

## 📋 Hooks Git Automatiques

### Pre-Commit Hook (avant chaque commit)

**Que fait-il ?**
1. Vérification de la couverture de tests pour nouveaux fichiers `.py`
2. Vérification que `openapi.json` est à jour si les routers changent
3. **Exécution d'Anima (DocKeeper)** - détecte les gaps de documentation
4. **Exécution de Neo (IntegrityWatcher)** - vérifie l'intégrité backend/frontend

**Comportement :**
- ✅ **Commit autorisé** si aucun problème critique
- ⚠️ **Warnings affichés** mais commit autorisé
- 🚨 **Commit BLOQUÉ** si erreurs critiques d'intégrité

**Bypass (déconseillé) :**
```bash
git commit --no-verify
```

### Post-Commit Hook (après chaque commit)

**Que fait-il ?**
1. **Génère le rapport unifié (Nexus)** qui combine tous les agents
2. Affiche un **résumé détaillé** des vérifications
3. Liste les **recommandations principales**
4. Si `AUTO_UPDATE_DOCS=1` : analyse et propose des mises à jour de documentation
5. Si `AUTO_APPLY=1` : commit automatiquement les mises à jour de docs

**Exemple de feedback :**
```
🎯 ÉMERGENCE Guardian: Feedback Post-Commit
=============================================================

📝 Commit: a1b2c3d4
   Message: feat: add new authentication module

🎯 Génération du rapport unifié (Nexus Coordinator)...
   ✅ Rapport Nexus généré

📊 RÉSUMÉ DES VÉRIFICATIONS
-------------------------------------------------------------
📚 Anima (DocKeeper) - Documentation:
   ⚠️  Status: NEEDS UPDATE
      - Gaps trouvés: 3 (High: 1, Medium: 2)
      📄 Détails: .../reports/docs_report.json

🔐 Neo (IntegrityWatcher) - Intégrité:
   ✅ Status: OK - Intégrité vérifiée

🎯 Nexus (Coordinator) - Rapport Unifié:
   📋 System requires attention: 1 high-priority item(s)
   💡 Recommandations principales:
      🔴 [HIGH] Update authentication documentation
      📄 Rapport complet: .../reports/unified_report.json
```

### Pre-Push Hook (avant chaque push)

**Que fait-il ?**
1. **Exécute ProdGuardian** - vérifie l'état de la production via Cloud Run logs
2. Vérifie que les rapports Documentation et Intégrité sont OK
3. Alerte si la production a des problèmes avant de déployer

**Comportement :**
- ✅ **Push autorisé** si production OK et rapports clean
- ⚠️ **Warnings affichés** si production dégradée mais push autorisé
- 🚨 **Push BLOQUÉ** si production en état CRITICAL

**Bypass (déconseillé) :**
```bash
git push --no-verify
```

---

## 🔧 Variables d'Environnement

### `AUTO_UPDATE_DOCS`

**Description :** Active l'analyse et la proposition de mises à jour de documentation

**Valeurs :**
- `0` (défaut) : Désactivé
- `1` : Activé

**Comportement quand activé :**
- Le post-commit hook exécute `auto_update_docs.py`
- Analyse les changements de code et propose des mises à jour de docs
- Affiche les recommandations

### `AUTO_APPLY`

**Description :** Applique et commit automatiquement les mises à jour de documentation

**Prérequis :** `AUTO_UPDATE_DOCS=1`

**Valeurs :**
- `0` (défaut) : Propose seulement, ne modifie pas
- `1` : Applique ET commit automatiquement

**⚠️ Attention :** En mode `AUTO_APPLY=1`, un commit peut générer un commit automatique de documentation. Utilise avec précaution.

### `CHECK_GIT_STATUS`

**Description :** Vérifie les changements non commités avant d'exécuter le scheduler

**Valeurs :**
- `0` : Skip la vérification (mode monitoring continu)
- `1` (défaut) : Vérifie et skip si changements non commités

**Utilisation :** Utile pour le monitoring en arrière-plan via `scheduler.py`

---

## 🔄 Monitoring Continu en Arrière-Plan

Pour un monitoring qui tourne en permanence (vérifie toutes les heures) :

### Option 1 : Windows Task Scheduler

Voir le guide complet : [GUIDE_TASK_SCHEDULER.md](GUIDE_TASK_SCHEDULER.md)

**Résumé rapide :**
```powershell
# Créer une tâche qui exécute toutes les heures
schtasks /create /tn "EMERGENCE Guardian" /tr "C:\dev\emergenceV8\.venv\Scripts\python.exe C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts\scheduler.py" /sc HOURLY /st 09:00
```

### Option 2 : Mode Hidden (sans bloquer sur git status)

```bash
# Configure pour ignorer les changements non commités
export CHECK_GIT_STATUS=0

# Lance le scheduler en mode continu
python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

Voir le guide complet : [HIDDEN_MODE_GUIDE.md](HIDDEN_MODE_GUIDE.md)

### Option 3 : Linux/Mac Cron Job

```bash
# Édite ta crontab
crontab -e

# Ajoute cette ligne pour exécuter toutes les heures
0 * * * * cd /path/to/emergenceV8 && /path/to/venv/bin/python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

---

## 📊 Rapports Générés

Tous les rapports sont sauvegardés dans :
`claude-plugins/integrity-docs-guardian/reports/`

### Rapports Individuels

**1. `docs_report.json` (Anima - DocKeeper)**
- Détecte les gaps de documentation
- Liste les fichiers modifiés nécessitant des mises à jour de docs
- Propose des actions concrètes

**2. `integrity_report.json` (Neo - IntegrityWatcher)**
- Vérifie la cohérence backend/frontend
- Détecte les endpoints manquants ou mal documentés
- Valide le schéma OpenAPI

**3. `prod_report.json` (ProdGuardian)**
- Analyse les logs de production (Cloud Run)
- Détecte erreurs, warnings, crashes, OOMKilled
- Recommande des actions (rollback, augmenter mémoire, etc.)

### Rapport Unifié

**`unified_report.json` (Nexus - Coordinator)**
- Combine tous les rapports individuels
- Génère un résumé exécutif avec headline
- Liste les recommandations par priorité (HIGH/MEDIUM/LOW)
- Calcule un score de santé globale

**Structure :**
```json
{
  "timestamp": "2025-10-17T...",
  "executive_summary": {
    "headline": "System requires attention: 1 high-priority item(s)",
    "top_recommendations": [
      {
        "priority": "HIGH",
        "agent": "Anima",
        "action": "Update authentication documentation",
        "details": "..."
      }
    ]
  },
  "individual_reports": {
    "anima": { ... },
    "neo": { ... },
    "prodguardian": { ... }
  }
}
```

---

## 🎯 Workflows Recommandés

### Workflow Standard (Développement Local)

1. **Développe ta feature**
   ```bash
   # Code normalement
   git add src/backend/features/auth/auth_service.py
   ```

2. **Commit avec vérification automatique**
   ```bash
   git commit -m "feat: add JWT authentication"
   # → Pre-commit hook vérifie tout automatiquement
   # → Post-commit hook affiche le feedback
   ```

3. **Review les rapports si nécessaire**
   ```bash
   # Si warnings, consulte les détails
   cat claude-plugins/integrity-docs-guardian/reports/docs_report.json
   ```

4. **Push vers remote**
   ```bash
   git push
   # → Pre-push hook vérifie la production
   ```

### Workflow avec Auto-Update de Docs

1. **Active les variables d'environnement**
   ```bash
   export AUTO_UPDATE_DOCS=1
   export AUTO_APPLY=1
   ```

2. **Commit normalement**
   ```bash
   git commit -m "feat: add new feature"
   # → Agents s'exécutent
   # → Documentation est analysée
   # → Mises à jour appliquées ET commitées automatiquement
   ```

3. **Résultat : 2 commits créés**
   - Commit 1 : Ta feature
   - Commit 2 : Mise à jour auto de la documentation

### Workflow CI/CD (Déploiement)

1. **Pre-Push vérifie la production**
   ```bash
   git push origin main
   # → ProdGuardian vérifie l'état actuel
   # → Bloque si CRITICAL
   ```

2. **Si production OK → Déploiement continue**
   - Les tests CI/CD s'exécutent
   - Déploiement sur Cloud Run

3. **Post-déploiement : Monitoring continu**
   - Le scheduler vérifie toutes les heures
   - Génère des rapports réguliers
   - Alerte si problème détecté

---

## 🔍 Debugging et Troubleshooting

### Les hooks ne s'exécutent pas

**Vérification :**
```bash
# Vérifie que les hooks existent
ls -la .git/hooks/

# Vérifie qu'ils sont exécutables (Unix/Mac/Linux)
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/post-commit
chmod +x .git/hooks/pre-push
```

**Sur Windows :** Git Bash gère les permissions automatiquement.

### Erreur "Python not found" dans les hooks

**Solution :**
Les hooks cherchent Python dans le venv. Assure-toi que :
- `.venv/Scripts/python.exe` existe (Windows)
- `.venv/bin/python` existe (Unix)

### ProdGuardian échoue avec "gcloud not found"

**Solutions :**
1. Installe Google Cloud SDK : https://cloud.google.com/sdk/docs/install
2. Authentifie-toi : `gcloud auth login`
3. Ou désactive la vérif de prod en skippant le pre-push : `git push --no-verify`

### Le scheduler skip toujours à cause de "changements non commités"

**Solution :**
```bash
# Active le mode HIDDEN qui ignore les changements
export CHECK_GIT_STATUS=0

# Ou commit tes changements
git add . && git commit -m "wip: save progress"
```

### Trop de rapports générés

**Nettoyage :**
```bash
# Les rapports sont stockés dans:
claude-plugins/integrity-docs-guardian/reports/

# Les anciens rapports (> 30 jours) sont automatiquement nettoyés
# Pour nettoyer manuellement:
rm claude-plugins/integrity-docs-guardian/reports/consolidated_report_*.json
```

---

## 📚 Ressources Complémentaires

- **[QUICKSTART_PHASE3.md](QUICKSTART_PHASE3.md)** - Guide Phase 3 complet
- **[HIDDEN_MODE_GUIDE.md](HIDDEN_MODE_GUIDE.md)** - Monitoring continu silencieux
- **[GUIDE_TASK_SCHEDULER.md](GUIDE_TASK_SCHEDULER.md)** - Configuration Windows Task Scheduler
- **[AUTO_ORCHESTRATION.md](AUTO_ORCHESTRATION.md)** - Détails de l'orchestration automatique
- **[README.md](README.md)** - Documentation principale du système Guardian

---

## 🤝 Support et Contribution

Si tu rencontres des problèmes ou as des suggestions :

1. **Check les logs** dans `claude-plugins/integrity-docs-guardian/logs/`
2. **Consulte les rapports** pour comprendre ce qui est détecté
3. **Teste manuellement** les agents :
   ```bash
   python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py
   python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py
   python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
   ```

---

**🎉 Félicitations ! Ton système Guardian est maintenant entièrement automatisé.**

**Prochain commit → Feedback automatique immédiat ! 🚀**
