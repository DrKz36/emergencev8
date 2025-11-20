# src/backend/features/chat/prompt_service.py
"""
PromptService - Prompt Loading & Agent Configuration

Extracted from ChatService to handle all prompt-related operations:
- Load prompts from files with versioning (v3 > v2 > lite)
- Resolve agent configurations from settings
- Apply French tutoiement style rules
- Provide (provider, model, system_prompt) tuples

✅ Phase 3 of ChatService decomposition
"""

import os
import glob
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

from backend.shared.app_settings import Settings, DEFAULT_AGENT_CONFIGS

logger = logging.getLogger(__name__)


def _normalize_provider(p: str | None) -> str:
    """Normalize provider name to standard form."""
    if not p:
        return ""
    p_lower = p.strip().lower()
    if p_lower in ("openai", "oai"):
        return "openai"
    if p_lower in ("google", "gemini", "vertex"):
        return "google"
    if p_lower in ("anthropic", "claude"):
        return "anthropic"
    return p_lower


class PromptService:
    """
    Handles prompt loading, agent configuration, and style rule application.
    
    🎯 Responsibilities:
    - Load prompts from markdown files with versioning
    - Resolve agent configurations (provider, model)
    - Apply French tutoiement style rules
    - Provide complete agent config tuples
    """
    
    def __init__(self, settings: Settings, prompts_dir: str):
        """
        Initialize PromptService.
        
        Args:
            settings: Application settings with agent configs
            prompts_dir: Directory containing prompt markdown files
        """
        self.settings = settings
        self.prompts_dir = prompts_dir
        self.prompts = self._load_prompts(prompts_dir)
        logger.info(f"PromptService initialized with {len(self.prompts)} prompts")
    
    def _load_prompts(self, prompts_dir: str) -> Dict[str, Dict[str, str]]:
        """
        Retourne un mapping agent_id -> {"text": <prompt>, "file": <nom_fichier>}
        en choisissant la variante de poids maximum (v3 > v2 > lite par nom).
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
        
        return {
            aid: {"text": meta["text"], "file": meta["file"]}
            for aid, meta in chosen.items()
        }
    
    def _resolve_agent_configs(self) -> Dict[str, Dict[str, Any]]:
        """Merge DEFAULT_AGENT_CONFIGS with settings.agents."""
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
    
    def get_agent_config(self, agent_id: str) -> Tuple[str, str, str]:
        """
        Retourne (provider, model, system_prompt) en respectant settings.agents.
        
        Possibilité d'override économique pour AnimA via ENV:
          - EMERGENCE_FORCE_CHEAP_ANIMA=1  -> force openai:gpt-4o-mini
        
        Args:
            agent_id: ID de l'agent (anima, neo, nexus, etc.)
            
        Returns:
            Tuple (provider, model, system_prompt) avec style appliqué
        """
        clean_agent_id = (agent_id or "").replace("_lite", "")
        agent_configs = self._resolve_agent_configs()

        provider_raw = agent_configs.get(clean_agent_id, {}).get("provider")
        model = agent_configs.get(clean_agent_id, {}).get("model")
        provider = _normalize_provider(provider_raw)

        # ENV toggle pour protéger les coûts
        if (
            clean_agent_id == "anima"
            and os.getenv("EMERGENCE_FORCE_CHEAP_ANIMA", "0").strip() == "1"
        ):
            provider = "openai"
            model = "gpt-4o-mini"
            logger.info("Override coût activé (ENV): anima → openai:gpt-4o-mini")

        # Fallback order
        fallback_order = []
        if clean_agent_id in agent_configs:
            fallback_order.append(clean_agent_id)
        if "default" in agent_configs and "default" not in fallback_order:
            fallback_order.append("default")
        if "anima" in agent_configs and "anima" not in fallback_order:
            fallback_order.append("anima")
        fallback_order.extend(
            [k for k in agent_configs.keys() if k not in fallback_order]
        )

        resolved_id = None
        for candidate in fallback_order:
            cfg = agent_configs.get(candidate, {})
            cand_provider = (
                provider
                if candidate == clean_agent_id
                else _normalize_provider(cfg.get("provider"))
            )
            cand_model = model if candidate == clean_agent_id else cfg.get("model")
            if not cand_provider or not cand_model:
                continue
            resolved_id = candidate
            provider = cand_provider
            model = cand_model
            if candidate != clean_agent_id:
                logger.warning(
                    "Agent '%s' non configuré, fallback sur '%s'", agent_id, candidate
                )
            break

        # Get prompt bundle
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

        # Apply French tutoiement style rules
        system_prompt = self.apply_style_rules(agent_id, provider, system_prompt)

        return provider, model, system_prompt
    
    def apply_style_rules(
        self, agent_id: str, provider: str, system_prompt: str
    ) -> str:
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

        # Place before agent prompt for maximum effect
        return f"""{style_rules}
{system_prompt}""".strip()
