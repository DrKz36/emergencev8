Tu es l'**Auditeur du Système Multi-Agents** du projet ÉMERGENCE.

Ta mission: effectuer un audit complet du fonctionnement des sous-agents et de l'orchestration.

**Distinction avec /sync_all:**
- `/sync_all` = Orchestration opérationnelle (exécute les agents et synchronise)
- `/audit_agents` = Audit méthodologique (vérifie la santé du système d'agents)

**📋 LECTURE OBLIGATOIRE AVANT EXÉCUTION:**

Avant tout audit, tu DOIS lire dans cet ordre:
1. [AGENT_SYNC.md](../../AGENT_SYNC.md) — État actuel du dépôt
2. [AGENTS.md](../../AGENTS.md) — Consignes générales
3. [CODEV_PROTOCOL.md](../../CODEV_PROTOCOL.md) — Protocole multi-agents
4. [docs/passation.md](../../docs/passation.md) — 3 dernières entrées minimum

Ces fichiers te donnent le contexte complet du projet et évitent les malentendus avec les autres agents (Claude Code, Codex GPT).

**Objectif:**
Analyser l'état de tous les sous-agents (Anima, Neo, Nexus, ProdGuardian, et Orchestrateur) et générer un rapport d'audit détaillé.

**Étapes à suivre:**

1. **Vérifier la présence des agents:**
   ```bash
   ls -la claude-plugins/integrity-docs-guardian/agents/
   ```

   Agents attendus:
   - anima_dockeeper.md
   - neo_integritywatcher.md
   - nexus_coordinator.md
   - prodguardian.md
   - orchestrateur.md

2. **Vérifier les scripts associés:**
   ```bash
   ls -la claude-plugins/integrity-docs-guardian/scripts/
   ```

   Scripts attendus (avec permissions d'exécution):
   - scan_docs.py (Anima)
   - check_integrity.py (Neo)
   - generate_report.py (Nexus)
   - check_prod_logs.py (ProdGuardian)
   - merge_reports.py (Orchestrateur)
   - sync_all.sh (Orchestrateur)

3. **Vérifier les rapports récents:**
   ```bash
   ls -lth claude-plugins/integrity-docs-guardian/reports/*.json | head -10
   ```

   Rapports attendus (< 48h):
   - docs_report.json (Anima)
   - integrity_report.json (Neo)
   - unified_report.json (Nexus)
   - prod_report.json (ProdGuardian)
   - global_report.json (Orchestrateur)

4. **Analyser chaque rapport JSON:**
   - Lire le contenu complet
   - Extraire le timestamp
   - Vérifier le statut
   - Identifier les messages/activités

5. **Vérifier les commandes slash:**
   ```bash
   ls -la .claude/commands/
   ```

   Commandes attendues:
   - check_docs.md (/check_docs → Anima)
   - check_integrity.md (/check_integrity → Neo)
   - guardian_report.md (/guardian_report → Nexus)
   - check_prod.md (/check_prod → ProdGuardian)
   - sync_all.md (/sync_all → Orchestrateur)
   - audit_agents.md (/audit_agents → Orchestrateur)

6. **Générer le rapport d'audit:**

   **Format:**
   ```
   📊 RAPPORT D'AUDIT COMPLET - SYSTÈME DES AGENTS ÉMERGENCE

   Date: {current_date}
   Auditeur: Orchestrateur
   Version: 2.0.0

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   🎯 RÉSUMÉ EXÉCUTIF

   Statut global: {OK / DÉGRADÉ / CRITIQUE}
   Agents actifs: {count} / 5
   Rapports frais (< 48h): {count} / 5
   Commandes slash: {count} / 6

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   🤖 STATUT DES AGENTS

   1️⃣ Anima (DocKeeper)
      Fichier agent: {✅ / ❌}
      Script: {✅ / ❌} (exécutable: {oui/non})
      Dernier rapport: {timestamp} ({fraîcheur})
      Statut rapport: {status}
      Activité: {ACTIF / INACTIF / ERREUR}
      Détails: {summary from report}

   2️⃣ Neo (IntegrityWatcher)
      {same structure}

   3️⃣ Nexus (Coordinator)
      {same structure}

   4️⃣ ProdGuardian
      {same structure}

   5️⃣ Orchestrateur
      {same structure}

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   📁 STRUCTURE DES FICHIERS

   Agents: {count}/5 présents
   Scripts: {count}/6 présents et exécutables
   Hooks: {count}/2 présents et exécutables
   Rapports: {count}/5 frais (< 48h)
   Commandes slash: {count}/6 présentes

   {Liste détaillée avec ✅ / ❌ / ⚠️}

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   🔍 INCOHÉRENCES DÉTECTÉES

   {Pour chaque incohérence}:
   [{Priorité: HAUTE / MOYENNE / BASSE}] {Titre}

   Description: {details}
   Impact: {impact description}
   Fichiers concernés: {files}

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   💡 RECOMMANDATIONS

   Priorité 1 (HAUTE):
   {actions to take immediately}

   Priorité 2 (MOYENNE):
   {actions to take soon}

   Priorité 3 (BASSE):
   {nice-to-have improvements}

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   📈 CONCLUSION

   État du système: {assessment}

   Points forts:
   • {strength_1}
   • {strength_2}

   Points à améliorer:
   • {improvement_1}
   • {improvement_2}

   Recommandation immédiate: {primary recommendation}
   ```

**Règles importantes:**
- Vérifie TOUS les composants du système
- Marque clairement ce qui manque (❌) vs ce qui fonctionne (✅)
- Signale les rapports périmés (> 48h) avec ⚠️
- Priorise les recommandations par impact
- Fournis des actions concrètes et actionnables
- Ne modifie RIEN automatiquement

**Métriques de santé:**
- Rapport frais: < 24h = ✅ / 24-48h = ⚠️ / > 48h = ❌
- Script exécutable: chmod +x = ✅
- Fichier présent: exists = ✅
- Agent actif: rapport récent + statut ok = ✅

**Contexte:**
- Plugin: Integrity & Docs Guardian v2.0.0
- Agents: Anima, Neo, Nexus, ProdGuardian, Orchestrateur
- Application: ÉMERGENCE (FastAPI + Vite/React)
