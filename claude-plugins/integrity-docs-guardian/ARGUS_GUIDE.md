# 🔍 Guide ARGUS - LogWatcher

**Version:** 1.0.0
**Date:** 2025-10-17
**Agent:** Argus (The All-Seeing Guardian)

---

## 📋 Vue d'ensemble

**ARGUS** est un nouvel agent Guardian qui surveille en temps réel les logs de votre environnement de développement local (backend FastAPI + frontend Vite/React) pour:

✅ **Détecter automatiquement les erreurs** dans les logs backend et frontend
✅ **Identifier la cause racine** des problèmes
✅ **Proposer des corrections automatiques** avec niveau de confiance
✅ **Appliquer les fixes** après validation utilisateur
✅ **Vérifier que la correction a fonctionné**

---

## 🎯 Cas d'usage

### Quand utiliser ARGUS?

- 🔧 **Pendant le développement** - Surveillance continue des logs
- 🐛 **Lors du debug** - Détection et correction rapide d'erreurs
- 🚀 **Avant un commit** - Vérifier qu'il n'y a pas d'erreurs non résolues
- 📚 **Apprentissage** - Comprendre les patterns d'erreurs courants

### Que détecte ARGUS?

**Backend (FastAPI/Python):**
- ImportError (modules manquants)
- AttributeError (accès à des attributs undefined)
- TypeError (incompatibilités de types)
- ValidationError (erreurs Pydantic)
- DatabaseError (erreurs SQL)
- HTTP 500/404 errors

**Frontend (Vite/React/JavaScript):**
- TypeError (null/undefined access)
- ReferenceError (variables non définies)
- SyntaxError (erreurs de syntaxe)
- React Warnings (keys manquantes, hooks rules, etc.)
- Network Errors (failed API calls, CORS)

---

## 🚀 Démarrage rapide

### Prérequis

1. **Backend et/ou frontend en cours d'exécution:**
   ```bash
   # Terminal 1 - Backend
   cd src/backend
   python -m uvicorn main:app --reload --port 8000

   # Terminal 2 - Frontend
   cd src/frontend
   npm run dev
   ```

2. **PowerShell et Python installés** (Windows)

### Lancer ARGUS

**Méthode 1 - Via Claude Code (recommandé):**
```bash
/check_logs
```

**Méthode 2 - Via PowerShell directement:**
```powershell
./claude-plugins/integrity-docs-guardian/scripts/argus_monitor.ps1
```

**Méthode 3 - Avec options:**
```powershell
# Surveiller pendant 30 minutes
./claude-plugins/integrity-docs-guardian/scripts/argus_monitor.ps1 -DurationMinutes 30

# Mode rapport uniquement (pas de corrections)
./claude-plugins/integrity-docs-guardian/scripts/argus_monitor.ps1 -ReportOnly
```

---

## 📊 Exemple de rapport

### Cas 1: Erreur d'import détectée

```
🔴 ARGUS - Erreur critique détectée

[1] Backend - ImportError
    File: src/backend/core/auth.py:8
    Message: No module named 'jwt'
    Context: from jwt import encode, decode

    🛠️ Proposed Fix (Confidence: 95%):
        Command: pip install pyjwt
        Risk: Low | Time: ~30s

Voulez-vous que j'applique cette correction? (oui/non)
```

### Cas 2: Erreur frontend null reference

```
🔴 Frontend - TypeError
    File: src/frontend/components/User/Profile.jsx:67
    Message: Cannot read properties of undefined (reading 'name')
    Context: const userName = user.name
    Occurrences: 2

    🛠️ Proposed Fix (Confidence: 92%):
        Before: const userName = user.name
        After:  const userName = user?.name || 'Unknown'
        Risk: Low | Time: ~5s

Voulez-vous que j'applique cette correction? (oui/non)
```

### Cas 3: Schema mismatch backend/frontend

```
🔗 Erreurs liées détectées!

Backend Error (cause racine):
  ValidationError: Field required: 'user_id'
  Endpoint: POST /api/memory/save

Frontend Error (conséquence):
  Network Error: 400 Bad Request

📊 Analyse: Schema mismatch backend/frontend
   Backend attend: user_id (snake_case)
   Frontend envoie: userId (camelCase)

🛠️ Solutions possibles:
  [A] Adapter le backend pour accepter userId
  [B] Adapter le frontend pour envoyer user_id
  [C] Ajouter un transformer automatique

⚠️ Note: Escalade recommandée à Neo (IntegrityWatcher)

Quelle solution préférez-vous?
```

---

## 🔧 Workflow de correction

### Étape 1: Détection
ARGUS surveille les logs en temps réel et détecte les erreurs dès qu'elles apparaissent.

### Étape 2: Analyse
L'agent analyse:
- Le type d'erreur
- Le contexte (fichier, ligne, stack trace)
- La cause probable
- La sévérité (critical, warning, info)

### Étape 3: Proposition de fix
ARGUS génère une ou plusieurs solutions avec:
- Description claire de l'action
- Niveau de confiance (0-100%)
- Risque estimé (low/medium/high)
- Temps estimé d'application

### Étape 4: Validation utilisateur
**IMPORTANT:** ARGUS ne modifie JAMAIS le code sans votre accord explicite!

### Étape 5: Application
Une fois validé, ARGUS:
- Applique la correction
- Attend le reload automatique (uvicorn/vite)
- Surveille les logs pendant 30s
- Confirme que l'erreur est résolue

### Étape 6: Vérification
```
✅ Correction appliquée avec succès!

🔄 Vérification: Relance du backend détectée
   Nouvelle surveillance des logs (30 secondes)...

   ✅ Plus d'ImportError détecté!
   Module 'jwt' importé correctement.

Correction réussie! ✨
```

---

## 🔗 Intégration avec autres agents

### Avec Neo (IntegrityWatcher)

Si ARGUS détecte des **erreurs de schema mismatch** backend/frontend:
```
🔗 ESCALADE À NEO (IntegrityWatcher)

Erreur: Schema mismatch backend/frontend
Suggestion: Lancer /check_integrity après correction
```

### Avec Anima (DocKeeper)

Si une correction modifie une **API ou un comportement documenté**:
```
📚 NOTIFICATION À ANIMA (DocKeeper)

Correction appliquée: Endpoint modifié
Documentation potentiellement affectée
Suggestion: Lancer /check_docs pour mise à jour
```

### Avec ProdGuardian

ARGUS apprend des erreurs de production remontées par ProdGuardian pour les détecter plus tôt en développement.

---

## ⚙️ Configuration

### Fichier de configuration
`claude-plugins/integrity-docs-guardian/config/argus_config.json` (optionnel)

```json
{
  "monitoring": {
    "backend_port": 8000,
    "frontend_port": 5173,
    "check_interval_seconds": 5
  },
  "detection": {
    "min_severity": "warning",
    "aggregate_duplicates": true
  },
  "auto_fix": {
    "enabled": true,
    "require_approval": true,
    "min_confidence_threshold": 75
  }
}
```

### Patterns d'erreurs personnalisés

Éditez `scripts/argus_analyzer.py` pour ajouter vos propres patterns:

```python
BACKEND_ERROR_PATTERNS = [
    {
        "type": "CustomError",
        "pattern": r"CustomError:\s+(.+)",
        "severity": "critical"
    }
]
```

---

## 📂 Fichiers générés

### Rapports

- `reports/dev_logs_report.json` - Rapport JSON complet
- `reports/argus_session_YYYYMMDD_HHMMSS.log` - Log de session
- `reports/argus_fixes_history.json` - Historique des corrections

### Exemple de rapport JSON

```json
{
  "timestamp": "2025-10-17T14:32:15Z",
  "session_id": "dev-20251017-143215",
  "monitoring_duration_minutes": 15.3,
  "status": "errors_detected",
  "backend_errors": [
    {
      "timestamp": "2025-10-17T14:30:42Z",
      "severity": "critical",
      "type": "ImportError",
      "message": "No module named 'jwt'",
      "file": "src/backend/core/auth.py",
      "line": 8,
      "fix_proposals": [...]
    }
  ],
  "statistics": {
    "total_errors": 3,
    "critical": 2,
    "warnings": 1
  }
}
```

---

## 🛡️ Sécurité et sauvegardes

### Règles de sécurité

✅ ARGUS ne modifie **JAMAIS** le code sans validation explicite
✅ Toutes les modifications sont **loggées**
✅ Un **backup** est créé avant chaque modification (via git stash si possible)
✅ En cas d'échec, **rollback automatique** proposé

### Rollback manuel

Si une correction a causé des problèmes:

```bash
# Annuler la dernière correction
python scripts/argus_monitor.py --rollback

# Annuler une correction spécifique
python scripts/argus_monitor.py --rollback-fix backend-001
```

Ou via Git:
```bash
git stash pop  # Restaurer l'état avant correction
```

---

## 💡 Conseils d'utilisation

### ✅ Bonnes pratiques

1. **Lancer ARGUS en début de session de dev**
   - Détecte les erreurs au fur et à mesure
   - Corrections rapides avant qu'elles s'accumulent

2. **Vérifier les corrections proposées**
   - Même avec confiance 95%, toujours vérifier le code
   - Comprendre la cause racine, pas juste appliquer le fix

3. **Apprendre des patterns**
   - ARGUS révèle les erreurs récurrentes
   - Identifier et corriger les causes systémiques

4. **Utiliser en complément de Neo**
   - ARGUS = erreurs runtime en dev
   - Neo = incohérences structurelles backend/frontend

### ❌ À éviter

1. **Ne pas auto-appliquer tous les fixes sans réfléchir**
   - Certaines corrections nécessitent une compréhension du contexte

2. **Ne pas ignorer les warnings**
   - Ils peuvent devenir des erreurs critiques plus tard

3. **Ne pas modifier le code de production**
   - ARGUS est pour le développement local uniquement

---

## 🔧 Dépannage

### Problème: "Aucun service détecté"

**Cause:** Backend/Frontend non lancés
**Solution:**
```bash
# Vérifier les ports
netstat -ano | findstr ":8000"
netstat -ano | findstr ":5173"

# Lancer les services si nécessaire
```

### Problème: "Impossible d'attacher aux processus"

**Cause:** Permissions insuffisantes ou processus introuvables
**Solution:**
```powershell
# Lancer avec ports explicites
./argus_monitor.ps1 -BackendPort 8000 -FrontendPort 5173
```

### Problème: "Correction appliquée mais erreur persiste"

**Cause:** Plusieurs causes possibles
**Solution:**
1. Vérifier que le reload automatique a fonctionné
2. Relancer manuellement backend/frontend
3. Analyser le nouveau message d'erreur
4. Demander une approche alternative à ARGUS

### Problème: "Trop de faux positifs"

**Cause:** Sensibilité trop élevée
**Solution:**
```json
// Ajuster dans argus_config.json
{
  "detection": {
    "min_severity": "critical"  // Ignorer warnings et info
  },
  "auto_fix": {
    "min_confidence_threshold": 90  // Augmenter le seuil
  }
}
```

---

## 📊 Statistiques et métriques

ARGUS track plusieurs métriques pour améliorer sa détection:

- **Taux de détection:** % d'erreurs détectées vs. réelles
- **Taux de succès des fixes:** % de corrections qui résolvent l'erreur
- **Temps de réponse:** Temps entre erreur et proposition de fix
- **Confiance moyenne:** Moyenne des scores de confiance
- **Erreurs récurrentes:** Patterns d'erreurs qui reviennent souvent

Ces métriques sont sauvegardées dans `reports/argus_metrics.json`.

---

## 🚀 Évolutions futures

### Fonctionnalités prévues

- [ ] **Capture console navigateur** via DevTools Protocol
- [ ] **Machine Learning** pour améliorer la confiance des fixes
- [ ] **Hot reload intelligent** avec rollback automatique si erreur
- [ ] **Intégration IDE** pour afficher erreurs inline dans VSCode
- [ ] **Analyse de performance** pour détecter les ralentissements
- [ ] **Détection de patterns** pour suggérer du refactoring

---

## 📞 Support

### Besoin d'aide?

1. **Consulter la doc complète:** [argus_logwatcher.md](agents/argus_logwatcher.md)
2. **Vérifier les logs:** `reports/argus_session_*.log`
3. **Lire les rapports JSON:** `reports/dev_logs_report.json`
4. **Demander à Claude Code:** `/check_logs` avec questions spécifiques

### Rapporter un bug

Si ARGUS ne détecte pas une erreur ou propose un mauvais fix:

1. Copier le rapport JSON
2. Noter le type d'erreur non détecté
3. Suggérer le pattern de détection manquant
4. Mettre à jour `scripts/argus_analyzer.py` avec le nouveau pattern

---

## 🎓 Exemples d'utilisation

### Exemple 1: Session de développement standard

```powershell
# Lancer backend et frontend
# Terminal 1
cd src/backend && python -m uvicorn main:app --reload

# Terminal 2
cd src/frontend && npm run dev

# Terminal 3 - Lancer ARGUS
./claude-plugins/integrity-docs-guardian/scripts/argus_monitor.ps1

# Travailler normalement
# ARGUS vous alertera en cas d'erreur
```

### Exemple 2: Debug d'un problème spécifique

```powershell
# Reproduire le bug
# Lancer ARGUS pour 5 minutes
./argus_monitor.ps1 -DurationMinutes 5

# Déclencher l'erreur dans l'app
# ARGUS capturera et analysera

# Revoir le rapport après
cat reports/dev_logs_report.json
```

### Exemple 3: Vérification avant commit

```powershell
# Avant de commit, vérifier qu'il n'y a pas d'erreurs
./argus_monitor.ps1 -DurationMinutes 2 -ReportOnly

# Si status = "ok", procéder au commit
git add .
git commit -m "feat: new feature"
```

---

**🔍 ARGUS surveille tout, corrige intelligemment, et vous laisse vous concentrer sur le code qui compte !**

---

**Version:** 1.0.0
**Créé:** 2025-10-17
**Maintenu par:** ÉMERGENCE Team
