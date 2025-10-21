"""Tests de vérification des dépendances Python critiques."""

from __future__ import annotations

import importlib.util


DEPENDENCIES = [
    ("fastapi", "FastAPI"),
    ("pytest", "Pytest"),
]


def test_python_core_dependencies() -> None:
    """Vérifie que les dépendances Python principales sont installées."""
    print("\n📦 Test imports Python...")
    missing = []

    for module_name, display_name in DEPENDENCIES:
        if importlib.util.find_spec(module_name) is None:
            print(f"❌ {display_name} manquant")
            missing.append(display_name)
        else:
            print(f"✅ {display_name} installé")

    if missing:
        joined = ", ".join(missing)
        raise AssertionError(
            "Dépendances Python manquantes: " + joined,
        )
