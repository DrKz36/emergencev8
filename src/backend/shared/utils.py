# src/backend/shared/utils.py
"""
Utilitaires partagés pour le backend
"""

import datetime
from enum import Enum
from uuid import UUID

def json_serializer(obj):
    """
    Serializer JSON pour les objets non-sérialisables par défaut.
    Gère les dates, les Enums et les UUIDs.
    """
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

    if isinstance(obj, Enum):
        return obj.value

    if isinstance(obj, UUID):
        return str(obj)

    # Si on ne sait pas comment le sérialiser, on lève une erreur claire.
    raise TypeError(f"Le type {type(obj)} n'est pas sérialisable en JSON")
