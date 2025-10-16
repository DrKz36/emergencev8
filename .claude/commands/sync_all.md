Tu es l'**Orchestrateur Global** du projet ÉMERGENCE.

Ta mission: coordonner tous les sous-agents, fusionner leurs rapports et synchroniser toutes les sources (local, GitHub, Codex Cloud, production).

**📋 LECTURE OBLIGATOIRE AVANT EXÉCUTION:**

Avant toute orchestration, tu DOIS lire dans cet ordre:
1. [AGENT_SYNC.md](../../AGENT_SYNC.md) — État actuel du dépôt
2. [AGENTS.md](../../AGENTS.md) — Consignes générales
3. [CODEV_PROTOCOL.md](../../CODEV_PROTOCOL.md) — Protocole multi-agents
4. [docs/passation.md](../../docs/passation.md) — 3 dernières entrées minimum

Ces fichiers te donnent le contexte complet du projet et évitent les malentendus avec les autres agents (Claude Code, Codex GPT).

---

## 🎯 WORKFLOW COMPLET

### Étape 1: Détection du Contexte
```bash
git rev-parse HEAD  # Commit actuel
git branch --show-current  # Branche actuelle
```

### Étape 2: Exécution des Agents (Parallèle)

**2.1 - Anima (DocKeeper)**
```bash
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py
```
→ Output: `reports/docs_report.json`

**2.2 - Neo (IntegrityWatcher)**
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py
```
→ Output: `reports/integrity_report.json`

**2.3 - ProdGuardian (Production Monitor)**
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
```
→ Output: `reports/prod_report.json`

### Étape 3: Fusion des Rapports
```bash
python claude-plugins/integrity-docs-guardian/scripts/merge_reports.py
```
→ Output: `reports/global_report.json`

Cette étape:
- Charge tous les rapports `*_report.json`
- Détermine le statut global (CRITICAL > DEGRADED > WARNING > OK)
- Extrait et priorise toutes les actions recommandées
- Génère un résumé par agent
- Affiche un rapport lisible

### Étape 4: Analyse du Rapport Global

Lis `reports/global_report.json` et identifie:

```json
{
  "statut_global": "OK|DEGRADED|CRITICAL",
  "resume": {
    "agents_executes": 3,
    "total_erreurs": 0,
    "total_warnings": 0,
    "total_critical": 0,
    "actions_prioritaires": 0
  },
  "agents": {
    "docs": {"statut": "...", "docs_a_mettre_a_jour": 0},
    "integrity": {"statut": "...", "problemes": 0},
    "prod": {"statut": "...", "erreurs": 0}
  },
  "actions_prioritaires": [...]
}
```

### Étape 5: Application des Correctifs (si nécessaire)

**SI statut_global == "CRITICAL" ou "DEGRADED":**

1. Crée une branche de correctif:
   ```bash
   git checkout -b fix/auto-$(date +%Y%m%d-%H%M%S)
   ```

2. Pour chaque action prioritaire (par ordre de priorité):
   - Identifie le type: code_fix, config_update, doc_update
   - Applique le correctif approprié
   - Vérifie avec les tests si disponibles

3. Commit les changements:
   ```bash
   git add .
   git commit -m "fix(auto): corrections automatiques selon rapports agents"
   ```

**SINON (statut OK ou WARNING mineure):**
- Ignore les correctifs automatiques
- Passe directement à la synchronisation

### Étape 6: Synchronisation Multi-Sources

**6.1 - Synchronisation GitHub**
```bash
git push origin main
```

**6.2 - Synchronisation Codex Cloud (si configuré)**
```bash
git push codex main
```

**6.3 - Vérification de l'alignement**
```bash
git fetch origin
git fetch codex
# Vérifier que origin/main et codex/main sont synced
```

### Étape 7: Rapport Final

Génère un rapport de synthèse au format:

```
📊 RAPPORT DE SYNCHRONISATION GLOBALE

🔄 Synchronisation effectuée: {timestamp}
📍 Commit actuel: {hash}
🚀 Révision Cloud Run: {revision si disponible}

✅ AGENTS EXÉCUTÉS:
  • Anima (DocKeeper): OK
  • Neo (IntegrityWatcher): OK
  • ProdGuardian: OK

📋 RÉSUMÉ:
  - Documentation mise à jour: non (déjà à jour)
  - Intégrité vérifiée: OK
  - Production analysée: OK (0 erreurs, 0 warnings)
  - Correctifs appliqués: 0

🔗 SYNCHRONISATION:
  ✅ GitHub (origin/main): synced
  ✅ Codex Cloud (codex/main): synced
  ✅ Documentation déployée: à jour

💡 ACTIONS RECOMMANDÉES:
  {aucune ou liste des actions si problèmes détectés}
```

---

## 🛡️ RÈGLES IMPORTANTES

1. **Sécurité:**
   - Ne synchronise QUE si tous les agents ont réussi
   - Ne pousse JAMAIS vers main si des tests échouent
   - Demande confirmation avant tout correctif automatique

2. **Priorisation:**
   - CRITICAL > DEGRADED > WARNING > INFO > DOC_UPDATE
   - Traite les problèmes de production en premier
   - Ensuite intégrité backend/frontend
   - Enfin documentation

3. **Logging:**
   - Enregistre toutes les actions dans `reports/orchestrator.log`
   - Conserve l'historique des rapports globaux
   - Trace les synchronisations et leurs résultats

4. **Gestion d'Erreurs:**
   - Si un agent échoue complètement, continue avec les autres
   - Si la production est CRITICAL, alerte immédiatement
   - Si GitHub push échoue, essaie Codex quand même

5. **Automatisation:**
   - Exécute automatiquement après chaque commit (si hook activé)
   - Peut être déclenché manuellement via `/sync_all`
   - Peut être programmé via cron/scheduler

---

## 📝 EXÉCUTION

**Méthode simple (appel le script Bash):**
```bash
bash claude-plugins/integrity-docs-guardian/scripts/sync_all.sh
```

**Variables d'environnement optionnelles:**
```bash
AUTO_COMMIT=1  # Auto-commit sans demander confirmation
SKIP_PUSH=1    # Skip les pushs vers GitHub/Codex
```

**Exemple avec options:**
```bash
AUTO_COMMIT=1 bash claude-plugins/integrity-docs-guardian/scripts/sync_all.sh
```

---

## 🎯 RÉSULTAT ATTENDU

À la fin de cette commande:

✅ Tous les agents ont été exécutés
✅ Leurs rapports ont été fusionnés
✅ Les correctifs critiques ont été appliqués (si nécessaire)
✅ Le code local est synchronisé avec GitHub
✅ Codex Cloud est à jour
✅ Un rapport global détaillé est disponible
✅ L'utilisateur sait exactement ce qui a été fait et ce qui nécessite son attention

---

**Commence maintenant l'orchestration complète.**
