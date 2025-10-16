# Vérification Systématique des Fichiers de Coordination

## 🔍 Règle Obligatoire pour TOUS les Agents

Avant de commencer toute tâche de développement, analyse, ou modification, **tu DOIS lire les fichiers de coordination dans l'ordre suivant** :

### 📋 Ordre de Lecture Obligatoire

```
1. AGENT_SYNC.md
   → État actuel du dépôt, progression roadmap, déploiement production

2. AGENTS.md
   → Consignes générales pour tous les agents

3. CODEV_PROTOCOL.md
   → Protocole de collaboration multi-agents

4. docs/passation.md (3 dernières entrées minimum)
   → Historique des sessions de travail récentes

5. git status + git log --oneline -10
   → État Git actuel
```

### 🎯 Pourquoi C'est Critical

**Sans cette lecture systématique, tu risques :**
- ❌ Dupliquer du travail déjà fait par Codex GPT
- ❌ Créer des conflits avec les changements en cours
- ❌ Ignorer des décisions architecturales récentes
- ❌ Casser des fonctionnalités récemment ajoutées
- ❌ Ne pas respecter le contexte de production actuel

**Avec cette lecture systématique, tu garantis :**
- ✅ Coordination optimale avec Codex GPT et autres agents
- ✅ Respect du protocole multi-agents
- ✅ Continuité logique des sessions de travail
- ✅ Connaissance de l'état production
- ✅ Pas de régression ou duplication

### 🚫 Exceptions (Très Rares)

Tu peux skip cette lecture UNIQUEMENT si :
- Question ponctuelle de l'utilisateur sans modification de code
- Simple lecture/analyse sans changement
- Réponse immédiate sur un concept théorique

**Dans TOUS les autres cas, lis les fichiers de coordination d'abord !**

### 🔄 Intégration avec Sub-Agents

Les sub-agents (Anima, Neo, Nexus, ProdGuardian, `/sync_all`, `/audit_agents`) incluent déjà cette directive dans leurs prompts. Si tu lances un de ces agents, il lira automatiquement les fichiers de coordination.

### ✅ Validation

Après avoir lu les fichiers, tu devrais être capable de répondre :
1. Quelle est la dernière phase roadmap complétée ?
2. Quel est le statut de production actuel ?
3. Quels sont les 3 derniers changements documentés ?
4. Y a-t-il des blocages ou problèmes en cours ?
5. Quel est le commit actuel et la branche active ?

Si tu ne peux pas répondre à ces 5 questions, **relis les fichiers de coordination**.

---

**Cette règle est le cœur de la coordination multi-agents du projet ÉMERGENCE.** 🎯
