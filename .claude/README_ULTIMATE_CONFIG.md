# Claude Code - Configuration Ultimate

**Mode Full Auto avec 160+ permissions pré-remplies**

## Ce qui a été fait

Au lieu d'attendre que les permissions s'accumulent session après session, on a pré-rempli le fichier `settings.local.json` avec **TOUTES les permissions possibles** du projet.

## Contenu

### Fichiers

- **`settings.local.json`** : Config active avec 161 permissions
- **`settings.local.json.ULTIMATE`** : Template avec 142 permissions standards
- **`apply_ultimate_config.py`** : Script de merge intelligent
- **`settings.local.json.backup_*`** : Backups automatiques

### Permissions incluses (161 total)

#### Git (20 permissions)
- status, add, commit, push, pull, diff, log, branch, merge, stash

#### NPM & Build (6 permissions)
- install, build, dev, test, audit

#### Python & Tests (9 permissions)
- pytest (tous modes), ruff, mypy

#### PowerShell Scripts (6 permissions)
- Tous les scripts du projet (run-backend, deploy-canary, etc.)

#### Docker & GCloud (9 permissions)
- build, push, run, logs, services, secrets

#### Fichiers Read (18 permissions)
- Tous types : py, js, ts, json, md, yaml, ps1, env, etc.
- Tous dossiers : src, docs, scripts, tests, reports, claude-plugins

#### Fichiers Edit/Write (17 permissions)
- Édition tous fichiers projet
- Écriture reports et docs

#### Bash Utils (10 permissions)
- cat, ls, pwd, which, echo, version checks

#### Guardian Scripts (5 permissions)
- scan_docs, check_integrity, generate_report, check_prod_logs, archive_guardian

#### Divers (61 permissions restantes)
- attrib, vscode, sqlite3, curl, wget, tar, zip, grep, find, etc.

## Usage

### Appliquer la config ultimate

```powershell
# Dry-run pour voir ce qui serait fait
python .claude/apply_ultimate_config.py --dry-run

# Appliquer réellement (avec backup automatique)
python .claude/apply_ultimate_config.py

# Sans backup (non recommandé)
python .claude/apply_ultimate_config.py --no-backup
```

### Résultat

Après application :
- ✅ **161 permissions** pré-remplies
- ✅ **Mode full auto** dès la prochaine session
- ✅ **Plus besoin d'accepter** les permissions manuellement
- ✅ **Backup automatique** créé avant application

## Stratégie

### Avant (Accumulation Progressive)

1. Session 1 : Claude demande 5-10 permissions → Accepter
2. Session 2 : Claude demande 3-5 nouvelles → Accepter
3. Session 3 : Claude demande 1-2 nouvelles → Accepter
4. Session 4+ : Plus aucune demande

**Inconvénient** : 3-4 sessions pour arriver au mode full auto

### Après (Pré-remplissage)

1. Exécuter `apply_ultimate_config.py` **une seule fois**
2. **Toutes les permissions** déjà présentes
3. **Session 1** : Déjà en mode full auto ! ✅

**Avantage** : Mode full auto **immédiat**

## Maintenance

### Ajouter de nouvelles permissions

Si de nouvelles commandes sont ajoutées au projet :

1. Éditer `settings.local.json.ULTIMATE`
2. Ajouter les nouvelles permissions dans le tableau `allow`
3. Relancer `python .claude/apply_ultimate_config.py`

Le script merge intelligemment (garde les anciennes + ajoute les nouvelles).

### Restaurer depuis backup

```powershell
# Lister les backups
ls .claude\settings.local.json.backup_*

# Restaurer un backup spécifique
cp .claude\settings.local.json.backup_20251018_102359 .claude\settings.local.json
```

## Flags expérimentaux

**Note** : Les flags expérimentaux dans le fichier ULTIMATE (`dangerouslySkipAllPermissions`, etc.) ont été **retirés** car ils ne sont **pas supportés** par Claude Code.

Le seul moyen fiable de skip les permissions est le flag CLI `--dangerously-skip-permissions` (utilisé par la commande `ec`).

## Documentation complémentaire

- [CLAUDE_AUTO_MODE_SETUP.md](../CLAUDE_AUTO_MODE_SETUP.md) : Guide complet mode automatique
- [CLAUDE.md](../CLAUDE.md) : Instructions système projet Emergence V8

## Historique

- **2025-10-18** : Création config ultimate (161 permissions)
- **2025-10-18** : Script apply_ultimate_config.py
- **2025-10-18** : Template settings.local.json.ULTIMATE

---

**Généré automatiquement par Claude Code**
