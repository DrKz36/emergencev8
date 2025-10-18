# Session Suivante - P1 Audit Cleanup & Consolidation

**Contexte** : Suite de l'audit complet système réalisé le 2025-10-17 par Claude Code (Sonnet 4.5)

**Commit précédent** : `043b9de` - "docs: update backend docs (chat, memory) + cleanup obsolete files (P0)"

**État actuel** : Actions P0 complétées ✅ → Passer aux actions P1

---

## 📋 ACTIONS P1 À RÉALISER (3 tâches max)

### Tâche 1 : Mettre à jour documentation backend/architecture restante

**Fichiers à modifier** :
1. `docs/backend/dashboard.md`
2. `docs/architecture/30-Contracts.md`

**Modifications nécessaires** :

#### Pour `docs/backend/dashboard.md` :
- Vérifier section admin_router.py et admin_service.py
- Ajouter modifications récentes détectées par Anima (voir rapport)
- Mettre à jour version et date de dernière mise à jour
- Documenter endpoints modifiés si applicable

#### Pour `docs/architecture/30-Contracts.md` :
- Vérifier contrats API pour dashboard et memory endpoints
- Ajouter paramètre `agent_id` dans contrats memory si absent
- Mettre à jour avec modifications routers récentes
- Synchroniser avec openapi.json si nécessaire

**Durée estimée** : 20-30 minutes

**Références** :
- Rapport Anima : `claude-plugins/integrity-docs-guardian/reports/docs_report.json`
- Fichiers backend modifiés :
  - `src/backend/features/dashboard/admin_router.py`
  - `src/backend/features/dashboard/admin_service.py`
  - `src/backend/features/memory/router.py`

---

### Tâche 2 : Consolider roadmaps et supprimer doublons

**Actions** :

1. **Supprimer fichier obsolète** :
   ```bash
   git rm docs/ROADMAP_SETUP_2025-10-15.md
   ```
   Raison : Setup spécifique à une date, devenu obsolète

2. **Analyser et fusionner/supprimer** :
   - Lire `docs/ROADMAP_README.md`
   - Si contenu utile → fusionner dans `ROADMAP_OFFICIELLE.md`
   - Si redondant → supprimer avec `git rm docs/ROADMAP_README.md`

3. **Ajouter redirections dans README principal** :
   - Vérifier que `README.md` pointe vers `ROADMAP_OFFICIELLE.md`
   - Ajouter note claire : "Document unique officiel de roadmap"

**Durée estimée** : 15-20 minutes

**Résultat attendu** :
- Structure roadmap clarifiée
- 2 fichiers roadmap actifs maximum : `ROADMAP_OFFICIELLE.md` + `ROADMAP_PROGRESS.md`
- Tous les anciens dans `docs/archive/`

---

### Tâche 3 : Archiver rapports obsolètes (avant 2025-10-17)

**Actions** :

1. **Créer répertoire d'archive** :
   ```bash
   mkdir -p docs/archive/REPORTS_OLD_2025-10
   ```

2. **Archiver rapports racine** :
   ```bash
   git mv AUDIT_FINAL_REPORT.md docs/archive/REPORTS_OLD_2025-10/
   git mv AUTH_FIXES_REPORT.md docs/archive/REPORTS_OLD_2025-10/
   git mv COORDINATION_SYSTEM_REPORT.md docs/archive/REPORTS_OLD_2025-10/
   git mv PLAN_DEBUG_COMPLET.md docs/archive/REPORTS_OLD_2025-10/
   git mv beta_report.html docs/archive/REPORTS_OLD_2025-10/
   ```

3. **Archiver rapports dans reports/** :
   ```bash
   # Lister d'abord pour confirmer
   ls -la reports/*.md | grep -E "2025-10-(0[1-9]|1[0-6])"

   # Archiver tous avant 2025-10-17
   git mv reports/ameliorations_memoire_15oct2025.md docs/archive/REPORTS_OLD_2025-10/
   git mv reports/phase1_implementation_summary.md docs/archive/REPORTS_OLD_2025-10/
   git mv reports/session_15oct2025_summary.md docs/archive/REPORTS_OLD_2025-10/
   # ... (continuer pour tous les rapports listés dans l'audit)
   ```

4. **Conserver rapports récents** :
   - `reports/memory_hallucination_fix_2025-10-17.md` ✅ Garder
   - `claude-plugins/integrity-docs-guardian/reports/ai_model_cost_audit_20251017.*` ✅ Garder

**Durée estimée** : 20-30 minutes

**Liste complète des rapports à archiver** :
Voir section "Rapports obsolètes à SUPPRIMER" dans le rapport d'audit précédent (commit 043b9de)

---

## ✅ VALIDATION AVANT COMMIT

**Checklist** :
- [ ] Documentation dashboard.md et Contracts.md mises à jour
- [ ] Roadmaps consolidées (max 2 fichiers actifs)
- [ ] Rapports obsolètes archivés dans `docs/archive/REPORTS_OLD_2025-10/`
- [ ] Aucun fichier important supprimé par erreur
- [ ] `git status` vérifié

**Tests recommandés** :
```bash
# Vérifier que la documentation est cohérente
grep -r "ROADMAP" README.md docs/
grep -r "V3.9\|V1.2" docs/backend/

# Vérifier structure archive
ls -la docs/archive/REPORTS_OLD_2025-10/

# Build frontend pour vérifier intégrité
npm run build
```

---

## 📝 COMMIT FINAL

```bash
git add docs/backend/dashboard.md docs/architecture/30-Contracts.md
git add docs/ROADMAP_SETUP_2025-10-15.md docs/ROADMAP_README.md
git add docs/archive/REPORTS_OLD_2025-10/
git add AUDIT_FINAL_REPORT.md AUTH_FIXES_REPORT.md COORDINATION_SYSTEM_REPORT.md PLAN_DEBUG_COMPLET.md beta_report.html
git add reports/

git commit -m "$(cat <<'EOF'
docs: complete P1 audit cleanup - consolidate docs, roadmaps, and archive old reports

Documentation updates:
- docs/backend/dashboard.md: Update with recent admin service changes
- docs/architecture/30-Contracts.md: Add agent_id parameter to memory endpoints

Roadmap consolidation:
- Remove obsolete ROADMAP_SETUP_2025-10-15.md
- Consolidate/remove redundant ROADMAP_README.md
- Keep only ROADMAP_OFFICIELLE.md + ROADMAP_PROGRESS.md as active

Archive old reports (38 files):
- Move all reports dated before 2025-10-17 to docs/archive/REPORTS_OLD_2025-10/
- Keep recent reports: memory_hallucination_fix, ai_model_cost_audit
- Archived: AUDIT_FINAL_REPORT, AUTH_FIXES_REPORT, COORDINATION_SYSTEM_REPORT, etc.

This completes P1 priority actions from audit report (043b9de).

Related: 043b9de (P0 cleanup), cb42460 (agent memory isolation)

🤖 Generated with Claude Code (https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 🔍 RAPPELS IMPORTANTS

**Lecture obligatoire avant session** :
1. `AGENT_SYNC.md` - État sync inter-agents
2. `AGENTS.md` - Consignes générales
3. `CODEV_PROTOCOL.md` - Protocole multi-agents
4. `docs/passation.md` - 3 dernières entrées minimum
5. `git status` + `git log --oneline -10`

**Guardians actifs** :
- Pre-commit hook exécutera Anima + Neo automatiquement
- Post-commit hook générera rapport Nexus
- Warnings attendus : Documentation gaps seront réduits après ces mises à jour

**Rapport d'audit complet** :
Voir commit `043b9de` pour contexte complet et liste détaillée des fichiers obsolètes.

---

## 🎯 RÉSULTAT ATTENDU

Après cette session :
- ✅ Documentation backend/architecture complète et synchronisée
- ✅ Roadmaps consolidées (structure claire)
- ✅ Rapports obsolètes archivés (~38 fichiers)
- ✅ Réduction warnings Anima (de 14 → ~6-8)
- ✅ Commit P1 créé et hooks Guardian exécutés

**Prochaine session** : P2 (organisation guides dans `docs/guides/` + mise à jour roadmap versions)

---

## 📚 RESSOURCES

**Rapports Guardian** :
- `claude-plugins/integrity-docs-guardian/reports/docs_report.json`
- `claude-plugins/integrity-docs-guardian/reports/integrity_report.json`
- `claude-plugins/integrity-docs-guardian/reports/unified_report.json`

**Documentation** :
- `claude-plugins/integrity-docs-guardian/AUTOMATION_GUIDE.md` - Guide hooks
- `GUARDIAN_SETUP_COMPLETE.md` - État système Guardian
- `docs/VERSIONING_GUIDE.md` - Guide versioning

**Contexte commit précédent** :
```bash
git show 043b9de --stat
git log --oneline -5
```
