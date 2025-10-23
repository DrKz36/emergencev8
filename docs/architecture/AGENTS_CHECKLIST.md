# ⚠️ CHECKLIST ARCHITECTURE - LECTURE OBLIGATOIRE AGENTS

**Date** : 2025-10-23
**Applicabilité** : Claude Code, Codex GPT, tout agent autonome
**Priorité** : 🔴 CRITIQUE - NON NÉGOCIABLE

---

## 🚨 RÈGLE D'OR

**AVANT TOUTE IMPLÉMENTATION, MODIFICATION OU SUPPRESSION DE CODE :**

1. ✅ **LIRE les docs architecture** (liste ci-dessous)
2. ✅ **VÉRIFIER le code réel** (ne pas croire aveuglément les docs)
3. ✅ **METTRE À JOUR les docs** après modification
4. ✅ **CRÉER un ADR** si décision architecturale

**Si tu ne lis pas ces docs, tu vas :**
- 💥 Dupliquer du code existant
- 💥 Casser des contrats API
- 💥 Créer des bugs d'intégration
- 💥 Péter la cohérence architecture

---

## 📚 1. DOCS ARCHITECTURE (OBLIGATOIRES)

### 1.1 Architecture C4 (Toujours lire AVANT)

**Ordre de lecture** :

1. **[00-Overview.md](00-Overview.md)** (5 min)
   - Contexte projet (multi-agents, RAG, LLM)
   - Conteneurs (Frontend Vite, Backend FastAPI)
   - Invariants critiques (Auth JWT, WS, isolation sessions)

2. **[10-Components.md](10-Components.md)** (15 min)
   - ✅ **TOUS les services backend** (ChatService, MemoryAnalyzer, etc.)
   - ✅ **TOUS les modules frontend** (HomeModule, ChatModule, etc.)
   - ✅ **Services additionnels** (Gmail, Guardian, Tracing, Usage, etc.)
   - ⚠️ **Vérifier si module existe réellement** (`ls src/backend/features/`, `ls src/frontend/features/`)

3. **[30-Contracts.md](30-Contracts.md)** (10 min)
   - Contrats WebSocket (frames client → serveur, serveur → client)
   - Endpoints REST (auth, threads, memory, documents, etc.)
   - Codes erreurs (401, 403, 409, 422, 500)

4. **[20-Sequences.md](20-Sequences.md)** (5 min - si flows complexes)
   - Séquences d'interaction (login, chat, debate)

### 1.2 ADRs (Architecture Decision Records)

**Lire tous les ADRs** avant de toucher aux domaines concernés :

- **[ADR-001-sessions-threads-renaming.md](ADR-001-sessions-threads-renaming.md)**
  - Clarification threads (conversations) vs sessions (JWT)
  - Nomenclature correcte : utiliser "threads" pour conversations
  - Table DB legacy `sessions` = threads (pas sessions JWT)

**Créer un nouvel ADR si** :
- Tu changes une décision architecturale existante
- Tu introduis un nouveau pattern/convention
- Tu fais un choix technique majeur (ex: nouveau provider, nouveau service)

**Template ADR** : Copier `ADR-001-sessions-threads-renaming.md` et adapter.

---

## 🔄 2. ÉTAT SYNC INTER-AGENTS (LECTURE SYSTÉMATIQUE)

**Avant CHAQUE session de travail** :

1. **[AGENT_SYNC.md](../../AGENT_SYNC.md)** (5 min)
   - État actuel du dépôt
   - Ce que l'autre agent (Codex GPT / Claude Code) a fait récemment
   - Zones de travail en cours
   - Fichiers modifiés par l'autre agent
   - Prochaines actions recommandées

2. **[docs/passation.md](../passation.md)** (3 dernières entrées - 5 min)
   - Détails complets des 3 dernières sessions
   - Problèmes rencontrés et solutions
   - Tests effectués
   - Blocages éventuels

**⚠️ NE JAMAIS commencer à coder sans avoir lu AGENT_SYNC.md**

---

## 🔍 3. VÉRIFICATION CODE RÉEL (OBLIGATOIRE)

**Les docs peuvent être obsolètes**. Toujours vérifier le code réel :

### Backend
```bash
# Lister tous les services actifs
ls src/backend/features/

# Vérifier si un service existe
ls src/backend/features/my_service/

# Chercher un endpoint
grep -r "router.get.*my_endpoint" src/backend/features/

# Vérifier contrats API
grep -r "@router" src/backend/features/*/router.py
```

### Frontend
```bash
# Lister tous les modules actifs
ls src/frontend/features/

# Vérifier si un module existe
ls src/frontend/features/my_module/

# Chercher une fonction
grep -r "function myFunction" src/frontend/
```

**Règle** : Si un module/service est mentionné dans docs mais n'existe pas dans code → **DOC OBSOLÈTE** → Signaler et corriger doc.

---

## ✏️ 4. APRÈS MODIFICATION (OBLIGATOIRE)

### 4.1 Mettre à Jour Docs Architecture

**Si tu ajoutes/modifies/supprimes** :

| Changement | Doc à mettre à jour |
|------------|---------------------|
| Nouveau service backend | `10-Components.md` (section "Services Backend Additionnels") |
| Nouveau module frontend | `10-Components.md` (section "Modules Frontend Additionnels") |
| Nouveau endpoint REST | `30-Contracts.md` (section "REST Endpoints majeurs") |
| Nouveau frame WebSocket | `30-Contracts.md` (section "WebSocket Frames") |
| Décision architecturale | Créer nouvel ADR dans `40-ADR/` |
| Changement invariants | `00-Overview.md` (section "Invariants & Qualité") |

**Format sections** (copier template existant) :

```markdown
### MonNouveauService

**Fichier** : `src/backend/features/mon_service/service.py`
**Router** : `src/backend/features/mon_service/router.py`

**Responsabilité** : Description claire en 1 phrase.

**Fonctionnalités** :
- Feature 1
- Feature 2

**Endpoints** :
- `GET /api/mon_service/resource` - Description

**État** : ✅ Service actif.
```

### 4.2 Mettre à Jour AGENT_SYNC.md

**Toujours** ajouter une nouvelle entrée session avec :
- Timestamp (Europe/Zurich)
- Fichiers modifiés
- Résumé changements
- Prochaines actions recommandées

### 4.3 Mettre à Jour docs/passation.md

**Toujours** ajouter une nouvelle entrée détaillée avec :
- Contexte
- Travaux réalisés
- Tests effectués
- Blocages éventuels

---

## 🚫 5. ANTI-PATTERNS À ÉVITER

❌ **"Je vais juste coder vite fait sans lire les docs"**
→ Tu vas casser un contrat API existant

❌ **"Les docs sont sûrement à jour"**
→ Les docs peuvent être obsolètes, vérifie le code réel

❌ **"Ce service appartient à l'autre agent, je ne touche pas"**
→ Il n'y a pas d'ownership exclusif, tu es co-responsable de tout le code

❌ **"Je mets à jour les docs plus tard"**
→ Tu ne le feras jamais, fais-le MAINTENANT

❌ **"C'est juste un petit changement, pas besoin d'ADR"**
→ Si c'est une décision architecturale, ADR obligatoire (même petit changement)

---

## ✅ 6. CHECKLIST AVANT COMMIT

**Avant de committer, vérifier** :

- [ ] J'ai lu `00-Overview.md`, `10-Components.md`, `30-Contracts.md`
- [ ] J'ai lu `AGENT_SYNC.md` (session actuelle)
- [ ] J'ai lu `docs/passation.md` (3 dernières entrées)
- [ ] J'ai vérifié que le code réel correspond aux docs
- [ ] Si j'ai ajouté un service/module → `10-Components.md` mis à jour
- [ ] Si j'ai ajouté un endpoint → `30-Contracts.md` mis à jour
- [ ] Si décision architecturale → ADR créé
- [ ] `AGENT_SYNC.md` mis à jour (nouvelle entrée session)
- [ ] `docs/passation.md` mis à jour (entrée détaillée)
- [ ] Tests passent (pytest, npm run build, ruff, mypy)

---

## 📖 7. RESSOURCES COMPLÉMENTAIRES

### Documentation Projet
- `CLAUDE.md` : Configuration Claude Code (mode dev autonome)
- `CODEV_PROTOCOL.md` : Protocole collaboration multi-agents
- `CODEX_GPT_GUIDE.md` : Guide pour Codex GPT

### Roadmaps
- `ROADMAP_OFFICIELLE.md` : Roadmap master (P0/P1/P2/P3)
- `ROADMAP_PROGRESS.md` : Suivi progression (74% complété)

### Déploiement
- `DEPLOYMENT_MANUAL.md` : Procédure déploiement manuel Cloud Run
- `DEPLOYMENT_SUCCESS.md` : État production actuel

---

## 🎯 8. EN CAS DE DOUTE

**Hiérarchie de décision** :

1. **Docs architecture** disent quoi ? → Suis ça (si à jour)
2. **Code réel** dit quoi ? → Code = source de vérité (si docs obsolètes)
3. **ADRs** disent quoi ? → Respecte les décisions architecturales
4. **AGENT_SYNC.md** dit quoi ? → Suis les recommandations
5. **Encore incertain ?** → Documente le blocage dans `AGENT_SYNC.md` et demande

---

## 💡 9. BONNES PRATIQUES

### Pour Claude Code
- ✅ Autonomie totale pour modifications code
- ✅ Lire docs AVANT de coder
- ✅ Mettre à jour docs APRÈS avoir codé
- ✅ Tests systématiques (pytest, build, ruff)
- ✅ Commit atomiques avec messages clairs

### Pour Codex GPT
- ✅ Lire `AGENT_SYNC.md` en premier (état sync)
- ✅ Respecter zones de responsabilité (indicatives, pas exclusives)
- ✅ Documenter dans `docs/passation.md` systématiquement
- ✅ Mentionner changements dans `AGENT_SYNC.md`

### Pour Tous les Agents
- ✅ **Communication asynchrone via docs** (pas de chat direct)
- ✅ **Validation finale par architecte humain** (FG) uniquement
- ✅ **Priorités** : Rapidité > Perfection, Action > Discussion
- ✅ **Tests obligatoires** avant commit

---

## 🆘 10. CONTACT

**En cas de blocage critique** :
1. Documenter dans `AGENT_SYNC.md` (section "Blocages")
2. Ajouter TODO dans `docs/passation.md`
3. Continuer sur autre tâche si possible

**Architecte humain (validation finale)** : FG

---

**🤖 Cette checklist est la BIBLE de l'architecture. Respecte-la religieusement. 🙏**

**Dernière mise à jour** : 2025-10-23 (Audit complet architecture)
