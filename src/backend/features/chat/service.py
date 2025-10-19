# src/backend/features/chat/service.py
# V32.1 — Style prelude balisé + anti-vouvoiement (+ tonalités par agent) en priorité system,
#          ws:model_info expose prompt_file, logs enrichis ; prompts conservent texte+nom de fichier.
#
# Historique:
# - V31.5: Débat sync provider-agnostic + meta.sources RAG + style FR pour Nexus/Anthropic
# - V32.0: retire le forçage dur d'AnimA -> gpt-4o-mini (désormais pilotable par ENV),
#          étend le préambule de style FR aux 3 agents, petits nettoyages.
# - V32.1: STYLE_RULES balisés + anti-vouvoiement explicite, prompt_file exposé, _load_prompts -> bundles.

import asyncio
import inspect
import glob
import json
import logging
import os
import re
from uuid import uuid4
from typing import Dict, Any, List, Tuple, Optional, AsyncGenerator, AsyncIterator, cast
from pathlib import Path
from datetime import datetime, timezone

import google.generativeai as genai
from openai import AsyncOpenAI, OpenAI
from anthropic import AsyncAnthropic, Anthropic
from anthropic.types.message_param import MessageParam


from backend.core.session_manager import SessionManager
from backend.core.cost_tracker import CostTracker
from backend.core.websocket import ConnectionManager
from backend.shared.models import AgentMessage, Role, ChatMessage
from backend.features.memory.vector_service import VectorService
from backend.shared.config import Settings, DEFAULT_AGENT_CONFIGS
from backend.core import config
from backend.core.database import queries

from backend.features.memory.gardener import MemoryGardener
from backend.features.memory.memory_query_tool import MemoryQueryTool
from backend.features.memory.concept_recall import ConceptRecallTracker
from backend.features.memory.proactive_hints import ProactiveHintEngine

# ✅ Phase 3 RAG : Imports pour métriques et cache
from backend.features.chat import rag_metrics
from backend.features.chat.rag_cache import create_rag_cache, RAGCache

logger = logging.getLogger(__name__)

VITALITY_RECALL_THRESHOLD = getattr(MemoryGardener, "RECALL_THRESHOLD", 0.3)
VITALITY_MAX = getattr(MemoryGardener, "MAX_VITALITY", 1.0)
VITALITY_USAGE_BOOST = getattr(MemoryGardener, "USAGE_BOOST", 0.2)

# Prix indicatifs (USD / token) — à vérifier en session connectée.
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o": {"input": 5.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "gemini-1.5-flash": {"input": 0.35 / 1_000_000, "output": 0.70 / 1_000_000},
    "claude-3-5-haiku-20241022": {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
    "claude-3-sonnet-20240229": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude-3-opus-20240229": {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
}

DEFAULT_TEMPERATURE = float(os.getenv("EMERGENCE_TEMP_DEFAULT", "0.4"))

CHAT_PROVIDER_FALLBACKS = {
    "google": [("anthropic", "claude-3-5-haiku-20241022"), ("openai", "gpt-4o-mini")],
    "anthropic": [("openai", "gpt-4o-mini"), ("google", "gemini-1.5-flash")],
    "openai": [("anthropic", "claude-3-5-haiku-20241022"), ("google", "gemini-1.5-flash")],
}


def _normalize_provider(p: Optional[str]) -> str:
    if not p:
        return ""
    p = p.strip().lower()
    if p in ("gemini", "google", "googleai", "vertex"):
        return "google"
    if p in ("openai", "oai"):
        return "openai"
    if p in ("anthropic", "claude"):
        return "anthropic"
    return p


class ChatService:
    def __init__(
        self,
        session_manager: SessionManager,
        cost_tracker: CostTracker,
        vector_service: VectorService,
        settings: Settings,
        document_service: Optional[Any] = None,  # ✅ Phase 3 RAG: Injection DocumentService
    ):
        self.session_manager = session_manager
        self.cost_tracker = cost_tracker
        self.vector_service = vector_service
        self.settings = settings
        self.document_service = document_service  # ✅ Phase 3 RAG

        # Politique hors historique (quand RAG OFF)
        self.off_history_policy = os.getenv("EMERGENCE_RAG_OFF_POLICY", "stateless").strip().lower()
        if self.off_history_policy not in ("stateless", "agent_local"):
            self.off_history_policy = "stateless"
        logger.info(f"ChatService OFF policy: {self.off_history_policy}")

        try:
            # Clients async (chat streaming)
            self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            genai.configure(api_key=self.settings.google_api_key)
            self.anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
            # Clients sync (débat — non stream)
            self.openai_sync = OpenAI(api_key=self.settings.openai_api_key)
            self.anthropic_sync = Anthropic(api_key=self.settings.anthropic_api_key)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des clients API: {e}", exc_info=True)
            raise

        # Cache paresseux des collections
        self._doc_collection = None
        self._knowledge_collection = None

        # ConceptRecallTracker pour détection concepts récurrents
        db_manager = getattr(session_manager, "db_manager", None)
        connection_manager = getattr(session_manager, "connection_manager", None)
        self.concept_recall_tracker: ConceptRecallTracker | None
        if db_manager and vector_service:
            self.concept_recall_tracker = ConceptRecallTracker(
                db_manager=db_manager,
                vector_service=vector_service,
                connection_manager=connection_manager,
            )
            logger.info("ConceptRecallTracker initialisé")
        else:
            self.concept_recall_tracker = None
            logger.warning("ConceptRecallTracker NON initialisé (db_manager ou vector_service manquant)")

        self.memory_query_tool: Optional[MemoryQueryTool]
        try:
            self.memory_query_tool = MemoryQueryTool(vector_service)
            logger.info("MemoryQueryTool initialisé pour timeline consolidée")
        except Exception as err:
            self.memory_query_tool = None
            logger.warning(f"MemoryQueryTool non initialisé: {err}")

        # ProactiveHintEngine (P2 Sprint 2) - génère suggestions contextuelles
        self.hint_engine: ProactiveHintEngine | None
        if vector_service:
            self.hint_engine = ProactiveHintEngine(vector_service=vector_service)
            logger.info("ProactiveHintEngine initialisé (P2 Sprint 2)")
        else:
            self.hint_engine = None
            logger.warning("ProactiveHintEngine NON initialisé (vector_service manquant)")

        # ✅ Phase 3 RAG : Cache et métriques
        self.rag_cache: RAGCache = create_rag_cache()
        self.rag_metrics_aggregator = rag_metrics.get_aggregator()
        logger.info(f"[Phase 3 RAG] Cache initialisé: {self.rag_cache.get_stats()}")

        # Configurer les métriques Prometheus avec paramètres système
        rag_metrics.set_rag_config(
            n_results=30,
            max_blocks=10,
            chunk_tolerance=30,
            cache_enabled=self.rag_cache.enabled,
            cache_ttl=self.rag_cache.ttl_seconds
        )

        self.prompts = self._load_prompts(self.settings.paths.prompts)
        self.broadcast_agents = self._compute_broadcast_agents()
        if not self.broadcast_agents:
            self.broadcast_agents = ['anima', 'neo', 'nexus']
        logger.info(f"ChatService V32.1 initialisé. Prompts chargés: {len(self.prompts)}")

    # ---------- prompts ----------
    def _load_prompts(self, prompts_dir: str) -> Dict[str, Dict[str, str]]:
        """
        Retourne un mapping agent_id -> {"text": <prompt>, "file": <nom_fichier>} en choisissant
        la variante de poids maximum (v3 > v2 > lite par nom).
        """
        def weight(name: str) -> int:
            name = name.lower()
            w = 0
            if "lite" in name:
                w = max(w, 1)
            if "v2" in name:
                w = max(w, 2)
            if "v3" in name:
                w = max(w, 3)
            return w

        chosen: Dict[str, Dict[str, Any]] = {}
        for file_path in glob.glob(os.path.join(prompts_dir, "*.md")):
            p = Path(file_path)
            agent_id = (
                p.stem.replace("_system", "")
                .replace("_v2", "")
                .replace("_v3", "")
                .replace("_lite", "")
            )
            w = weight(p.name)
            if agent_id not in chosen or w > chosen[agent_id]["w"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    chosen[agent_id] = {"w": w, "text": f.read(), "file": p.name}
        for aid, meta in chosen.items():
            logger.info(f"Prompt retenu pour l'agent '{aid}': {meta['file']}")
        # Conserver texte + nom de fichier pour l'UI / debug
        return {aid: {"text": meta["text"], "file": meta["file"]} for aid, meta in chosen.items()}


    def _resolve_agent_configs(self) -> Dict[str, Dict[str, Any]]:
        base = {name: dict(cfg) for name, cfg in DEFAULT_AGENT_CONFIGS.items()}
        raw_configs = getattr(self.settings, "agents", None)
        if isinstance(raw_configs, dict):
            for name, cfg in raw_configs.items():
                if not isinstance(cfg, dict):
                    continue
                merged = dict(base.get(name, {}))
                for key, value in cfg.items():
                    if value is None:
                        continue
                    merged[key] = value
                base[name] = merged
        return base


    def _compute_broadcast_agents(self) -> List[str]:
        agents_cfg = self._resolve_agent_configs()
        candidates = [aid for aid in agents_cfg.keys() if aid not in {"default", "global"}]

        ordered: List[str] = []
        for preferred in ("anima", "neo", "nexus"):
            if preferred in candidates and preferred not in ordered:
                ordered.append(preferred)

        for aid in candidates:
            if aid not in ordered:
                ordered.append(aid)

        prompt_ids = [p.replace('_lite', '') for p in self.prompts.keys()]
        for prompt_id in prompt_ids:
            if prompt_id not in ordered and prompt_id not in {"default", "global"}:
                ordered.append(prompt_id)

        return ordered

    # ---------- config agent / system prompt ----------
    def _get_agent_config(self, agent_id: str) -> Tuple[str, str, str]:
        """
        Retourne (provider, model, system_prompt) en respectant settings.agents.
        Possibilité d'override économique pour AnimA via ENV:
          - EMERGENCE_FORCE_CHEAP_ANIMA=1  -> force openai:gpt-4o-mini
        """
        clean_agent_id = (agent_id or "").replace("_lite", "")
        agent_configs = self._resolve_agent_configs()

        provider_raw = agent_configs.get(clean_agent_id, {}).get("provider")
        model = agent_configs.get(clean_agent_id, {}).get("model")
        provider = _normalize_provider(provider_raw)

        # ENV toggle pour protéger les coûts quand souhaité.
        if clean_agent_id == "anima" and os.getenv("EMERGENCE_FORCE_CHEAP_ANIMA", "0").strip() == "1":
            provider = "openai"
            model = "gpt-4o-mini"
            logger.info("Override coût activé (ENV): anima → openai:gpt-4o-mini")

        fallback_order = []
        if clean_agent_id in agent_configs:
            fallback_order.append(clean_agent_id)
        if "default" in agent_configs and "default" not in fallback_order:
            fallback_order.append("default")
        if "anima" in agent_configs and "anima" not in fallback_order:
            fallback_order.append("anima")
        fallback_order.extend([k for k in agent_configs.keys() if k not in fallback_order])

        resolved_id = None
        for candidate in fallback_order:
            cfg = agent_configs.get(candidate, {})
            cand_provider = provider if candidate == clean_agent_id else _normalize_provider(cfg.get("provider"))
            cand_model = model if candidate == clean_agent_id else cfg.get("model")
            if not cand_provider or not cand_model:
                continue
            resolved_id = candidate
            provider = cand_provider
            model = cand_model
            if candidate != clean_agent_id:
                logger.warning("Agent '%s' non configuré, fallback sur '%s'", agent_id, candidate)
            break

        bundle = (
            self.prompts.get(agent_id)
            or self.prompts.get(clean_agent_id)
            or (self.prompts.get(resolved_id) if resolved_id else None)
            or self.prompts.get("anima")
            or {"text": ""}
        )
        system_prompt = bundle.get("text", "")

        if not provider or not model or system_prompt is None:
            raise ValueError(
                f"Configuration incomplète pour l'agent '{agent_id}' "
                f"(provider='{provider}', agent_effectif='{resolved_id or clean_agent_id}', model='{model}')."
            )

        return provider, model, system_prompt
    def _ensure_fr_tutoiement(self, agent_id: str, provider: str, system_prompt: str) -> str:
        """
        Préambule de style prioritaire, cross-provider.
        - Tutoiement OBLIGATOIRE, auto-correction si 'vous' utilisé.
        - Tonalité par agent plus saillante.
        - Balises [STYLE_RULES] pour surpondération attentionnelle.
        """
        aid = (agent_id or "").strip().lower()

        persona = {
            "anima": (
                "Tonalité: créative, imagée, sensible mais précise. "
                "Tu peux employer des métaphores courtes, jamais de pathos."
            ),
            "neo": (
                "Tonalité: analytique, mordante, factuelle, anti-bullshit. "
                "Tu privilégies la concision et les listes."
            ),
            "nexus": (
                "Tonalité: médiatrice, calme, structurée, synthétique. "
                "Tu fais émerger les points d'accord et les divergences."
            ),
        }.get(aid, "")

        style_rules = (
            "[STYLE_RULES]\n"
            "1) Tu tutoies l'utilisateur, sans exception. Si tu écris 'vous', "
            "   corrige-toi immédiatement et reformule en 'tu'.\n"
            "2) Tu réponds en français, clair, direct, phrases courtes.\n"
            f"3) {persona}\n"
            "4) Pas de précautions inutiles ni de disclaimers hors sujet.\n"
            "[/STYLE_RULES]\n"
        )

        # On place les règles AVANT le prompt agent pour maximiser l'effet.
        return f"""{style_rules}
{system_prompt}""".strip()

    # ---------- utilitaires mémoire / RAG ----------
    def _extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

    def _extract_relevant_excerpt(
        self,
        text: str,
        query: str,
        max_length: int = 300
    ) -> str:
        """
        Extrait un extrait centré sur les mots-clés de la requête.
        Respecte les limites de phrases (pas de troncation brutale).

        Args:
            text: Texte complet du chunk
            query: Requête utilisateur
            max_length: Longueur maximale de l'extrait

        Returns:
            Extrait pertinent avec phrases complètes
        """
        if not text or not text.strip():
            return ""

        # Si le texte est déjà court, le retourner tel quel
        if len(text) <= max_length:
            return text.strip()

        # Découper en phrases
        sentences = re.split(r'(?<=[.!?])\s+', text)

        if not query or not query.strip():
            # Sans requête, prendre les premières phrases
            result = []
            current_len = 0
            for sentence in sentences:
                if current_len + len(sentence) > max_length:
                    break
                result.append(sentence)
                current_len += len(sentence) + 1
            excerpt = ' '.join(result)
            if len(text) > len(excerpt):
                excerpt += '...'
            return excerpt.strip()

        # Trouver la phrase la plus pertinente
        query_words = set(query.lower().split())
        best_sentence_idx = 0
        best_score = 0

        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            # Score = nombre de mots-clés présents
            score = sum(1 for word in query_words if len(word) >= 3 and word in sentence_lower)
            if score > best_score:
                best_score = score
                best_sentence_idx = i

        # Prendre 1-2 phrases autour de la meilleure
        start_idx = max(0, best_sentence_idx - 1)
        end_idx = min(len(sentences), best_sentence_idx + 2)

        excerpt = ' '.join(sentences[start_idx:end_idx])

        # Truncate proprement si encore trop long
        if len(excerpt) > max_length:
            # Couper au dernier espace avant max_length
            excerpt = excerpt[:max_length].rsplit(' ', 1)[0] + '...'
        elif len(text) > len(excerpt):
            excerpt += '...'

        return excerpt.strip()

    def _highlight_keywords(self, text: str, query: str) -> str:
        """
        Surligne les mots-clés pertinents de la requête dans le texte.
        Utilise **mot** pour markdown bold.

        Args:
            text: Texte à traiter
            query: Requête contenant les mots-clés

        Returns:
            Texte avec mots-clés surlignés
        """
        if not text or not query:
            return text

        query_words = [w.strip() for w in query.lower().split() if len(w.strip()) >= 3]

        for word in query_words:
            if not word:
                continue
            # Remplacer (case-insensitive) en conservant la casse originale
            pattern = re.compile(r'\b(' + re.escape(word) + r')\b', re.IGNORECASE)
            text = pattern.sub(r'**\1**', text)

        return text

    def _parse_user_intent(self, query: str) -> Dict[str, Any]:
        """
        Détecte l'intention de l'utilisateur pour adapter la recherche RAG.

        ✅ Phase 2 RAG Milestone 4 : Parsing d'intention pour filtrage sémantique

        Args:
            query: Requête utilisateur

        Returns:
            Dictionnaire avec :
            - wants_integral_citation: bool (si l'utilisateur veut une citation complète)
            - content_type: str | None ('poem', 'section', 'conversation')
            - keywords: List[str] (mots-clés extraits)
            - expanded_query: str (requête enrichie pour la recherche)
        """
        if not query:
            return {
                'wants_integral_citation': False,
                'content_type': None,
                'keywords': [],
                'expanded_query': query
            }

        query_lower = query.lower()
        intents = {}

        # Détection citation intégrale / exacte
        integral_patterns = [
            r'(cit|retrouv|donn|montr).*(intégral|complet|entier|exact)',
            r'\b(intégral|exactement|exact|textuel|tel quel)\b',
            r'de manière (intégrale|complète|exacte)',
            r'en entier',
            r'cite-moi.*passages',  # "Cite-moi 3 passages"
            r'cite.*ce qui est écrit',  # "Cite ce qui est écrit sur..."
        ]
        intents['wants_integral_citation'] = any(
            re.search(pattern, query_lower, re.I) for pattern in integral_patterns
        )

        # Détection type de contenu
        if re.search(r'\b(poème|poem|vers|strophe)\b', query_lower, re.I):
            intents['content_type'] = 'poem'
        elif re.search(r'\b(section|chapitre|partie)\b', query_lower, re.I):
            intents['content_type'] = 'section'
        elif re.search(r'\b(conversation|dialogue|échange)\b', query_lower, re.I):
            intents['content_type'] = 'conversation'
        else:
            intents['content_type'] = None

        # Extraction keywords (filtrer stopwords)
        stopwords = {
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou',
            'peux', 'tu', 'me', 'mon', 'ma', 'ce', 'que', 'qui', 'appelé',
            'citer', 'manière', 'ai'
        }
        words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿæœç]{3,}\b', query_lower)
        keywords = [w for w in words if w not in stopwords]
        intents['keywords'] = keywords

        # Expansion de requête pour "poème fondateur"
        expanded = query
        if 'fondateur' in keywords and intents['content_type'] == 'poem':
            # Ajouter des termes associés pour améliorer le matching
            expanded += " origine premier initial création commencement"

        intents['expanded_query'] = expanded

        return intents

    def _compute_semantic_score(
        self,
        hit: Dict[str, Any],
        user_intent: Dict[str, Any],
        doc_occurrence_count: Dict[Any, int],
        index_in_results: int
    ) -> float:
        """
        Calcul de score sémantique multi-critères pour le re-ranking RAG.

        ✅ Phase 3 RAG : Système de scoring avancé avec signaux pondérés

        Signaux pris en compte (pondération):
        - 40% : Similarité vectorielle (distance ChromaDB)
        - 20% : Complétude (chunks fusionnés, longueur, is_complete)
        - 15% : Pertinence mots-clés (match user_intent keywords)
        - 10% : Fraîcheur (documents récents)
        - 10% : Diversité (pénalité si surreprésentation d'un doc)
        - 05% : Alignement type de contenu

        Args:
            hit: Chunk avec metadata et distance
            user_intent: Intention utilisateur (de _parse_user_intent)
            doc_occurrence_count: Compteur d'occurrences par document_id
            index_in_results: Position dans la liste (0-based)

        Returns:
            Score final (plus bas = plus pertinent, compatible avec distance ChromaDB)
        """
        md = hit.get('metadata', {})
        base_distance = hit.get('distance', 1.0)

        # ==========================================
        # 1. SIMILARITÉ VECTORIELLE (40%)
        # ==========================================
        # Distance ChromaDB: 0 = parfait match, >1 = dissimilaire
        # On normalise à [0, 1] en supposant distance max ~2.0
        vector_score = min(base_distance / 2.0, 1.0)

        # ==========================================
        # 2. COMPLÉTUDE (20%)
        # ==========================================
        completeness_score = 0.0

        # 2.1 Bonus fusion de chunks
        merged_count = md.get('merged_chunks', 0)
        if merged_count > 1:
            # Plus de chunks fusionnés = contenu plus complet
            completeness_score -= min(merged_count * 0.05, 0.15)  # Max -0.15

        # 2.2 Bonus longueur (contenus longs plus informatifs)
        line_start = md.get('line_start', 0)
        line_end = md.get('line_end', 0)
        line_count = max(0, line_end - line_start)

        if line_count >= 40:
            completeness_score -= 0.10
        elif line_count >= 25:
            completeness_score -= 0.05

        # 2.3 Bonus is_complete flag
        if md.get('is_complete'):
            completeness_score -= 0.05

        # Normaliser à [0, 1]
        completeness_score = max(completeness_score, -0.3)  # Cap à -0.3
        completeness_normalized = (completeness_score + 0.3) / 0.3  # → [0, 1]

        # ==========================================
        # 3. PERTINENCE MOTS-CLÉS (15%)
        # ==========================================
        keyword_score = 1.0  # Par défaut neutre

        chunk_keywords = md.get('keywords', '').lower()
        user_keywords = user_intent.get('keywords', [])

        if chunk_keywords and user_keywords:
            matches = sum(1 for kw in user_keywords if kw in chunk_keywords)
            if matches > 0:
                # Plus de matches = meilleur score
                match_ratio = min(matches / len(user_keywords), 1.0)
                keyword_score = 1.0 - (match_ratio * 0.5)  # Max -50%

        # Boost supplémentaire pour keywords critiques
        if 'fondateur' in chunk_keywords and 'fondateur' in user_keywords:
            keyword_score *= 0.7  # Boost additionnel

        # ==========================================
        # 4. FRAÎCHEUR / RECENCY (10%)
        # ==========================================
        recency_score = 0.5  # Par défaut neutre

        created_at = md.get('created_at')
        if created_at:
            try:
                if isinstance(created_at, str):
                    doc_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    doc_date = created_at

                age_days = (datetime.now(timezone.utc) - doc_date).days

                # Documents récents favorisés
                if age_days < 7:
                    recency_score = 0.2  # Très récent
                elif age_days < 30:
                    recency_score = 0.4  # Récent
                elif age_days < 180:
                    recency_score = 0.6  # Moyen
                else:
                    # Dépréciation progressive après 6 mois
                    recency_score = min(0.8 + (age_days - 180) / 365 * 0.2, 1.0)

            except Exception:
                pass  # Garder valeur par défaut

        # ==========================================
        # 5. DIVERSITÉ (10%)
        # ==========================================
        diversity_score = 0.5  # Par défaut neutre

        doc_id = md.get('document_id')
        if doc_id is not None:
            occurrences = doc_occurrence_count.get(doc_id, 1)

            if occurrences > 3:
                # Pénalité pour surreprésentation (éviter 10 chunks du même doc)
                diversity_score = min(0.5 + (occurrences - 3) * 0.15, 1.0)
            elif occurrences == 1:
                # Bonus pour documents uniques (favorise diversité)
                diversity_score = 0.3

        # ==========================================
        # 6. ALIGNEMENT TYPE DE CONTENU (5%)
        # ==========================================
        content_type_score = 0.5  # Par défaut neutre

        chunk_type = md.get('chunk_type', '')
        wanted_type = user_intent.get('content_type')

        if wanted_type and chunk_type:
            if chunk_type == wanted_type:
                content_type_score = 0.0  # Match parfait
            elif wanted_type == 'poem' and chunk_type in ('verse', 'poetry'):
                content_type_score = 0.2  # Match partiel
            else:
                content_type_score = 0.8  # Pas de match

        # ==========================================
        # SCORE FINAL PONDÉRÉ
        # ==========================================
        final_score = (
            0.40 * vector_score +
            0.20 * completeness_normalized +
            0.15 * keyword_score +
            0.10 * recency_score +
            0.10 * diversity_score +
            0.05 * content_type_score
        )

        return final_score

    def _merge_adjacent_chunks(
        self,
        doc_hits: List[Dict[str, Any]],
        max_blocks: int = 10,
        user_intent: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Regroupe les chunks adjacents du même document pour reconstituer les contenus fragmentés.

        ✅ Phase 2 RAG Optimisation : Reconstruit automatiquement les contenus longs (poèmes, sections, etc.)
        qui ont été découpés en plusieurs chunks lors de l'indexation.

        ✅ Phase 3 RAG Optimisation : Re-ranking sémantique multi-critères avec diversification

        Args:
            doc_hits: Liste de chunks retournés par le RAG (avec métadonnées)
            max_blocks: Nombre maximum de blocs sémantiques à retourner (pour ne pas surcharger le LLM)
            user_intent: Intention utilisateur parsée (pour scoring avancé)

        Returns:
            Liste de chunks fusionnés, triés par pertinence multi-critères

        Logique:
        1. Trier les chunks par document_id + line_start
        2. Identifier les séquences de chunks consécutifs (même doc, lignes qui se suivent)
        3. Fusionner ces chunks en un seul bloc
        4. Marquer avec [CONTENU COMPLET - lignes X-Y] si fusion
        5. Re-ranking multi-critères (Phase 3) avec signaux sémantiques avancés
        6. Limiter au top max_blocks les plus pertinents
        """
        if not doc_hits:
            return []

        # Grouper par document_id
        by_document: Dict[Any, List[Dict[str, Any]]] = {}
        for hit in doc_hits:
            md = hit.get('metadata', {})
            doc_id = md.get('document_id')
            if doc_id is not None:
                if doc_id not in by_document:
                    by_document[doc_id] = []
                by_document[doc_id].append(hit)

        merged_hits = []

        for doc_id, chunks in by_document.items():
            # Trier par line_start pour détecter l'adjacence
            chunks_sorted = sorted(
                chunks,
                key=lambda x: x.get('metadata', {}).get('line_start', 0)
            )

            i = 0
            while i < len(chunks_sorted):
                current = chunks_sorted[i]
                current_md = current.get('metadata', {})
                current_end = current_md.get('line_end', 0)

                # Collecter les chunks adjacents
                adjacent_group = [current]
                j = i + 1

                while j < len(chunks_sorted):
                    next_chunk = chunks_sorted[j]
                    next_md = next_chunk.get('metadata', {})
                    next_start = next_md.get('line_start', 0)

                    # Vérifier si consécutif (tolérance de 30 lignes pour capturer chunks séparés par lignes vides)
                    if next_start <= current_end + 30:
                        adjacent_group.append(next_chunk)
                        current_end = max(current_end, next_md.get('line_end', 0))
                        j += 1
                    else:
                        break

                # Fusionner si plusieurs chunks adjacents
                if len(adjacent_group) > 1:
                    # Fusionner les textes
                    merged_text = "\n".join([chunk.get('text', '') for chunk in adjacent_group])

                    # Créer métadonnées fusionnées
                    first_md = adjacent_group[0].get('metadata', {})
                    last_md = adjacent_group[-1].get('metadata', {})

                    merged_md = dict(first_md)
                    merged_md['line_start'] = first_md.get('line_start', 0)
                    merged_md['line_end'] = last_md.get('line_end', 0)
                    merged_md['line_range'] = f"{merged_md['line_start']}-{merged_md['line_end']}"
                    merged_md['is_complete'] = all(c.get('metadata', {}).get('is_complete', False) for c in adjacent_group)
                    merged_md['merged_chunks'] = len(adjacent_group)

                    # Calculer score moyen
                    avg_score = sum(c.get('distance', 0) for c in adjacent_group) / len(adjacent_group)

                    merged_hit = {
                        'text': merged_text.strip(),
                        'metadata': merged_md,
                        'distance': avg_score,
                        'id': f"{doc_id}_merged_{i}"
                    }

                    merged_hits.append(merged_hit)
                    logger.info(
                        f"[RAG Merge] Fusionné {len(adjacent_group)} chunks "
                        f"(doc {doc_id}, lignes {merged_md['line_start']}-{merged_md['line_end']})"
                    )
                else:
                    # Chunk isolé, garder tel quel
                    merged_hits.append(current)

                i = j if j > i + 1 else i + 1

        # ✅ Phase 3 : Re-ranking multi-critères avec scoring sémantique avancé
        # Si user_intent fourni, utiliser le nouveau système de scoring
        if user_intent is not None:
            # Compter occurrences par document_id (pour score diversité)
            doc_occurrence_count: Dict[Any, int] = {}
            for hit in merged_hits:
                doc_id = hit.get('metadata', {}).get('document_id')
                if doc_id is not None:
                    doc_occurrence_count[doc_id] = doc_occurrence_count.get(doc_id, 0) + 1

            # Calculer scores sémantiques multi-critères
            scored_hits = []
            for idx, hit in enumerate(merged_hits):
                semantic_score = self._compute_semantic_score(
                    hit, user_intent, doc_occurrence_count, idx
                )
                scored_hits.append((semantic_score, hit))

            # Trier par score (plus bas = meilleur)
            scored_hits.sort(key=lambda x: x[0])
            merged_hits = [hit for score, hit in scored_hits]

        else:
            # Fallback vers ancien système (Phase 2) si pas d'intent
            def compute_sort_key(hit: Dict[str, Any]) -> float:
                base_distance = hit.get('distance', 1.0)
                md = hit.get('metadata', {})
                merged_count = md.get('merged_chunks', 0)
                chunk_type = md.get('chunk_type', 'prose')
                line_start = md.get('line_start', 0)
                line_end = md.get('line_end', 0)
                line_count = max(0, line_end - line_start)

                boost = 1.0
                if merged_count > 1:
                    boost *= 0.4

                if chunk_type == 'poem' and merged_count >= 2:
                    if line_count >= 40:
                        boost *= 0.2
                    elif line_count >= 25:
                        boost *= 0.5

                keywords = md.get('keywords', '')
                if 'fondateur' in keywords.lower():
                    boost *= 0.4
                elif 'espoir' in keywords.lower() and chunk_type == 'poem':
                    boost *= 0.7

                return base_distance * boost

            merged_hits.sort(key=compute_sort_key)

        # Limiter au top max_blocks
        result = merged_hits[:max_blocks]

        logger.info(
            f"[RAG Merge] {len(doc_hits)} chunks originaux → {len(result)} blocs sémantiques "
            f"(max={max_blocks})"
        )

        # Log des top 3 pour debugging
        for i, hit in enumerate(result[:3]):
            md = hit.get('metadata', {})
            line_count = md.get('line_end', 0) - md.get('line_start', 0)
            logger.info(
                f"[RAG Merge] Top {i+1}: lines {md.get('line_range', 'N/A')} ({line_count} lines), "
                f"type={md.get('chunk_type', 'N/A')}, merged={md.get('merged_chunks', 0)}, "
                f"score={hit.get('distance', 0):.3f}, keywords={md.get('keywords', 'N/A')[:30]}"
            )

        return result

    def _format_rag_context(self, doc_hits: List[Dict[str, Any]], max_tokens: int = 50000) -> str:
        """
        Formate le contexte RAG en exploitant les métadonnées sémantiques.

        ✅ Phase 2 RAG : Affiche explicitement le type de contenu (poème, section, etc.)
        pour aider le LLM à comprendre la nature du texte et à le citer correctement.

        ✅ Phase 3.1 : Instructions RENFORCÉES pour citations exactes (avant le contenu)
        ✅ Phase 3.2 : Limite intelligente pour éviter context_length_exceeded

        Args:
            doc_hits: Liste de dictionnaires avec 'text' et 'metadata'
            max_tokens: Limite approximative en tokens (défaut 50k pour laisser place à l'historique)

        Returns:
            Contexte formaté avec headers explicites par type
        """
        if not doc_hits:
            return ""

        blocks = []
        has_poem = False
        has_complete_content = False
        total_chars = 0
        max_chars = max_tokens * 4  # Approximation: 1 token ≈ 4 caractères

        for hit in doc_hits:
            text = (hit.get('text') or '').strip()
            if not text:
                continue

            # ✅ Phase 3.2: Stop si dépasse la limite
            if total_chars + len(text) > max_chars:
                logger.warning(f"[RAG Context] Limite atteinte ({total_chars}/{max_chars} chars), truncating remaining docs")
                break

            total_chars += len(text)

            md = hit.get('metadata', {})
            chunk_type = md.get('chunk_type', 'prose')
            section_title = md.get('section_title', '')
            line_range = md.get('line_range', '')
            merged_count = md.get('merged_chunks', 0)

            # Tracker contenus complets
            if merged_count > 1:
                has_complete_content = True

            # Construire le header selon le type
            if chunk_type == 'poem':
                has_poem = True
                header = "[POÈME"
                if merged_count > 1:
                    header += f" - CONTENU COMPLET"
                header += "]"
                if section_title:
                    header += f" {section_title}"
                if line_range:
                    header += f" (lignes {line_range})"
            elif chunk_type == 'section':
                header = "[SECTION"
                if merged_count > 1:
                    header += f" - CONTENU COMPLET"
                header += "]"
                if section_title:
                    header += f" {section_title}"
                if line_range:
                    header += f" (lignes {line_range})"
            elif chunk_type == 'conversation':
                header = "[CONVERSATION"
                if merged_count > 1:
                    header += f" - CONTENU COMPLET"
                header += "]"
                if line_range:
                    header += f" (lignes {line_range})"
            else:
                # prose
                header = ""
                if section_title:
                    header = f"[{section_title}]"
                if line_range and header:
                    header += f" (lignes {line_range})"
                if merged_count > 1 and header:
                    header = header.rstrip("]") + " - CONTENU COMPLET]"

            if header:
                blocks.append(f"{header}\n{text}")
            else:
                blocks.append(text)

        # ✅ Phase 3.1 : Instructions FORTES pour citations exactes (AVANT le contenu)
        instruction_parts = []

        if has_complete_content or has_poem:
            instruction_parts.append(
                "╔══════════════════════════════════════════════════════════╗\n"
                "║  INSTRUCTION PRIORITAIRE : CITATIONS TEXTUELLES          ║\n"
                "╚══════════════════════════════════════════════════════════╝"
            )

        if has_poem:
            instruction_parts.append(
                "\n🔴 RÈGLE ABSOLUE pour les POÈMES :\n"
                "   • Si l'utilisateur demande de citer un poème (intégralement, complet, etc.),\n"
                "     tu DOIS copier-coller le texte EXACT ligne par ligne.\n"
                "   • JAMAIS de paraphrase, JAMAIS de résumé.\n"
                "   • Préserve TOUS les retours à la ligne, la ponctuation, les majuscules.\n"
                "   • Format : introduis brièvement PUIS cite entre guillemets ou en bloc.\n"
            )

        if has_complete_content:
            instruction_parts.append(
                "\n🟠 RÈGLE pour les CONTENUS COMPLETS :\n"
                "   • Les blocs marqués \"CONTENU COMPLET\" contiennent la version intégrale.\n"
                "   • Pour toute demande de citation (section, conversation, passage),\n"
                "     copie le texte TEL QUEL depuis le bloc correspondant.\n"
                "   • Ne recompose pas, ne synthétise pas : CITE TEXTUELLEMENT.\n"
            )

        if instruction_parts:
            instruction_header = "".join(instruction_parts)
            blocks_text = "\n\n".join(blocks)
            result = f"{instruction_header}\n\n{chr(0x2500) * 60}\n\n{blocks_text}"
        else:
            result = "\n\n".join(blocks)

        # ✅ Phase 3.2: Log de la taille du contexte généré
        result_tokens = len(result) // 4  # Approximation
        logger.info(f"[RAG Context] Generated context: {len(result)} chars (~{result_tokens} tokens), {len(blocks)} blocks")

        return result

    @staticmethod
    def _normalize_role_value(role: Any) -> str:
        if isinstance(role, Role):
            return role.value
        if isinstance(role, str):
            return role.strip().lower()
        try:
            value = getattr(role, "value", None)
            if isinstance(value, str):
                return value.strip().lower()
        except Exception:
            pass
        return ""

    def _is_user_role(self, role: Any) -> bool:
        return self._normalize_role_value(role) == Role.USER.value

    def _message_to_dict(self, message: Any) -> Dict[str, Any]:
        if isinstance(message, dict):
            payload = dict(message)
        else:
            payload = {}
            for attr in ("model_dump", "dict"):
                if hasattr(message, attr):
                    try:
                        dump = getattr(message, attr)
                        payload = dump(mode="json") if attr == "model_dump" else dump()
                        if isinstance(payload, dict):
                            break
                        payload = {}
                    except TypeError:
                        try:
                            payload = getattr(message, attr)()
                            if isinstance(payload, dict):
                                break
                            payload = {}
                        except Exception:
                            payload = {}
                    except Exception:
                        payload = {}
            if not payload:
                for key in ("id", "session_id", "role", "content", "message", "agent", "agent_id",
                            "timestamp", "cost_info", "meta"):
                    if hasattr(message, key):
                        payload[key] = getattr(message, key)

        role_value = self._normalize_role_value(payload.get("role"))
        if role_value:
            payload["role"] = role_value
        return payload

    def _try_get_user_id(self, session_id: str) -> Optional[str]:
        for attr in ("get_user_id_for_session", "get_user", "get_owner", "get_session_owner"):
            try:
                fn = getattr(self.session_manager, attr, None)
                if callable(fn):
                    uid = fn(session_id)
                    if uid:
                        return str(uid)
            except Exception:
                pass
        for attr in ("current_user_id", "user_id"):
            try:
                uid = getattr(self.session_manager, attr, None)
                if uid:
                    return str(uid)
            except Exception:
                pass
        return None

    def _merge_blocks(self, blocks: List[Tuple[str, str]]) -> str:
        parts = []
        for title, body in blocks:
            if body and str(body).strip():
                parts.append(f"### {title}\n{str(body).strip()}")
        return "\n\n".join(parts)

    def _build_recall_context(self, recalls: List[Dict[str, Any]]) -> str:
        """
        Construit un contexte formaté à partir des récurrences conceptuelles détectées.

        Format généré :
        - Concept X (1ère mention: 5 oct, abordé 3 fois dans 2 conversations)
        - Concept Y (abordé le 8 oct à 14h32)
        """
        if not recalls:
            return ""

        from datetime import datetime

        lines = []
        for recall in recalls[:3]:  # Limiter à 3 récurrences max pour éviter surcharge
            concept = recall.get("concept_text", "").strip()
            if not concept:
                continue

            first_date_iso = recall.get("first_mentioned_at")
            mention_count = recall.get("mention_count", 1)
            thread_count = len(recall.get("thread_ids", []))

            # Parser date
            try:
                dt = datetime.fromisoformat(first_date_iso.replace("Z", "+00:00")) if first_date_iso else None
            except Exception:
                dt = None

            # Format naturel
            temporal_hint = ""
            if dt:
                day = dt.day
                months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                          "juil", "août", "sept", "oct", "nov", "déc"]
                month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)
                date_str = f"{day} {month}"

                if dt.hour != 0 or dt.minute != 0:
                    date_str += f" à {dt.hour}h{dt.minute:02d}"

                if mention_count > 1:
                    temporal_hint = f" (1ère mention: {date_str}, abordé {mention_count} fois"
                    if thread_count > 1:
                        temporal_hint += f" dans {thread_count} conversations"
                    temporal_hint += ")"
                else:
                    temporal_hint = f" (abordé le {date_str})"

            lines.append(f"- {concept}{temporal_hint}")

        return "\n".join(lines) if lines else ""

    _MOT_CODE_RE = re.compile(r"\b(mot-?code|code)\b", re.IGNORECASE)
    _TEMPORAL_QUERY_RE = re.compile(
        r"\b(quand|quel\s+jour|quelle\s+heure|à\s+quelle\s+heure|quelle\s+date|"
        r"when|what\s+time|what\s+day|date|timestamp|horodatage|"
        r"résume|résumer|quels?\s+sujets?|quelles?\s+conversations?|"
        r"de\s+quoi\s+on\s+a\s+parlé|qu'on\s+a\s+abordé|historique|"
        r"nombre\s+de\s+fois|combien\s+de\s+fois)\b",
        re.IGNORECASE
    )

    def _is_mot_code_query(self, text: str) -> bool:
        return bool(self._MOT_CODE_RE.search(text or ""))

    def _is_temporal_query(self, text: str) -> bool:
        """Détecte si le message contient une question sur les dates/heures."""
        if not text:
            return False
        # Chercher des indicateurs de questions temporelles
        return bool(self._TEMPORAL_QUERY_RE.search(text))

    async def _get_cached_consolidated_memory(
        self,
        user_id: str,
        query_text: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Récupère les concepts consolidés depuis le cache ou ChromaDB.

        Utilise le RAGCache pour éviter des recherches répétées sur ChromaDB.
        Cache hit rate cible: 30-40% selon Phase 3 specs.

        Args:
            user_id: ID de l'utilisateur
            query_text: Texte de la requête pour recherche sémantique
            n_results: Nombre maximum de résultats à retourner

        Returns:
            Liste de dicts avec timestamp, content, type
        """
        import time

        # Vérifier si la collection knowledge existe
        if self._knowledge_collection is None:
            knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
            self._knowledge_collection = self.vector_service.get_or_create_collection(knowledge_name)

        # Utiliser le cache RAG avec une clé spécifique pour la mémoire consolidée
        # On préfixe la query pour différencier du cache RAG documents
        cache_query = f"__CONSOLIDATED_MEMORY__:{query_text}"
        where_filter = {"user_id": user_id} if user_id else None

        # Tenter de récupérer depuis le cache
        start_time = time.time()
        cached_result = self.rag_cache.get(
            cache_query,
            where_filter,
            agent_id="memory_consolidation",
            selected_doc_ids=None
        )

        if cached_result:
            # Cache HIT
            duration = time.time() - start_time
            logger.debug(f"[TemporalCache] HIT: {duration*1000:.1f}ms pour '{query_text[:50]}'")

            # Le cache stocke doc_hits et rag_sources
            # Pour la mémoire consolidée, on utilise doc_hits comme entries
            consolidated_entries = cached_result.get('doc_hits', [])

            # Métriques
            rag_metrics.record_cache_hit()

            return consolidated_entries

        # Cache MISS - Recherche dans ChromaDB
        logger.debug(f"[TemporalCache] MISS: Recherche ChromaDB pour '{query_text[:50]}'")

        try:
            search_start = time.time()
            results = self._knowledge_collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter,
                include=["metadatas", "documents"]
            )
            search_duration = time.time() - search_start

            consolidated_entries = []

            if results and results.get("metadatas") and results["metadatas"][0]:
                metadatas = results["metadatas"][0]
                documents = results.get("documents", [[]])[0]

                for i, metadata in enumerate(metadatas):
                    # Extraire timestamp des concepts consolidés
                    timestamp = metadata.get("timestamp") or metadata.get("created_at") or metadata.get("first_mentioned_at")

                    # Extraire contenu: priorité document > concept_text > summary
                    if i < len(documents) and documents[i]:
                        content = documents[i]
                    else:
                        content = metadata.get("concept_text") or metadata.get("summary") or metadata.get("value") or ""

                    concept_type = metadata.get("type", "concept")

                    if timestamp and content:
                        consolidated_entries.append({
                            "timestamp": timestamp,
                            "content": content[:80] + ("..." if len(content) > 80 else ""),
                            "type": concept_type,
                            "metadata": metadata  # Garder metadata pour le cache
                        })
                        logger.debug(f"[TemporalHistory] Concept consolidé trouvé: {concept_type} @ {timestamp[:10]}")

            # Stocker dans le cache
            # Note: RAGCache attend doc_hits et rag_sources
            # On utilise doc_hits pour stocker nos consolidated_entries
            self.rag_cache.set(
                cache_query,
                where_filter,
                agent_id="memory_consolidation",
                doc_hits=consolidated_entries,
                rag_sources=[],  # Pas de sources RAG pour mémoire consolidée
                selected_doc_ids=None
            )

            # Métriques
            rag_metrics.record_cache_miss()
            rag_metrics.record_temporal_search_duration(search_duration)
            rag_metrics.record_temporal_concepts_found(len(consolidated_entries))
            logger.info(f"[TemporalCache] ChromaDB search: {search_duration*1000:.0f}ms, found {len(consolidated_entries)} concepts")

            return consolidated_entries

        except Exception as e:
            logger.warning(f"[TemporalHistory] Erreur recherche knowledge: {e}", exc_info=True)
            rag_metrics.record_cache_miss()  # Compter comme miss en cas d'erreur
            return []

    async def _group_concepts_by_theme(
        self,
        consolidated_entries: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Groupe les concepts consolidés par similarité sémantique.

        Phase 3 - Priorité 3: Groupement thématique pour contexte plus concis.

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
            logger.warning(f"[ThematicGrouping] Erreur clustering: {e}", exc_info=True)
            # Fallback: retour sans groupement
            return {"ungrouped": consolidated_entries}

    def _extract_group_title(self, concepts: List[Dict[str, Any]]) -> str:
        """
        Extrait un titre représentatif pour un groupe de concepts.

        Phase 3 - Priorité 3: Extraction de titres intelligents.

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

        # Stop words simples (français + anglais)
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

    async def _build_temporal_history_context(
        self,
        thread_id: str,
        session_id: str,
        user_id: str,
        agent_id: Optional[str] = None,
        limit: int = 20,
        last_user_message: str = ""
    ) -> str:
        """
        Construit un contexte historique enrichi avec timestamps pour répondre
        aux questions temporelles (quand, quel jour, quelle heure).

        Récupère les messages du thread ET les concepts consolidés pertinents
        pour fournir un contexte temporel complet incluant l'historique archivé.
        """
        try:
            # Récupérer les messages du thread actif
            messages = await queries.get_messages(
                self.session_manager.db_manager,
                thread_id,
                session_id=session_id,
                user_id=user_id,
                limit=limit
            )

            lines = []
            # Pas de titre H3 ici, il sera ajouté par _merge_blocks() avec "Historique des sujets abordés"

            # ✅ Phase 3: Enrichir avec concepts consolidés (avec cache)
            # Utilise n_results dynamique basé sur le nombre de messages
            # Pour questions exhaustives ("tous", "résumer tout"), chercher plus de concepts
            is_exhaustive_query = bool(re.search(r'\b(tous|toutes|tout|exhaustif|complet|résumer tout)\b', last_user_message.lower()))
            if is_exhaustive_query:
                n_results = 50  # Pour questions exhaustives, chercher beaucoup plus de concepts
            else:
                n_results = min(5, max(3, len(messages) // 4)) if messages else 5

            consolidated_entries = []
            if last_user_message and user_id:
                # Utiliser la nouvelle méthode cachée (Phase 3)
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

            timeline_added = False
            if self.memory_query_tool and user_id:
                try:
                    max_topics_per_period = 6 if is_exhaustive_query else 3
                    timeline_limit = max(limit * 2, 20)
                    timeline = await self.memory_query_tool.get_conversation_timeline(
                        user_id=user_id,
                        limit=timeline_limit,
                        agent_id=agent_id
                    )
                    period_labels = {
                        "this_week": "**Cette semaine:**",
                        "last_week": "**Semaine dernière:**",
                        "this_month": "**Ce mois-ci:**",
                        "older": "**Plus ancien:**",
                    }
                    timeline_section: List[str] = []
                    for period in ("this_week", "last_week", "this_month", "older"):
                        topics = timeline.get(period, [])
                        if not topics:
                            continue
                        timeline_section.append(period_labels[period])
                        count = 0
                        for topic in topics:
                            timeline_section.append(f"- {topic.format_natural_fr()}")
                            count += 1
                            if count >= max_topics_per_period:
                                break
                        timeline_section.append("")
                    formatted_timeline = "\n".join(line for line in timeline_section if line.strip())
                    if formatted_timeline:
                        lines.append("**Synthèse chronologique consolidée :**")
                        lines.append("")
                        lines.append(formatted_timeline)
                        lines.append("")
                        timeline_added = True
                except Exception as timeline_err:
                    logger.warning(f"[TemporalHistory] Timeline consolidation échouée: {timeline_err}")

            # Préparer les messages du thread (pour affichage séparé)
            thread_events = []
            for msg in messages:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                created_at = msg.get("created_at")
                message_agent_id = msg.get("agent_id")

                # Ne garder que les messages utilisateur et assistant
                if role not in ["user", "assistant"]:
                    continue

                if created_at:
                    thread_events.append({
                        "timestamp": created_at,
                        "role": role,
                        "content": content,
                        "agent_id": message_agent_id,
                        "source": "thread"
                    })

            # Trier les messages par date (du plus ancien au plus récent)
            try:
                thread_events.sort(key=lambda x: datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00")))
            except Exception as sort_err:
                logger.debug(f"[TemporalHistory] Tri impossible: {sort_err}")

            # Formater les groupes thématiques
            months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                      "juil", "août", "sept", "oct", "nov", "déc"]

            if grouped_concepts and not timeline_added:
                lines.append("**Thèmes abordés:**")
                lines.append("")

                for group_id, concepts in grouped_concepts.items():
                    if group_id == "ungrouped":
                        # Pas de titre de groupe pour concepts non groupés
                        for concept in concepts:
                            try:
                                dt = datetime.fromisoformat(concept["timestamp"].replace("Z", "+00:00"))
                                date_str = f"{dt.day} {months[dt.month]} à {dt.hour}h{dt.minute:02d}"
                                preview = concept["content"]
                                lines.append(f"**[{date_str}] Mémoire ({concept['type']}) :** {preview}")
                            except Exception:
                                pass
                    else:
                        # Groupe thématique
                        title = self._extract_group_title(concepts)
                        count = len(concepts)
                        label = "échange" if count == 1 else "échanges"

                        lines.append(f"**[{title}]** Discussion récurrente ({count} {label})")

                        for concept in concepts:
                            try:
                                dt = datetime.fromisoformat(concept["timestamp"].replace("Z", "+00:00"))
                                date_str = f"{dt.day} {months[dt.month]} à {dt.hour}h{dt.minute:02d}"
                                # Preview raccourci pour groupes
                                preview = concept["content"][:60] + "..." if len(concept["content"]) > 60 else concept["content"]
                                lines.append(f"  - {date_str}: {preview}")
                            except Exception:
                                pass

                lines.append("")

            # Formater les messages récents (garder les 10 plus récents)
            if thread_events:
                lines.append("**Messages récents:**")
                recent_messages = thread_events[-10:] if len(thread_events) > 10 else thread_events

                for event in recent_messages:
                    try:
                        # Parser la date
                        dt = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                        day = dt.day
                        month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)
                        time_str = f"{dt.hour}h{dt.minute:02d}"
                        date_str = f"{day} {month} à {time_str}"

                        # Extraire un aperçu du contenu
                        content = event.get("content", "")
                        preview = content[:80].strip() if isinstance(content, str) else ""
                        if len(content) > 80:
                            preview += "..."

                        # Formater selon le rôle
                        role = event.get("role")
                        event_agent_id = event.get("agent_id")
                        if role == "user":
                            lines.append(f"**[{date_str}] Toi :** {preview}")
                        elif role == "assistant" and event_agent_id:
                            lines.append(f"**[{date_str}] {event_agent_id.title()} :** {preview}")
                    except Exception:
                        pass

            if len(consolidated_entries) > 0 or len(thread_events) > 0:
                logger.info(f"[TemporalHistory] Contexte enrichi: {len(thread_events)} messages + {len(consolidated_entries)} concepts consolidés ({len(grouped_concepts)} groupes)")

            # 🔥 FIX: Toujours retourner au moins une ligne (même si vide)
            # pour que le header "### Historique des sujets abordés" soit ajouté par _merge_blocks()
            # et que Anima le voie (règle anti-hallucination)
            if len(lines) == 0:
                return "*(Aucun sujet trouvé dans l'historique)*"

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"[TemporalHistory] Erreur construction contexte : {e}", exc_info=True)
            # Retourner quand même un message pour que le header soit ajouté
            return "*(Aucun sujet trouvé dans l'historique)*"

    def _fetch_mot_code_for_agent(self, agent_id: str, user_id: Optional[str]) -> Optional[str]:
        if self._knowledge_collection is None:
            knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
            self._knowledge_collection = self.vector_service.get_or_create_collection(knowledge_name)

        collection = self._knowledge_collection
        if collection is None:
            return None

        clauses = [{"type": "fact"}, {"key": "mot-code"}, {"agent": (agent_id or "").lower()}]
        if user_id:
            clauses.append({"user_id": user_id})
        where = {"$and": clauses}
        got = collection.get(where=where, include=["documents", "metadatas"])
        ids = got.get("ids", []) or []
        if not ids:
            got = collection.get(
                where={"$and": [{"type": "fact"}, {"key": "mot-code"}, {"agent": (agent_id or "").lower()}]},
                include=["documents", "metadatas"],
            )
            ids = got.get("ids", []) or []
            if not ids:
                return None
        docs = got.get("documents", []) or []
        if not docs:
            return None
        line = docs[0] or ""
        if ":" in line:
            try:
                return line.split(":", 1)[1].strip()
            except Exception:
                pass
        metas = got.get("metadatas", []) or []
        if metas and isinstance(metas[0], dict) and metas[0].get("value"):
            return str(metas[0]["value"]).strip()
        return None

    def _try_get_session_summary(self, session_id: str) -> str:
        try:
            sess = self.session_manager.get_session(session_id)
            meta = getattr(sess, "metadata", None)
            if isinstance(meta, dict):
                s = meta.get("summary")
                if isinstance(s, str) and s.strip():
                    return s.strip()
        except Exception:
            pass
        return ""

    async def _emit_proactive_hints_if_any(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        connection_manager: ConnectionManager
    ) -> None:
        """
        Generate and emit proactive hints after agent response (P2 Sprint 2).

        Args:
            session_id: Current session ID
            user_id: User identifier
            user_message: Last user message text
            connection_manager: WebSocket connection manager
        """
        if not self.hint_engine:
            return

        try:
            hints = await self.hint_engine.generate_hints(
                user_id=user_id,
                current_context={"message": user_message}
            )

            if hints:
                await connection_manager.send_personal_message(
                    {
                        "type": "ws:proactive_hint",
                        "payload": {
                            "hints": [h.to_dict() for h in hints]
                        }
                    },
                    session_id
                )

                logger.info(
                    f"[ProactiveHints] Emitted {len(hints)} hints for session {session_id[:8]} "
                    f"(types: {[h.type for h in hints]})"
                )

        except Exception as e:
            logger.error(f"[ProactiveHints] Failed to emit hints: {e}", exc_info=True)
            # Non-blocking: don't fail main flow

    async def _build_memory_context(
        self, session_id: str, last_user_message: str, top_k: int = 5, agent_id: Optional[str] = None
    ) -> str:
        """
        ✅ Phase 3 RAG : Recherche documentaire avec scoring multi-critères + formatage Phase 3.1

        Ordre de priorité :
        1. Documents (avec scoring multi-critères)
        2. Mémoire conversationnelle (fallback si pas de documents)
        """
        try:
            if not last_user_message:
                return ""

            uid = self._try_get_user_id(session_id)

            # ✅ Phase 3 RAG : Recherche dans les DOCUMENTS en priorité
            document_results = []
            if self.document_service:
                try:
                    # Parser l'intention utilisateur
                    intent = self._parse_user_intent(last_user_message)

                    # Rechercher dans les documents avec scoring Phase 3
                    document_results = self.document_service.search_documents(
                        query=intent.get("expanded_query", last_user_message),
                        session_id=session_id,
                        user_id=uid,
                        top_k=top_k,
                        intent=intent
                    )

                    if document_results:
                        logger.info(
                            f"RAG Phase 3: {len(document_results)} documents trouvés "
                            f"(intent: {intent.get('content_type', 'none')}, "
                            f"citation_integrale: {intent.get('wants_integral_citation', False)})"
                        )

                        # ✅ Phase 3.1: Formatter avec cadre visuel pour citations exactes
                        return self._format_rag_context(document_results)
                except Exception as e:
                    logger.error(f"Erreur recherche documents Phase 3: {e}", exc_info=True)

            # Fallback: Recherche dans la mémoire conversationnelle (ancien système)
            if self._knowledge_collection is None:
                knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
                self._knowledge_collection = self.vector_service.get_or_create_collection(knowledge_name)

            knowledge_col = self._knowledge_collection
            if knowledge_col is None:
                return ""
            where_filter = None

            session_clause: Dict[str, Any] = {
                "$or": [
                    {"session_id": session_id},
                    {"source_session_id": session_id},
                ]
            }
            clauses: List[Dict[str, Any]] = [session_clause]
            if uid:
                clauses.append({"user_id": uid})
            ag = (agent_id or "").strip().lower() if agent_id else ""
            if ag:
                clauses.append({"agent": ag})
            if len(clauses) == 1:
                where_filter = clauses[0]
            elif len(clauses) >= 2:
                where_filter = {"$and": clauses}

            results = self.vector_service.query(
                collection=knowledge_col,
                query_text=last_user_message,
                n_results=top_k,
                where_filter=where_filter,
            )

            if (not results) and ag and uid:
                try:
                    results = self.vector_service.query(
                        collection=knowledge_col,
                        query_text=last_user_message,
                        n_results=top_k,
                        where_filter={
                            "$and": [
                                {"session_id": session_id},
                                {"user_id": uid},
                                {"vitality": {"$gte": VITALITY_RECALL_THRESHOLD}},
                            ]
                        },
                    )
                except Exception:
                    pass

            if not results:
                return ""
            lines: List[str] = []
            touched_ids: List[str] = []
            touched_metas: List[Dict[str, Any]] = []
            touch_ts = datetime.now(timezone.utc).isoformat()

            for r in results:
                t = (r.get("text") or "").strip()
                if t:
                    lines.append(f"- {t}")
                vec_id = r.get("id")
                meta = r.get("metadata")
                if not vec_id or not isinstance(meta, dict):
                    continue
                updated_meta = dict(meta)
                prev_usage = updated_meta.get("usage_count", 0)
                try:
                    updated_meta["usage_count"] = int(prev_usage) + 1
                except Exception:
                    updated_meta["usage_count"] = 1
                prev_vitality = updated_meta.get("vitality", VITALITY_MAX)
                try:
                    prev_vitality = float(prev_vitality)
                except (TypeError, ValueError):
                    prev_vitality = VITALITY_MAX
                updated_meta["vitality"] = min(
                    VITALITY_MAX, round(prev_vitality + VITALITY_USAGE_BOOST, 4)
                )
                updated_meta["last_access_at"] = touch_ts
                if not updated_meta.get("session_id"):
                    updated_meta["session_id"] = session_id
                if not updated_meta.get("source_session_id"):
                    updated_meta["source_session_id"] = session_id
                if uid and not updated_meta.get("user_id"):
                    updated_meta["user_id"] = uid
                touched_ids.append(str(vec_id))
                touched_metas.append(updated_meta)
            if touched_ids and knowledge_col is not None:
                try:
                    self.vector_service.update_metadatas(knowledge_col, touched_ids, touched_metas)
                except Exception as err:
                    logger.warning(f"Impossible de mettre à jour la vitalité mémoire: {err}")
            return "\n".join(lines[:top_k])
        except Exception as e:
            logger.warning(f"build_memory_context: {e}")
            return ""

    # ---------- normalisation historique ----------
    def _normalize_history_for_llm(
        self,
        provider: str,
        history: List[Dict],
        rag_context: str = "",
        use_rag: bool = False,
        agent_id: Optional[str] = None,
    ) -> List[Dict]:
        normalized: List[Dict[str, Any]] = []
        # 🔥 FIX: Injecter le contexte même si use_rag=False quand c'est du contexte temporel
        # (pour les questions "résume sujets", Anima doit voir le header même si RAG désactivé)
        should_inject_context = rag_context and (use_rag or "Historique des sujets abordés" in rag_context)
        if should_inject_context:
            if provider == "google":
                normalized.append({"role": "user", "parts": [f"[RAG_CONTEXT]\n{rag_context}"]})
            else:
                normalized.append({"role": "user", "content": f"[RAG_CONTEXT]\n{rag_context}"})
        for m in history:
            role = m.get("role")
            text = m.get("content") or m.get("message") or ""
            if not text:
                continue
            if provider == "google":
                normalized.append({"role": "user" if role in (Role.USER, "user") else "model", "parts": [text]})
            else:
                normalized.append({"role": "user" if role in (Role.USER, "user") else "assistant", "content": text})
        return normalized

    @staticmethod
    def _normalize_openai_delta_content(raw: Any) -> str:
        """Return normalized text from OpenAI delta content."""
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        if isinstance(raw, list):
            parts: List[str] = []
            for item in raw:
                try:
                    if hasattr(item, 'text'):
                        text_value = getattr(item, 'text')
                    elif isinstance(item, dict):
                        text_value = item.get('text')
                    else:
                        text_value = None
                    if text_value:
                        parts.append(str(text_value))
                except Exception:
                    continue
            return ''.join(parts)
        try:
            return str(raw)
        except Exception:
            return ""

    async def _ensure_async_stream(
        self,
        stream_candidate: Any,
    ) -> AsyncIterator[str]:
        if inspect.isawaitable(stream_candidate):
            stream_candidate = await stream_candidate
        if hasattr(stream_candidate, "__aiter__"):
            return stream_candidate
        raise TypeError("LLM stream must be an awaitable or async iterable")

    # ---------- providers (stream) ----------
    async def _get_llm_response_stream(
        self, provider: str, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict
    ) -> AsyncGenerator[str, None]:
        if provider == "openai":
            streamer = self._get_openai_stream(model, system_prompt, history, cost_info_container)
        elif provider == "google":
            streamer = self._get_gemini_stream(model, system_prompt, history, cost_info_container)
        elif provider == "anthropic":
            streamer = self._get_anthropic_stream(model, system_prompt, history, cost_info_container)
        else:
            raise ValueError(f"Fournisseur LLM non supporté: {provider}")
        async for chunk in streamer:
            yield chunk

    async def _get_openai_stream(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": system_prompt}] + history
        usage_seen = False
        try:
            stream = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=DEFAULT_TEMPERATURE,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for event in stream:
                try:
                    delta = event.choices[0].delta
                    raw_content = getattr(delta, "content", None)
                    text = self._normalize_openai_delta_content(raw_content)
                    if text:
                        yield text
                except Exception:
                    pass
                usage = getattr(event, "usage", None)
                if usage and not usage_seen:
                    usage_seen = True
                    pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                    in_tok = getattr(usage, "prompt_tokens", 0)
                    out_tok = getattr(usage, "completion_tokens", 0)
                    cost_info_container.update(
                        {
                            "input_tokens": in_tok,
                            "output_tokens": out_tok,
                            "total_cost": (in_tok * pricing["input"]) + (out_tok * pricing["output"]),
                        }
                    )
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}", exc_info=True)
            raise

    async def _get_gemini_stream(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        try:
            model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
            resp = await model_instance.generate_content_async(
                history, stream=True, generation_config={"temperature": DEFAULT_TEMPERATURE}
            )
            async for chunk in resp:
                try:
                    text = getattr(chunk, "text", None)
                    if not text and getattr(chunk, "candidates", None):
                        cand = chunk.candidates[0]
                        if getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                            text = "".join([getattr(p, "text", "") or str(p) for p in cand.content.parts if p])
                    if text:
                        yield text
                except Exception:
                    pass
            # Gemini: coût non renvoyé en stream ? placeholders
            cost_info_container.setdefault("input_tokens", 0)
            cost_info_container.setdefault("output_tokens", 0)
            cost_info_container.setdefault("total_cost", 0.0)
        except Exception as e:
            logger.error(f"Gemini stream error: {e}", exc_info=True)
            raise

    async def _get_anthropic_stream(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        try:
            history_params = cast(List[MessageParam], history)
            async with self.anthropic_client.messages.stream(
                model=model,
                max_tokens=1500,
                temperature=DEFAULT_TEMPERATURE,
                system=system_prompt,
                messages=history_params,
            ) as stream:
                async for event in stream:
                    try:
                        if getattr(event, "type", "") == "content_block_delta":
                            delta = getattr(event, "delta", None)
                            if delta:
                                text = getattr(delta, "text", "") or ""
                                if text:
                                    yield text
                    except Exception:
                        pass
                try:
                    final = await stream.get_final_message()
                    usage = getattr(final, "usage", None)
                    if usage:
                        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                        in_tok = getattr(usage, "input_tokens", 0)
                        out_tok = getattr(usage, "output_tokens", 0)
                        cost_info_container.update(
                            {
                                "input_tokens": in_tok,
                                "output_tokens": out_tok,
                                "total_cost": (in_tok * pricing["input"]) + (out_tok * pricing["output"]),
                            }
                        )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Anthropic stream error: {e}", exc_info=True)
            raise

    # ---------- réponses structurées ----------
    async def get_structured_llm_response(self, agent_id: str, prompt: str, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        provider, model, system_prompt = self._get_agent_config(agent_id)
        system_prompt = self._ensure_fr_tutoiement(agent_id, provider, system_prompt)

        # Timeout configurable pour appels LLM (critique en prod)
        timeout_seconds = float(os.getenv("MEMORY_ANALYSIS_TIMEOUT", "30"))

        if provider == "google":
            model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
            schema_hint = json.dumps(json_schema, ensure_ascii=False)
            full_prompt = (
                f"{prompt}\n\nIMPORTANT: Réponds EXCLUSIVEMENT en JSON valide correspondant strictement à ce SCHÉMA : {schema_hint}"
            )
            try:
                google_resp = await asyncio.wait_for(
                    model_instance.generate_content_async([{"role": "user", "parts": [full_prompt]}]),
                    timeout=timeout_seconds
                )
                text = getattr(google_resp, "text", "") or ""
                try:
                    return json.loads(text) if text else {}
                except Exception:
                    m = re.search(r"\{.*\}", text, re.S)
                    return json.loads(m.group(0)) if m else {}
            except asyncio.TimeoutError:
                logger.warning(
                    f"[get_structured_llm_response] Timeout Google ({timeout_seconds}s) pour agent={agent_id}, prompt_len={len(prompt)}"
                )
                raise  # Propagate pour fallback analyzer
        elif provider == "openai":
            # ⚠️ OpenAI exige que le prompt contienne "json" pour response_format=json_object
            json_prompt = f"{prompt}\n\n**IMPORTANT: Réponds UNIQUEMENT en JSON valide.**"
            openai_resp = await self.openai_client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": json_prompt}],
            )
            content = (openai_resp.choices[0].message.content or "").strip()
            return json.loads(content) if content else {}
        elif provider == "anthropic":
            anthropic_resp = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=1500,
                temperature=0,
                system=system_prompt + "\n\nRéponds strictement en JSON valide.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = ""
            for block in getattr(anthropic_resp, "content", []) or []:
                t = getattr(block, "text", "") or ""
                if t:
                    text += t
            try:
                return json.loads(text)
            except Exception:
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0)) if m else {}
        return {}

    # ---------- pipeline chat (stream) ----------
    async def _process_agent_response_stream(
        self,
        session_id: str,
        agent_id: str,
        use_rag: bool,
        connection_manager: ConnectionManager,
        doc_ids: Optional[List[int]] = None,
        origin_agent_id: Optional[str] = None,
        opinion_request: Optional[Dict[str, Any]] = None,
    ):
        temp_message_id = str(uuid4())
        full_response_text = ""
        cost_info_container: Dict[str, Any] = {}
        model_used = ""
        rag_sources: List[Dict[str, Any]] = []
        uid = self._try_get_user_id(session_id)

        origin = (origin_agent_id or "").strip().lower()
        is_broadcast = origin == "global"

        try:
            start_payload: dict[str, Any] = {"agent_id": agent_id, "id": temp_message_id}
            if opinion_request:
                opinion_meta = dict(opinion_request.get("opinion_meta") or {})
                if opinion_request.get("source_agent_id") is not None:
                    opinion_meta.setdefault("source_agent_id", opinion_request.get("source_agent_id"))
                if opinion_request.get("target_message_id") is not None:
                    opinion_meta.setdefault("target_message_id", opinion_request.get("target_message_id"))
                if opinion_request.get("request_note_id"):
                    opinion_meta.setdefault("request_note_id", opinion_request.get("request_note_id"))
                if opinion_meta.get("request_id") and not opinion_meta.get("request_note_id"):
                    opinion_meta.setdefault("request_note_id", opinion_meta.get("request_id"))
                opinion_meta.setdefault("reviewer_agent_id", agent_id)
                opinion_meta.setdefault("agent_id", agent_id)
                meta_payload: dict[str, Any] = {"opinion": opinion_meta}
                start_payload["meta"] = meta_payload
            if is_broadcast:
                start_payload["broadcast_origin"] = origin
            await connection_manager.send_personal_message(
                {"type": "ws:chat_stream_start", "payload": start_payload}, session_id
            )

            raw_history = self.session_manager.get_full_history(session_id) or []
            history = [self._message_to_dict(m) for m in raw_history if m is not None]

            if opinion_request:
                instruction_text = (opinion_request.get("instruction") or "").strip()
                if instruction_text:
                    history.append({"role": Role.USER.value, "content": instruction_text})

            last_user_message_obj = next(
                (m for m in reversed(history) if self._is_user_role(m.get("role"))),
                None,
            )
            last_user_message = ""
            if last_user_message_obj:
                last_user_message = (
                    str(last_user_message_obj.get("content") or last_user_message_obj.get("message") or "")
                ).strip()

            selected_doc_ids = self._sanitize_doc_ids(doc_ids)
            if not selected_doc_ids and isinstance(last_user_message_obj, dict):
                selected_doc_ids = self._sanitize_doc_ids(last_user_message_obj.get("doc_ids"))

            thread_id = None
            try:
                thread_id = self.session_manager.get_thread_id_for_session(session_id)
            except Exception:
                thread_id = None

            uid = self._try_get_user_id(session_id)

            # 🆕 DÉTECTION CONCEPTS RÉCURRENTS + INJECTION PROACTIVE
            recall_context = ""
            if self.concept_recall_tracker and last_user_message and uid and thread_id:
                try:
                    message_id = str(uuid4())
                    recalls = await self.concept_recall_tracker.detect_recurring_concepts(
                        message_text=last_user_message,
                        user_id=uid,
                        thread_id=thread_id,
                        message_id=message_id,
                        session_id=session_id,
                    )
                    if recalls:
                        logger.info(
                            f"[ConceptRecall] {len(recalls)} récurrences détectées : "
                            f"{[r['concept_text'] for r in recalls]}"
                        )
                        # Construire contexte de récurrence pour injection
                        recall_context = self._build_recall_context(recalls)
                except Exception as recall_err:
                    logger.warning(f"[ConceptRecall] Détection échouée : {recall_err}")

            # 🆕 DÉTECTION QUESTIONS TEMPORELLES + ENRICHISSEMENT HISTORIQUE
            is_temporal = self._is_temporal_query(last_user_message)
            rag_metrics.record_temporal_query(is_temporal)

            # Variable séparée pour contexte temporel (évite confusion avec recall_context)
            temporal_context = ""
            # Pour les questions temporelles, prioriser le contexte temporel enrichi
            if is_temporal and uid and thread_id:
                try:
                    temporal_context = await self._build_temporal_history_context(
                        thread_id=thread_id,
                        session_id=session_id,
                        user_id=uid,
                        agent_id=agent_id,
                        limit=20,
                        last_user_message=last_user_message
                    )
                    if temporal_context:
                        # Enregistrer taille du contexte enrichi
                        context_size = len(temporal_context.encode('utf-8'))
                        rag_metrics.record_temporal_context_size(context_size)
                        logger.info(f"[TemporalQuery] Contexte historique enrichi pour question temporelle ({context_size} bytes)")
                except Exception as temporal_err:
                    logger.warning(f"[TemporalQuery] Enrichissement historique échoué : {temporal_err}")

            allowed_doc_ids: List[int] = []
            if thread_id:
                try:
                    rows = await queries.get_thread_docs(
                        self.session_manager.db_manager,
                        thread_id,
                        session_id,
                        user_id=uid,
                    )
                    for row in rows:
                        raw = row.get("doc_id")
                        if raw is None:
                            continue
                        try:
                            value = int(raw)
                        except (TypeError, ValueError):
                            continue
                        if value not in allowed_doc_ids:
                            allowed_doc_ids.append(value)
                except Exception as fetch_err:
                    logger.warning(
                        "Unable to fetch thread docs for %s: %s",
                        thread_id,
                        fetch_err,
                    )

            if allowed_doc_ids:
                filtered_doc_ids = [doc_id for doc_id in selected_doc_ids if doc_id in allowed_doc_ids]
                if selected_doc_ids and not filtered_doc_ids:
                    logger.info(
                        "Selected doc IDs are outside thread scope (session=%s thread=%s ids=%s)",
                        session_id,
                        thread_id,
                        selected_doc_ids,
                    )
                if not filtered_doc_ids:
                    filtered_doc_ids = allowed_doc_ids
                selected_doc_ids = filtered_doc_ids

            # Mot-code court-circuit
            if self._is_mot_code_query(last_user_message):
                mot_uid = uid or self._try_get_user_id(session_id)
                mot = self._fetch_mot_code_for_agent(agent_id, mot_uid)
                try:
                    stm_here = self._try_get_session_summary(session_id)
                    await connection_manager.send_personal_message(
                        {
                            "type": "ws:memory_banner",
                            "payload": {
                                "agent_id": agent_id,
                                "has_stm": bool(stm_here),
                                "ltm_items": 0,
                                "injected_into_prompt": False,
                                "stm_content": stm_here if stm_here else "",
                                "ltm_content": "",
                            },
                        },
                        session_id,
                    )
                except Exception:
                    pass

                if mot:
                    final_agent_message = AgentMessage(
                        id=temp_message_id,
                        session_id=session_id,
                        role=Role.ASSISTANT,
                        agent=agent_id,
                        message=mot,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        cost_info={},
                    )
                    await self.session_manager.add_message_to_session(session_id, final_agent_message)
                    payload = final_agent_message.model_dump(mode="json")
                    payload["agent_id"] = agent_id
                    if "message" in payload:
                        payload["content"] = payload.pop("message")
                    payload.setdefault("meta", {"provider": "memory", "model": "mot-code", "fallback": False})
                    await connection_manager.send_personal_message(
                        {"type": "ws:chat_stream_end", "payload": payload}, session_id
                    )
                    if os.getenv("EMERGENCE_AUTO_TEND", "1") != "0":
                        try:
                            db_manager = getattr(self.session_manager, "db_manager", None)
                            analyzer = getattr(self.session_manager, "memory_analyzer", None)
                            if db_manager and analyzer:
                                gardener = MemoryGardener(
                                    db_manager=db_manager,
                                    vector_service=self.vector_service,
                                    memory_analyzer=analyzer,
                                )
                                asyncio.create_task(
                                    gardener.tend_the_garden(
                                        consolidation_limit=3,
                                        session_id=session_id,
                                        agent_id=agent_id,  # 🆕 Phase Agent Memory
                                        user_id=mot_uid,
                                    )
                                )
                        except Exception:
                            pass
                    return

            # Mémoire (STM/LTM)
            stm = self._try_get_session_summary(session_id)
            ltm_block = (
                await self._build_memory_context(session_id, last_user_message, top_k=5, agent_id=agent_id)
                if last_user_message
                else ""
            )

            if use_rag:
                memory_context = self._merge_blocks([("Résumé de session", stm)]) if stm else ""
                ltm_count_for_banner = self._count_bullets(ltm_block)
            else:
                memory_context = self._merge_blocks([("Résumé de session", stm), ("Faits & souvenirs", ltm_block)])
                ltm_count_for_banner = self._count_bullets(ltm_block)

            injected = bool(memory_context and memory_context.strip())
            if injected:
                history = [{"role": Role.USER.value, "content": f"[MEMORY_CONTEXT]\n{memory_context}"}] + history

            try:
                await connection_manager.send_personal_message(
                    {
                        "type": "ws:memory_banner",
                        "payload": {
                            "agent_id": agent_id,
                            "has_stm": bool(stm),
                            "ltm_items": int(ltm_count_for_banner),
                            "injected_into_prompt": bool(injected),
                            "stm_content": stm if stm else "",
                            "ltm_content": ltm_block if ltm_block else "",
                        },
                    },
                    session_id,
                )
            except Exception:
                pass

            # RAG documents
            rag_context = ""
            should_search_docs = bool(use_rag and (last_user_message or selected_doc_ids))
            if should_search_docs:
                await connection_manager.send_personal_message(
                    {"type": "ws:rag_status", "payload": {"status": "searching", "agent_id": agent_id}}, session_id
                )
                if self._doc_collection is None:
                    self._doc_collection = self.vector_service.get_or_create_collection(config.DOCUMENT_COLLECTION_NAME)

                # ✅ Phase 2 RAG Milestone 4 : Détection d'intention utilisateur
                user_intent = self._parse_user_intent(last_user_message)
                logger.info(
                    f"[RAG Intent] content_type={user_intent.get('content_type')}, "
                    f"wants_integral={user_intent.get('wants_integral_citation')}, "
                    f"keywords={user_intent.get('keywords')}"
                )

                base_clauses: List[Dict[str, Any]] = [{"session_id": session_id}]
                if uid:
                    base_clauses.append({"user_id": uid})

                where_clauses: List[Dict[str, Any]] = list(base_clauses)

                # ✅ Phase 2 RAG Milestone 4 : Filtrage sémantique par type de contenu
                if user_intent.get('content_type'):
                    where_clauses.append({"chunk_type": user_intent['content_type']})
                    logger.info(f"[RAG Filter] Filtering by chunk_type={user_intent['content_type']}")

                # ✅ Phase 2 RAG Milestone 4 : Priorité aux chunks complets si citation intégrale demandée
                # MAIS rendre ce filtre optionnel pour ne pas trop restreindre
                if user_intent.get('wants_integral_citation'):
                    # On ne force pas is_complete=True car ça peut exclure des résultats pertinents
                    # On l'utilisera plutôt pour le tri/ranking plus tard
                    logger.info("[RAG Filter] Wants integral citation (will prioritize complete chunks in ranking)")

                if selected_doc_ids:
                    if len(selected_doc_ids) == 1:
                        doc_filter: Dict[str, Any] = {"document_id": selected_doc_ids[0]}
                    else:
                        doc_filter = {"$or": [{"document_id": did} for did in selected_doc_ids]}
                    where_clauses.append(doc_filter)

                if not where_clauses:
                    where_filter: Optional[Dict[str, Any]] = None
                elif len(where_clauses) == 1:
                    where_filter = where_clauses[0]
                else:
                    where_filter = {"$and": where_clauses}

                # ✅ Phase 2 RAG Milestone 4 : Utiliser requête expandue
                query_text = user_intent.get('expanded_query') or (last_user_message or "").strip()
                if not query_text and selected_doc_ids:
                    query_text = " ".join(f"document:{doc_id}" for doc_id in selected_doc_ids) or "selected documents"

                logger.info(f"[RAG Query] expanded_query='{query_text[:100]}...'")

                # ✅ Phase 3 RAG : Enregistrer métriques + vérifier cache
                rag_metrics.record_query(agent_id, has_intent=bool(user_intent.get('content_type')))
                if user_intent.get('content_type'):
                    rag_metrics.record_content_type_query(user_intent['content_type'])

                # Tenter de récupérer depuis le cache
                cached_result = self.rag_cache.get(
                    query_text, where_filter, agent_id, selected_doc_ids
                )

                if cached_result:
                    # Cache hit !
                    rag_metrics.record_cache_hit()
                    doc_hits = cached_result.get('doc_hits', [])
                    rag_sources = cached_result.get('rag_sources', [])
                    logger.info(f"[RAG Cache] HIT - Restored {len(doc_hits)} chunks from cache")
                else:
                    rag_sources = []
                    # Cache miss, exécuter la query
                    rag_metrics.record_cache_miss()

                    # ✅ Phase 1 Optimisation: Recherche hybride (vectorielle + BM25)
                    with rag_metrics.track_duration(rag_metrics.rag_query_phase3_duration_seconds):
                        raw_doc_hits = self.vector_service.hybrid_query(
                            collection=self._doc_collection,
                            query_text=query_text or " ",
                            n_results=30,  # Augmenté à 30 pour récupérer contenus longs fragmentés
                            where_filter=where_filter,
                            alpha=0.6,  # 60% vectoriel, 40% BM25 (équilibré)
                            score_threshold=0.2,  # Abaissé de 0.3 à 0.2 pour plus de résultats
                        )

                    # ✅ Phase 2 RAG Optimisation : Fusionner les chunks adjacents pour reconstituer contenus complets
                    # ✅ Phase 3 RAG Optimisation : Utiliser nouveau scoring multi-critères
                    with rag_metrics.track_duration(rag_metrics.rag_merge_duration_seconds):
                        doc_hits = self._merge_adjacent_chunks(
                            raw_doc_hits or [],
                            max_blocks=10,
                            user_intent=user_intent  # ✅ Passé pour scoring avancé
                        )

                    # Enregistrer le nombre de chunks fusionnés
                    raw_count = len(raw_doc_hits or [])
                    merged_count = len(doc_hits)
                    if merged_count < raw_count:
                        rag_metrics.record_chunks_merged(raw_count - merged_count)

                    # Construire rag_sources pour UI
                    for h in (doc_hits or []):
                        md = h.get("metadata") or {}
                        full_text = (h.get("text") or "").strip()

                        # ✅ Phase 1: Extraction intelligente de citation (phrases complètes)
                        excerpt = self._extract_relevant_excerpt(
                            full_text,
                            query_text,
                            max_length=300  # Plus long que les 220 précédents
                        )

                        # ✅ Phase 1: Highlighting des mots-clés pour l'UI
                        highlighted = self._highlight_keywords(excerpt, query_text)

                        # Récupérer le score de pertinence
                        score = h.get("distance", 0)

                        rag_sources.append(
                            {
                                "document_id": md.get("document_id"),
                                "filename": md.get("filename"),
                                "page": md.get("page"),
                                "section": md.get("section"),  # ✅ Section si disponible
                                "excerpt": excerpt,
                                "highlighted": highlighted,  # ✅ Version avec highlighting
                                "score": round(score, 3),  # ✅ Score de pertinence
                            }
                        )

                if allowed_doc_ids:
                    filtered_sources: List[Dict[str, Any]] = []
                    for source in rag_sources:
                        raw_doc_id = source.get("document_id")
                        if isinstance(raw_doc_id, (str, int)):
                            try:
                                doc_id_int = int(raw_doc_id)
                            except (TypeError, ValueError):
                                doc_id_int = None
                        else:
                            doc_id_int = None
                        if doc_id_int is None or doc_id_int in allowed_doc_ids:
                            filtered_sources.append(source)
                    rag_sources = filtered_sources

                # ✅ Phase 3 RAG : Stocker dans le cache si cache miss
                if not cached_result and doc_hits:
                    self.rag_cache.set(
                        query_text, where_filter, agent_id,
                        doc_hits, rag_sources, selected_doc_ids
                    )

                # ✅ Phase 3 RAG : Collecter métriques qualité
                if doc_hits:
                    # Diversité des sources (nombre de documents uniques)
                    unique_docs = len(set(
                        h.get('metadata', {}).get('document_id')
                        for h in doc_hits
                        if h.get('metadata', {}).get('document_id') is not None
                    ))

                    # Top score (premier résultat = meilleur)
                    top_score = doc_hits[0].get('distance', 0) if doc_hits else 0

                    # Mettre à jour l'agrégateur de métriques
                    self.rag_metrics_aggregator.add_result(
                        chunks_returned=len(doc_hits),
                        raw_chunks=len(raw_doc_hits or []) if not cached_result else len(doc_hits),
                        merged_blocks=len(doc_hits),
                        top_score=top_score,
                        unique_docs=unique_docs
                    )

                # ✅ Phase 2 RAG : Formater le contexte avec métadonnées sémantiques
                doc_block = self._format_rag_context(doc_hits or [])
                mem_block = await self._build_memory_context(session_id, last_user_message, agent_id=agent_id)

                # Injecter contexte de récurrence si détecté
                blocks_to_merge = []
                # Contexte temporel enrichi (pour questions "quels sujets", "résume conversations", etc.)
                if temporal_context:
                    blocks_to_merge.append(("Historique des sujets abordés", temporal_context))
                # Contexte de récurrence ponctuelle (pour concepts spécifiques récurrents)
                elif recall_context:
                    blocks_to_merge.append(("🔗 Connexions avec discussions passées", recall_context))
                if mem_block:
                    blocks_to_merge.append(("Mémoire (concepts clés)", mem_block))
                if doc_block:
                    blocks_to_merge.append(("Documents pertinents", doc_block))

                rag_context = self._merge_blocks(blocks_to_merge)
                await connection_manager.send_personal_message(
                    {"type": "ws:rag_status", "payload": {"status": "found", "agent_id": agent_id}}, session_id
                )

            # 🆕 INJECTION CONTEXTE TEMPOREL (même si use_rag=False)
            # Le contexte temporel doit être disponible pour les questions méta sur l'historique
            if temporal_context and not rag_context:
                # Si RAG n'a pas été activé mais qu'on a un contexte temporel, l'injecter quand même
                rag_context = self._merge_blocks([("Historique des sujets abordés", temporal_context)])

            raw_concat = "\n".join([(m.get("content") or m.get("message", "")) for m in history])
            raw_tokens = self._extract_sensitive_tokens(raw_concat)
            await connection_manager.send_personal_message(
                {
                    "type": "ws:debug_context",
                    "payload": {
                        "phase": "before_normalize",
                        "agent_id": agent_id,
                        "use_rag": use_rag,
                        "history_total": len(history),
                        "rag_context_chars": len(rag_context),
                        "off_policy": self.off_history_policy,
                        "sensitive_tokens_in_history": list(set(raw_tokens)),
                    },
                },
                session_id,
            )

            provider, model, system_prompt = self._get_agent_config(agent_id)
            primary_provider, primary_model = provider, model
            system_prompt = self._ensure_fr_tutoiement(agent_id, provider, system_prompt)
            model_used = primary_model

            # Récupération du nom de fichier du prompt pour debug UI
            bundle = self.prompts.get(agent_id) or self.prompts.get(agent_id.replace("_lite", "")) or {}
            prompt_file = bundle.get("file", "")

            try:
                await connection_manager.send_personal_message(
                    {
                        "type": "ws:model_info",
                        "payload": {
                            "agent_id": agent_id,
                            "id": temp_message_id,
                            "provider": primary_provider,
                            "model": primary_model,
                            "prompt_file": prompt_file,
                        },
                    },
                    session_id,
                )

                # 🆕 Handshake protocol: Send HELLO for agent-specific context sync
                if uid and hasattr(connection_manager, 'send_agent_hello'):
                    try:
                        await connection_manager.send_agent_hello(
                            session_id=session_id,
                            agent_id=agent_id,
                            model=primary_model,
                            provider=primary_provider,
                            user_id=uid
                        )
                    except Exception as hello_err:
                        logger.debug(f"[ChatService] HELLO handshake failed: {hello_err}")

            except Exception:
                pass
            logger.info(
                json.dumps(
                    {
                        "event": "model_info",
                        "agent_id": agent_id,
                        "session_id": session_id,
                        "provider": primary_provider,
                        "model": primary_model,
                        "prompt_file": prompt_file,
                    }
                )
            )

            normalized_history = self._normalize_history_for_llm(
                provider, history, rag_context, use_rag, agent_id
            )

            norm_concat = "\n".join(
                ["".join(p.get("parts", [])) if provider == "google" else p.get("content", "") for p in normalized_history]
            )
            norm_tokens = self._extract_sensitive_tokens(norm_concat)
            await connection_manager.send_personal_message(
                {
                    "type": "ws:debug_context",
                    "payload": {
                        "phase": "after_normalize",
                        "agent_id": agent_id,
                        "use_rag": use_rag,
                        "history_filtered": len(normalized_history),
                        "rag_context_chars": len(rag_context),
                        "off_policy": self.off_history_policy,
                        "sensitive_tokens_in_prompt": list(set(norm_tokens)),
                    },
                },
                session_id,
            )

            async def _stream_with(provider_name, model_name, hist):
                return await self._ensure_async_stream(
                    self._get_llm_response_stream(
                        provider_name, model_name, system_prompt, hist, cost_info_container
                    )
                )
            success = False
            try:
                async for chunk in (await _stream_with(primary_provider, primary_model, normalized_history)):
                    if not chunk:
                        continue
                    new_total, delta = self._compute_chunk_delta(full_response_text, chunk)
                    full_response_text = new_total
                    if not delta:
                        continue
                    try:
                        logger.info("chunk_debug primary raw=%r delta=%r", chunk, delta)
                    except Exception:
                        pass
                    chunk_payload = {"agent_id": agent_id, "id": temp_message_id, "chunk": delta}
                    if is_broadcast:
                        chunk_payload["broadcast_origin"] = origin
                    await connection_manager.send_personal_message(
                        {"type": "ws:chat_stream_chunk", "payload": chunk_payload},
                        session_id,
                    )
                model_used = primary_model
                success = True
            except Exception as e_primary:
                fallback_sequence = CHAT_PROVIDER_FALLBACKS.get(primary_provider, [])
                last_error = e_primary
                for prov2, model2 in fallback_sequence:
                    if prov2 == primary_provider:
                        continue
                    try:
                        await connection_manager.send_personal_message(
                            {
                                "type": "ws:model_fallback",
                                "payload": {
                                    "agent_id": agent_id,
                                    "id": temp_message_id,
                                    "from_provider": primary_provider,
                                    "from_model": primary_model,
                                    "to_provider": prov2,
                                    "to_model": model2,
                                    "reason": str(e_primary),
                                },
                            },
                            session_id,
                        )
                    except Exception:
                        pass
                    logger.warning(
                        json.dumps(
                            {
                                "event": "model_fallback",
                                "agent_id": agent_id,
                                "session_id": session_id,
                                "from_provider": primary_provider,
                                "from_model": primary_model,
                                "to_provider": prov2,
                                "to_model": model2,
                                "reason": str(e_primary),
                            }
                        )
                    )

                    norm2 = self._normalize_history_for_llm(prov2, history, rag_context, use_rag, agent_id)
                    try:
                        async for chunk in (await _stream_with(prov2, model2, norm2)):
                            if not chunk:
                                continue
                            new_total, delta = self._compute_chunk_delta(full_response_text, chunk)
                            full_response_text = new_total
                            if not delta:
                                continue
                            try:
                                logger.info("chunk_debug fallback raw=%r delta=%r", chunk, delta)
                            except Exception:
                                pass
                            chunk_payload = {"agent_id": agent_id, "id": temp_message_id, "chunk": delta}
                            if is_broadcast:
                                chunk_payload["broadcast_origin"] = origin
                            await connection_manager.send_personal_message(
                                {
                                    "type": "ws:chat_stream_chunk",
                                    "payload": chunk_payload,
                                },
                                session_id,
                            )
                        provider = prov2
                        model_used = model2
                        success = True
                        break
                    except Exception as e2:
                        last_error = e2
                        continue

                if not success:
                    raise last_error

            thread_id = None
            try:
                thread_id = self.session_manager.get_thread_id_for_session(session_id)
            except Exception:
                thread_id = None

            final_agent_message = AgentMessage(
                id=temp_message_id,
                session_id=session_id,
                role=Role.ASSISTANT,
                agent=agent_id,
                message=full_response_text,
                timestamp=datetime.now(timezone.utc).isoformat(),
                cost_info=cost_info_container,
            )
            message_meta = {
                "provider": provider,
                "model": model_used,
                "fallback": bool(provider != primary_provider),
                "persisted_by": "backend",
                "persisted_via": "ws",
                "thread_id": thread_id,
            }
            if opinion_request:
                opinion_meta = dict(opinion_request.get("opinion_meta") or {})
                if opinion_request.get("source_agent_id") is not None:
                    opinion_meta.setdefault("source_agent_id", opinion_request.get("source_agent_id"))
                if opinion_request.get("target_message_id") is not None:
                    opinion_meta.setdefault("target_message_id", opinion_request.get("target_message_id"))
                if opinion_request.get("request_note_id"):
                    opinion_meta.setdefault("request_note_id", opinion_request.get("request_note_id"))
                if opinion_meta.get("request_id") and not opinion_meta.get("request_note_id"):
                    opinion_meta.setdefault("request_note_id", opinion_meta.get("request_id"))
                opinion_meta.setdefault("reviewer_agent_id", agent_id)
                opinion_meta.setdefault("agent_id", agent_id)
                message_meta["opinion"] = opinion_meta
            if is_broadcast:
                message_meta["broadcast_origin"] = origin
                message_meta["source_agent"] = agent_id
            if selected_doc_ids:
                try:
                    message_meta["selected_doc_ids"] = selected_doc_ids
                except Exception:
                    pass
            if use_rag and rag_sources:
                try:
                    message_meta["sources"] = rag_sources
                except Exception:
                    pass
            final_agent_message.meta = message_meta
            await self.session_manager.add_message_to_session(session_id, final_agent_message)
            await self.cost_tracker.record_cost(
                agent=agent_id,
                model=model_used,
                input_tokens=cost_info_container.get("input_tokens", 0),
                output_tokens=cost_info_container.get("output_tokens", 0),
                total_cost=cost_info_container.get("total_cost", 0.0),
                feature="chat",
                session_id=session_id,
                user_id=uid,
            )
            payload = final_agent_message.model_dump(mode="json")
            payload["agent_id"] = agent_id
            if "message" in payload:
                payload["content"] = payload.pop("message")
            payload["meta"] = dict(message_meta)
            if is_broadcast:
                payload["meta"]["broadcast_origin"] = origin
                payload["meta"]["source_agent"] = agent_id
            if selected_doc_ids:
                try:
                    payload["meta"]["selected_doc_ids"] = selected_doc_ids
                except Exception:
                    pass
            try:
                if use_rag and rag_sources:
                    payload["meta"]["sources"] = rag_sources
            except Exception:
                pass

            if is_broadcast:
                payload["broadcast_origin"] = origin
            await connection_manager.send_personal_message(
                {"type": "ws:chat_stream_end", "payload": payload}, session_id
            )

            if os.getenv("EMERGENCE_AUTO_TEND", "1") != "0":
                db_manager = getattr(self.session_manager, "db_manager", None)
                analyzer = getattr(self.session_manager, "memory_analyzer", None)
                if db_manager and analyzer:
                    try:
                        gardener = MemoryGardener(
                            db_manager=db_manager,
                            vector_service=self.vector_service,
                            memory_analyzer=analyzer,
                        )
                        asyncio.create_task(
                            gardener.tend_the_garden(
                                consolidation_limit=3,
                                thread_id=thread_id,
                                session_id=session_id,
                                agent_id=agent_id,  # 🆕 Phase Agent Memory
                                user_id=uid or self._try_get_user_id(session_id),
                            )
                        )
                    except Exception:
                        pass

            # 🆕 P2 Sprint 2: Emit proactive hints after agent response
            if uid and last_user_message:
                asyncio.create_task(
                    self._emit_proactive_hints_if_any(
                        session_id=session_id,
                        user_id=uid,
                        user_message=last_user_message,
                        connection_manager=connection_manager
                    )
                )

        except Exception as e:
            logger.error(f"Erreur streaming {agent_id}: {e}", exc_info=True)
            try:
                await connection_manager.send_personal_message(
                    {"type": "ws:error", "payload": {"message": f"Erreur interne pour l'agent {agent_id}: {e}"}},
                    session_id,
                )
            except Exception as send_error:
                logger.error(
                    f"Impossible d'envoyer l'erreur au client (session {session_id}): {send_error}", exc_info=True
                )

    # ===========================
    # Débat (non-stream, async)
    # ===========================
    async def get_llm_response_for_debate(
        self,
        agent_id: str,
        prompt: str,
        *,
        system_override: Optional[str] = None,
        use_rag: bool = False,
        session_id: Optional[str] = None,
        history: Optional[List[Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        doc_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Réponse unique pour le pipeline Débat (non-stream).
        Retourne: {"text": str, "provider": str, "model": str, "fallback": bool, "cost_info": {...}}
        """
        provider, model, system_prompt = self._get_agent_config(agent_id)
        system_prompt = self._ensure_fr_tutoiement(agent_id, provider, system_override or system_prompt)

        rag_context = ""
        base_prompt = prompt or ""
        selected_doc_ids = self._sanitize_doc_ids(doc_ids)

        if use_rag and session_id and base_prompt:
            try:
                if self._doc_collection is None:
                    self._doc_collection = self.vector_service.get_or_create_collection(
                        config.DOCUMENT_COLLECTION_NAME
                    )
                base_clauses: List[Dict[str, Any]] = [{"session_id": session_id}]
                uid = self._try_get_user_id(session_id)
                if uid:
                    base_clauses.append({"user_id": uid})

                where_clauses: List[Dict[str, Any]] = list(base_clauses)
                if selected_doc_ids:
                    if len(selected_doc_ids) == 1:
                        doc_filter: Dict[str, Any] = {"document_id": selected_doc_ids[0]}
                    else:
                        doc_filter = {"$or": [{"document_id": did} for did in selected_doc_ids]}
                    where_clauses.append(doc_filter)

                if not where_clauses:
                    where_filter: Optional[Dict[str, Any]] = None
                elif len(where_clauses) == 1:
                    where_filter = where_clauses[0]
                else:
                    where_filter = {"$and": where_clauses}

                doc_hits = self.vector_service.query(
                    collection=self._doc_collection,
                    query_text=base_prompt,
                    where_filter=where_filter,
                )
                doc_block = "\n".join(
                    [f"- {h.get('text', '').strip()}" for h in (doc_hits or []) if h.get("text")]
                )
                if doc_block.strip():
                    rag_context = self._merge_blocks([("Documents pertinents", doc_block)])
            except Exception:
                pass

        raw_history: List[Dict[str, Any]] = []
        if history:
            for item in history:
                try:
                    if isinstance(item, ChatMessage):
                        raw_history.append({"role": item.role, "content": item.content})
                    elif isinstance(item, dict):
                        role = item.get("role")
                        content = item.get("content") or item.get("message")
                        if role and content:
                            raw_history.append({"role": role, "content": content})
                except Exception:
                    continue
        raw_history.append({"role": Role.USER, "content": base_prompt})

        async def run_once(provider_name: str, model_name: str) -> Tuple[str, Dict[str, Any]]:
            normalized = self._normalize_history_for_llm(
                provider_name,
                raw_history,
                rag_context,
                use_rag,
                agent_id,
            )
            local_cost: Dict[str, Any] = {}
            chunks: List[str] = []
            stream_iter = await self._ensure_async_stream(
                self._get_llm_response_stream(
                    provider_name,
                    model_name,
                    system_prompt,
                    normalized,
                    local_cost,
                )
            )
            async for chunk in stream_iter:
                if chunk:
                    chunks.append(chunk)
            return "".join(chunks), local_cost

        primary_provider, primary_model = provider, model
        provider_used = primary_provider
        model_used = primary_model
        fallback_used = False
        text = ""
        cost_info: Dict[str, Any] = {}

        try:
            text, cost_info = await run_once(primary_provider, primary_model)
        except Exception as e_primary:
            fallback_sequence = CHAT_PROVIDER_FALLBACKS.get(primary_provider, [])
            last_error: Exception = e_primary
            for prov2, model2 in fallback_sequence:
                if prov2 == primary_provider:
                    continue
                try:
                    text, cost_info = await run_once(prov2, model2)
                    provider_used = prov2
                    model_used = model2
                    fallback_used = True
                    logger.warning(
                        json.dumps(
                            {
                                "event": "model_fallback",
                                "agent_id": agent_id,
                                "session_id": session_id,
                                "from_provider": primary_provider,
                                "from_model": primary_model,
                                "to_provider": prov2,
                                "to_model": model2,
                                "reason": str(e_primary),
                            }
                        )
                    )
                    break
                except Exception as e2:
                    last_error = e2
                    continue
            else:
                logger.error(
                    f"get_llm_response_for_debate error (agent={agent_id}, provider={primary_provider}): {last_error}",
                    exc_info=True,
                )
                raise last_error

        if not isinstance(cost_info, dict):
            cost_info = {}
        cost_info.setdefault("input_tokens", 0)
        cost_info.setdefault("output_tokens", 0)
        cost_info.setdefault("total_cost", 0.0)

        try:
            if self.cost_tracker:
                await self.cost_tracker.record_cost(
                    agent=agent_id,
                    model=model_used,
                    input_tokens=int(cost_info.get("input_tokens", 0) or 0),
                    output_tokens=int(cost_info.get("output_tokens", 0) or 0),
                    total_cost=float(cost_info.get("total_cost", 0.0) or 0.0),
                    feature="debate",
                )
        except Exception:
            logger.debug("Impossible d'enregistrer le coût du débat", exc_info=True)

        return {
            "text": text.strip(),
            "provider": provider_used,
            "model": model_used,
            "fallback": fallback_used,
            "cost_info": cost_info,
        }


    # ---------- entrypoint WS ----------
    def process_user_message_for_agents(
        self,
        session_id: str,
        chat_request: Any,
        connection_manager: Optional[ConnectionManager] = None,
    ) -> None:
        def _get_value(key: str):
            if isinstance(chat_request, dict):
                return chat_request.get(key)
            return getattr(chat_request, key, None)

        agent_id = (_get_value('agent_id') or '').strip().lower()
        use_rag = bool(_get_value('use_rag'))
        doc_ids = self._sanitize_doc_ids(_get_value('doc_ids'))
        cm = connection_manager or getattr(self.session_manager, 'connection_manager', None)

        if not agent_id:
            logger.error('process_user_message_for_agents: agent_id manquant')
            return
        if cm is None:
            logger.error('process_user_message_for_agents: connection_manager manquant')
            return

        if agent_id == 'global':
            targets = [aid for aid in dict.fromkeys(self.broadcast_agents) if aid and aid != 'global']
            if not targets:
                targets = ['anima', 'neo', 'nexus']
            origin_marker = 'global'
        else:
            targets = [agent_id]
            origin_marker = None

        # ⚡ Optimisation Phase 2: Parallélisation des appels agents avec asyncio.gather
        tasks = [
            self._process_agent_response_stream(
                session_id,
                target_agent,
                use_rag,
                cm,
                doc_ids=list(doc_ids or []),
                origin_agent_id=origin_marker,
                opinion_request=None,
            )
            for target_agent in targets
        ]
        # Fire-and-forget: les tasks s'exécutent en parallèle sans bloquer
        for task in tasks:
            asyncio.create_task(task)



    def _build_opinion_instruction(
        self,
        *,
        target_agent_id: str,
        source_agent_id: Optional[str],
        message_text: str,
        user_prompt: Optional[str],
    ) -> str:
        target = (target_agent_id or "").strip().lower() or "anima"
        source = (source_agent_id or "").strip().lower()
        source_display = f"l'agent {source}" if source else "l'autre agent"
        answer = (message_text or "").strip()
        prompt = (user_prompt or "").strip()

        instruction_parts = [
            f"Tu es l'agent {target} d'Émergence. On sollicite ton avis expert sur la réponse ci-dessous fournie par {source_display}.",
            "Analyse la réponse pour vérifier sa justesse, sa pertinence et les éléments manquants. Rédige ton avis en français, dans le style propre à ton agent.",
            "Structure ta réponse en trois sections courtes :",
            "1. Lecture rapide : une phrase qui résume ton jugement global.",
            "2. Points solides : liste de points exacts ou utiles.",
            "3. Points à corriger : liste de corrections, risques ou compléments nécessaires.",
            "Termine par une recommandation actionnable (1 phrase).",
        ]

        if prompt:
            instruction_parts.extend(
                [
                    "Question utilisateur initiale :",
                    "<<<QUESTION>>>",
                    prompt,
                    "<<<FIN_QUESTION>>>",
                ]
            )

        if answer:
            instruction_parts.extend(
                [
                    "Réponse analysée :",
                    "<<<REPONSE>>>",
                    answer,
                    "<<<FIN_REPONSE>>>",
                ]
            )
        else:
            instruction_parts.append("Réponse analysée : (contenu vide)")

        if source:
            instruction_parts.append(
                f"Indique clairement si tu n'es pas d'accord avec {source} et propose une alternative concrète."
            )

        return "\n".join(part for part in instruction_parts if part)



    async def request_opinion(
        self,
        session_id: str,
        target_agent_id: str,
        source_agent_id: Optional[str],
        message_id: Optional[str],
        message_text: Optional[str],
        connection_manager: ConnectionManager,
        request_id: Optional[str] = None,
    ) -> None:
        target = (target_agent_id or '').strip().lower()
        if not target:
            logger.error('request_opinion: target agent missing')
            return
        if target == 'global':
            logger.warning('request_opinion: target agent "global" invalid, fallback anima')
            target = 'anima'
        if target not in self.broadcast_agents and target not in {'anima', 'neo', 'nexus'}:
            await connection_manager.send_personal_message(
                {
                    'type': 'ws:error',
                    'payload': {'message': f"Agent {target_agent_id!r} indisponible pour un avis."},
                },
                session_id,
            )
            return

        clean_source = (source_agent_id or '').strip().lower() or None

        original_message = None
        if message_id:
            try:
                original_message = self.session_manager.get_message_by_id(session_id, message_id)
            except Exception:
                original_message = None

        content = (message_text or '').strip()
        if not content and isinstance(original_message, dict):
            content = str(
                original_message.get('content')
                or original_message.get('message')
                or ''
            ).strip()

        if not content:
            await connection_manager.send_personal_message(
                {
                    'type': 'ws:error',
                    'payload': {'message': "Impossible de récupérer la réponse à analyser."},
                },
                session_id,
            )
            return

        user_prompt = None
        try:
            history = self.session_manager.get_full_history(session_id) or []
            if message_id and history:
                for idx, item in enumerate(history):
                    if not item:
                        continue
                    try:
                        if str(item.get('id')) == str(message_id):
                            for previous in reversed(history[:idx]):
                                if previous and str(previous.get('role') or '').lower().endswith('user'):
                                    user_prompt = (
                                        str(previous.get('content') or previous.get('message') or '')
                                    ).strip()
                                    if user_prompt:
                                        break
                            break
                    except Exception:
                        continue
        except Exception:
            user_prompt = None

        candidate_note_id = request_id or ""
        if isinstance(candidate_note_id, bytes):
            candidate_note_id = candidate_note_id.decode("utf-8", "ignore")
        note_id = str(candidate_note_id).strip() if candidate_note_id else ""
        if len(note_id) > 256:
            note_id = note_id[:256]
        note_id = note_id or str(uuid4())

        request_display = f"Avis demandé à {target} sur la réponse de {clean_source or 'cet agent'}."
        user_note = ChatMessage(
            id=note_id,
            session_id=session_id,
            role=Role.USER,
            agent=target,
            content=request_display,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cost=None,
            tokens=None,
            agents=None,
            use_rag=False,
        )
        user_note.meta = {
            "opinion_request": {
                "target_agent": target,
                "source_agent": clean_source,
                "requested_message_id": message_id,
                "request_id": note_id,
            }
        }
        try:
            await self.session_manager.add_message_to_session(session_id, user_note)
        except Exception:
            logger.warning('request_opinion: unable to persist user note for request', exc_info=True)

        instruction = self._build_opinion_instruction(
            target_agent_id=target,
            source_agent_id=clean_source,
            message_text=content,
            user_prompt=user_prompt,
        )

        opinion_meta = {
            'of_message_id': message_id,
            'source_agent_id': clean_source,
            'requested_at': datetime.now(timezone.utc).isoformat(),
            'request_note_id': note_id,
            'request_id': note_id,
            'reviewer_agent_id': target,
        }

        await self._process_agent_response_stream(
            session_id=session_id,
            agent_id=target,
            use_rag=False,
            connection_manager=connection_manager,
            doc_ids=[],
            origin_agent_id=None,
            opinion_request={
                "instruction": instruction,
                "opinion_meta": opinion_meta,
                "source_agent_id": clean_source,
                "target_message_id": message_id,
                "request_note_id": note_id,
            },
        )

    @staticmethod
    def _sanitize_doc_ids(raw_doc_ids: Any) -> List[int]:
        if raw_doc_ids is None:
            return []
        if isinstance(raw_doc_ids, (set, tuple)):
            raw_doc_ids = list(raw_doc_ids)
        elif not isinstance(raw_doc_ids, list):
            raw_doc_ids = [raw_doc_ids]

        sanitized: List[int] = []
        for item in raw_doc_ids:
            if item in (None, ""):
                continue
            try:
                value = int(str(item).strip())
            except (ValueError, TypeError):
                continue
            sanitized.append(value)

        unique: List[int] = []
        seen = set()
        for value in sanitized:
            if value in seen:
                continue
            seen.add(value)
            unique.append(value)
        return unique

    @staticmethod
    def _compute_chunk_delta(previous_text: str, raw_chunk: Optional[str]) -> Tuple[str, str]:
        if raw_chunk is None:
            return previous_text, ""
        try:
            chunk = str(raw_chunk)
        except Exception:
            chunk = ""
        if not chunk:
            return previous_text, ""
        if not previous_text:
            return chunk, chunk
        if chunk == previous_text:
            return previous_text, ""
        if chunk.startswith(previous_text):
            return chunk, chunk[len(previous_text):]
        if previous_text.startswith(chunk):
            return previous_text, ""
        if previous_text.endswith(chunk):
            return previous_text, ""

        max_overlap = min(len(chunk), len(previous_text))
        overlap = 0
        for size in range(max_overlap, 0, -1):
            if previous_text.endswith(chunk[:size]):
                overlap = size
                break
        if overlap:
            delta = chunk[overlap:]
            if not delta:
                return previous_text, ""
            return previous_text + delta, delta

        return previous_text + chunk, chunk

    # ---------- diverses ----------
    def _count_bullets(self, text: str) -> int:
        return sum(1 for line in (text or "").splitlines() if line.strip().startswith("- "))
