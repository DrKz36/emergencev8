# Configuration Claude Code — Emergence V8

## Permissions d'exécution automatique

Ce dossier contient la configuration locale pour Claude Code.

### Fichier `settings.local.json`

```json
{
  "permissions": {
    "allow": ["*"],
    ...
  }
}
```

**Le wildcard `"*"` en première position** dans la liste `"allow"` active l'**exécution automatique** de toutes les opérations sans demande d'autorisation à l'utilisateur.

### Pourquoi cette configuration ?

- **Workflow fluide** : Claude Code peut accomplir les tâches de bout en bout sans interruption
- **Gain de temps** : Plus besoin de valider chaque étape manuellement
- **Mode co-développeur** : Claude Code agit comme un développeur autonome qui complète les tâches assignées

### Commandes pré-approuvées spécifiques

Les commandes listées après le wildcard dans `"allow"` sont maintenues pour référence historique :
- Vérification des tâches planifiées Guardian
- Exécution des scripts email et rapports
- Scripts PowerShell de configuration

Ces commandes spécifiques sont déjà couvertes par le wildcard `"*"`, mais sont conservées pour documentation.

### Sécurité

Cette configuration accorde une **confiance totale** à Claude Code pour :
- Lire/écrire tous les fichiers du projet
- Exécuter des commandes bash/PowerShell
- Modifier la configuration git
- Installer des dépendances

**Important** : Cette configuration est appropriée pour un environnement de développement local contrôlé. Ne pas utiliser dans un contexte non sécurisé ou avec du code non vérifié.

### Modification de la configuration

Pour revenir en mode "demande d'autorisation", retirer le `"*"` de la liste `"allow"` :

```json
{
  "permissions": {
    "allow": [
      "Bash(commande spécifique 1)",
      "Bash(commande spécifique 2)"
    ],
    "deny": [],
    "ask": []
  }
}
```

---

**Date de configuration** : 2025-10-18
**Configuré par** : Claude Code (Sonnet 4.5)
**Validé par** : FG (Architecte)
