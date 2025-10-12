# Phase 3.1 RAG : Citations Exactes Sans Hallucination

**Date** : 2025-10-12
**Context** : Suite à Phase 3 (re-ranking + cache + métriques)
**Problème** : Les agents résument/paraphrasent au lieu de citer textuellement
**Solution** : Triple renforcement (RAG formatting + agent prompts + marqueurs visuels)

---

## 🎯 Problème Identifié

### Symptômes observés
L'utilisateur demande :
> "Peux-tu me citer de manière intégrale mon poème fondateur ?"

**Comportement observé** (Phase 2/3) :
- Anima répond : "Je ne peux pas te le citer intégralement, mais..."
- Anima donne une version partielle/incorrecte
- Anima paraphrase au lieu de copier-coller

**Comportement attendu** :
- Copie exacte du texte depuis le RAG
- Préservation des retours à la ligne
- Aucune modification, aucune hallucination

### Causes root

1. **Instructions RAG faibles** :
   - Instruction placée APRÈS le contenu → ignorée par le LLM
   - Formulation passive : "Lorsqu'on te demande..." vs directive "tu DOIS"
   - Uniquement pour les poèmes, pas les autres types

2. **Prompts agents encouragent paraphrase** :
   - Anima (v2) : "Cite ce qu'il t'apporte (« Les sources montrent… »)"
   - Neo (v3) : "cite ce qu'il démontre"
   - Nexus (v2) : Pas d'instruction pour citations

3. **Pas de marqueurs visuels** :
   - Le LLM ne voit pas clairement qu'il doit COPIER-COLLER
   - Pas de délimiteur fort pour contenus citables

---

## ✅ Solution Implémentée : Triple Renforcement

### Niveau 1 : Instructions RAG AVANT le contenu

**Fichier** : `src/backend/features/chat/service.py`
**Fonction** : `_format_rag_context()` (lignes 847-961)

**Changements** :

#### 1.1 Détection contenus complets
```python
has_complete_content = False

# Tracker contenus complets
if merged_count > 1:
    has_complete_content = True
```

#### 1.2 En-tête visuel avec cadre
```python
if has_complete_content or has_poem:
    instruction_parts.append(
        "╔══════════════════════════════════════════════════════════╗\n"
        "║  INSTRUCTION PRIORITAIRE : CITATIONS TEXTUELLES          ║\n"
        "╚══════════════════════════════════════════════════════════╝"
    )
```

#### 1.3 Règles ABSOLUES pour poèmes
```python
if has_poem:
    instruction_parts.append(
        "\n🔴 RÈGLE ABSOLUE pour les POÈMES :\n"
        "   • Si l'utilisateur demande de citer un poème (intégralement, complet, etc.),\n"
        "     tu DOIS copier-coller le texte EXACT ligne par ligne.\n"
        "   • JAMAIS de paraphrase, JAMAIS de résumé.\n"
        "   • Préserve TOUS les retours à la ligne, la ponctuation, les majuscules.\n"
        "   • Format : introduis brièvement PUIS cite entre guillemets ou en bloc.\n"
    )
```

#### 1.4 Règles pour contenus complets
```python
if has_complete_content:
    instruction_parts.append(
        "\n🟠 RÈGLE pour les CONTENUS COMPLETS :\n"
        "   • Les blocs marqués \"CONTENU COMPLET\" contiennent la version intégrale.\n"
        "   • Pour toute demande de citation (section, conversation, passage),\n"
        "     copie le texte TEL QUEL depuis le bloc correspondant.\n"
        "   • Ne recompose pas, ne synthétise pas : CITE TEXTUELLEMENT.\n"
    )
```

#### 1.5 Placement AVANT le contenu
```python
if instruction_parts:
    instruction_header = "".join(instruction_parts)
    result = f"{instruction_header}\n\n{chr(0x2500) * 60}\n\n{''.join(blocks)}"
```

**Résultat visuel** :
```
╔══════════════════════════════════════════════════════════╗
║  INSTRUCTION PRIORITAIRE : CITATIONS TEXTUELLES          ║
╚══════════════════════════════════════════════════════════╝

🔴 RÈGLE ABSOLUE pour les POÈMES :
   • Si l'utilisateur demande de citer un poème (intégralement, complet, etc.),
     tu DOIS copier-coller le texte EXACT ligne par ligne.
   • JAMAIS de paraphrase, JAMAIS de résumé.
   • Préserve TOUS les retours à la ligne, la ponctuation, les majuscules.
   • Format : introduis brièvement PUIS cite entre guillemets ou en bloc.

────────────────────────────────────────────────────────────

[POÈME - CONTENU COMPLET] (lignes 1-14)
J'ai aperçu l'espoir du lendemain sur mon chemin.
Une sorte de mirage et une promesse à la fois.
...
```

### Niveau 2 : Modification Prompts Agents

#### 2.1 Anima (v2)

**Fichier** : `prompts/anima_system_v2.md`
**Section** : Mission (lignes 13-25)

**Ajout** :
```markdown
- **🔴 CITATIONS EXACTES** :
  - Si l'utilisateur demande de citer un poème, un passage, une section **de manière intégrale/complète/exacte**,
    tu DOIS copier-coller le texte TEL QUEL depuis le contexte RAG.
  - JAMAIS de paraphrase pour les demandes de citations complètes.
  - Format : introduis brièvement ("Voici le poème fondateur :") PUIS cite entre guillemets ou en bloc.
  - Préserve TOUS les retours à la ligne, la ponctuation originale.
- Pour les analyses/discussions : tu peux résumer et paraphraser normalement (« Les sources montrent… », « Le document précise… »).
```

#### 2.2 Neo (v3)

**Fichier** : `prompts/neo_system_v3.md`
**Section** : Mission (lignes 13-22)

**Ajout** :
```markdown
- **🔴 CITATIONS EXACTES** :
  - Si l'utilisateur demande de citer un passage, une section **de manière intégrale/complète/exacte**,
    tu DOIS copier-coller le texte TEL QUEL depuis le contexte RAG.
  - JAMAIS de paraphrase pour les demandes de citations complètes.
  - Format : introduis brièvement ("Voilà ce qui est écrit :") PUIS cite le texte exact.
```

#### 2.3 Nexus (v2)

**Fichier** : `prompts/nexus_system_v2.md`
**Section** : Mission (lignes 15-24)

**Ajout** :
```markdown
- **🔴 CITATIONS EXACTES** :
  - Si l'utilisateur demande de citer un passage, un poème, une section **de manière intégrale/complète/exacte**,
    tu DOIS copier-coller le texte TEL QUEL depuis le contexte RAG.
  - JAMAIS de paraphrase pour les demandes de citations complètes.
  - Format : introduis brièvement ("Voilà ce qui est écrit :") PUIS cite le texte exact.
```

### Niveau 3 : Marqueurs Visuels Forts

**Déjà présent dans Phase 2** :
- Headers `[POÈME - CONTENU COMPLET]`
- Headers `[SECTION - CONTENU COMPLET]`
- Headers `[CONVERSATION - CONTENU COMPLET]`

**Renforcé Phase 3.1** :
- Cadre visuel ASCII art (╔═══╗)
- Emojis 🔴/🟠 pour attirer l'attention
- Séparateur `────────────────` entre instructions et contenu
- Bullet points `•` pour lister les règles

---

## 📊 Impact Attendu

### Avant Phase 3.1

| Requête | Comportement |
|---------|--------------|
| "Cite le poème fondateur intégralement" | "Je ne peux pas" ou paraphrase |
| "Donne-moi le texte exact" | Résumé ou version partielle |
| "Cite-moi la section complète" | Paraphrase |

### Après Phase 3.1

| Requête | Comportement |
|---------|--------------|
| "Cite le poème fondateur intégralement" | Copie-coller exact du poème |
| "Donne-moi le texte exact" | Citation textuelle |
| "Cite-moi la section complète" | Copie du CONTENU COMPLET |

### Métriques de succès

- **Taux de citation exacte** : 0% → 80%+ (attendu)
- **Hallucination** : Présente → Absente (pour citations)
- **Satisfaction utilisateur** : Frustration → Confiance

---

## 🧪 Tests de Validation

### Test 1 : Poème fondateur (complet)

**Requête** :
```
Peux-tu me citer de manière intégrale mon poème fondateur ?
```

**Validation** :
- [ ] L'agent cite le poème ligne par ligne
- [ ] Tous les retours à la ligne sont préservés
- [ ] Ponctuation identique à l'original
- [ ] Aucune modification du texte
- [ ] Pas de résumé, pas de paraphrase

### Test 2 : Section mémoire.txt

**Requête** :
```
Cite-moi 3 passages clés sur le thème "renaissance" tirés de mémoire.txt
```

**Validation** :
- [ ] Citations textuelles (pas paraphrasées)
- [ ] 3 passages distincts
- [ ] Introduits brièvement puis cités
- [ ] Mention des lignes si disponible

### Test 3 : Analyse vs Citation

**Requête 1** (analyse) :
```
Résume-moi les thèmes principaux de mémoire.txt
```
**Comportement attendu** : Résumé/paraphrase OK

**Requête 2** (citation) :
```
Cite exactement ce qui est écrit sur Céline dans mémoire.txt
```
**Comportement attendu** : Citation textuelle

---

## 🔧 Configuration

**Aucune configuration requise** : Les modifications sont automatiquement actives.

### Désactivation possible (si problème)

**Méthode 1** : Retirer instructions RAG
```python
# Dans service.py, ligne 955-959
# Commenter le bloc if instruction_parts:
result = "\n\n".join(blocks)  # Ancien comportement
```

**Méthode 2** : Retirer sections prompts agents
```markdown
# Dans chaque prompt, supprimer bloc "🔴 CITATIONS EXACTES"
```

---

## 🐛 Troubleshooting

### Problème : Agent cite encore incorrectement

**Causes possibles** :
1. **Cache RAG** : Ancien contexte sans nouvelles instructions
   - Solution : Invalider cache `rag_cache.invalidate_all()`

2. **Prompt agent pas rechargé** : Backend utilise ancienne version
   - Solution : Redémarrer backend

3. **LLM ignore instructions** : Trop de contexte, instructions noyées
   - Solution : Réduire `n_results` de 30 à 20

### Problème : Citations trop longues

**Symptôme** : Agent cite 500+ lignes

**Solution** :
- Ajuster `max_blocks` de 10 à 5
- Améliorer découpage sémantique lors de l'indexation

### Problème : Agent refuse de citer

**Symptôme** : "Je ne peux pas citer ce document"

**Cause** : Chunk pas dans top-10, ou pas marqué CONTENU COMPLET

**Solution** :
- Vérifier logs RAG : `[RAG Merge] Top 1: ...`
- Augmenter `n_results` de 30 à 50
- Améliorer keywords dans metadata

---

## 📈 Évolutions Futures (Phase 4)

### Améliorations potentielles

1. **Citations avec références précises** :
   ```
   Selon mémoire.txt (lignes 42-58) :
   "[citation exacte]"
   ```

2. **Validation automatique citations** :
   - Comparer output agent vs texte RAG
   - Métriques Prometheus : `rag_citation_accuracy`

3. **Feedback utilisateur** :
   - Boutons 👍/👎 sur citations
   - Apprendre quelles formulations marchent mieux

4. **Multi-documents** :
   - Citer depuis plusieurs sources
   - Synthèse avec citations entrelacées

---

## 📝 Fichiers Modifiés

**Code** :
- `src/backend/features/chat/service.py` (~50 lignes modifiées)
  - Fonction `_format_rag_context()` : Instructions AVANT contenu

**Prompts** :
- `prompts/anima_system_v2.md` (+8 lignes)
- `prompts/neo_system_v3.md` (+6 lignes)
- `prompts/nexus_system_v2.md` (+6 lignes)

**Documentation** :
- `docs/rag_phase3.1_exact_citations.md` (ce fichier)

**Total modifications** : ~70 lignes

---

## 🎯 Rétrocompatibilité

**100% rétrocompatible** :
- Instructions RAG n'affectent pas les requêtes sans citation
- Prompts agents distinguent analyse vs citation
- Pas de breaking change pour flux existants

**Rollback simple** :
1. Commenter bloc instructions dans `_format_rag_context()`
2. Retirer sections `🔴 CITATIONS EXACTES` des prompts

---

## ✅ Checklist Déploiement

- [x] Modifications code Python
- [x] Modifications prompts agents (3)
- [x] Tests syntaxe Python
- [ ] Tests E2E citations poème
- [ ] Tests E2E citations sections
- [ ] Tests E2E analyse vs citation
- [ ] Validation en production
- [ ] Collecte feedback utilisateur

---

## 🎉 Conclusion

**Phase 3.1 implémentée** avec succès :
- Triple renforcement (RAG + prompts + marqueurs)
- ~70 lignes modifiées
- 100% rétrocompatible
- Prêt pour tests

**Prochaine étape** : Démarrer backend et tester avec vraies requêtes utilisateur.

---

**Implémentation Phase 3.1 : TERMINÉE ✅**

*Les agents devraient maintenant citer exactement au lieu de paraphraser.*
