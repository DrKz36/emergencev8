# Passation Agent: {{FROM_AGENT}} → {{TO_AGENT}}

**Date**: {{DATE}}
**Timestamp**: {{TIMESTAMP}}
**Patch**: {{PATCH_NAME}}

---

## 📦 Contenu de la Passation

### Fichiers à Transférer

1. **Patch principal**: `.sync/patches/{{PATCH_NAME}}`
2. **Métadonnées**: `.sync/patches/{{METADATA_NAME}}`
3. **Instructions**: `.sync/patches/INSTRUCTIONS_{{TIMESTAMP}}.txt`

### Commande de Synchronisation

```bash
# Pour {{TO_AGENT}}
{{SYNC_COMMAND}}
```

---

## 🎯 Contexte du Travail

### Ce qui a été fait

{{WORK_SUMMARY}}

### État actuel du code

- **Branche**: {{BRANCH_NAME}}
- **Dernier commit**: {{LAST_COMMIT}}
- **Fichiers modifiés**: {{FILES_COUNT}}
- **Status**: {{STATUS}}

---

## 🚧 Travail en Cours

### Tâches Complétées

{{COMPLETED_TASKS}}

### Tâches en Cours

{{IN_PROGRESS_TASKS}}

### Tâches Restantes

{{PENDING_TASKS}}

---

## ⚠️ Points d'Attention

### Problèmes Connus

{{KNOWN_ISSUES}}

### Dépendances

{{DEPENDENCIES}}

### Conflits Potentiels

{{POTENTIAL_CONFLICTS}}

---

## 📚 Documentation Mise à Jour

- [ ] `AGENT_SYNC.md` mis à jour
- [ ] `docs/passation.md` nouvelle entrée ajoutée
- [ ] Documentation technique mise à jour
- [ ] Tests documentés

---

## 🔧 Configuration Requise

### Environnement

{{ENVIRONMENT_REQUIREMENTS}}

### Outils Nécessaires

{{REQUIRED_TOOLS}}

### Variables d'Environnement

{{ENV_VARIABLES}}

---

## 💡 Recommandations pour {{TO_AGENT}}

{{RECOMMENDATIONS}}

---

## 📞 Contact

En cas de problème avec ce patch:
- Consulter le log: `.sync/logs/export_{{TIMESTAMP}}.log`
- Vérifier les métadonnées: `.sync/patches/{{METADATA_NAME}}`
- Consulter l'historique: `python .sync/scripts/sync-tracker.py find {{PATCH_NAME}}`

---

**Passation générée automatiquement le {{DATE}}**
