# src/backend/shared/exceptions.py
# V1.1 - Ajout de TemporalSearchException

class LifespanException(Exception):
    """
    Exception spécifique levée lors d'erreurs critiques pendant
    le cycle de vie (startup/shutdown) de l'application.
    """
    pass

class UserFriendlyException(Exception):
    """
    Exception générique pour les erreurs qui doivent être affichées
    à l'utilisateur final de manière compréhensible.
    """
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)

class TemporalSearchException(Exception):
    """
    Exception spécifique levée lors d'une erreur dans le service TemporalSearch.
    """
    pass
