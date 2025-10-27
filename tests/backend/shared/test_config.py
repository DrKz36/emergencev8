from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "src"))

from backend.shared.app_settings import Settings


@pytest.fixture(autouse=True)
def clear_api_env(monkeypatch):
    for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def make_settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_settings_uses_gemini_key_when_google_missing():
    settings = make_settings(
        openai_api_key="sk-openai",
        anthropic_api_key="sk-anthropic",
        gemini_api_key="sk-gemini",
    )

    assert settings.google_api_key == "sk-gemini"
    assert settings.gemini_api_key == "sk-gemini"


def test_settings_requires_google_or_gemini_key():
    with pytest.raises(ValueError) as exc:
        make_settings(
            openai_api_key="sk-openai",
            anthropic_api_key="sk-anthropic",
        )

    assert "GOOGLE_API_KEY or GEMINI_API_KEY" in str(exc.value)


def test_settings_propagates_google_key_to_gemini():
    settings = make_settings(
        openai_api_key="sk-openai",
        anthropic_api_key="sk-anthropic",
        google_api_key="sk-google",
    )

    assert settings.google_api_key == "sk-google"
    assert settings.gemini_api_key == "sk-google"
