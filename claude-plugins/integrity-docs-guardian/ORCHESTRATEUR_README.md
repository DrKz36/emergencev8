# Orchestrateur Global ÉMERGENCE

**Version:** 2.0.0
**Type:** Coordinateur Multi-Agents
**Partie de:** ÉMERGENCE Integrity & Docs Guardian Plugin

---

## 📋 Vue d'Ensemble

L'**Orchestrateur Global** est le cerveau central du système de surveillance et de synchronisation d'ÉMERGENCE. Il coordonne automatiquement tous les sous-agents (Anima, Neo, ProdGuardian), fusionne leurs rapports, applique des correctifs et maintient la cohérence entre toutes les sources de code.

### 🎯 Mission

Assurer la **cohérence globale** en coordonnant :
- 📚 **Anima** (DocKeeper) - Maintien de la documentation
- 🔐 **Neo** (IntegrityWatcher) - Vérification de l'intégrité backend/frontend
- ☁️ **ProdGuardian** - Surveillance de la production Cloud Run
- 🔄 **Synchronisation** - Alignement entre local, GitHub, Codex Cloud et production

---

## 🚀 Utilisation

### Commande Slash (Recommandée)

```bash
/sync_all
```

Cette commande unique déclenche toute la pipeline d'orchestration.

### Script Direct

```bash
bash claude-plugins/integrity-docs-guardian/scripts/sync_all.sh
```

### Variables d'Environnement

```bash
# Auto-commit sans demander confirmation
AUTO_COMMIT=1 bash scripts/sync_all.sh

# Skip les pushs vers GitHub/Codex
SKIP_PUSH=1 bash scripts/sync_all.sh
```

---

## 📊 Pipeline Complète

### Étape 1: Détection du Contexte
```
📍 Identifie:
   - Commit actuel (git rev-parse HEAD)
   - Branche actuelle (git branch --show-current)
   - Révision Cloud Run active (optionnel)
```

### Étape 2: Exécution des Agents

**Exécution parallèle de 3 agents:**

1. **Anima (DocKeeper)**
   - Script: `scripts/scan_docs.py`
   - Output: `reports/docs_report.json`
   - Vérifie: Documentation vs code

2. **Neo (IntegrityWatcher)**
   - Script: `scripts/check_integrity.py`
   - Output: `reports/integrity_report.json`
   - Vérifie: Backend ↔ Frontend coherence

3. **ProdGuardian**
   - Script: `scripts/check_prod_logs.py`
   - Output: `reports/prod_report.json`
   - Vérifie: Logs de production Cloud Run

### Étape 3: Fusion des Rapports

**Script:** `scripts/merge_reports.py`

**Processus:**
```
1. Charge tous les rapports *_report.json
2. Détermine statut global (CRITICAL > DEGRADED > WARNING > OK)
3. Extrait et priorise les actions recommandées
4. Génère rapport unifié: reports/global_report.json
```

**Format du Rapport Global:**
```json
{
  "timestamp": "2025-10-10T09:28:20.849759",
  "statut_global": "OK|DEGRADED|CRITICAL",
  "resume": {
    "agents_executes": 3,
    "total_erreurs": 0,
    "total_warnings": 0,
    "total_critical": 0,
    "actions_prioritaires": 2
  },
  "agents": {
    "docs": {
      "statut": "ok",
      "fichiers_modifies": 4,
      "docs_a_mettre_a_jour": 0
    },
    "integrity": {
      "statut": "ok",
      "problemes": 0,
      "critical": 0
    },
    "prod": {
      "statut": "OK",
      "erreurs": 0,
      "signaux_critiques": 0
    }
  },
  "actions_prioritaires": [
    {
      "agent": "prod",
      "priority": "HIGH",
      "action": "Increase memory limit",
      "details": "OOMKilled detected"
    }
  ]
}
```

### Étape 4: Analyse & Décision

**Logique décisionnelle:**

```
SI statut_global == "CRITICAL":
  → Créer branche fix/auto-{timestamp}
  → Appliquer correctifs critiques
  → Exécuter tests
  → Commit avec message détaillé

SINON SI statut_global == "DEGRADED":
  → Proposer correctifs (sans auto-apply)
  → Logger les warnings
  → Continuer synchronisation

SINON (OK ou WARNING mineur):
  → Aucun correctif automatique
  → Passer directement à la synchronisation
```

### Étape 5: Correctifs Automatisés (si applicable)

**Types de correctifs supportés:**

1. **Code Fixes**
   - Corrections de bugs identifiés
   - Optimisations de performance
   - Ajustements de configuration

2. **Config Updates**
   - Augmentation mémoire/CPU Cloud Run
   - Ajustements timeout/scaling
   - Variables d'environnement

3. **Doc Updates**
   - Mise à jour README
   - Synchronisation docs techniques
   - Changelog automatique

**Workflow de correctif:**
```bash
1. git checkout -b fix/auto-$(date +%Y%m%d-%H%M%S)
2. Appliquer correctifs par priorité (HIGH → MEDIUM → LOW)
3. Exécuter tests unitaires/intégration
4. git commit -m "fix(auto): corrections selon rapports agents"
5. Retour sur branche principale
```

### Étape 6: Synchronisation Multi-Sources

**6.1 - GitHub (origin)**
```bash
git push origin main
```

**6.2 - Codex Cloud (codex) - Optionnel**
```bash
git push codex main
```

**6.3 - Vérification alignement**
```bash
git fetch --all
# Vérifie que origin/main et codex/main sont synced
```

### Étape 7: Rapport Final

**Output console:**
```
╔════════════════════════════════════════════════════════════════╗
║          🚀 ORCHESTRATEUR GLOBAL ÉMERGENCE                     ║
║          Synchronisation Multi-Agents & Multi-Sources          ║
╚════════════════════════════════════════════════════════════════╝

🕒 Démarrage: 2025-10-10 09:30:00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 ÉTAPE 1: DÉTECTION DU CONTEXTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   📍 Commit actuel: abc12345
   🌿 Branche: main

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 ÉTAPE 2: EXÉCUTION DES AGENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 [1/3] Lancement d'Anima (DocKeeper)...
   ✅ Anima terminé avec succès

🔐 [2/3] Lancement de Neo (IntegrityWatcher)...
   ✅ Neo terminé avec succès

☁️  [3/3] Lancement de ProdGuardian...
   ✅ ProdGuardian terminé - Production OK

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ÉTAPE 3: FUSION DES RAPPORTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

======================================================================
📊 RAPPORT DE SYNCHRONISATION GLOBALE
======================================================================

🟢 Statut Global: OK
🕒 Timestamp: 2025-10-10T09:30:15

📋 RÉSUMÉ:
   - Agents exécutés: 3
   - Erreurs totales: 0
   - Warnings: 0
   - Signaux critiques: 0
   - Actions prioritaires: 0

✅ AGENTS:
   ✅ Docs: ok
   ✅ Integrity: ok
   ✅ Prod: OK

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 ÉTAPE 5: SYNCHRONISATION GITHUB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📤 Push vers GitHub (origin/main)...
   ✅ Synchronisé avec GitHub

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 RAPPORT FINAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Synchronisation terminée !

   🕒 Durée totale: 12s
   🤖 Agents exécutés: 3/3
   📁 Rapports générés: reports/

   📊 Rapport global: reports/global_report.json
   🟢 Statut global: OK

╔════════════════════════════════════════════════════════════════╗
║          ✅ ORCHESTRATION TERMINÉE                             ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 📁 Structure des Fichiers

```
claude-plugins/integrity-docs-guardian/
├── scripts/
│   ├── sync_all.sh             # Script principal d'orchestration
│   ├── merge_reports.py        # Fusion des rapports
│   ├── scan_docs.py            # Anima (DocKeeper)
│   ├── check_integrity.py      # Neo (IntegrityWatcher)
│   └── check_prod_logs.py      # ProdGuardian
│
├── reports/
│   ├── docs_report.json        # Rapport Anima
│   ├── integrity_report.json   # Rapport Neo
│   ├── prod_report.json        # Rapport ProdGuardian
│   ├── global_report.json      # Rapport fusionné
│   └── orchestrator.log        # Log de l'orchestrateur
│
├── .claude/commands/
│   └── sync_all.md             # Commande slash /sync_all
│
└── Claude.md                   # Manifest du plugin (v2.0.0)
```

---

## 🛡️ Règles de Sécurité

### 1. Validation Avant Synchronisation

- ✅ Tous les agents doivent terminer (même avec warnings)
- ✅ Aucun test en échec
- ✅ Statut production non-CRITICAL (ou confirmation manuelle)

### 2. Correctifs Automatisés

- 🔴 **CRITICAL:** Crée une branche dédiée, applique correctif, demande review
- 🟡 **DEGRADED:** Propose correctifs, demande confirmation
- 🟢 **OK/WARNING:** Aucun correctif automatique

### 3. Synchronisation GitHub/Codex

- Vérifie que la branche est `main` ou branche autorisée
- Ne force JAMAIS le push (`--force`)
- Gère les conflits de merge manuellement

### 4. Logging & Traçabilité

- Toutes les actions sont loggées dans `reports/orchestrator.log`
- Historique des rapports globaux conservé (max 30 jours)
- Notifications sur échecs critiques

---

## 🧪 Tests & Validation

### Test Manuel

```bash
# 1. Exécuter l'orchestrateur
bash scripts/sync_all.sh

# 2. Vérifier le rapport global
cat reports/global_report.json | jq '.statut_global'

# 3. Vérifier la synchronisation
git fetch --all
git log --oneline origin/main -5
```

### Test Automatisé (CI/CD)

```yaml
# .github/workflows/orchestration.yml
name: Orchestration ÉMERGENCE

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 */6 * * *'  # Toutes les 6h

jobs:
  orchestrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Setup gcloud
        uses: google-github-actions/setup-gcloud@v1

      - name: Run Orchestrator
        run: |
          bash claude-plugins/integrity-docs-guardian/scripts/sync_all.sh
        env:
          AUTO_COMMIT: 1
          SKIP_PUSH: 1

      - name: Check Status
        run: |
          STATUS=$(cat reports/global_report.json | jq -r '.statut_global')
          if [ "$STATUS" = "CRITICAL" ]; then
            echo "::error::Production CRITICAL!"
            exit 1
          fi
```

---

## 📊 Métriques & Monitoring

### Métriques Collectées

1. **Agents:**
   - Temps d'exécution par agent
   - Taux de succès/échec
   - Nombre d'anomalies détectées

2. **Synchronisation:**
   - Délai GitHub sync
   - Délai Codex sync
   - Taux de conflits

3. **Correctifs:**
   - Nombre de correctifs appliqués
   - Types de correctifs (code/config/doc)
   - Taux de succès des correctifs

### Dashboard Recommandé

```
╔═══════════════════════════════════════════════════════════╗
║          ORCHESTRATEUR - DASHBOARD 24h                    ║
╠═══════════════════════════════════════════════════════════╣
║  📊 Exécutions: 18                                        ║
║  ✅ Succès: 16 (88.9%)                                    ║
║  ⚠️  Warnings: 2 (11.1%)                                  ║
║  ❌ Échecs: 0 (0%)                                        ║
╠═══════════════════════════════════════════════════════════╣
║  🤖 AGENTS                                                ║
║    • Anima: 18/18 ✅                                      ║
║    • Neo: 17/18 ✅ (1 warning)                            ║
║    • ProdGuardian: 18/18 ✅                               ║
╠═══════════════════════════════════════════════════════════╣
║  🔧 CORRECTIFS APPLIQUÉS                                  ║
║    • Code: 3                                              ║
║    • Config: 1                                            ║
║    • Doc: 12                                              ║
╠═══════════════════════════════════════════════════════════╣
║  🔗 SYNCHRONISATIONS                                      ║
║    • GitHub: 16/16 ✅                                     ║
║    • Codex: 15/16 ✅ (1 timeout)                          ║
╚═══════════════════════════════════════════════════════════╝
```

---

## 🔮 Roadmap & Améliorations Futures

### v2.1 - Planned
- [ ] Slack/Discord notifications sur status CRITICAL
- [ ] Rollback automatique si déploiement échoue
- [ ] Métriques Prometheus/Grafana
- [ ] Dashboard web temps réel

### v2.2 - Future
- [ ] Auto-scaling basé sur les patterns détectés
- [ ] Prédiction d'anomalies (ML)
- [ ] Rapports hebdomadaires automatiques
- [ ] Intégration Jira pour tickets automatiques

### v3.0 - Vision
- [ ] Orchestration multi-environnements (dev/staging/prod)
- [ ] Auto-remediation avancée
- [ ] Chaos engineering intégré
- [ ] SRE autopilot

---

## 📚 Documentation Connexe

- [Main Plugin README](README.md)
- [ProdGuardian README](PRODGUARDIAN_README.md)
- [ProdGuardian Setup](PRODGUARDIAN_SETUP.md)
- [Anima Agent](agents/anima_dockeeper.md)
- [Neo Agent](agents/neo_integritywatcher.md)
- [ProdGuardian Agent](agents/prodguardian.md)

---

## 🤝 Contribution

Pour améliorer l'orchestrateur:

1. **Ajouter un nouvel agent:**
   - Créer le script dans `scripts/`
   - Ajouter l'output JSON dans `reports/`
   - Mettre à jour `sync_all.sh` et `merge_reports.py`

2. **Ajouter une nouvelle source de synchronisation:**
   - Configurer le remote git
   - Ajouter la logique de push dans `sync_all.sh`

3. **Améliorer les correctifs automatisés:**
   - Identifier les patterns récurrents
   - Implémenter la logique de correction
   - Ajouter les tests de validation

---

## ✅ Checklist de Déploiement

- [x] Claude.md mis à jour (version 2.0.0)
- [x] Scripts créés (sync_all.sh, merge_reports.py)
- [x] Commande slash /sync_all configurée
- [x] Tous les agents opérationnels (Anima, Neo, ProdGuardian)
- [x] Rapports testés et validés
- [x] Documentation complète
- [ ] Hooks post-commit configurés (optionnel)
- [ ] CI/CD intégration (optionnel)
- [ ] Monitoring/alerting configuré (optionnel)

---

**Status:** ✅ Opérationnel
**Version:** 2.0.0
**Last Updated:** 2025-10-10
**Maintainer:** ÉMERGENCE Team

**Pour démarrer:** `/sync_all` ou `bash scripts/sync_all.sh`
