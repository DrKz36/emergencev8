# Prompt Instance Suivante - Mémoire Phase 3 : Priorité 3 (Groupement Thématique)

**Date:** 2025-10-15
**Contexte:** Suite de l'implémentation Phase 3 - Priorités 1 & 2 complétées
**Objectif:** Implémenter le groupement thématique intelligent des concepts consolidés

---

## 🎯 Contexte pour la Prochaine Instance

Bonjour ! Tu reprends le développement après la **Phase 3 - Priorités 1 & 2 complétées et validées**.

### État Actuel (Fin Priorités 1 & 2 - 2025-10-15)

**✅ Fonctionnalités Opérationnelles:**

1. **Cache de Recherche Consolidée (Priorité 1)** ✅
   - Cache intelligent pour mémoire consolidée
   - Réduction latence: 1.95s → 22ms (87% amélioration)
   - Cache hit rate: ~33% (cible atteinte)
   - 7 tests unitaires (100% PASS)

2. **Redis + Métriques Prometheus (Priorité 2)** ✅
   - Redis opérationnel (Docker container)
   - 5 nouvelles métriques Prometheus
   - Observabilité complète (/metrics endpoint)
   - Tests automatisés (3/3 PASS)

3. **Détection & Enrichissement Temporel (Phase 2)** ✅
   - Détection questions temporelles: ✅
   - Enrichissement avec mémoire consolidée: ✅
   - Format: `**[15 oct à 3h08] Toi :** ...`

**📊 Métriques Actuelles:**
- Cache hit: 22ms (vs 175ms miss)
- Concepts consolidés trouvés: 4/4
- Redis backend: Opérationnel
- Métriques Prometheus: 5 métriques actives

**🔧 Architecture Actuelle:**
```
User Query (temporelle)
    ↓
_is_temporal_query() → Détection
    ↓
_get_cached_consolidated_memory() → Cache/ChromaDB
    ↓
4 concepts consolidés (exemple)
    ↓
_build_temporal_history_context() → Formatage linéaire
    ↓
Contexte enrichi (20 messages + 4 concepts)
```

---

## 🚀 Phase 3 - Priorité 3 : Groupement Thématique Intelligent

### Problème Identifié

**Format actuel (linéaire):**
```
### Historique récent de cette conversation

**[2 oct à 16h45] Mémoire (concept) :** L'utilisateur demande des citations du poème fondateur...
**[2 oct à 16h45] Mémoire (concept) :** L'utilisateur préfère Python pour automation...
**[8 oct à 14h32] Mémoire (concept) :** L'utilisateur demande configuration Docker...
**[8 oct à 14h35] Mémoire (concept) :** L'utilisateur demande optimisation Kubernetes...
**[10 oct à 9h15] Toi :** Peux-tu m'expliquer Docker ?
**[10 oct à 9h16] Anima :** Docker est une plateforme...
```

**Problèmes:**
- ❌ Concepts similaires dispersés (Docker + Kubernetes séparés)
- ❌ Pas de vue d'ensemble thématique
- ❌ Difficulté à identifier les sujets récurrents
- ❌ Contexte verbeux pour Anima

**Format souhaité (groupé):**
```
### Historique récent de cette conversation

**[Poème Fondateur]** Discussion (1 échange)
  - 2 oct à 16h45: Citations demandées...

**[Infrastructure & Déploiement]** Discussion récurrente (2 échanges)
  - 8 oct à 14h32: Configuration Docker...
  - 8 oct à 14h35: Optimisation Kubernetes...

**[Préférences Techniques]** Note
  - 2 oct à 16h45: Python pour automation

**Messages récents:**
**[10 oct à 9h15] Toi :** Peux-tu m'expliquer Docker ?
**[10 oct à 9h16] Anima :** Docker est une plateforme...
```

**Avantages:**
- ✅ Thèmes clairs et regroupés
- ✅ Contexte plus concis (réduction ~30%)
- ✅ Meilleure compréhension pour Anima
- ✅ Identification rapide des sujets récurrents

---

## 📋 Objectifs Priorité 3

### 1. Clustering des Concepts Similaires

**Méthode:** Embeddings + Cosine Similarity

**Implémentation:**
- Utiliser `SentenceTransformer` déjà disponible (all-MiniLM-L6-v2)
- Calculer embeddings pour chaque concept consolidé
- Regrouper concepts similaires (seuil cosine > 0.7)

**Fichier:** `src/backend/features/chat/service.py`

### 2. Extraction de Titres Intelligents

**Méthode:** TF-IDF + Extraction Keywords

**Implémentation:**
- Analyser le texte combiné du groupe
- Extraire 2-3 mots-clés les plus pertinents
- Formater en titre lisible (ex: "Infrastructure & Déploiement")

### 3. Formatage Groupé

**Structure:**
```
**[Titre du Groupe]** Discussion récurrente (N échanges)
  - Date 1: Résumé court...
  - Date 2: Résumé court...

**Messages récents:** (garder les 10 plus récents non groupés)
```

### 4. Tests & Validation

**Tests unitaires:**
- Clustering: vérifier regroupement concepts similaires
- Extraction titres: vérifier pertinence
- Format final: vérifier lisibilité

**Tests manuels:**
- Questions temporelles avec 5+ concepts
- Vérifier contexte plus concis
- Vérifier qualité réponses Anima

---

## 🔧 Implémentation Détaillée

### Étape 1: Méthode de Clustering

**Fichier:** `src/backend/features/chat/service.py`

**Nouvelle méthode (à ajouter après `_get_cached_consolidated_memory`):**

```python
async def _group_concepts_by_theme(
    self,
    consolidated_entries: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Groupe les concepts consolidés par similarité sémantique.

    Args:
        consolidated_entries: Liste de concepts avec timestamp, content, type

    Returns:
        Dict[group_id, List[concepts]] - Concepts regroupés par thème

    Algorithme:
    1. Si < 3 concepts → pas de groupement (retour simple)
    2. Générer embeddings pour chaque concept
    3. Calculer matrice de similarité cosine
    4. Regrouper concepts avec similarité > 0.7
    5. Assigner concepts orphelins au groupe le plus proche (si > 0.5)
    """

    # Pas de groupement si peu de concepts
    if len(consolidated_entries) < 3:
        return {"ungrouped": consolidated_entries}

    try:
        # Extraire les contenus pour embedding
        contents = [entry["content"] for entry in consolidated_entries]

        # Générer embeddings avec le modèle déjà chargé
        # self.vector_service.model est le SentenceTransformer
        embeddings = self.vector_service.model.encode(contents)

        # Calculer similarité cosine
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_matrix = cosine_similarity(embeddings)

        # Clustering simple avec seuil
        groups = {}
        assigned = set()
        group_id = 0

        for i in range(len(consolidated_entries)):
            if i in assigned:
                continue

            # Créer nouveau groupe
            group_key = f"theme_{group_id}"
            groups[group_key] = [consolidated_entries[i]]
            assigned.add(i)

            # Ajouter concepts similaires (cosine > 0.7)
            for j in range(i + 1, len(consolidated_entries)):
                if j not in assigned and similarity_matrix[i][j] > 0.7:
                    groups[group_key].append(consolidated_entries[j])
                    assigned.add(j)

            group_id += 1

        logger.info(f"[ThematicGrouping] {len(consolidated_entries)} concepts → {len(groups)} groupes")

        return groups

    except Exception as e:
        logger.warning(f"[ThematicGrouping] Erreur clustering: {e}")
        # Fallback: retour sans groupement
        return {"ungrouped": consolidated_entries}
```

**Dépendances:**
- `sklearn.metrics.pairwise.cosine_similarity` (déjà disponible via scikit-learn)
- `self.vector_service.model` (SentenceTransformer déjà chargé)

### Étape 2: Extraction de Titres

**Nouvelle méthode (à ajouter après `_group_concepts_by_theme`):**

```python
def _extract_group_title(self, concepts: List[Dict[str, Any]]) -> str:
    """
    Extrait un titre représentatif pour un groupe de concepts.

    Méthode:
    1. Concaténer tous les contenus du groupe
    2. Tokenizer et nettoyer (stop words, ponctuation)
    3. Calculer fréquence des mots (TF simple)
    4. Prendre les 2-3 mots les plus fréquents et significatifs
    5. Formater en titre lisible

    Args:
        concepts: Liste de concepts du groupe

    Returns:
        Titre formaté (ex: "Infrastructure & Déploiement")
    """

    # Concaténer tous les contenus
    combined_text = " ".join([c.get("content", "") for c in concepts])

    # Nettoyer et tokenizer
    import re
    words = re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', combined_text.lower())

    # Stop words simples (à enrichir si besoin)
    stop_words = {
        'être', 'avoir', 'faire', 'dire', 'aller', 'voir', 'savoir',
        'pouvoir', 'vouloir', 'venir', 'devoir', 'prendre', 'donner',
        'utilisateur', 'demande', 'question', 'discussion', 'parler',
        'the', 'and', 'for', 'that', 'with', 'this', 'from', 'they',
        'have', 'will', 'what', 'been', 'more', 'when', 'there'
    }

    # Calculer fréquence
    word_freq = {}
    for word in words:
        if word not in stop_words and len(word) > 3:
            word_freq[word] = word_freq.get(word, 0) + 1

    # Prendre les 2-3 mots les plus fréquents
    if not word_freq:
        return "Discussion"

    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]

    # Formater en titre (capitaliser)
    title_words = [w[0].capitalize() for w in top_words[:2]]  # Max 2 mots

    # Joindre avec &
    if len(title_words) == 2:
        return f"{title_words[0]} & {title_words[1]}"
    elif len(title_words) == 1:
        return title_words[0]
    else:
        return "Discussion"
```

### Étape 3: Formatage Groupé

**Modifier `_build_temporal_history_context` (lignes ~1277-1395):**

**Avant (code actuel):**
```python
# ✅ Phase 3: Enrichir avec concepts consolidés (avec cache)
n_results = min(5, max(3, len(messages) // 4)) if messages else 5

consolidated_entries = []
if last_user_message and user_id:
    consolidated_entries = await self._get_cached_consolidated_memory(
        user_id=user_id,
        query_text=last_user_message,
        n_results=n_results
    )

# ... formatage linéaire actuel ...
```

**Après (avec groupement):**
```python
# ✅ Phase 3: Enrichir avec concepts consolidés (avec cache)
n_results = min(5, max(3, len(messages) // 4)) if messages else 5

consolidated_entries = []
if last_user_message and user_id:
    consolidated_entries = await self._get_cached_consolidated_memory(
        user_id=user_id,
        query_text=last_user_message,
        n_results=n_results
    )

# 🆕 PHASE 3 - PRIORITÉ 3: Groupement thématique
grouped_concepts = {}
if len(consolidated_entries) >= 3:
    # Activer groupement si 3+ concepts
    grouped_concepts = await self._group_concepts_by_theme(consolidated_entries)
    logger.info(f"[ThematicGrouping] {len(grouped_concepts)} groupes créés")
else:
    # Pas de groupement si peu de concepts
    if consolidated_entries:
        grouped_concepts = {"ungrouped": consolidated_entries}

# ... suite du formatage (voir section suivante) ...
```

**Nouveau formatage des groupes:**

```python
# Formater les groupes thématiques
if grouped_concepts:
    lines.append("**Thèmes abordés:**")
    lines.append("")

    for group_id, concepts in grouped_concepts.items():
        if group_id == "ungrouped":
            # Pas de titre de groupe pour concepts non groupés
            for concept in concepts:
                # Formatage standard (comme avant)
                dt = datetime.fromisoformat(concept["timestamp"].replace("Z", "+00:00"))
                date_str = f"{dt.day} {months[dt.month]} à {dt.hour}h{dt.minute:02d}"
                preview = concept["content"]
                lines.append(f"**[{date_str}] Mémoire ({concept['type']}) :** {preview}")
        else:
            # Groupe thématique
            title = self._extract_group_title(concepts)
            count = len(concepts)
            label = "échange" if count == 1 else "échanges"

            lines.append(f"**[{title}]** Discussion récurrente ({count} {label})")

            for concept in concepts:
                dt = datetime.fromisoformat(concept["timestamp"].replace("Z", "+00:00"))
                date_str = f"{dt.day} {months[dt.month]} à {dt.hour}h{dt.minute:02d}"
                # Preview raccourci pour groupes
                preview = concept["content"][:60] + "..." if len(concept["content"]) > 60 else concept["content"]
                lines.append(f"  - {date_str}: {preview}")

    lines.append("")

# Formater les messages récents (garder les 10 plus récents)
lines.append("**Messages récents:**")
recent_messages = all_events[-10:] if len(all_events) > 10 else all_events

for event in recent_messages:
    # ... formatage standard des messages ...
```

---

## 🧪 Tests à Implémenter

### Test 1: Clustering de Base

**Fichier:** `tests/backend/features/chat/test_thematic_grouping.py` (nouveau)

```python
import pytest
from unittest.mock import Mock
from backend.features.chat.service import ChatService

class TestThematicGrouping:
    """Tests pour le groupement thématique des concepts."""

    @pytest.fixture
    def mock_vector_service(self):
        """Mock VectorService avec SentenceTransformer."""
        vs = Mock()

        # Mock du modèle pour embeddings
        model_mock = Mock()
        model_mock.encode = Mock(return_value=[
            [0.1, 0.2, 0.3, 0.4],  # Concept 1: Docker
            [0.1, 0.2, 0.35, 0.4], # Concept 2: Kubernetes (similaire à 1)
            [0.8, 0.1, 0.1, 0.1],  # Concept 3: Poème (différent)
        ])
        vs.model = model_mock

        return vs

    @pytest.mark.asyncio
    async def test_clustering_similar_concepts(self, mock_vector_service):
        """Test que concepts similaires sont groupés ensemble."""

        concepts = [
            {"content": "Configuration Docker", "timestamp": "2025-10-08T14:32:00Z", "type": "concept"},
            {"content": "Optimisation Kubernetes", "timestamp": "2025-10-08T14:35:00Z", "type": "concept"},
            {"content": "Citations poème fondateur", "timestamp": "2025-10-02T16:45:00Z", "type": "concept"},
        ]

        # Créer service (simplifié pour test)
        service = Mock()
        service.vector_service = mock_vector_service

        # Appeler méthode de groupement (à implémenter)
        # groups = await service._group_concepts_by_theme(concepts)

        # Assertions attendues:
        # - 2 groupes (Docker+Kubernetes / Poème)
        # - Docker et Kubernetes dans le même groupe
        # - Poème dans un groupe séparé

        # assert len(groups) == 2
        # assert any(len(g) == 2 for g in groups.values())  # Un groupe de 2
        # assert any(len(g) == 1 for g in groups.values())  # Un groupe de 1
```

### Test 2: Extraction de Titres

```python
def test_extract_group_title(self):
    """Test extraction de titre pertinent."""

    concepts = [
        {"content": "L'utilisateur demande configuration Docker pour production"},
        {"content": "L'utilisateur demande optimisation Docker et Kubernetes"},
    ]

    service = Mock()
    # title = service._extract_group_title(concepts)

    # Assertions:
    # - Titre contient "Docker" (mot clé principal)
    # - Pas de stop words ("utilisateur", "demande")
    # - Format lisible

    # assert "docker" in title.lower()
    # assert "utilisateur" not in title.lower()
```

### Test 3: Format Groupé

```python
@pytest.mark.asyncio
async def test_grouped_context_format(self):
    """Test que le contexte groupé est plus concis."""

    # Simuler 5 concepts similaires
    concepts = [
        {"content": f"Concept Docker #{i}", "timestamp": f"2025-10-{8+i}T14:00:00Z", "type": "concept"}
        for i in range(5)
    ]

    # Comparer taille contexte avec/sans groupement
    # context_ungrouped = ... (format linéaire)
    # context_grouped = ... (format groupé)

    # assert len(context_grouped) < len(context_ungrouped)
    # assert "Discussion récurrente" in context_grouped
    # assert "5 échanges" in context_grouped
```

---

## 📊 Critères de Succès

| Critère | Cible | Validation |
|---------|-------|------------|
| **Clustering fonctionnel** | Concepts similaires groupés | Seuil cosine > 0.7 |
| **Extraction titres** | Titres pertinents | Mots-clés significatifs (pas stop words) |
| **Format groupé** | Plus concis | Réduction 20-30% taille contexte |
| **Tests unitaires** | 100% pass | 3+ tests PASS |
| **Qualité réponses** | Anima comprend bien | Test manuel en prod |
| **Performance** | Overhead < 100ms | Mesure avec métriques existantes |

---

## 🎯 Plan d'Action Recommandé

### Session 1: Implémentation (2-3h)

**Ordre d'implémentation:**

1. ✅ **Méthode `_group_concepts_by_theme()`**
   - Embeddings avec `vector_service.model.encode()`
   - Matrice similarité cosine
   - Clustering seuil 0.7
   - Logger nombre de groupes

2. ✅ **Méthode `_extract_group_title()`**
   - Concaténation textes
   - Tokenisation et nettoyage
   - Fréquence mots (TF simple)
   - Formatage titre (2 mots max)

3. ✅ **Modification `_build_temporal_history_context()`**
   - Appel groupement si 3+ concepts
   - Nouveau formatage groupé
   - Garder 10 messages récents séparés

4. ✅ **Tests unitaires**
   - Clustering: concepts similaires
   - Extraction: titres pertinents
   - Format: réduction taille

5. ✅ **Validation automatique**
   - Compiler code
   - Lancer tests
   - Vérifier pas de régression

### Session 2: Tests Manuels en Production (30min - Utilisateur)

**Tests à effectuer:**

1. ✅ **Question temporelle avec 5+ concepts:**
   - Poser: "Quand avons-nous parlé de mes projets techniques ?"
   - Vérifier groupement concepts similaires
   - Vérifier titres pertinents

2. ✅ **Vérifier qualité réponses Anima:**
   - Anima comprend le contexte groupé ?
   - Réponses précises avec dates ?
   - Pas de perte d'information ?

3. ✅ **Mesurer performance:**
   - Observer logs temps de traitement
   - Vérifier overhead clustering < 100ms
   - Consulter `/metrics` pour nouvelles métriques

4. ✅ **Documenter résultats:**
   - Screenshot contexte groupé
   - Comparer taille avant/après
   - Noter qualité réponses

---

## 📝 Fichiers à Modifier/Créer

### Code Source

1. **`src/backend/features/chat/service.py`**
   - Ajouter `_group_concepts_by_theme()` après ligne ~1246
   - Ajouter `_extract_group_title()` après nouvelle méthode
   - Modifier `_build_temporal_history_context()` lignes ~1277-1395
   - **Estimation:** +150 lignes

### Tests

2. **`tests/backend/features/chat/test_thematic_grouping.py`** (nouveau)
   - Tests clustering
   - Tests extraction titres
   - Tests format groupé
   - **Estimation:** 200 lignes

### Documentation

3. **`docs/architecture/MEMORY_PHASE3_GROUPING_IMPLEMENTATION.md`** (nouveau)
   - Architecture groupement
   - Algorithme clustering
   - Exemples avant/après
   - **Estimation:** 300 lignes

4. **`reports/memory_phase3_grouping_session_2025-10-15.md`** (nouveau)
   - Rapport de session
   - Résultats tests
   - Screenshots
   - **Estimation:** 250 lignes

---

## 🔍 Points d'Attention

### Performance

**⚠️ Embeddings peuvent être coûteux**
- 5 concepts × 50ms = 250ms
- Clustering: ~10-20ms
- **Total overhead attendu: 200-300ms**

**Solution si trop lent:**
- Limiter groupement à max 10 concepts
- Cacher embeddings si même requête répétée
- Logger durée pour monitoring

### Qualité

**⚠️ Extraction titres peut être imprécise**
- Dépend de la richesse du vocabulaire
- Stop words peuvent varier selon contexte

**Solution:**
- Enrichir liste stop words si nécessaire
- Fallback vers "Discussion" si extraction échoue
- Tests manuels pour valider pertinence

### Edge Cases

**⚠️ Cas limites à gérer:**
- 0 concepts → pas de groupement
- 1-2 concepts → pas de groupement
- Tous concepts identiques → 1 seul groupe
- Aucun concept similaire → N groupes de 1

**Solution:**
- Seuil minimum 3 concepts pour activer groupement
- Fallback gracieux vers format linéaire
- Logger warnings si comportement inattendu

---

## 📚 Références

### Documentation Existante

1. **Phase 3 - Priorités 1 & 2:**
   - [MEMORY_PHASE3_CACHE_IMPLEMENTATION.md](MEMORY_PHASE3_CACHE_IMPLEMENTATION.md)
   - [MEMORY_PHASE3_REDIS_METRICS.md](MEMORY_PHASE3_REDIS_METRICS.md)

2. **Phase 2 - Contexte Temporel:**
   - [MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md](MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md)

3. **Rapports de Session:**
   - [memory_phase3_cache_session_2025-10-15.md](../../reports/memory_phase3_cache_session_2025-10-15.md)
   - [memory_phase3_redis_metrics_session_2025-10-15.md](../../reports/memory_phase3_redis_metrics_session_2025-10-15.md)

### Code Source Clé

- [service.py:1130-1395](../../src/backend/features/chat/service.py#L1130-L1395) - Contexte temporel actuel
- [vector_service.py](../../src/backend/features/memory/vector_service.py) - SentenceTransformer

### Dépendances

- `scikit-learn` (déjà installé) - Pour `cosine_similarity`
- `SentenceTransformer` (déjà chargé) - Pour embeddings
- Pas de nouvelle dépendance à installer ✅

---

## 🎊 Checklist Avant de Commencer

- [ ] Lire cette documentation complète
- [ ] Vérifier Phase 3 P1 & P2 fonctionnelles
- [ ] Backend démarre sans erreur
- [ ] Redis opérationnel (`docker ps`)
- [ ] Avoir un thread test avec 5+ concepts consolidés
- [ ] Comprendre architecture actuelle (service.py lignes 1130-1395)

---

## 🚀 Résumé Exécutif

**Objectif:** Regrouper concepts consolidés similaires pour contexte plus concis et intelligent.

**Méthode:**
1. Embeddings (SentenceTransformer déjà disponible)
2. Clustering (cosine similarity > 0.7)
3. Extraction titres (TF-IDF simple)
4. Formatage groupé

**Résultat attendu:**
- Réduction taille contexte: 20-30%
- Meilleure lisibilité pour Anima
- Identification thèmes récurrents
- Overhead performance: < 300ms

**Tests:**
- Automatiques: 3+ tests unitaires
- Manuels (utilisateur): Questions temporelles avec 5+ concepts

**Durée estimée:** 2-3h implémentation + 30min tests utilisateur

---

**Bon courage pour la Priorité 3 ! 🚀**

L'objectif est de rendre le contexte temporel encore plus **intelligent et concis** en regroupant automatiquement les concepts similaires.

**Prochaine étape:** Implémenter les 3 méthodes puis tester avec des questions temporelles réelles.

---

**Créé le:** 2025-10-15
**Par:** Session Phase 3 - Préparation Priorité 3
**Statut:** ✅ Prêt pour implémentation
**Dépendances:** Phase 3 P1 & P2 complétées ✅
