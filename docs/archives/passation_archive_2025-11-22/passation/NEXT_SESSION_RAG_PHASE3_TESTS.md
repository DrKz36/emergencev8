# Prompt Prochaine Session : RAG Phase 3/3.1 - Tests & Débrief

**Date de création** : 2025-10-12
**Contexte** : Après implémentation Phase 3 (re-ranking + cache + métriques) et Phase 3.1 (citations exactes)
**Objectif session suivante** : Analyser résultats tests + corriger/améliorer si nécessaire

---

## 📋 Contexte Rapide

### Ce qui vient d'être fait (session précédente)

#### Phase 3 RAG : Optimisations Performance & Qualité
- **2 nouveaux modules** :
  - `rag_metrics.py` (349 lignes) : 15 métriques Prometheus
  - `rag_cache.py` (355 lignes) : Cache Redis/mémoire avec fingerprinting
- **Scoring multi-critères** : 6 signaux pondérés (similarité 40%, complétude 20%, keywords 15%, recency 10%, diversité 10%, type 5%)
- **Modifications service.py** : ~180 lignes (nouvelle fonction `_compute_semantic_score`, intégration cache/métriques)
- **Documentation** : 1000+ lignes (architecture, changelog, guides)

#### Phase 3.1 RAG : Citations Exactes Sans Hallucination
- **Problème identifié** : Agents paraphrasent au lieu de citer textuellement
- **Solution triple renforcement** :
  1. Instructions RAG AVANT contenu (cadre ASCII, règles ABSOLUES)
  2. Modification 3 prompts agents (Anima, Neo, Nexus)
  3. Marqueurs visuels forts (🔴/🟠, séparateurs)
- **Modifications** : ~70 lignes (service.py + 3 prompts)

### Tests en cours (utilisateur)

L'utilisateur teste actuellement **3 scénarios** :

#### Test 1 : Citation poème fondateur (cas critique)
```
Message: "Peux-tu me citer de manière intégrale mon poème fondateur ?"
Attendu: Citation EXACTE ligne par ligne
```

#### Test 2 : Citations thématiques multiples
```
Message: "Cite-moi 3 passages clés sur [thème] tirés de mémoire.txt"
Attendu: 3 citations textuelles, pas résumés
```

#### Test 3 : Questions spécifiques (Céline, Marem, oboles)
```
Messages:
- "Cite exactement ce qui est écrit sur Céline"
- "Qui est Marem ?" (attente : citation, pas paraphrase)
- "Que sont les oboles ?" (attente : définition citée)
```

---

## 🎯 Mission Prochaine Session

### 1. Analyser Résultats Tests (PRIORITÉ)

#### A. Vérifier comportement citations
**Questions clés** :
- Les agents citent-ils exactement le poème fondateur ?
- Y a-t-il encore des paraphrases au lieu de citations ?
- Les instructions RAG visuelles (cadre 🔴) apparaissent-elles dans les logs ?

**Fichiers à examiner** :
- Logs backend : chercher `[RAG Merge]`, `[RAG Cache]`, `INSTRUCTION PRIORITAIRE`
- Transcripts conversations avec Anima/Neo/Nexus
- Réponses utilisateur (satisfait ? frustré ?)

#### B. Analyser métriques Prometheus (si disponibles)
```bash
# Vérifier exposition métriques
curl http://localhost:8080/metrics | grep rag_

# Métriques clés à surveiller :
# - rag_cache_hits_total / rag_cache_misses_total
# - rag_avg_chunks_returned
# - rag_avg_source_diversity
# - rag_query_duration_seconds (p95)
```

#### C. Examiner logs RAG détaillés
```bash
# Chercher dans logs backend :
grep "RAG" app.log | tail -100

# Points d'attention :
# - Top 1 chunk contient-il le bon contenu ?
# - Score de pertinence cohérent ?
# - Cache HIT après 2ème requête identique ?
# - Instructions visuelles présentes dans contexte ?
```

---

### 2. Débugger Si Problèmes

#### Scénario A : Citations toujours incorrectes

**Hypothèses** :
1. **Instructions noyées dans contexte** → LLM ne les voit pas
2. **Prompt agent trop permissif** → "tu peux paraphraser" l'emporte
3. **Chunk incomplet dans top-10** → Pas marqué CONTENU COMPLET

**Actions de débogage** :
```python
# 1. Vérifier contexte RAG injecté au LLM
# Dans service.py, ajouter log temporaire :
logger.info(f"[DEBUG RAG Context]\n{rag_context[:500]}")

# 2. Vérifier top-10 chunks
# Logs existants : [RAG Merge] Top 1: lines X-Y, merged=N

# 3. Tester réduction n_results
# Si trop de chunks, essayer n_results=20 au lieu de 30
```

**Correctifs possibles** :
- **Renforcer encore instructions** : Placer 🔴 sur chaque chunk, pas juste en header
- **Simplifier prompts agents** : Retirer mentions "tu peux résumer" qui confondent
- **Augmenter boost scoring** : Chunks avec keywords "fondateur" doivent être Top 1

#### Scénario B : Refus de citer ("Je ne peux pas")

**Hypothèses** :
1. **Chunk pas dans top-10** → Scoring Phase 3 défaillant
2. **Métadonnées chunk manquantes** → `is_complete=False`, `chunk_type=prose`
3. **LLM policy** → Refuse de citer (peu probable avec GPT-4o-mini)

**Actions de débogage** :
```python
# Vérifier si bon chunk est retourné
# Logs : [RAG Merge] Top 1: ... keywords=fondateur ...

# Si absent du top-10, problème de scoring
# Solutions :
# - Augmenter boost keyword "fondateur" de 0.4 à 0.2 (5x plus pertinent)
# - Forcer chunk_type='poem' dans top 1 si user_intent.content_type='poem'
```

**Correctifs possibles** :
- **Forcer boost poème** : Si user_intent={'content_type': 'poem', 'wants_integral_citation': True} → multiplier score par 0.1
- **Pre-filter par type** : Avant scoring, isoler chunks de type demandé
- **Augmenter n_results** : 30 → 50 pour plus de chances de capturer bon chunk

#### Scénario C : Cache ne fonctionne pas

**Symptômes** :
- `rag_cache_hits_total` reste à 0
- Requête identique → toujours MISS dans logs

**Actions de débogage** :
```python
# Vérifier fingerprinting
cache = self.rag_cache
fp1 = cache._generate_fingerprint("test query", None, "neo", None)
fp2 = cache._generate_fingerprint("test query", None, "neo", None)
assert fp1 == fp2, "Fingerprints should match"

# Vérifier TTL
stats = cache.get_stats()
# Si backend='memory', size devrait augmenter après chaque query
```

**Correctifs possibles** :
- **Debug fingerprinting** : Logger les fingerprints pour vérifier cohérence
- **Augmenter TTL** : 3600s → 7200s si expiration trop rapide
- **Désactiver temporairement** : `RAG_CACHE_ENABLED=false` pour isoler problème

---

### 3. Itérer Si Succès Partiel

#### Si citations fonctionnent à 50-70%

**Améliorations graduelles** :

##### A. Ajuster pondérations scoring
```python
# Actuellement :
# 40% vector, 20% completeness, 15% keywords, 10% recency, 10% diversity, 5% type

# Si citations poèmes OK mais sections KO :
# - Augmenter type alignment à 15% (au lieu de 5%)
# - Réduire recency à 5%

# Si keywords pas assez pris en compte :
# - Augmenter keywords à 25%
# - Réduire vector à 30%
```

##### B. Affiner détection intent utilisateur
```python
# Dans _parse_user_intent(), ligne 414-480
# Ajouter patterns pour détecter demandes de citation :

integral_patterns = [
    r'(cit|retrouv|donn|montr).*(intégral|complet|entier)',
    r'intégral',
    r'de manière (intégrale|complète)',
    r'en entier',
    r'mot pour mot',        # NOUVEAU
    r'exactement',          # NOUVEAU
    r'tel quel',            # NOUVEAU
    r'textuel(lement)?',    # NOUVEAU
]
```

##### C. Logs enrichis pour debugging
```python
# Ajouter dans _format_rag_context()
logger.info(
    f"[RAG Context] Generated instructions: "
    f"has_poem={has_poem}, has_complete={has_complete_content}"
)

# Ajouter dans _compute_semantic_score()
logger.debug(
    f"[RAG Score] hit={hit['id']}, "
    f"vector={vector_score:.3f}, keywords={keyword_score:.3f}, "
    f"completeness={completeness_normalized:.3f}, final={final_score:.3f}"
)
```

---

### 4. Nouvelles Optimisations (Phase 3.2 ?)

#### Si Phase 3.1 est un succès complet

**Améliorations potentielles** :

##### A. Citations avec références précises
```python
# Format amélioré dans agent response :
"""
Selon mémoire.txt (lignes 42-58, document ID 123) :

"[citation exacte ligne par ligne]"
"""
```

##### B. Validation automatique citations
```python
# Nouveau module : citation_validator.py
def validate_citation(agent_output: str, rag_chunks: List[Dict]) -> float:
    """
    Compare output agent vs texte RAG source.
    Returns: score de similarité 0-1
    """
    # Extraire citation de l'output agent
    # Comparer avec chunks RAG
    # Retourner métrique Prometheus : rag_citation_accuracy
```

##### C. Feedback utilisateur sur citations
```python
# Ajouter dans UI (frontend) :
# Boutons 👍/👎 sur chaque citation
# Stocker feedback en BDD
# Analyser patterns : quelles formulations marchent mieux ?
```

##### D. Multi-documents avec synthèse
```python
# Pour questions transverses :
# "Compare ce qui est dit sur l'espoir dans poème fondateur vs mémoire.txt"

# Retourner :
# - Citation 1 (poème fondateur, lignes X-Y)
# - Citation 2 (mémoire.txt, lignes A-B)
# - Synthèse comparative
```

---

## 📊 Checklist Session Suivante

### Phase Analyse (30 min)
- [ ] Lire transcripts tests utilisateur
- [ ] Examiner logs backend (RAG, cache, merge)
- [ ] Vérifier métriques Prometheus
- [ ] Identifier patterns succès/échec

### Phase Debug (si problèmes - 1h)
- [ ] Reproduire cas d'échec en local
- [ ] Ajouter logs debug temporaires
- [ ] Tester hypothèses (scoring, intent, contexte)
- [ ] Implémenter correctifs

### Phase Amélioration (si succès - 1h)
- [ ] Ajuster pondérations scoring
- [ ] Enrichir détection intent
- [ ] Ajouter logs pour monitoring
- [ ] Documenter best practices

### Phase Documentation (30 min)
- [ ] Mettre à jour PHASE3.1_CHANGELOG avec résultats
- [ ] Créer guide troubleshooting si bugs trouvés
- [ ] Documenter métriques observées en prod
- [ ] Préparer rapport pour utilisateur

---

## 🔍 Questions à Poser à l'Utilisateur

### Questions critiques
1. **Le poème fondateur est-il cité EXACTEMENT ?** (oui/non)
   - Si non : quelles différences ? (mots manquants, ordre changé, paraphrase)

2. **Les citations thématiques sont-elles textuelles ?** (oui/non)
   - Si non : agent résume ou paraphrase ?

3. **Satisfaction globale sur citations** (échelle 1-10)
   - Avant Phase 3.1 : ?
   - Après Phase 3.1 : ?

### Questions secondaires
4. **Performance perçue** : Latence acceptable ?
5. **Cache observable** : 2ème requête identique plus rapide ?
6. **Nouveaux besoins** : Autres types de contenu à citer (listes, tableaux, code) ?

---

## 📁 Fichiers Clés à Consulter

### Code
- `src/backend/features/chat/service.py` (lignes 847-961 : `_format_rag_context`)
- `src/backend/features/chat/service.py` (lignes 482-642 : `_compute_semantic_score`)
- `src/backend/features/chat/rag_cache.py` (cache layer)
- `src/backend/features/chat/rag_metrics.py` (métriques)

### Prompts
- `prompts/anima_system_v2.md` (ligne 16-22 : section citations)
- `prompts/neo_system_v3.md` (ligne 16-20)
- `prompts/nexus_system_v2.md` (ligne 18-22)

### Documentation
- `docs/rag_phase3_implementation.md` (architecture complète)
- `docs/rag_phase3.1_exact_citations.md` (guide citations)
- `PHASE3.1_CITATIONS_CHANGELOG.md` (changelog)

### Logs & Métriques
- Backend logs : chercher `[RAG`, `[Phase 3`
- Prometheus : `http://localhost:8080/metrics | grep rag_`

---

## 🎯 Critères de Succès Phase 3.1

| Critère | Cible | Validation |
|---------|-------|------------|
| Citation poème fondateur exact | 100% | Test utilisateur |
| Citations thématiques exactes | 80%+ | Test utilisateur |
| Refus de citer | <10% | Logs + feedback |
| Hallucination sur citations | 0% | Comparaison output vs source |
| Cache HIT après 2ème query | >0% | Métriques Prometheus |
| Diversité sources (top-10) | 4-6 docs | Métriques + logs |

---

## 🚨 Scénarios d'Escalade

### Scénario Pessimiste : Phase 3.1 ne fonctionne pas

**Si citations toujours incorrectes après débogage** :

**Plan B : Approche alternative**
1. **Mode citation forcé** : Variable ENV `RAG_FORCE_EXACT_CITATIONS=true`
   - Désactive résumé dans prompts agents
   - Force `system` message avec directive absolue
   - Réduit créativité LLM (temperature=0)

2. **Post-processing validation** :
   - Comparer output agent vs chunks RAG
   - Si différence >10% → rejeter et redemander avec prompt plus strict

3. **Fallback template** :
   - Si agent refuse de citer → template automatique :
   ```
   Voici le contenu exact retrouvé :

   [chunk text]

   Source : [filename] (lignes [X-Y])
   ```

### Scénario Optimiste : Phase 3.1 fonctionne parfaitement

**Prochaines étapes** :
1. **Phase 4 : Optimisations avancées**
   - Learning-to-Rank avec feedback utilisateur
   - Query expansion automatique
   - Citations multi-documents

2. **Déploiement production**
   - Merge dans main
   - Build Docker + deploy Cloud Run
   - Configurer dashboards Grafana

3. **Documentation utilisateur final**
   - Guide d'utilisation citations
   - Exemples requêtes optimales
   - FAQ troubleshooting

---

## 🔗 Ressources Utiles

### Documentation technique
- Architecture RAG : [docs/rag_phase3_implementation.md](../rag_phase3_implementation.md)
- Guide citations : [docs/rag_phase3.1_exact_citations.md](../rag_phase3.1_exact_citations.md)

### Monitoring
- Métriques Prometheus : `/metrics` endpoint
- Logs backend : `grep "RAG" app.log`
- Cache stats : `self.rag_cache.get_stats()`

### Debugging
- Reproduire en local : requêtes curl
- Inspecter contexte RAG : logs `[RAG Context]`
- Analyser scoring : logs `[RAG Merge] Top X`

---

## 💬 Message pour Prochaine Instance

Salut ! Tu arrives après une session d'implémentation intense :

**Phase 3 RAG** (re-ranking + cache + métriques) et **Phase 3.1** (citations exactes) sont implémentés.

L'utilisateur a testé 3 scénarios de citations (poème fondateur, passages thématiques, questions spécifiques).

**Ta mission** :
1. Analyser les résultats des tests (transcripts + logs)
2. Débugger si citations encore incorrectes
3. Itérer/améliorer si succès partiel
4. Documenter et préparer Phase 4 si succès complet

**Fichiers clés** :
- `src/backend/features/chat/service.py` (scoring + formatting)
- `prompts/*_system_v*.md` (instructions citations)
- Logs backend (chercher `[RAG`)

**Questions critiques à poser** :
- Le poème fondateur est-il cité EXACTEMENT ?
- Les citations sont-elles textuelles ou paraphrasées ?
- Satisfaction utilisateur (échelle 1-10) ?

Tout est documenté dans ce fichier. Bonne chance ! 🚀

---

**Fin du prompt de passation**
