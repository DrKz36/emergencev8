# 📖 GUIDE D'UTILISATION - ROADMAP EMERGENCE V8

> **Document d'instruction** - Comment utiliser et maintenir la roadmap officielle

---

## 🎯 FICHIERS DE LA ROADMAP

### 1. [ROADMAP_OFFICIELLE.md](../ROADMAP_OFFICIELLE.md)
**Rôle** : Source de vérité unique pour toutes les fonctionnalités à implémenter

**Contenu** :
- Détail de chaque fonctionnalité (description, tâches, acceptance criteria)
- Priorisation par phases (P0 → P1 → P2 → P3)
- Estimations de temps
- Références vers le code existant
- Critères de succès

**Quand le consulter** :
- ✅ Avant de démarrer une nouvelle fonctionnalité
- ✅ Pour comprendre le scope complet d'une feature
- ✅ Pour valider les acceptance criteria
- ✅ Pour planifier un sprint

**Quand le modifier** :
- ⚠️ Ajout d'une nouvelle fonctionnalité
- ⚠️ Modification d'une priorité
- ⚠️ Ajustement des estimations (avec justification)
- ⚠️ Mise à jour des références techniques

---

### 2. [ROADMAP_PROGRESS.md](../ROADMAP_PROGRESS.md)
**Rôle** : Suivi quotidien de la progression

**Contenu** :
- Statuts en temps réel (⏳ → 🟡 → ✅)
- Checklists détaillées par tâche
- Notes de progression (blocages, décisions, astuces)
- Journal de bord quotidien
- Statistiques (temps passé, vélocité)

**Quand le consulter** :
- ✅ Tous les jours (début et fin de journée)
- ✅ Pour savoir où on en est
- ✅ Pour voir ce qui reste à faire
- ✅ Pour identifier les blocages

**Quand le modifier** :
- 📝 **TOUS LES JOURS** (fin de journée) :
  - Cocher `[x]` les tâches terminées
  - Mettre à jour les statuts
  - Ajouter notes dans "Notes de progression"
  - Remplir "Journal de Bord"
  - Mettre à jour "Prochaines Actions"

---

## 🔄 WORKFLOW QUOTIDIEN

### 🌅 Début de Journée (5 minutes)
1. Ouvrir [ROADMAP_PROGRESS.md](../ROADMAP_PROGRESS.md)
2. Consulter section "Prochaines Actions"
3. Identifier la tâche en cours (statut 🟡)
4. Si nouvelle tâche : changer statut de ⏳ à 🟡
5. Noter heure de début dans "Notes de progression"

### 🌆 Fin de Journée (10 minutes)
1. Cocher `[x]` toutes les tâches terminées aujourd'hui
2. Mettre à jour statuts :
   - Tâche complète : 🟡 → ✅
   - Tâche en cours : ⏳ → 🟡
3. Remplir "Notes de progression" :
   ```
   [2025-10-15] [18:30] - Archivage UI : onglet "Archives" implémenté et testé.
   Problème rencontré : CSS conflit avec sidebar. Résolu avec class specificity.
   ```
4. Ajouter entrée "Journal de Bord" :
   ```
   ### 2025-10-15 - Jour 1 Phase P0
   - ✅ Archivage UI : onglet Archives créé
   - 🟡 Archivage UI : filtre Actifs/Archivés en cours
   - 📝 Note : Prévoir refacto CSS sidebar avant P1
   ```
5. Mettre à jour "Prochaines Actions" pour demain

---

## 📋 PROCÉDURES SPÉCIFIQUES

### Démarrer une Nouvelle Fonctionnalité

#### Étape 1 : Lire le détail dans ROADMAP_OFFICIELLE.md
```bash
# Exemple : Archivage UI
1. Ouvrir ROADMAP_OFFICIELLE.md
2. Trouver "1. Archivage des Conversations (UI)"
3. Lire :
   - Statut actuel
   - Fichiers concernés
   - Liste des tâches
   - Acceptance Criteria
```

#### Étape 2 : Initialiser dans ROADMAP_PROGRESS.md
```markdown
### 1. Archivage des Conversations (UI)
**Statut** : 🟡 EN COURS    # Changer de ⏳ à 🟡
**Début** : 2025-10-15      # Ajouter date du jour
```

#### Étape 3 : Travailler sur la fonctionnalité
- Cocher `[x]` au fur et à mesure dans la checklist
- Ajouter notes importantes dans "Notes de progression"

#### Étape 4 : Finaliser
```markdown
**Statut** : ✅ TERMINÉ     # Changer de 🟡 à ✅
**Fin** : 2025-10-16        # Ajouter date de fin
**Temps réel** : 1 jour     # Calculer temps passé
```

---

### Gérer un Blocage

#### Identifier le blocage
```markdown
### Notes de progression
[2025-10-15] [14:00] - BLOCAGE : API backend /api/threads/{id}/archive
retourne 500. Nécessite investigation backend.
```

#### Documenter dans "Blocages Identifiés"
```markdown
### Blocages Identifiés
1. **Archivage API 500** (2025-10-15)
   - Contexte : Appel PUT /api/threads/{id}/archive échoue
   - Erreur : "SQLAlchemyError: no such column: archived_at"
   - Impact : Bloque feature archivage UI
   - Résolution : Nécessite migration BDD pour ajouter colonne
   - Responsable : Backend team
   - Statut : ⏳ À résoudre
```

#### Passer à autre chose
```markdown
### Prochaines Actions
1. ⏳ En attente résolution blocage Archivage → passer à Graphe (P0.2)
2. 🟡 Démarrer intégration Graphe de Connaissances
```

---

### Modifier une Priorité

#### Cas 1 : Urgence business
```markdown
# Dans ROADMAP_OFFICIELLE.md

## 🎯 PHASE P0 - QUICK WINS (3-5 jours)
> ⚠️ MODIFICATION PRIORITÉ (2025-10-15) : Export CSV/PDF monté en P0
> suite demande client. Archivage descend en P1.
```

#### Cas 2 : Dépendance technique
```markdown
# Dans ROADMAP_PROGRESS.md

### Notes de progression
[2025-10-15] [16:00] - DÉCISION : Thème clair/sombre déplacé APRÈS
gestion concepts car nécessite refacto CSS globale. Priorité P1 ajustée.
```

---

## 📊 MÉTRIQUES À SUIVRE

### Métriques Obligatoires (à jour quotidiennement)
1. **Progression Globale** : `X/23 (Y%)`
2. **Statuts** : Nombre ✅ / 🟡 / ⏳
3. **Temps Réel vs Estimé** : Par fonctionnalité
4. **Vélocité** : Fonctionnalités / jour

### Métriques Optionnelles (à jour hebdomadairement)
1. **Burn-down Chart** : Fonctionnalités restantes par semaine
2. **Taux de blocage** : Nombre blocages / total tâches
3. **Écart d'estimation** : (Temps réel - Temps estimé) / Temps estimé

---

## ⚠️ RÈGLES IMPORTANTES

### ✅ À FAIRE
1. **Consulter ROADMAP_OFFICIELLE.md avant toute nouvelle feature**
2. **Mettre à jour ROADMAP_PROGRESS.md tous les jours**
3. **Documenter TOUS les blocages et décisions**
4. **Respecter l'ordre des phases (P0 → P1 → P2 → P3)**
5. **Cocher `[x]` uniquement quand tâche 100% terminée + testée**

### ❌ À NE PAS FAIRE
1. **Modifier ROADMAP_OFFICIELLE.md sans justification**
2. **Sauter des tâches dans la checklist**
3. **Oublier de documenter une décision importante**
4. **Démarrer P1 sans avoir fini P0**
5. **Marquer ✅ sans avoir vérifié les Acceptance Criteria**

---

## 🎯 QUAND DEMANDER "Réfère-toi à la roadmap"

### Contextes où utiliser cette phrase
1. **Démarrage de journée** : "Réfère-toi à la roadmap pour voir ce qu'on fait aujourd'hui"
2. **Fin de fonctionnalité** : "Réfère-toi à la roadmap pour passer à la suivante"
3. **Priorisation** : "Réfère-toi à la roadmap pour confirmer les priorités"
4. **Estimation** : "Réfère-toi à la roadmap pour voir le temps estimé"
5. **Blocage** : "Réfère-toi à la roadmap pour documenter le blocage"

### Ce que Claude fera automatiquement
1. ✅ Ouvrir [ROADMAP_PROGRESS.md](../ROADMAP_PROGRESS.md)
2. ✅ Identifier la tâche en cours (statut 🟡)
3. ✅ Consulter la checklist de la tâche
4. ✅ Proposer la prochaine sous-tâche à faire
5. ✅ Vérifier si des blocages sont documentés
6. ✅ Rappeler les Acceptance Criteria à valider

---

## 📚 RÉFÉRENCES

### Documents Liés
- [ROADMAP_OFFICIELLE.md](../ROADMAP_OFFICIELLE.md) - Roadmap complète
- [ROADMAP_PROGRESS.md](../ROADMAP_PROGRESS.md) - Suivi de progression
- [AUDIT_FEATURES_2025-10-15.md](AUDIT_FEATURES_2025-10-15.md) - Audit initial

### Templates

#### Template Note de Progression
```markdown
[YYYY-MM-DD] [HH:MM] - [Contexte] : [Description détaillée]
[Problème rencontré / Décision prise / Astuce découverte]
[Action prise / Résolution / Impact]
```

#### Template Journal de Bord
```markdown
### YYYY-MM-DD - [Titre de la journée]
- ✅ [Feature] : [Sous-tâche complétée]
- 🟡 [Feature] : [Sous-tâche en cours]
- ⏳ [Feature] : [Sous-tâche à faire demain]
- 📝 Note : [Note importante / Décision / Blocage]
```

#### Template Blocage
```markdown
1. **[Titre du blocage]** (YYYY-MM-DD)
   - Contexte : [Où et quand]
   - Erreur : [Message d'erreur exact]
   - Impact : [Quelle feature est bloquée]
   - Résolution : [Prochaines étapes]
   - Responsable : [Qui s'en occupe]
   - Statut : [⏳ / 🟡 / ✅]
```

---

## 🔧 MAINTENANCE DE LA ROADMAP

### Revue Hebdomadaire (Lundi matin)
1. Vérifier cohérence ROADMAP_OFFICIELLE.md vs ROADMAP_PROGRESS.md
2. Calculer vélocité de la semaine précédente
3. Ajuster estimations si écarts significatifs (>50%)
4. Identifier tendances (blocages récurrents, types de tâches lentes)
5. Prioriser les tâches de la semaine

### Revue de Phase (Fin P0, P1, P2, P3)
1. Calculer métriques globales de la phase
2. Documenter lessons learned
3. Ajuster méthode si nécessaire
4. Archiver notes de progression de la phase
5. Préparer kickoff phase suivante

---

## 📞 CONTACTS & SUPPORT

**Product Owner** : gonzalefernando@gmail.com
**Tech Lead** : [À définir]
**Documentation** : docs/ROADMAP_README.md (ce fichier)

---

**Document créé le** : 2025-10-15
**Dernière révision** : 2025-10-15
**Version** : 1.0
