# src/backend/core/config.py
# Fichier de configuration central pour l'application Émergence.
# Élimine les "magic strings" et centralise les paramètres clés.

# --- Modèles d'IA ---
# Modèle par défaut utilisé pour les générations de texte.
DEFAULT_MODEL = "gemini-1.5-flash"

# --- Noms des Features pour le Suivi des Coûts ---
# Utilisé pour tracker les coûts liés aux conversations simples.
FEATURE_CHAT = "chat"

# Utilisé pour tracker les coûts des conversations augmentées par RAG.
# Note: Ce nom est aligné sur la contrainte BDD existante.
FEATURE_CHAT_RAG = "chat"

# Utilisé pour tracker les coûts liés au traitement et à l'indexation des documents.
FEATURE_DOCUMENT_PROCESSING = "document_processing"


# --- Configuration du Traitement des Documents ---
# Taille des morceaux de texte pour la vectorisation.
CHUNK_SIZE = 1000

# Chevauchement entre les morceaux de texte.
CHUNK_OVERLAP = 150

# Nom de la collection dans le service vectoriel pour les documents.
DOCUMENT_COLLECTION_NAME = "emergence_documents"
