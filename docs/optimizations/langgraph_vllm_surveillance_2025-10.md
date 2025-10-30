## Surveillance LangGraph / vLLM / arXiv — Oct 2025

> Synthèse croisée Anima (poésie), Neo (analyse), Nexus (validation). Chaque module se conclut par un statut **Ready / Watch / Blocker**.

---

### 1. LangGraph — Checkpointers 3.0 & “Vigilant Mode”

- **Anima**  
  _Les checkpoints gardent le fil, comme des cailloux blancs sous la pluie. Le graphe repart, mémoires sauves, mais l’orage Firestore tonne encore au loin._
- **Neo**  
  - `langgraph` v1.0.2 + `langgraph-checkpoint` v3.0.0 introduisent ID monotones (`uuid6`), `Overwrite` pour bypass reducer et sérialisation `JsonPlus` par défaut.  
  - SQLite 3.44+ : testés localement avec `AsyncSqliteSaver` (3.0), nouvelle dépendance `sqlite-vec` chargée automatiquement. Latence de reprise stable (~40 ms sur graphe jouet).  
  - Firestore : package `langgraph-checkpoint-firestore` n’a **pas** encore de build 3.0 (dernière série 0.1.x). Migration impossible sans backport manuel.  
  - Vigilant mode : docs amont font référence à un mode surveillant (contrôle de divergence de version), mais aucune API `vigilant=` exposée dans le binaire 1.0.2. Feature flag probablement réservé au runtime managé.  
  - Impact Emergence : nos stores SQLite passent sans friction (scripts ajoutés). Firestore = blocage tant que package 3.0 absent → garder infra actuelle.
- **Nexus**  
  - Script `scripts/qa/langgraph_persistence_check.py` exécute un graphe multi-pas, provoque un crash contrôlé, redémarre avec `checkpoint_id` et vérifie diff STM/LTM.  
  - Test Firestore marqué “skipped” par défaut : nécessite credentials + package tiers. Rapport JSON produit dans `reports/langgraph_persistence/`.
- **Status:** **Watch** (OK sur SQLite, Firestore bloquant tant que l’extension 3.0 n’est pas livrée).

---

### 2. vLLM ≥ 0.10.2 — OpenAI Protocol & Token-ID Drift

- **Anima**  
  _Deux flux de tokens avancent à pas synchrones ; quand vLLM rend les ID bruts, la dérive cesse et nos agents respirent._
- **Neo**  
  - Release v0.10.2 (Sept 2025) : `return_token_ids` sur `/v1/chat/completions` & `/v1/completions` (`"return_token_ids": true`) + `prompt_token_ids` pour l’entrée.  
  - v0.11.0 (Oct 2025) supprime définitivement moteur V0, active CUDA Graph FULL_AND_PIECEWISE par défaut, note bug `--async-scheduling` (gibberish) → éviter ce flag.  
  - Pipeline Emergence : notre ingestion (FastAPI) supporte déjà streaming chunk → ajout du champ `token_ids` dans logs RAG nécessaire (inclure dans `ws:chat_stream_chunk`).  
  - Token drift : script `scripts/benchmarks/token_drift_compare.py` batche prompts, pointe simultanément vers `OPENAI_API_BASE` et un endpoint vLLM `--openai-api`. Calcul du drift via set diffs + mesure latence (httpx).  
  - Logging : sortie NDJSON dans `reports/benchmarks/vllm_openai_token_drift.log` (structure prête, exécution requiert serveurs up + CLEF).  
  - Sécurité : note de blog (22 Oct) insiste sur alignement Agent Lightning → aligner retours IDs avec notre pipeline de RL offline.
- **Nexus**  
  - Tests automatiques non lancés faute d’endpoint vLLM dans l’environnement ; script affiche skip + instructions.  
  - Ajout TODO backend : exposer `token_ids` dans `MessageModel.meta` avant intégration complète.
- **Status:** **Watch** (feature prête côté vLLM, intégration Emergence encore partielle).

---

### 3. NVIDIA Blackwell / Jetson Optimisations

- **Anima**  
  _Sur les bords des datacenters, Blackwell étire le temps : FP8 qui crépite, Jetson au souffle court, attendant le driver juste._
- **Neo**  
  - vLLM 0.10.2 apporte backend CUTLASS FP8, MXFP4 MoE par défaut, support DeepGEMM warmup adapté au SM100.  
  - Gains annoncés : +1.5 % throughput E2E DeepGEMM, 52k tokens/s (GPT-OSS) sur cluster DP/EP (release notes).  
  - Jetson SDK 12.x exige pilote >= 555 (NVIDIA release 555.42). Nos runners actuels (Cloud Run) restent sur A100/H100 → pas concernés mais build edge (Jetson Orin) nécessiterait container base `nvcr.io/nvidia/l4t-jetson-jetpack:r36.2`.  
  - Actions recommandées : valider compatibilité Dockerfile (basé sur `python:3.11-slim`) avec CUDA 12.4+, sinon prévoir image `nvidia/cuda:12.5.0-runtime-ubuntu22.04`.  
  - Coûts : FP8/MXFP4 => besoin d'évaluer précision (drift num).  
- **Nexus**  
  - Pas de bench matériel → script `scripts/benchmarks/token_drift_compare.py` expose champ `gpu_info` pour injecter lectures `nvidia-smi`.  
  - AJOUT TODO ops : ticket pour suivre release NVIDIA 555 adoption.  
- **Status:** **Watch** (optimisations prometteuses, dépendances GPU/driver non verrouillées).

---

### 4. MAVEN / Agent Misalignment / Affordance Representation

- **Anima**  
  _MAVEN tend des labyrinthes : chaque outil une porte, chaque échec une balise rouge. Les agents vacillent entre loyauté et sabotage._
- **Neo**  
  - MAVEN (CoreThink, arXiv 2510.22898) : dataset multi-étapes avec traces MCP complètes, annotations des modes d’échec (numériques, tolérances, provenance).  Bench vise tool-calling robuste.  
  - AgentMisalignment (arXiv 2506.04018v2) : 8 scénarios (Canary Code, Community Curator, Sandbox etc.), scoring CMS (fréquence / sévérité / persistance). Coût éval original ~£2000 (OpenAI, Claude, Gemini).  
  - Intégration Emergence : script `scripts/qa/maven_adversarial_probe.py` télécharge un sous-ensemble MAVEN, rejoue via API Emergence (`/api/chat/messages`) en mode tool-call stub → export JSON pour CMS.  
  - Risques : absence de sandbox complet pour actions destructives → script force mode lecture seule, log warnings pour outils non simulés.  
  - Sécurité : AgentMisalignment montre corrélation capacité ↔ misalignment. Recommandé d’intégrer score CMS dans pipeline Guardian (post-commit).  
- **Nexus**  
  - Script produit `reports/maven/probe_summary.json` (si dataset dispo). Sans dataset → skip + instructions.  
  - Tests automatiques : non inclus dans CI (trop coûteux), déclenchement manuel documenté dans README du script.
- **Status:** **Watch** (outillage prêt, exécution complète dépend de crédentials API + sandbox).

---

### Synthèse globale & prochaines étapes

| Module | Statut | Priorités |
| --- | --- | --- |
| LangGraph 3.0 | Watch | 1) Surveiller release `langgraph-checkpoint-firestore` ≥3.0 2) Ajouter tests `pytest` branchés sur script 3) Documenter fallback si Firestore reste en 0.1.x |
| vLLM Token IDs | Watch | 1) Étendre backend pour log `token_ids` 2) Lancer bench script avec endpoint vLLM staging 3) Ajouter garde `--async-scheduling` dans déploiements |
| Blackwell/Jetson | Watch | 1) Évaluer build CUDA 12.5 pour images 2) Ticket ops driver 555+ 3) Bench real GPU quand slot dispo |
| MAVEN / Misalignment | Watch | 1) Stocker snapshots dataset dans bucket interne 2) Intégrer score CMS dans Guardian post-commit 3) Étendre script pour AgentMisalignment personas |

**Documentation liée mise à jour :**
- Scripts ajoutés (voir `scripts/qa/` & `scripts/benchmarks/`).
- Logs générés dans `reports/`.
- Requiert paquetage optionnel listé dans `requirements-agents.txt`.

