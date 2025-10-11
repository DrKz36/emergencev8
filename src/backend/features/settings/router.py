# src/backend/features/settings/router.py
# API endpoints for application settings

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
import json
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["Settings"])

# Path to settings file (persistent storage)
SETTINGS_FILE = os.path.join(
    os.path.dirname(__file__),
    "../../../data/settings.json"
)


# ============================================================
# Models
# ============================================================

class RAGSettings(BaseModel):
    """RAG system configuration"""
    strict_mode: bool = Field(default=False, description="Enable strict RAG mode (filter by threshold)")
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum score threshold for results")


class ModelSettings(BaseModel):
    """Model configuration for agents"""
    model: str = Field(default="gpt-4", description="Model ID")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2000, ge=100, le=32000)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)


# ============================================================
# Storage Helpers
# ============================================================

def load_settings() -> Dict[str, Any]:
    """Load settings from file"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
    return {}


def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to file"""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        logger.info(f"Settings saved to {SETTINGS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise


# ============================================================
# RAG Settings Endpoints
# ============================================================

@router.get("/rag")
async def get_rag_settings() -> RAGSettings:
    """
    Get current RAG settings.
    """
    try:
        all_settings = load_settings()
        rag_settings = all_settings.get("rag", {})

        return RAGSettings(
            strict_mode=rag_settings.get("strict_mode", False),
            score_threshold=rag_settings.get("score_threshold", 0.7)
        )
    except Exception as e:
        logger.error(f"Failed to get RAG settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get RAG settings: {str(e)}")


@router.post("/rag")
async def update_rag_settings(settings: RAGSettings) -> Dict[str, str]:
    """
    Update RAG settings.
    """
    try:
        all_settings = load_settings()
        all_settings["rag"] = settings.dict()
        save_settings(all_settings)

        logger.info(f"RAG settings updated: {settings.dict()}")

        return {
            "status": "success",
            "message": "RAG settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update RAG settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update RAG settings: {str(e)}")


# ============================================================
# Model Settings Endpoints
# ============================================================

@router.get("/models")
async def get_model_settings() -> Dict[str, ModelSettings]:
    """
    Get model settings for all agents.
    """
    try:
        all_settings = load_settings()
        model_settings = all_settings.get("models", {})

        # Convert to ModelSettings objects
        result = {}
        for agent_id, config in model_settings.items():
            result[agent_id] = ModelSettings(**config)

        return result
    except Exception as e:
        logger.error(f"Failed to get model settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get model settings: {str(e)}")


@router.post("/models")
async def update_model_settings(settings: Dict[str, ModelSettings]) -> Dict[str, str]:
    """
    Update model settings for agents.
    """
    try:
        all_settings = load_settings()

        # Convert ModelSettings to dict
        models_dict = {}
        for agent_id, config in settings.items():
            models_dict[agent_id] = config.dict()

        all_settings["models"] = models_dict
        save_settings(all_settings)

        logger.info(f"Model settings updated for {len(settings)} agents")

        return {
            "status": "success",
            "message": f"Model settings updated for {len(settings)} agents"
        }
    except Exception as e:
        logger.error(f"Failed to update model settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update model settings: {str(e)}")


# ============================================================
# General Settings Endpoints
# ============================================================

@router.get("/all")
async def get_all_settings() -> Dict[str, Any]:
    """
    Get all application settings.
    """
    try:
        return load_settings()
    except Exception as e:
        logger.error(f"Failed to get all settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")


@router.delete("/all")
async def reset_all_settings() -> Dict[str, str]:
    """
    Reset all settings to defaults.
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            os.remove(SETTINGS_FILE)
            logger.info("All settings reset to defaults")

        return {
            "status": "success",
            "message": "All settings reset to defaults"
        }
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset settings: {str(e)}")
