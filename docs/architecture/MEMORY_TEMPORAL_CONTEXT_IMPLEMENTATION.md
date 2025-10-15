# Implémentation Contexte Temporel pour Mémoire - 2025-10-15

## 📋 Vue d'ensemble

**Objectif** : Permettre à Anima de répondre précisément aux questions temporelles ("Quand avons-nous parlé de X ?", "Quel jour et à quelle heure avons-nous abordé Y ?")

**Statut** : ✅ Implémenté et prêt pour tests

**Date** : 2025-10-15

---

## 🎯 Contexte

### Problème Initial

Lorsque l'utilisateur demandait :
- "Quels sujets avons-nous abordés cette semaine ?" → ✅ Anima répondait correctement
- "Quel jour et à quelle heure avons-nous abordé ces sujets ?" → ❌ Anima ne pouvait pas fournir les détails temporels

**Diagnostic** :
- Le système de rappel de concepts récurrents (`ConceptRecallTracker`) fonctionnait correctement
- Les timestamps étaient stockés dans la base de données
- Le contexte RAG ne contenait pas l'historique des messages avec timestamps lors de questions temporelles explicites
- Le `recall_context` n'était enrichi que si des concepts récurrents étaient détectés dans le message actuel

### Solution Implémentée

Ajout d'une détection proactive des questions temporelles qui enrichit automatiquement le contexte avec l'historique complet des messages et leurs timestamps.

---

## 🏗️ Architecture

### Composants Modifiés

#### 1. ChatService ([service.py](../../src/backend/features/chat/service.py))

**Ajouts** :

1. **Regex de détection** (lignes 1114-1118)
```python
_TEMPORAL_QUERY_RE = re.compile(
    r"\b(quand|quel\s+jour|quelle\s+heure|à\s+quelle\s+heure|quelle\s+date|"
    r"when|what\s+time|what\s+day|date|timestamp|horodatage)\b",
    re.IGNORECASE
)
```

2. **Fonction de détection** (lignes 1123-1128)
```python
def _is_temporal_query(self, text: str) -> bool:
    """Détecte si le message contient une question sur les dates/heures."""
    if not text:
        return False
    return bool(self._TEMPORAL_QUERY_RE.search(text))
```

3. **Fonction de construction du contexte** (lignes 1130-1202)
```python
async def _build_temporal_history_context(
    self,
    thread_id: str,
    session_id: str,
    user_id: str,
    limit: int = 20
) -> str:
    """
    Construit un contexte historique enrichi avec timestamps pour répondre
    aux questions temporelles.

    Format généré :
    ### Historique récent de cette conversation

    **[15 oct à 3h08] Toi :** Quels sujets avons-nous abordés cette semaine ?
    **[15 oct à 3h08] Anima :** Cette semaine, on a principalement exploré...
    **[15 oct à 3h09] Toi :** Quel jour et à quelle heure avons nous abordé...
    """
```

4. **Intégration dans le flux RAG** (lignes 1697-1709)
```python
# 🆕 DÉTECTION QUESTIONS TEMPORELLES + ENRICHISSEMENT HISTORIQUE
if not recall_context and self._is_temporal_query(last_user_message) and uid and thread_id:
    try:
        recall_context = await self._build_temporal_history_context(
            thread_id=thread_id,
            session_id=session_id,
            user_id=uid,
            limit=20
        )
        if recall_context:
            logger.info(f"[TemporalQuery] Contexte historique enrichi pour question temporelle")
    except Exception as temporal_err:
        logger.warning(f"[TemporalQuery] Enrichissement historique échoué : {temporal_err}")
```

#### 2. MemoryGardener ([gardener.py](../../src/backend/features/memory/gardener.py))

**Correction** (lignes 669-671) :
```python
# Utiliser get_thread_any pour récupérer le thread avec fallback
# puis extraire le user_id pour les requêtes suivantes
thr = await queries.get_thread_any(
    self.db, tid, session_id=normalized_session, user_id=user_id
)
```

**Problème corrigé** : Erreur "user_id est obligatoire pour accéder aux threads" lors de la consolidation mémoire.

---

## 🔄 Flux de Traitement

### Avant (Question Temporelle Ignorée)

```
User: "Quel jour et à quelle heure avons-nous abordé ces sujets ?"
  ↓
ChatService._build_prompt()
  ↓
ConceptRecallTracker.detect_recurring_concepts()
  → Aucun concept récurrent détecté (question méta)
  → recall_context = "" (vide)
  ↓
RAG Context = Mémoire + Documents uniquement
  ↓
Anima: "Je n'ai pas de détails précis sur les dates et heures..."
```

### Après (Question Temporelle Enrichie)

```
User: "Quel jour et à quelle heure avons-nous abordé ces sujets ?"
  ↓
ChatService._build_prompt()
  ↓
_is_temporal_query(message) → True
  ↓
_build_temporal_history_context()
  → Récupération des 20 derniers messages du thread
  → Formatage avec timestamps : "**[15 oct à 3h08] Toi :** ..."
  → recall_context = "### Historique récent de cette conversation\n..."
  ↓
RAG Context = Historique Temporel + Mémoire + Documents
  ↓
Anima: "On a exploré ton pipeline CI/CD le 5 octobre à 14h32, puis Docker le 8 à 14h32..."
```

---

## 📊 Format du Contexte Temporel

### Structure Générée

```markdown
### Historique récent de cette conversation

**[15 oct à 3h08] Toi :** Quels sujets avons-nous abordés cette semaine ?
**[15 oct à 3h08] Anima :** Cette semaine, on a principalement exploré ton poème fondateur...
**[15 oct à 3h09] Toi :** Quel jour et à quelle heure avons nous abordé ces sujets?
```

### Détails d'Implémentation

- **Limite** : 20 derniers messages (configurable)
- **Format date** : `15 oct à 3h08` (jour + mois abrégé + heure)
- **Aperçu message** : 80 premiers caractères (+ "..." si tronqué)
- **Rôles affichés** : `user` (Toi) et `assistant` (Nom de l'agent)
- **Injection** : Section "🔗 Connexions avec discussions passées" dans le prompt système

---

## 🔍 Détection des Questions Temporelles

### Patterns Reconnus

**Français** :
- "quand"
- "quel jour"
- "quelle heure"
- "à quelle heure"
- "quelle date"
- "horodatage"

**Anglais** :
- "when"
- "what time"
- "what day"
- "date"
- "timestamp"

### Exemples de Questions Détectées

✅ Détecté :
- "Quand avons-nous parlé de CI/CD ?"
- "Quel jour avons-nous abordé ce sujet ?"
- "À quelle heure a-t-on discuté de cela ?"
- "Quelle date pour cette conversation ?"

❌ Non détecté (questions générales, pas temporelles) :
- "De quoi avons-nous parlé ?"
- "Peux-tu résumer nos discussions ?"
- "Quels sujets avons-nous abordés ?"

---

## 🧪 Tests Requis

### Test 1 : Question Temporelle Simple

**Action** :
```
User: "Quand avons-nous parlé de [sujet] ?"
```

**Résultat attendu** :
- Log backend : `[TemporalQuery] Contexte historique enrichi pour question temporelle`
- Réponse Anima : Inclut date et heure précises ("le 15 octobre à 3h08")

### Test 2 : Question sur Plusieurs Sujets

**Action** :
```
User: "Quels sujets avons-nous abordés cette semaine ?"
User: "Quel jour et à quelle heure avons-nous abordé ces sujets ?"
```

**Résultat attendu** :
- Première réponse : Liste des sujets (comportement existant)
- Deuxième réponse : Dates et heures précises pour chaque sujet

### Test 3 : Formats Temporels Variés

**Actions** :
```
User: "À quelle heure on a parlé de X ?"
User: "Quelle date pour cette discussion ?"
User: "When did we discuss Y?"
```

**Résultat attendu** :
- Toutes les questions déclenchent l'enrichissement temporel
- Réponses cohérentes avec timestamps

### Test 4 : Gardener Consolidation

**Action** :
```
POST /api/memory/tend-garden
```

**Résultat attendu** :
- Pas d'erreur "user_id est obligatoire pour accéder aux threads"
- Consolidation réussie
- Log : `[MemoryGardener] Consolidation réussie pour thread XXX`

---

## 📝 Logs à Surveiller

### Logs Positifs

```
[TemporalQuery] Contexte historique enrichi pour question temporelle
[ConceptRecall] 3 récurrences détectées : ['CI/CD', 'Docker', 'Kubernetes']
```

### Logs d'Erreur

```
[TemporalQuery] Enrichissement historique échoué : <erreur>
[MemoryGardener] Erreur consolidation thread XXX: user_id est obligatoire
```

---

## 🚀 Prochaines Étapes

### Phase de Test (Prochaine Instance)

1. **Tests Fonctionnels** :
   - [ ] Tester questions temporelles (FR/EN)
   - [ ] Vérifier précision des timestamps dans les réponses
   - [ ] Tester avec différents agents (Anima, Neo, Nexus)
   - [ ] Vérifier consolidation mémoire fonctionne sans erreur

2. **Tests de Performance** :
   - [ ] Mesurer impact sur temps de réponse (récupération 20 messages)
   - [ ] Vérifier pas de surcharge mémoire
   - [ ] Tester avec threads longs (100+ messages)

3. **Corrections Potentielles** :
   - [ ] Ajuster limite de messages si nécessaire (20 → 30 ou 10)
   - [ ] Améliorer regex détection si faux positifs/négatifs
   - [ ] Optimiser formatage pour threads très longs
   - [ ] Ajouter cache si appels répétés

### Améliorations Futures

1. **Groupement Thématique** :
   - Grouper les messages par sujet/thème plutôt que chronologique
   - Utiliser embeddings pour détecter changements de sujet

2. **Résumé Temporel Intelligent** :
   - Si plus de 20 messages, résumer les plus anciens
   - Garder les 5-10 plus récents en détail

3. **Support Multi-Thread** :
   - Si question porte sur plusieurs conversations
   - Chercher dans plusieurs threads de l'utilisateur

4. **Métriques Prometheus** :
   - Compteur de questions temporelles détectées
   - Histogram temps récupération contexte
   - Gauge taille moyenne du contexte temporel

---

## 📚 Références

### Fichiers Modifiés

- [service.py](../../src/backend/features/chat/service.py) - ChatService avec détection temporelle
- [gardener.py](../../src/backend/features/memory/gardener.py) - MemoryGardener fix user_id
- [CHANGELOG.md](../../CHANGELOG.md) - Documentation des changements

### Documentation Connexe

- [CONCEPT_RECALL.md](./CONCEPT_RECALL.md) - Système de rappel conceptuel
- [anima_system_v2.md](../../prompts/anima_system_v2.md) - Prompt système Anima avec instructions mémoire temporelle

### Issues & Tickets

- Issue initiale : "Anima ne peut pas répondre aux questions temporelles"
- Fix : Enrichissement proactif du contexte pour questions temporelles
- Ticket connexe : "Erreur gardener user_id obligatoire"

---

## 🤝 Contributeurs

- Claude Code (Anthropic) - Implémentation et documentation
- Équipe Emergence - Tests et validation

---

**Dernière mise à jour** : 2025-10-15
**Version** : 1.0
**Statut** : ✅ Prêt pour tests
