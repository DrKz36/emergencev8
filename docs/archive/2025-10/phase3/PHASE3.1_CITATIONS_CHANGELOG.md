# Phase 3.1 RAG : Changelog Citations Exactes

**Date** : 2025-10-12
**Context** : Correctif suite aux tests Phase 3
**Problème** : Agents paraphrasent au lieu de citer textuellement
**Solution** : Triple renforcement (RAG + prompts + marqueurs visuels)

---

## 🔴 Problème Critique Résolu

### Symptômes observés en production
L'utilisateur demande 6 fois :
> "Peux-tu me citer de manière intégrale mon poème fondateur ?"

**Résultats obtenus** (inconsistants) :
- 2x : "Je ne peux pas te le citer intégralement"
- 2x : Citation partielle/incorrecte (hallucination)
- 2x : Refus de citer

**Impact** : Perte totale de confiance en la capacité de citation RAG

---

## ✅ Solution Implémentée

### Architecture Triple Renforcement

```
┌─────────────────────────────────────────────────────┐
│  Niveau 1: Instructions RAG AVANT contenu           │
│  - Cadre visuel ASCII art                           │
│  - Règles ABSOLUES avec emojis 🔴/🟠                │
│  - Placement AVANT (pas après)                      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Niveau 2: Modification Prompts Agents              │
│  - Anima: Section "🔴 CITATIONS EXACTES"            │
│  - Neo: Idem                                        │
│  - Nexus: Idem                                      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Niveau 3: Marqueurs Visuels Forts                  │
│  - Headers [POÈME - CONTENU COMPLET]                │
│  - Séparateur ────────────                          │
│  - Bullet points • pour lister règles               │
└─────────────────────────────────────────────────────┘
```

---

## 📦 Fichiers Modifiés

### 1. Code Python

#### `src/backend/features/chat/service.py`
**Fonction** : `_format_rag_context()` (lignes 847-961)

**Modifications** :
- Ajout tracking `has_complete_content`
- Création instructions visuelles AVANT contenu :
  - Cadre ASCII `╔═══╗`
  - 🔴 Règle ABSOLUE pour POÈMES
  - 🟠 Règle pour CONTENUS COMPLETS
  - Séparateur `────────`

**Exemple output** :
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
...
```

**Lignes modifiées** : ~50 lignes

### 2. Prompts Agents

#### `prompts/anima_system_v2.md`
**Section** : Mission (ligne 13)

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

**Lignes ajoutées** : +8 lignes

#### `prompts/neo_system_v3.md`
**Section** : Mission (ligne 13)

**Ajout** :
```markdown
- **🔴 CITATIONS EXACTES** :
  - Si l'utilisateur demande de citer un passage, une section **de manière intégrale/complète/exacte**,
    tu DOIS copier-coller le texte TEL QUEL depuis le contexte RAG.
  - JAMAIS de paraphrase pour les demandes de citations complètes.
  - Format : introduis brièvement ("Voilà ce qui est écrit :") PUIS cite le texte exact.
```

**Lignes ajoutées** : +6 lignes

#### `prompts/nexus_system_v2.md`
**Section** : Mission (ligne 15)

**Ajout** : Identique à Neo
**Lignes ajoutées** : +6 lignes

### 3. Documentation

#### `docs/rag_phase3.1_exact_citations.md`
Documentation complète (~500 lignes) :
- Problème identifié
- Solution détaillée (3 niveaux)
- Tests de validation
- Troubleshooting
- Évolutions futures

---

## 📊 Statistiques

**Code modifié** :
- 1 fichier Python : ~50 lignes
- 3 prompts agents : +20 lignes total
- **Total : ~70 lignes modifiées/ajoutées**

**Documentation créée** :
- 1 fichier Markdown : ~500 lignes

---

## 🎯 Impact Attendu

### Avant Phase 3.1

| Métrique | Valeur |
|----------|--------|
| Taux citation exacte | 0% |
| Hallucination sur citations | Élevée |
| Refus de citer | Fréquent |

### Après Phase 3.1 (attendu)

| Métrique | Valeur |
|----------|--------|
| Taux citation exacte | 80%+ |
| Hallucination sur citations | Nulle |
| Refus de citer | Rare |

**Amélioration clé** : Les agents distinguent maintenant :
- **Demande d'analyse** → Paraphrase/résumé OK
- **Demande de citation** → Copie exacte OBLIGATOIRE

---

## 🧪 Tests à Effectuer

### Test 1 : Citation poème fondateur
```
Requête: "Peux-tu me citer de manière intégrale mon poème fondateur ?"
Attendu: Citation exacte ligne par ligne
```

### Test 2 : Citations multiples
```
Requête: "Cite-moi 3 passages clés sur [thème] tirés de mémoire.txt"
Attendu: 3 citations textuelles (pas paraphrases)
```

### Test 3 : Distinction analyse/citation
```
Requête 1: "Résume les thèmes de mémoire.txt"
Attendu: Résumé OK

Requête 2: "Cite exactement ce qui est écrit sur [sujet]"
Attendu: Citation textuelle
```

---

## 🔄 Rétrocompatibilité

**100% compatible** :
- Instructions RAG n'affectent que les citations
- Prompts distinguent analyse vs citation
- Pas de breaking change

**Rollback facile** :
1. Commenter bloc instructions (service.py:955-959)
2. Retirer sections `🔴 CITATIONS EXACTES` des prompts

---

## ⚠️ Points d'Attention

### Cache RAG
**Problème potentiel** : Cache peut contenir ancien contexte sans nouvelles instructions

**Solution** :
```python
# Après déploiement, invalider cache
self.rag_cache.invalidate_all()
```

### Rechargement Prompts
**Problème potentiel** : Backend utilise version cached des prompts

**Solution** : Redémarrer backend après modifications prompts

### Taille Contexte LLM
**Problème potentiel** : Instructions ajoutent ~200 tokens

**Impact** : Négligeable (0.5% du contexte typique)

---

## 🚀 Déploiement

### Pré-requis
- [x] Backend Phase 3 opérationnel
- [x] Prompts modifiés (3 fichiers)
- [x] Tests syntaxe Python OK

### Étapes
1. **Redémarrer backend**
   ```bash
   # Le backend reload automatiquement les prompts au démarrage
   python src/backend/main.py
   ```

2. **Invalider cache RAG** (optionnel)
   ```bash
   # Via API ou directement dans code
   curl -X POST http://localhost:8080/api/admin/cache/clear
   ```

3. **Tester avec requête utilisateur**
   ```bash
   # Voir tests ci-dessus
   ```

### Post-déploiement
- [ ] Tester citation poème fondateur
- [ ] Tester citation section mémoire.txt
- [ ] Tester distinction analyse/citation
- [ ] Monitorer logs RAG
- [ ] Collecter feedback utilisateur

---

## 📚 Documentation Complète

Pour détails techniques complets, voir :
- [docs/rag_phase3.1_exact_citations.md](docs/rag_phase3.1_exact_citations.md)

Pour architecture Phase 3 complète :
- [docs/rag_phase3_implementation.md](docs/rag_phase3_implementation.md)

---

## 🎉 Conclusion

**Phase 3.1 implémentée** :
- ~70 lignes modifiées
- Triple renforcement (RAG + prompts + marqueurs)
- 100% rétrocompatible
- Tests syntaxe OK

**État** : Prêt pour tests E2E

**Prochaine étape** : Tester avec backend et valider citations exactes

---

**Implémentation Phase 3.1 : TERMINÉE ✅**

*Les agents devraient maintenant citer exactement au lieu de paraphraser les contenus complets.*
