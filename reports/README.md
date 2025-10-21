# 📊 Guardian Reports - Documentation

**Statut** : Rapports locaux uniquement (NON versionnés dans Git)

---

## 🎯 Pourquoi les rapports ne sont PAS versionnés ?

**Problème initial** : Les hooks Git régénéraient les rapports à chaque commit, créant une boucle infinie de modifications (timestamps changeant constamment).

**Solution** : Les rapports sont **générés automatiquement localement** par les hooks, mais **ignorés par Git** via `.gitignore`.

### Avantages de cette approche

✅ **Rapports toujours frais localement** - Hooks les régénèrent automatiquement
✅ **Pas de pollution Git** - Pas de commits inutiles avec juste des timestamps
✅ **Pas de boucle infinie** - Les hooks ne créent plus de modifications à commiter
✅ **Workflow fluide** - Commit/push sans blocage
✅ **Codex GPT peut les lire** - Les fichiers existent localement

---

## 📁 Rapports Disponibles (Locaux)

Les rapports suivants sont **générés automatiquement** par les hooks Guardian :

### Rapports Principaux

| Fichier | Générateur | Description |
|---------|-----------|-------------|
| `unified_report.json` | Nexus (Coordinator) | Rapport unifié de tous les agents |
| `codex_summary.md` | Script generate_codex_summary.py | Résumé enrichi pour Codex GPT (narratif exploitable) |
| `prod_report.json` | ProdGuardian | État production Cloud Run + logs erreurs |
| `integrity_report.json` | Neo (IntegrityWatcher) | Intégrité backend/frontend |
| `docs_report.json` | Anima (DocKeeper) | Documentation + versioning |
| `auto_update_report.json` | AutoUpdate Service | Mises à jour auto doc |

### Quand sont-ils générés ?

**Post-Commit Hook** :
- Nexus → `unified_report.json`
- Codex Summary → `codex_summary.md`
- AutoUpdate (si activé) → `auto_update_report.json`

**Pre-Push Hook** :
- ProdGuardian → `prod_report.json` (vérif prod avant push)
- Codex Summary régénéré (rapports frais)

**Pre-Commit Hook** :
- Anima → `docs_report.json`
- Neo → `integrity_report.json`

---

## 🔧 Génération Manuelle

Si tu veux régénérer les rapports manuellement :

### Rapport Unifié (Nexus)
```bash
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
```

### Résumé Codex GPT
```bash
python scripts/generate_codex_summary.py
```

### Production (ProdGuardian)
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
```

### Intégrité Backend/Frontend (Neo)
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py
```

### Documentation (Anima)
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_docs.py
```

### Audit Complet (Tous les agents)
```bash
pwsh -File claude-plugins/integrity-docs-guardian/scripts/run_audit.ps1
```

---

## 🤖 Pour Codex GPT et Claude Code

**Comment accéder aux rapports ?**

Les rapports sont **locaux dans ce dossier `reports/`**. Tu peux les lire directement :

```markdown
Fichier recommandé pour LLM : reports/codex_summary.md
(Résumé narratif enrichi avec insights + code snippets + recommandations)
```

Rapports JSON bruts (détails) :
- [reports/prod_report.json](./prod_report.json)
- [reports/unified_report.json](./unified_report.json)
- [reports/integrity_report.json](./integrity_report.json)
- [reports/docs_report.json](./docs_report.json)

**Note** : Si les rapports n'existent pas encore, lance un commit/push ou génère-les manuellement (commandes ci-dessus).

---

## 🛡️ Setup Guardian

Pour installer/réinstaller les hooks Guardian :

```powershell
cd claude-plugins\integrity-docs-guardian\scripts
.\setup_guardian.ps1
```

**Documentation complète** : [docs/GUARDIAN_COMPLETE_GUIDE.md](../docs/GUARDIAN_COMPLETE_GUIDE.md)

---

## 📝 Notes Importantes

1. **Rapports locaux uniquement** - Pas versionnés dans Git (voir `.gitignore`)
2. **Générés automatiquement** - Par les hooks Git (post-commit, pre-push)
3. **Pas de boucle infinie** - Les hooks ne commitent PAS les rapports
4. **Codex GPT peut les lire** - Fichiers disponibles localement
5. **Production vérifiée avant push** - ProdGuardian peut bloquer si CRITICAL

---

**Dernière mise à jour** : 2025-10-21 (Claude Code - Stratégie rapports locaux)
