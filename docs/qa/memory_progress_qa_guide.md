# Guide QA - Barre de Progression Mémoire
**Feature:** Feedback temps réel consolidation mémoire
**Version:** V3.8 (2025-10-15)
**Temps estimé:** 15 minutes

---

## 📋 Objectifs du Test

Valider que la barre de progression de consolidation mémoire :
1. ✅ S'affiche correctement pendant l'analyse
2. ✅ Affiche les bonnes phases traduites en français
3. ✅ Compte les sessions correctement (X/Y)
4. ✅ Affiche le message final avec résumé
5. ✅ Se masque automatiquement après 3 secondes
6. ✅ Gère les erreurs gracieusement

---

## 🛠️ Prérequis

### Backend
- Backend démarré : `npm run backend` ou `uvicorn`
- Port : `http://localhost:8000`
- ChromaDB actif et accessible
- Clés API LLM configurées (Google/Anthropic/OpenAI)

### Frontend
- Build récent : `npm run build`
- CSS importé : `src/frontend/features/memory/memory.css`
- WebSocket connecté

### Données de Test
- Créer 3-5 conversations avec 10+ messages chacune
- OU utiliser script : `scripts/qa/seed_test_conversations.ps1` (si disponible)

---

## 🧪 Scénarios de Test

### Test 1 : Consolidation Session Unique

**Objectif** : Vérifier barre progression pour 1 seule session

**Étapes** :
1. Créer une conversation avec 15 messages
2. Aller dans **Centre Mémoire** (menu principal)
3. Cliquer sur **"Consolider mémoire"**

**Vérifications** :
- [ ] Barre de progression apparaît immédiatement
- [ ] Texte affiché : "Extraction des concepts... (1/1 sessions)"
- [ ] Barre se remplit progressivement (animation fluide)
- [ ] Pas d'erreur console (F12)
- [ ] Message final : "✓ Consolidation terminée : 1 session, X nouveaux items"
- [ ] Barre se masque après 3 secondes
- [ ] Compteur LTM augmente (carte LTM)

**Durée attendue** : 20-40 secondes

**Résultat attendu** : ✅ PASS si toutes les vérifications cochées

---

### Test 2 : Consolidation Multiple Sessions

**Objectif** : Vérifier progression incrémentale (X/Y)

**Étapes** :
1. Créer 3 conversations distinctes (10 messages chacune)
2. Aller dans **Centre Mémoire**
3. Cliquer sur **"Consolider mémoire"**

**Vérifications** :
- [ ] Barre apparaît avec "(1/3 sessions)"
- [ ] Texte change : "(1/3)" → "(2/3)" → "(3/3)"
- [ ] Barre se remplit : 33% → 66% → 100%
- [ ] Phases affichées (au moins une) :
  - [ ] "Extraction des concepts..."
  - [ ] "Analyse des préférences..." (optionnel)
  - [ ] "Vectorisation des connaissances..." (optionnel)
- [ ] Message final : "✓ Consolidation terminée : 3 sessions, X nouveaux items"
- [ ] Durée cohérente (~60-90 secondes pour 3 sessions)

**Durée attendue** : 60-120 secondes

**Résultat attendu** : ✅ PASS si progression incrémentale visible

---

### Test 3 : Bouton Désactivé Pendant Analyse

**Objectif** : Éviter double-clic pendant consolidation

**Étapes** :
1. Aller dans **Centre Mémoire**
2. Cliquer sur **"Consolider mémoire"**
3. **Immédiatement** essayer de re-cliquer le bouton

**Vérifications** :
- [ ] Bouton désactivé (grisé, `disabled="true"`)
- [ ] Texte bouton change : "Consolider mémoire" → "Consolidation..."
- [ ] Aucun événement déclenché au 2e clic
- [ ] Bouton redevient actif après consolidation
- [ ] Texte revient : "Consolidation..." → "Consolider mémoire"

**Résultat attendu** : ✅ PASS si bouton correctement désactivé

---

### Test 4 : Tooltip Explicatif

**Objectif** : Vérifier tooltip au survol bouton

**Étapes** :
1. Aller dans **Centre Mémoire**
2. **Survoler** (hover) le bouton "Consolider mémoire"
3. Attendre 1 seconde

**Vérifications** :
- [ ] Tooltip apparaît
- [ ] Texte affiché : "Extrait concepts, préférences et faits structurés des conversations récentes"
- [ ] Tooltip bien positionné (au-dessus du bouton, centré)
- [ ] Tooltip disparaît quand on retire la souris
- [ ] Pas de collision avec autres éléments UI

**Note** : Sur mobile, tooltip peut être masqué (CSS media query)

**Résultat attendu** : ✅ PASS si tooltip visible et correct

---

### Test 5 : Gestion Erreur LLM

**Objectif** : Vérifier comportement si analyse échoue

**Préparation** :
- Désactiver temporairement clés API (`.env`) :
  ```bash
  GOOGLE_API_KEY=""
  ANTHROPIC_API_KEY=""
  OPENAI_API_KEY=""
  ```
- Redémarrer backend

**Étapes** :
1. Créer une conversation avec 10 messages
2. Aller dans **Centre Mémoire**
3. Cliquer sur **"Consolider mémoire"**

**Vérifications** :
- [ ] Barre de progression démarre normalement
- [ ] Erreur détectée côté backend (logs)
- [ ] Barre disparaît (ou affiche état erreur)
- [ ] Toast d'erreur affiché : "Analyse mémoire : échec"
- [ ] Bouton "Réessayer" disponible dans le toast
- [ ] Clic "Réessayer" relance consolidation
- [ ] Pas de crash frontend

**Restauration** :
- Réactiver clés API
- Redémarrer backend

**Résultat attendu** : ✅ PASS si erreur gérée gracieusement

---

### Test 6 : Consolidation Vide (Aucune Session)

**Objectif** : Vérifier comportement si aucune session à consolider

**Préparation** :
- Effacer toute la mémoire (bouton "Effacer")
- OU utiliser base de données vide

**Étapes** :
1. Aller dans **Centre Mémoire**
2. Vérifier compteurs : STM=Vide, LTM=0
3. Cliquer sur **"Consolider mémoire"**

**Vérifications** :
- [ ] Pas de barre de progression (ou disparaît immédiatement)
- [ ] Toast informatif : "Aucune session à consolider" (optionnel)
- [ ] Aucune erreur console
- [ ] Compteurs restent inchangés

**Résultat attendu** : ✅ PASS si comportement cohérent

---

### Test 7 : Responsive Mobile

**Objectif** : Vérifier affichage mobile

**Étapes** :
1. Ouvrir DevTools (F12)
2. Activer mode responsive (Ctrl+Shift+M)
3. Sélectionner "iPhone 12" ou "Galaxy S20"
4. Aller dans **Centre Mémoire**
5. Cliquer sur **"Consolider mémoire"**

**Vérifications** :
- [ ] Barre de progression visible et adaptée
- [ ] Texte lisible (pas tronqué)
- [ ] Pas de débordement horizontal
- [ ] Bouton cliquable (zone tactile suffisante)
- [ ] Tooltip masqué (média query @768px)
- [ ] Animation fluide (pas de lag)

**Résultat attendu** : ✅ PASS si UI responsive

---

### Test 8 : WebSocket Connexion/Déconnexion

**Objectif** : Vérifier robustesse si WebSocket se déconnecte

**Préparation** :
- Ouvrir DevTools → Network
- Filtrer sur "WS" (WebSocket)

**Étapes** :
1. Démarrer consolidation
2. **Pendant l'exécution**, couper le backend (Ctrl+C)
3. Observer le comportement

**Vérifications** :
- [ ] Barre progression "freeze" (ne se met plus à jour)
- [ ] Timeout après 30-60s (optionnel)
- [ ] Message erreur : "Connexion perdue"
- [ ] Bouton reste cliquable après reconnexion
- [ ] Relancer backend → Retry fonctionne

**Résultat attendu** : ✅ PASS si pas de crash, erreur claire

---

### Test 9 : Consolidation Successive

**Objectif** : Vérifier qu'on peut lancer plusieurs consolidations

**Étapes** :
1. Créer 2 conversations
2. Consolider (attendre fin)
3. Créer 2 nouvelles conversations
4. Re-consolider immédiatement

**Vérifications** :
- [ ] 1ère consolidation : "✓ ... 2 sessions, X items"
- [ ] 2e consolidation : "✓ ... 2 sessions, Y items"
- [ ] Compteur LTM augmente à chaque fois
- [ ] Pas de duplication (items X + Y ≈ LTM total)
- [ ] Pas de fuite mémoire (observer RAM dans Task Manager)

**Résultat attendu** : ✅ PASS si consolidations successives OK

---

### Test 10 : Performances (Stress Test)

**Objectif** : Vérifier comportement avec volume important

**Préparation** :
- Créer 10 conversations avec 20 messages chacune
- OU utiliser script seed : `scripts/qa/seed_large_dataset.ps1`

**Étapes** :
1. Aller dans **Centre Mémoire**
2. Cliquer sur **"Consolider mémoire"**
3. Observer progression

**Vérifications** :
- [ ] Barre progression fluide (pas de saccades)
- [ ] Durée totale < 5 minutes
- [ ] RAM backend stable (<500 MB increase)
- [ ] Pas de timeout WebSocket
- [ ] Message final correct : "10 sessions, X items"
- [ ] Frontend responsive (UI pas gelée)

**Durée attendue** : 2-5 minutes pour 10 sessions

**Résultat attendu** : ✅ PASS si performances acceptables

---

## 📊 Tableau Récapitulatif

| Test | Description | Durée | Criticité | Résultat |
|------|-------------|-------|-----------|----------|
| Test 1 | Session unique | 1 min | 🔴 Haute | ☐ PASS / ☐ FAIL |
| Test 2 | Multiple sessions | 2 min | 🔴 Haute | ☐ PASS / ☐ FAIL |
| Test 3 | Bouton désactivé | 1 min | 🟡 Moyenne | ☐ PASS / ☐ FAIL |
| Test 4 | Tooltip | 30s | 🟢 Basse | ☐ PASS / ☐ FAIL |
| Test 5 | Gestion erreur | 3 min | 🔴 Haute | ☐ PASS / ☐ FAIL |
| Test 6 | Consolidation vide | 1 min | 🟡 Moyenne | ☐ PASS / ☐ FAIL |
| Test 7 | Responsive mobile | 2 min | 🟡 Moyenne | ☐ PASS / ☐ FAIL |
| Test 8 | WebSocket perte | 3 min | 🔴 Haute | ☐ PASS / ☐ FAIL |
| Test 9 | Consolidations successives | 3 min | 🟡 Moyenne | ☐ PASS / ☐ FAIL |
| Test 10 | Performances (stress) | 5 min | 🟡 Moyenne | ☐ PASS / ☐ FAIL |

**Total** : ~22 minutes

---

## 🐛 Bugs Connus / Limitations

### Pas encore implémentés (Roadmap Phase 2)

- [ ] Annulation consolidation en cours
- [ ] Estimation temps restant (ETA)
- [ ] Phases détaillées (extraction vs vectorisation vs sauvegarde)
- [ ] Notifications push navigateur
- [ ] Historique consolidations (journal avec timestamps)

### Comportements Attendus (Pas des bugs)

- **Pas de notification** si toutes sessions déjà consolidées
- **Fallback LLM** peut prendre 30s par provider (timeout)
- **Barre 0%** pendant 2-3s au début (initialisation)
- **Phases pas toujours affichées** : dépend du timing WebSocket

---

## 🔍 Logs à Vérifier

### Frontend (Console F12)

**Événements WebSocket attendus** :
```
ws:memory_progress {current: 1, total: 3, phase: "extracting_concepts", status: "in_progress"}
ws:memory_progress {current: 2, total: 3, ...}
ws:memory_progress {current: 3, total: 3, ...}
ws:memory_progress {status: "completed", consolidated_sessions: 3, new_items: 23}
```

**Erreurs à surveiller** :
- `TypeError: Cannot read property 'progress' of null`
- `WebSocket connection failed`
- `Failed to fetch /api/memory/tend-garden`

### Backend (Logs Uvicorn)

**Logs attendus** :
```
INFO:     [memory:garden:start] Starting consolidation...
INFO:     [memory:garden:done] {consolidated_sessions: 3, new_concepts: 23}
INFO:     ws:memory_progress sent to session_123
```

**Erreurs critiques** :
- `TimeoutError: LLM call exceeded 30s`
- `ChromaDB connection failed`
- `Session not found`

---

## 📝 Rapport de Test

**Date** : ___________
**Testeur** : ___________
**Environnement** : ☐ Local ☐ Staging ☐ Production
**Version** : V3.8

### Résumé

- Tests PASS : _____ / 10
- Tests FAIL : _____ / 10
- Criticité haute FAIL : _____ / 4

### Bugs Identifiés

| Bug | Sévérité | Description | Étapes Reproduction |
|-----|----------|-------------|---------------------|
| #1 | 🔴 / 🟡 / 🟢 | | |
| #2 | 🔴 / 🟡 / 🟢 | | |
| #3 | 🔴 / 🟡 / 🟢 | | |

### Recommandations

- ☐ **Prêt pour déploiement** (tous tests PASS)
- ☐ **Déploiement avec réserves** (bugs 🟡 identifiés)
- ☐ **Bloquer déploiement** (bugs 🔴 critiques)

---

## 🚀 Checklist Pré-Déploiement

Avant de merger la feature en `main` :

- [ ] Tous tests haute criticité PASS
- [ ] Responsive mobile validé
- [ ] Gestion erreur validée
- [ ] Tooltip présent et correct
- [ ] CSS `memory.css` importé dans bundle
- [ ] WebSocket événement `ws:memory_progress` documenté dans API
- [ ] Changelog mis à jour
- [ ] Capture d'écran barre progression ajoutée dans `docs/assets/memoire/`

---

**Créé le** : 2025-10-15
**Dernière révision** : 2025-10-15
**Statut** : ✅ Prêt pour QA
