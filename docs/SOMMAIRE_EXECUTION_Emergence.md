# ÉMERGENCE — Sommaire des documents de référence

📌 **Snapshot ARBO-LOCK actif** : `arborescence_synchronisée_20250829.txt`

---

## 1. Vision & Genèse
- **ÉMERGENCE_Genese 120625.pdf**  
  → Document fondateur : philosophie du projet, objectifs initiaux, articulation mémoire multi-agents.

---

## 2. Déploiement & Infrastructure
- **Résumé déploiement Cloud Run (MAJ v4)**  
  → Migration Cloud Run, authentification email + mot de passe (JWT HS256), suppression IAP, endpoints `/api/*` protégés.
  → Page `/dev-auth.html` transformée en outil de login local (email + mot de passe).
  → Prochaines étapes : UX login (erreurs explicites) et audit allowlist/révocation.
- **scripts/seed_admin.py**  
  -> Initialisation admin (email/mot de passe) idempotente; seed aligne sur l'isolation des sessions (`session_id`).

---

## 3. Roadmaps & Stratégie
- **ROADMAP_STRATEGIQUE_EmergenceV8_update.pdf**  
  → Plan V8 : priorités P0 (auth, responsive, branding) → P5 (infra souveraine).  
  → Pré-Beta : ouverture à bêta-testeurs (amis + Boris).  
  → Axes majeurs : RAG multi-docs, persistance multi-tenant, mémoire STM/LTM, cockpit coûts.

- **EMERGENCE_Roadmap_Exec_P0-P1.5_20250829.md**  
  → Plan d’exécution immédiat (2–3 semaines).  
  → **P0** : Auth + WebSocket mobile, fallback Neo, stats docs, quick-wins UI.  
  → **P1** : RAG multi-docs, iso débats.  
  → **P1.5** : persistance cross-device threads/messages (pré-Beta).  
  → **P2** : mémoire progressive (STM/LTM, Jardinier).

---

## 4. Analyse Externe
- **Panorama comparatif des projets similaires à ÉMERGENCE.pdf**  
  → Benchmark (AutoGPT, BabyAGI, AutoGen, LangChain, MetaGPT/ChatDev, CAMEL, HuggingGPT, etc.).  
  → Positionnement différenciant : multi-agents, ARBO-LOCK, souveraineté, expérimentation mémoire.

---

## 5. Architecture
- **arborescence_synchronisée_20250829.txt**  
  → Source absolue de vérité sur l’architecture du repo (strict ARBO-LOCK).  
- **docs/architecture/00-Overview.md**  
  -> SessionManager + `X-Session-Id` documentes (isolation par session, reset front).
- **docs/architecture/20-Sequences.md**  
  -> Sequences Auth/Chat/Memoire ajoutes au scope `session_id` et `StateManager.resetForSession()`.
  → Toute création/déplacement = annonce + snapshot.

---

## Synthèse hiérarchisée
- **Vision** → Genèse  
- **Implémentation technique** → Déploiement & Arbo  
- **Stratégie & Priorités** → Roadmaps  
- **Benchmark externe** → Panorama  
- **Vérrouillage structurel** → Snapshot Arbo (ARBO-LOCK)
