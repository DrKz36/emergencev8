# Prompt de Continuité - Implémentation Mémoire Temporelle

## 🎯 Contexte pour la Prochaine Instance

Bonjour ! Tu reprends le développement du système de mémoire d'Émergence après l'implémentation du contexte temporel enrichi.

---

## ✅ Ce qui a été fait (Instance précédente - 2025-10-15)

### 1. Fix du Memory Gardener

**Problème** : Erreur lors de la consolidation mémoire
**Message d'erreur** : `user_id est obligatoire pour accéder aux threads`

**Solution implémentée** :
- Fichier : [gardener.py:669-671](../../src/backend/features/memory/gardener.py#L669-L671)
- Changement : Utilisation de `get_thread_any()` au lieu de `get_thread()`
- Statut : ✅ Corrigé et testé (backend démarre sans erreur)

### 2. Détection Questions Temporelles + Enrichissement Contexte

**Problème** : Anima ne pouvait pas répondre aux questions temporelles
**Exemple** :
- User : "Quels sujets avons-nous abordés cette semaine ?" → ✅ Réponse OK
- User : "Quel jour et à quelle heure avons-nous abordé ces sujets ?" → ❌ Réponse vague

**Solution implémentée** :
- Fichier : [service.py](../../src/backend/features/chat/service.py)
- Ajouts :
  1. Regex `_TEMPORAL_QUERY_RE` (lignes 1114-1118) pour détecter questions temporelles
  2. Fonction `_is_temporal_query()` (lignes 1123-1128) pour validation
  3. Fonction `_build_temporal_history_context()` (lignes 1130-1202) pour enrichissement
  4. Intégration dans flux RAG (lignes 1697-1709) pour injection automatique

**Fonctionnement** :
- Détecte mots-clés : "quand", "quel jour", "quelle heure", "à quelle heure", "quelle date"
- Récupère les 20 derniers messages du thread avec timestamps
- Formate : `**[15 oct à 3h08] Toi :** Aperçu du message...`
- Injecte dans contexte RAG sous section "🔗 Connexions avec discussions passées"

**Statut** : ✅ Implémenté mais NON TESTÉ en production

---

## 🧪 Ce qu'il faut faire MAINTENANT (Priorité 1)

### Phase de Tests et Corrections

**Objectif** : Valider que l'implémentation fonctionne correctement et corriger les bugs détectés.

#### Test 1 : Question Temporelle Simple

**Action** :
1. Ouvrir une conversation avec Anima
2. Poser une question simple : "Quand avons-nous parlé de [sujet récent] ?"

**Résultats attendus** :
- ✅ Log backend : `[TemporalQuery] Contexte historique enrichi pour question temporelle`
- ✅ Réponse Anima : Inclut date et heure précises ("le 15 octobre à 3h08")

**En cas d'échec** :
- Vérifier les logs pour identifier l'erreur
- Vérifier que `_is_temporal_query()` détecte bien la question
- Vérifier que `_build_temporal_history_context()` retourne du contenu

#### Test 2 : Question Multi-Sujets avec Suivi Temporel

**Action** :
1. Conversation : "Quels sujets avons-nous abordés cette semaine ?"
2. Suivi : "Quel jour et à quelle heure avons-nous abordé ces sujets ?"

**Résultats attendus** :
- ✅ Première réponse : Liste des sujets (comportement existant)
- ✅ Deuxième réponse : Dates et heures précises pour chaque sujet

**En cas d'échec** :
- Vérifier que le contexte référence bien les sujets de la réponse précédente
- Vérifier format des timestamps dans les messages

#### Test 3 : Consolidation Mémoire (Memory Gardener)

**Action** :
1. Déclencher consolidation : `POST /api/memory/tend-garden`
2. Vérifier logs

**Résultats attendus** :
- ✅ Pas d'erreur "user_id est obligatoire"
- ✅ Consolidation réussie
- ✅ Log : `[MemoryGardener] Consolidation réussie pour thread XXX`

**En cas d'échec** :
- Vérifier que `get_thread_any()` reçoit bien le `user_id`
- Vérifier logs pour identifier quelle requête échoue

#### Test 4 : Formats Temporels Variés

**Action** :
Tester différentes formulations :
- "À quelle heure on a parlé de X ?"
- "Quelle date pour cette discussion ?"
- "When did we discuss Y?" (anglais)

**Résultats attendus** :
- ✅ Toutes les questions déclenchent l'enrichissement temporel
- ✅ Réponses cohérentes avec timestamps

**En cas d'échec** :
- Ajuster regex `_TEMPORAL_QUERY_RE` pour couvrir plus de patterns
- Vérifier support multilingue

---

## 🔧 Corrections Potentielles Identifiées

### 1. Performance avec Threads Longs

**Problème potentiel** : Récupération de 20 messages peut être lente pour threads très longs

**Solution si problème détecté** :
- Ajouter index sur `created_at` dans table `messages`
- Ajuster limite (20 → 10 si nécessaire)
- Ajouter cache pour contexte temporel

### 2. Faux Positifs/Négatifs de Détection

**Problème potentiel** : Regex peut manquer certaines formulations ou détecter à tort

**Solution si problème détecté** :
- Étendre regex avec nouveaux patterns détectés
- Ajouter logs DEBUG pour voir quelles questions sont détectées
- Créer liste de test cases pour validation

### 3. Format des Timestamps

**Problème potentiel** : Format "15 oct à 3h08" peut être ambigu (année manquante, 24h vs 12h)

**Solution si problème détecté** :
- Ajouter année si conversation ancienne : "15 oct 2024 à 3h08"
- Clarifier 24h : "15 oct à 03h08" (zéro devant)
- Supporter format ISO si demandé explicitement

### 4. Contexte Trop Verbeux

**Problème potentiel** : 20 messages × 80 caractères = ~1600 caractères de contexte

**Solution si problème détecté** :
- Réduire limite à 10 messages les plus récents
- Réduire aperçu à 50 caractères au lieu de 80
- Grouper messages par jour pour résumé

---

## 📊 Métriques à Surveiller

### Logs Backend

**Positifs** :
```
[TemporalQuery] Contexte historique enrichi pour question temporelle
[ConceptRecall] 3 récurrences détectées : ['CI/CD', 'Docker', 'Kubernetes']
[MemoryGardener] Consolidation réussie pour thread XXX
```

**Erreurs** :
```
[TemporalQuery] Enrichissement historique échoué : <erreur>
[MemoryGardener] Erreur consolidation thread XXX: user_id est obligatoire
ERROR [backend.features.chat.service] <traceback>
```

### Comportement Utilisateur

**Positifs** :
- Réponses Anima incluent dates/heures précises
- Pas de "Je n'ai pas de détails précis sur les dates"
- Cohérence temporelle dans les réponses

**Négatifs** :
- Réponses toujours vagues sur temporalité
- Erreurs 500 lors de questions temporelles
- Contexte historique non injecté (visible dans logs)

---

## 🚀 Améliorations Futures (Après Tests)

### Phase 2 : Optimisations

1. **Cache Contexte Temporel** :
   - Éviter recalcul si thread pas modifié
   - Invalider cache à chaque nouveau message
   - Réduire latence de 50-100ms

2. **Groupement Thématique** :
   - Grouper messages par sujet plutôt que chronologique
   - Utiliser embeddings pour détecter changements de sujet
   - Format : "Pipeline CI/CD (5 oct 14h32, 8 oct 9h15) - 3 échanges"

3. **Résumé Intelligent** :
   - Si > 20 messages, résumer les plus anciens
   - Garder 5-10 plus récents en détail
   - Éviter surcharge du prompt

### Phase 3 : Métriques Prometheus

1. **Compteur Questions Temporelles** :
   - `memory_temporal_queries_total{detected=true|false}`
   - Suivre taux de détection

2. **Histogram Temps Récupération** :
   - `memory_temporal_context_duration_seconds`
   - Détecter ralentissements

3. **Gauge Taille Contexte** :
   - `memory_temporal_context_size_bytes`
   - Surveiller verbosité

---

## 📚 Fichiers Clés à Consulter

### Code Modifié

1. **[service.py](../../src/backend/features/chat/service.py)** :
   - Lignes 1114-1128 : Détection questions temporelles
   - Lignes 1130-1202 : Construction contexte historique
   - Lignes 1697-1709 : Intégration flux RAG

2. **[gardener.py](../../src/backend/features/memory/gardener.py)** :
   - Lignes 669-671 : Fix user_id avec get_thread_any()

### Documentation

1. **[MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md](./MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md)** :
   - Documentation complète de l'implémentation
   - Architecture, flux, tests, références

2. **[CHANGELOG.md](../../CHANGELOG.md)** :
   - Entrées du 2025-10-15 avec détails des corrections

3. **[anima_system_v2.md](../../prompts/anima_system_v2.md)** :
   - Section "Mémoire des Conversations (Phase 1)"
   - Instructions pour utilisation des timestamps

### Logs Backend

Surveiller dans terminal backend :
```bash
grep -E "\[TemporalQuery\]|\[MemoryGardener\]|\[ConceptRecall\]" logs.txt
```

---

## 🎬 Par où Commencer ?

### Checklist de Démarrage

1. **[ ] Vérifier backend démarre sans erreur** :
   ```bash
   cd /c/dev/emergenceV8
   pwsh -File scripts/run-backend.ps1
   # Chercher : "✅ Lifespan: Backend prêt"
   ```

2. **[ ] Ouvrir conversation avec Anima** :
   - Naviguer vers interface frontend
   - Créer nouveau thread ou reprendre existant

3. **[ ] Test Question Temporelle Simple** :
   - Écrire : "Quand avons-nous parlé de [sujet] ?"
   - Observer logs backend
   - Vérifier réponse Anima

4. **[ ] Analyser résultats** :
   - ✅ Si succès → Passer aux tests 2-4
   - ❌ Si échec → Debugging (voir section "En cas d'échec")

5. **[ ] Documenter findings** :
   - Créer fichier `MEMORY_TEMPORAL_TESTS_RESULTS.md`
   - Noter succès/échecs
   - Lister bugs/corrections nécessaires

6. **[ ] Itérer corrections** :
   - Corriger bugs identifiés
   - Re-tester
   - Mettre à jour documentation

---

## 💡 Conseils de Debugging

### Si la détection ne fonctionne pas

1. Ajouter logs DEBUG dans `_is_temporal_query()` :
```python
def _is_temporal_query(self, text: str) -> bool:
    if not text:
        return False
    result = bool(self._TEMPORAL_QUERY_RE.search(text))
    logger.debug(f"[TemporalQuery] Detection for '{text[:50]}...': {result}")
    return result
```

2. Tester regex manuellement :
```python
import re
pattern = re.compile(r"\b(quand|quel\s+jour|...)\b", re.IGNORECASE)
test_cases = [
    "Quand avons-nous parlé de X ?",  # True
    "Quel jour avons-nous abordé Y ?",  # True
    "De quoi avons-nous parlé ?"  # False
]
for test in test_cases:
    print(f"{test} → {bool(pattern.search(test))}")
```

### Si le contexte n'est pas enrichi

1. Vérifier logs :
```bash
grep "TemporalQuery" backend_logs.txt
```

2. Vérifier requête SQL dans `queries.get_messages()` :
```python
# Ajouter log dans _build_temporal_history_context()
logger.debug(f"[TemporalHistory] Fetching messages for thread={thread_id}, limit={limit}")
messages = await queries.get_messages(...)
logger.debug(f"[TemporalHistory] Retrieved {len(messages)} messages")
```

3. Vérifier format retourné :
```python
# Ajouter log avant return
logger.debug(f"[TemporalHistory] Context length: {len(result)} chars")
return result
```

### Si Anima ne répond pas correctement

1. Vérifier contexte injecté dans prompt :
```python
# Dans _build_prompt(), log le contexte RAG final
logger.debug(f"[RAG Context] {rag_context[:200]}...")
```

2. Vérifier prompt système Anima respecte instructions :
- Lire [anima_system_v2.md](../../prompts/anima_system_v2.md)
- Section "Mémoire Temporelle" doit être respectée

3. Tester manuellement avec contexte simulé :
```python
# Créer conversation test avec contexte temporel explicite
context = """
### Historique récent de cette conversation
**[15 oct à 3h08] Toi :** Test message
"""
```

---

## 🎯 Objectif de l'Instance

**À la fin de cette instance, on doit avoir** :

1. ✅ Tests complets effectués (4 tests minimum)
2. ✅ Bugs identifiés et corrigés
3. ✅ Documentation mise à jour avec résultats tests
4. ✅ Validation que Anima répond précisément aux questions temporelles
5. ✅ Confirmation que Memory Gardener fonctionne sans erreur

**Prochaine instance pourra alors** :
- Implémenter optimisations (cache, groupement thématique)
- Ajouter métriques Prometheus
- Étendre fonctionnalité (multi-thread, résumé intelligent)

---

## 📞 Contact & Questions

Si quelque chose n'est pas clair :

1. **Consulter documentation complète** :
   - [MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md](./MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md)

2. **Vérifier logs backend** :
   - Chercher `[TemporalQuery]`, `[MemoryGardener]`, `ERROR`

3. **Analyser code source** :
   - [service.py](../../src/backend/features/chat/service.py)
   - [gardener.py](../../src/backend/features/memory/gardener.py)

4. **Tester manuellement** :
   - Ouvrir Python REPL et importer modules
   - Tester fonctions isolément

---

Bon courage ! Tu as tous les éléments pour réussir cette phase de tests et corrections. 🚀

**Prochaine étape** : Lancer le backend et commencer les tests !
