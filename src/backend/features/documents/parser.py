# src/backend/features/documents/parser.py
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Type, Optional

logger = logging.getLogger(__name__)


def _import_pymupdf():
    """
    Import lazily PyMuPDF (fitz).
    Returns the module or None if unavailable so the service keeps working
    with the pure-Python fallback.
    """
    try:
        import fitz  # type: ignore[import-untyped]
        return fitz
    except ModuleNotFoundError:
        logger.warning("PyMuPDF (fitz) non installe - fallback PyPDF2 pour les PDF.")
        return None
    except Exception as exc:  # pragma: no cover - defensive log
        logger.warning(
            "Import PyMuPDF impossible - fallback PyPDF2 sera utilise: %s", exc
        )
        return None


def _import_pypdf_reader() -> Optional[Any]:
    """Import lazily PyPDF2.PdfReader, returns the class or None."""
    try:
        from PyPDF2 import PdfReader
        return PdfReader
    except Exception as exc:  # pragma: no cover - defensive log
        logger.error("Import PyPDF2 impossible: %s", exc, exc_info=True)
        return None


def _import_docx():
    """Import lazily python-docx to avoid crashing the whole service if missing."""
    try:
        import docx
        return docx
    except Exception as exc:
        logger.error("Import python-docx impossible: %s", exc, exc_info=True)
        raise


class FileParser(ABC):
    """
    Interface abstraite pour tous les parseurs de fichiers.
    """

    @abstractmethod
    def parse(self, filepath: str) -> str:
        """
        Extrait le contenu textuel d'un fichier.
        """
        raise NotImplementedError


class PDFParser(FileParser):
    """Parseur pour les fichiers PDF."""

    def parse(self, filepath: str) -> str:
        fitz_module = _import_pymupdf()
        if fitz_module:
            try:
                doc = fitz_module.open(filepath)
                text_parts = [page.get_text() for page in doc]
                full_text = "".join(text_parts)
                doc.close()
                if not full_text.strip():
                    logger.warning(
                        "Le fichier PDF '%s' ne contient aucun texte extractible.",
                        filepath,
                    )
                    return ""
                return full_text
            except Exception as e:
                logger.error("Echec du parsing PyMuPDF pour '%s': %s", filepath, e)
                raise

        # Fallback PyPDF2 lorsque PyMuPDF est absent
        pdf_reader_cls = _import_pypdf_reader()
        if pdf_reader_cls is None:
            raise RuntimeError(
                "Aucun parseur PDF disponible (PyMuPDF/PyPDF2 manquants)."
            )

        try:
            reader = pdf_reader_cls(filepath)
            text_parts = []
            for idx, page in enumerate(reader.pages):
                try:
                    text_parts.append(page.extract_text() or "")
                except Exception as page_err:  # pragma: no cover - best-effort log
                    logger.warning(
                        "Extraction texte impossible page %s du PDF '%s': %s",
                        idx,
                        filepath,
                        page_err,
                    )
            full_text = "".join(text_parts)
            if not full_text.strip():
                logger.warning(
                    "Le fichier PDF '%s' ne contient aucun texte extractible (fallback PyPDF2).",
                    filepath,
                )
            return full_text
        except Exception as e:
            logger.error("Echec du parsing PDF (fallback PyPDF2) '%s': %s", filepath, e)
            raise


class TXTParser(FileParser):
    """Parseur pour les fichiers texte bruts."""

    def parse(self, filepath: str) -> str:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error("Echec de la lecture du fichier texte '%s': %s", filepath, e)
            raise


class DocxParser(FileParser):
    """Parseur pour les fichiers DOCX."""

    def parse(self, filepath: str) -> str:
        docx_module = _import_docx()
        try:
            doc = docx_module.Document(filepath)
            full_text = [para.text for para in doc.paragraphs]
            return "\n".join(full_text)
        except Exception as e:
            logger.error("Echec du parsing du DOCX '%s': %s", filepath, e)
            raise


class ParserFactory:
    """
    Factory pour obtenir le parseur approprie en fonction de l'extension du fichier.
    """

    def __init__(self):
        self._parsers: Dict[str, Type[FileParser]] = {
            ".pdf": PDFParser,
            ".txt": TXTParser,
            ".docx": DocxParser,
        }
        logger.info(
            "ParserFactory initialisee avec les parseurs : %s",
            list(self._parsers.keys()),
        )

    def get_parser(self, file_type: str) -> FileParser:
        """
        Recupere une instance du parseur approprie.
        """
        parser_class = self._parsers.get(file_type.lower())
        if not parser_class:
            logger.error("Aucun parseur trouve pour le type de fichier : %s", file_type)
            raise ValueError(f"Type de fichier non supporte : {file_type}")
        return parser_class()


# --- Singleton pour la factory ---
_parser_factory_instance = None


def get_parser_factory():
    global _parser_factory_instance
    if _parser_factory_instance is None:
        _parser_factory_instance = ParserFactory()
    return _parser_factory_instance
