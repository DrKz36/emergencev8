# Checklist Pré-Synchronisation

**Date**: {{DATE}}
**Agent**: {{AGENT_NAME}}

---

## ✅ Vérifications Obligatoires

### 1. État Git

- [ ] Working tree propre OU modifications intentionnelles documentées
- [ ] Branche correcte (vérifier `git branch --show-current`)
- [ ] Pas de conflits non résolus
- [ ] Commits avec messages descriptifs

```bash
git status
git log --oneline -5
```

### 2. Tests et Qualité

- [ ] Build réussi (`npm run build`)
- [ ] Tests unitaires passent (`pytest tests/`)
- [ ] Pas d'erreur de linting (`ruff check src/`)
- [ ] Type checking OK (`mypy src/`)

OU utiliser le hook de validation:

```bash
python .sync/scripts/validate-before-sync.py --level standard
```

### 3. Documentation

- [ ] `AGENT_SYNC.md` mis à jour avec l'état actuel
- [ ] `docs/passation.md` nouvelle entrée préparée
- [ ] Commentaires dans le code pour changements complexes
- [ ] README mis à jour si nécessaire

### 4. Fichiers Sensibles

- [ ] Pas de secrets dans le code (tokens, passwords, API keys)
- [ ] Fichiers `.env` non inclus dans le patch
- [ ] Pas de données de test sensibles
- [ ] Pas de logs contenant des données personnelles

### 5. Dépendances

- [ ] `package.json` / `requirements.txt` à jour si dépendances ajoutées
- [ ] Dépendances compatibles avec environnement cible
- [ ] Pas de dépendances temporaires ou de debug

---

## 📋 Préparation Export

### 1. Générer le Patch

```bash
# Pour GPT Codex Cloud
bash .sync/scripts/cloud-export.sh
# OU
python .sync/scripts/cloud-export.py
```

### 2. Vérifier le Contenu

- [ ] Patch généré: `.sync/patches/sync_cloud_{{TIMESTAMP}}.patch`
- [ ] Métadonnées générées: `.sync/patches/sync_cloud_{{TIMESTAMP}}.json`
- [ ] Instructions créées: `.sync/patches/INSTRUCTIONS_{{TIMESTAMP}}.txt`
- [ ] Log d'export créé: `.sync/logs/export_{{TIMESTAMP}}.log`

### 3. Vérifier la Taille

```bash
ls -lh .sync/patches/sync_cloud_{{TIMESTAMP}}.patch
```

- [ ] Taille raisonnable (< 10MB recommandé)
- [ ] Si > 10MB, vérifier qu'il n'y a pas de fichiers binaires non souhaités

### 4. Contrôle Qualité Final

```bash
# Voir le contenu du patch
cat .sync/patches/sync_cloud_{{TIMESTAMP}}.patch | head -100

# Voir les métadonnées
cat .sync/patches/sync_cloud_{{TIMESTAMP}}.json
```

- [ ] Patch contient uniquement les fichiers souhaités
- [ ] Pas de fichiers générés automatiquement (node_modules/, __pycache__/, etc.)
- [ ] Métadonnées correctes

---

## 📤 Transfert

### Fichiers à Transférer

1. `.sync/patches/sync_cloud_{{TIMESTAMP}}.patch`
2. `.sync/patches/sync_cloud_{{TIMESTAMP}}.json`

### Méthode de Transfert

- [ ] Copie manuelle vers environnement cible
- [ ] Upload via interface cloud
- [ ] Partage de fichiers sécurisé
- [ ] Autre: _______________

---

## 📝 Communication

### Message pour Agent Destinataire

Préparer un message incluant:

- [ ] Contexte du travail effectué
- [ ] Liste des modifications principales
- [ ] Points d'attention particuliers
- [ ] Tests à exécuter après import
- [ ] Prochaines étapes suggérées

Utiliser le template: `.sync/templates/agent-handoff.md`

---

## 🔍 Vérification Post-Export

- [ ] Enregistrement dans l'historique: `python .sync/scripts/sync-tracker.py list`
- [ ] Backup de l'état actuel créé
- [ ] Documentation de session complétée

---

## ⚠️ En Cas de Problème

### Annuler l'Export

Si vous détectez un problème après export:

1. Ne pas transférer les fichiers
2. Corriger le problème localement
3. Re-générer le patch avec le script d'export
4. Vérifier à nouveau cette checklist

### Restaurer État Précédent

```bash
# Si vous avez fait un commit par erreur
git reset --soft HEAD~1

# Si vous voulez annuler toutes les modifications
git checkout HEAD -- .
```

---

**Cette checklist doit être complétée AVANT chaque synchronisation**

Date de complétion: _______________
Validé par: _______________
