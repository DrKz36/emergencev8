# src/backend/features/documents/parser.py
import logging
from abc import ABC, abstractmethod
from typing import Dict, Type

# --- Dépendances ---
import fitz  # type: ignore[import-untyped]  # PyMuPDF
import docx  # ✅ NOUVEAU : Pour lire les .docx

logger = logging.getLogger(__name__)


class FileParser(ABC):
    """
    Interface abstraite pour tous les parseurs de fichiers.
    """

    @abstractmethod
    def parse(self, filepath: str) -> str:
        """
        Extrait le contenu textuel d'un fichier.
        """
        pass


class PDFParser(FileParser):
    """Parseur pour les fichiers PDF."""

    def parse(self, filepath: str) -> str:
        try:
            doc = fitz.open(filepath)
            text_parts = [page.get_text() for page in doc]
            full_text = "".join(text_parts)
            doc.close()
            if not full_text.strip():
                logger.warning(
                    f"Le fichier PDF '{filepath}' ne contient aucun texte extractible."
                )
                return ""
            return full_text
        except Exception as e:
            logger.error(f"Échec du parsing du PDF '{filepath}': {e}")
            raise


class TXTParser(FileParser):
    """Parseur pour les fichiers texte bruts."""

    def parse(self, filepath: str) -> str:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Échec de la lecture du fichier texte '{filepath}': {e}")
            raise


# ✅ NOUVEAU : Le parseur pour les fichiers .docx
class DocxParser(FileParser):
    """Parseur pour les fichiers DOCX."""

    def parse(self, filepath: str) -> str:
        try:
            doc = docx.Document(filepath)
            full_text = [para.text for para in doc.paragraphs]
            return "\n".join(full_text)
        except Exception as e:
            logger.error(f"Échec du parsing du DOCX '{filepath}': {e}")
            raise


class ParserFactory:
    """
    Factory pour obtenir le parseur approprié en fonction de l'extension du fichier.
    """

    def __init__(self):
        self._parsers: Dict[str, Type[FileParser]] = {
            ".pdf": PDFParser,
            ".txt": TXTParser,
            ".docx": DocxParser,  # ✅ On l'ajoute à la liste
        }
        logger.info(
            f"ParserFactory initialisée avec les parseurs : {list(self._parsers.keys())}"
        )

    def get_parser(self, file_type: str) -> FileParser:
        """
        Récupère une instance du parseur approprié.
        """
        parser_class = self._parsers.get(file_type.lower())
        if not parser_class:
            logger.error(f"Aucun parseur trouvé pour le type de fichier : {file_type}")
            raise ValueError(f"Type de fichier non supporté : {file_type}")
        return parser_class()


# --- Singleton pour la factory ---
_parser_factory_instance = None


def get_parser_factory():
    global _parser_factory_instance
    if _parser_factory_instance is None:
        _parser_factory_instance = ParserFactory()
    return _parser_factory_instance
