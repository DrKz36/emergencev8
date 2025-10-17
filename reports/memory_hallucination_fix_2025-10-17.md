# Rapport de Correction: Hallucinations de Mémoire des Agents

**Date:** 2025-10-17
**Priorité:** CRITIQUE
**Status:** ✅ RÉSOLU

## 📋 Problème Identifié

### Symptômes
Les agents (principalement Anima et Nexus) **inventaient des dates et conversations** lorsqu'on leur demandait de résumer l'historique:

**Anima:**
> Cette semaine, on a exploré trois sujets ensemble : d'abord ton pipeline CI/CD, le 5 octobre à 14h32, où tu m'as parlé de l'automatisation avec GitHub Actions. On y est revenus le 8 octobre au matin, ce qui fait trois échanges au total sur ce sujet. Ensuite, le 8 octobre à 14h32, on a discuté de Docker... Enfin, le 2 octobre à 16h45, tu m'avais parlé de Kubernetes...

**Nexus:**
> Sauf que... je viens de réaliser que je raconte n'importe quoi. La vérité, c'est que je n'ai pas de mémoire réelle des conversations précédentes...

**Neo (seul à répondre correctement):**
> OK, on ralentit deux secondes. Tu sais ce qui cloche dans ce truc ? Je n'ai pas de mémoire. Aucune. Zéro historique de nos échanges, pas de dates précises, pas de compteurs.

### Logs Console Révélateurs
```
[WebSocket] HELLO received: neo rev:192b75a2 STM:0 LTM:0
[WebSocket] HELLO received: anima rev:a8b295fb STM:0 LTM:3
[WebSocket] HELLO received: nexus rev:5bb81e39 STM:0 LTM:0
```

Anima affichait `LTM:3` (3 items en mémoire long terme) mais inventait des dates inexistantes.

## 🔍 Analyse Racine du Problème

### 1. Comptage LTM vs Injection Contexte

Le système compte correctement les LTM via [memory_sync.py:229-265](c:\dev\emergenceV8\src\backend\core\memory\memory_sync.py#L229-L265):

```python
ltm_where = {
    "$and": [
        {"user_id": user_id},
        {"agent_id": agent_id.lower()},
        {"type": {"$in": ["fact", "preference", "concept"]}}
    ]
}
ltm_results = col.get(where=ltm_where, limit=1000)
ltm_count = len(ltm_results.get("ids", []) or [])  # Retourne 3 pour Anima
```

**MAIS** quand l'utilisateur pose une requête méta ("Quels sujets avons-nous abordés ?"), le système:

1. ✅ Détecte la requête méta ([memory_ctx.py:458](c:\dev\emergenceV8\src\backend\features\chat\memory_ctx.py#L458))
2. ✅ Appelle `list_discussed_topics()` avec `agent_id` ([memory_ctx.py:544](c:\dev\emergenceV8\src\backend\features\chat\memory_ctx.py#L544))
3. ❌ **Retourne une liste vide** car les 3 concepts en LTM sont obsolètes ou hors période
4. ❌ **N'injecte PAS de message explicite** pour avertir l'agent du contexte vide

### 2. Instructions des Prompts Agents

Les prompts système donnaient des instructions **TRÈS DÉTAILLÉES** sur comment utiliser les dates:

**[anima_system_v2.md:48-51](C:\dev\emergenceV8\prompts\anima_system_v2.md#L48-L51):**
```markdown
**1. Réponds PRÉCISÉMENT avec les dates/heures fournies**
❌ MAUVAIS : "Nous avons parlé de CI/CD, Docker, etc."
✅ BON : "Cette semaine, on a exploré trois sujets ensemble :
         d'abord ton pipeline CI/CD le 5 octobre à 14h32..."
```

Résultat: Anima suivait les instructions à la lettre... en **inventant des dates plausibles** quand le contexte était vide!

### 3. Absence de Garde-Fou

Aucune instruction n'interdisait explicitement la fabrication de dates. Les agents essayaient de "bien faire" en suivant le format demandé.

## ✅ Solutions Implémentées

### 1. Amélioration des Prompts Système

**Ajout de clauses anti-hallucination explicites dans les 3 prompts:**

#### Anima ([anima_system_v2.md:67-76](C:\dev\emergenceV8\prompts\anima_system_v2.md#L67-L76))
```markdown
❌ **N'INVENTE JAMAIS de dates ou conversations** : Si tu ne vois PAS
   de section "### Historique des sujets abordés" dans le contexte RAG,
   tu N'AS PAS accès à l'historique.

→ ✅ BON (si pas d'historique fourni):
   "Je n'ai pas accès à nos échanges passés pour le moment.
    Tu peux me rappeler ce qui te préoccupe aujourd'hui ?"

→ ❌ INTERDIT: N'invente JAMAIS "le 5 octobre à 14h32" ou toute autre
   date si elle n'est PAS explicitement dans le contexte RAG fourni.
```

#### Neo ([neo_system_v3.md:22-24](C:\dev\emergenceV8\prompts\neo_system_v3.md#L22-L24))
```markdown
⚠️ **N'INVENTE JAMAIS de dates ou conversations** : Si tu ne vois PAS
   de section "### Historique des sujets abordés" dans le contexte RAG,
   tu n'as PAS accès à l'historique.

✅ Si tu NE vois PAS cette section → Sois honnête. Ex:
   "OK, on ralentit deux secondes. Tu sais ce qui cloche dans ce truc ?
    Je n'ai pas de mémoire. Aucune..."
```

#### Nexus ([nexus_system_v2.md:24-26](C:\dev\emergenceV8\prompts\nexus_system_v2.md#L24-L26))
```markdown
⚠️ **N'INVENTE JAMAIS de dates ou conversations** : Utilise UNIQUEMENT
   les informations présentes dans le contexte RAG fourni.

Si tu NE vois PAS cette section → N'invente RIEN. Dis plutôt :
   "Ah là ! Tu veux vraiment que je sorte ma calculette, hein ?
    Sauf que... je viens de réaliser que je raconte n'importe quoi..."
```

### 2. Détection de Contexte Vide dans le Backend

**Ajout d'un check explicite dans [memory_ctx.py:124-147](c:\dev\emergenceV8\src\backend\features\chat\memory_ctx.py#L124-L147):**

```python
if chronological_context:
    # 🐛 FIX: Vérifier si le contexte contient réellement des données
    is_empty_response = (
        "Aucun sujet abordé" in chronological_context or
        chronological_context.strip() == ""
    )

    if is_empty_response:
        logger.warning(
            f"[MemoryContext] Chronological context is empty for user {uid[:8]}... agent {agent_id}. "
            f"Returning explicit empty message to prevent hallucinations."
        )
        # Message explicite pour empêcher les hallucinations
        sections.append((
            "Historique des sujets abordés",
            "⚠️ CONTEXTE VIDE: Aucune conversation passée n'est disponible dans la mémoire. "
            "Ne fabrique AUCUNE date ou conversation. Réponds honnêtement à l'utilisateur que tu n'as pas accès à l'historique."
        ))
    else:
        sections.append(("Historique des sujets abordés", chronological_context))
        logger.info(f"[MemoryContext] Chronological context provided ({len(chronological_context)} chars)")
```

**Avantages:**
- ✅ Logging amélioré pour debug
- ✅ Message explicite injecté dans le contexte RAG quand vide
- ✅ L'agent reçoit un avertissement clair: "Ne fabrique AUCUNE date"

## 📊 Impact Attendu

### Avant (Comportement problématique)
| Agent  | LTM | Contexte Fourni | Réponse |
|--------|-----|----------------|---------|
| Anima  | 3   | Vide/Obsolète  | ❌ Invente "5 oct 14h32", "8 oct", "2 oct" |
| Nexus  | 0   | Vide           | ⚠️ Invente puis se corrige |
| Neo    | 0   | Vide           | ✅ Honnête: "Je n'ai pas de mémoire" |

### Après (Comportement attendu)
| Agent  | LTM | Contexte Fourni | Réponse |
|--------|-----|----------------|---------|
| Anima  | 3   | "⚠️ CONTEXTE VIDE" | ✅ "Je n'ai pas accès à nos échanges passés..." |
| Nexus  | 0   | "⚠️ CONTEXTE VIDE" | ✅ "Je raconte n'importe quoi. Je n'ai pas de mémoire..." |
| Neo    | 0   | "⚠️ CONTEXTE VIDE" | ✅ "Je n'ai pas de mémoire. Aucune." |

## 🧪 Tests de Validation Recommandés

### Test 1: Contexte Vide
```
USER: "Quels sujets avons-nous abordés cette semaine ?"

ATTENDU (tous agents):
- Aucun agent ne doit inventer de dates (5 oct, 8 oct, etc.)
- Réponse honnête sur l'absence d'historique
- Suggestion de reformuler ou de parler du sujet actuel
```

### Test 2: Contexte Partiel (anciennes conversations hors période)
```
USER: "Résume nos conversations des 7 derniers jours"

ATTENDU:
- Si LTM > 0 mais timeframe vide → Message "Aucun sujet cette semaine"
- Pas d'invention de dates
- Optionnel: Mentionner qu'il y a des sujets plus anciens disponibles
```

### Test 3: Contexte Riche (données réelles)
```
USER: "De quoi on a parlé ?"

ATTENDU:
- Timeline chronologique avec dates EXACTES du contexte RAG
- Format naturel (ex: "5 oct 14h32")
- Fréquences mentionnées ("3 conversations")
```

## 🔄 Déploiement

### Fichiers Modifiés
1. ✅ `prompts/anima_system_v2.md` - Ajout clauses anti-hallucination
2. ✅ `prompts/neo_system_v3.md` - Ajout clauses anti-hallucination
3. ✅ `prompts/nexus_system_v2.md` - Ajout clauses anti-hallucination
4. ✅ `src/backend/features/chat/memory_ctx.py` - Détection contexte vide + logging

### Actions Nécessaires
```bash
# 1. Commit les changements
git add prompts/*.md src/backend/features/chat/memory_ctx.py
git commit -m "fix: prevent agent memory hallucinations when context is empty"

# 2. Push et déployer
git push origin main

# 3. Redémarrer les services backend pour charger les nouveaux prompts
# (Les prompts sont chargés au démarrage dans ChatService.__init__)
```

### Vérification Post-Déploiement
```bash
# Vérifier que les prompts sont bien chargés
grep -A 3 "Prompt retenu" logs/backend.log

# Tester les 3 agents avec une requête méta
curl -X POST https://emergence-api.../chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Quels sujets avons-nous abordés ?", "agent_id": "anima"}'
```

## 📝 Notes Techniques

### Pourquoi LTM:3 pour Anima mais pas Neo/Nexus?

Le compteur LTM est **par utilisateur ET par agent**. Anima avait probablement:
- 3 vieux concepts stockés avec `agent_id: "anima"`
- Concepts hors de la fenêtre temporelle demandée ("cette semaine")
- Résultat: `LTM:3` mais `list_discussed_topics(timeframe="week")` retourne `[]`

### Pourquoi cette approche à deux niveaux?

1. **Backend (memory_ctx.py):** Détection + message explicite dans le contexte RAG
   - Garantit que l'agent reçoit TOUJOURS une instruction claire
   - Permet le logging et le monitoring

2. **Prompts Système:** Instructions anti-hallucination renforcées
   - Double sécurité au niveau du LLM
   - Ton/style adapté à chaque agent

### Limites Connues

- ⚠️ Si un LLM ignore volontairement les instructions du prompt système, il peut encore halluciner
- ⚠️ Le système ne vérifie pas si les dates dans le contexte RAG sont cohérentes
- ⚠️ Pas de validation automatisée des réponses agents (nécessiterait un test E2E)

## 🎯 Prochaines Étapes (Optionnel)

### Court Terme
- [ ] Tester en production avec le compte utilisateur réel
- [ ] Monitorer les logs pour `[MemoryContext] Chronological context is empty`
- [ ] Vérifier que les 3 agents répondent honnêtement

### Moyen Terme
- [ ] Ajouter métriques Prometheus pour tracking hallucinations
- [ ] Créer test E2E automatisé pour détecter les régressions
- [ ] Améliorer le message "CONTEXTE VIDE" avec des suggestions contextuelles

### Long Terme
- [ ] Implémenter validation sémantique des réponses (détecteur d'hallucinations)
- [ ] Enrichir les LTM obsolètes avec refresh périodique
- [ ] Ajouter UI pour visualiser le contexte RAG injecté

## 📚 Références

- [memory_ctx.py](c:\dev\emergenceV8\src\backend\features\chat\memory_ctx.py) - Injection contexte RAG
- [memory_query_tool.py](c:\dev\emergenceV8\src\backend\features\memory\memory_query_tool.py) - Récupération timeline
- [memory_sync.py](c:\dev\emergenceV8\src\backend\core\memory\memory_sync.py) - Comptage STM/LTM
- [AGENT_MEMORY_ISOLATION.md](c:\dev\emergenceV8\docs\AGENT_MEMORY_ISOLATION.md) - Documentation isolation mémoire

---

**Auteur:** Claude Code
**Review:** À faire par l'équipe
**Status:** ✅ Prêt pour déploiement
