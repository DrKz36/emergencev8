"""
Guardian Cloud Storage Service
Gère upload/download des rapports Guardian vers Cloud Storage
Permet persistence des rapports entre redémarrages Cloud Run
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional, cast
import os

logger = logging.getLogger("emergence.guardian.storage")

# Configuration
BUCKET_NAME = os.getenv("GUARDIAN_BUCKET_NAME", "emergence-guardian-reports")
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "emergence-469005")

# Try to import Cloud Storage (optional dependency)
try:
    from google.cloud import storage  # type: ignore[attr-defined]
    GCS_AVAILABLE = True
except ImportError:
    logger.warning("google-cloud-storage not installed - Cloud Storage disabled")
    GCS_AVAILABLE = False


class GuardianStorageService:
    """Service pour stocker/récupérer rapports Guardian sur Cloud Storage"""

    def __init__(self, bucket_name: str = BUCKET_NAME, use_local_fallback: bool = True):
        """
        Initialize Guardian Storage Service

        Args:
            bucket_name: GCS bucket name for reports
            use_local_fallback: Use local filesystem if GCS not available
        """
        self.bucket_name = bucket_name
        self.use_local_fallback = use_local_fallback
        self.client = None
        self.bucket = None

        # Local fallback directory
        self.local_reports_dir = Path(__file__).parent.parent.parent.parent.parent / "reports"

        if GCS_AVAILABLE:
            try:
                self.client = storage.Client(project=PROJECT_ID)
                self.bucket = self.client.bucket(bucket_name)
                logger.info(f"GuardianStorageService initialized with bucket: {bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                if not use_local_fallback:
                    raise
        else:
            logger.warning("Cloud Storage not available - using local fallback only")

    def upload_report(self, report_name: str, report_data: dict[str, Any]) -> bool:
        """
        Upload rapport Guardian vers Cloud Storage

        Args:
            report_name: Nom du fichier (e.g., 'prod_report.json')
            report_data: Données du rapport (dict)

        Returns:
            True if success, False otherwise
        """
        try:
            # Try Cloud Storage first
            if self.bucket:
                blob = self.bucket.blob(f"reports/{report_name}")
                json_data = json.dumps(report_data, indent=2, ensure_ascii=False)
                blob.upload_from_string(
                    json_data,
                    content_type="application/json"
                )
                logger.info(f"✅ Uploaded {report_name} to gs://{self.bucket_name}/reports/")
                return True

            # Fallback to local
            elif self.use_local_fallback:
                self.local_reports_dir.mkdir(parents=True, exist_ok=True)
                local_path = self.local_reports_dir / report_name
                with open(local_path, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False)
                logger.info(f"✅ Saved {report_name} locally (GCS unavailable)")
                return True

            else:
                logger.error(f"Cannot upload {report_name} - no storage backend available")
                return False

        except Exception as e:
            logger.error(f"Error uploading {report_name}: {e}", exc_info=True)

            # Fallback to local on error
            if self.use_local_fallback:
                try:
                    self.local_reports_dir.mkdir(parents=True, exist_ok=True)
                    local_path = self.local_reports_dir / report_name
                    with open(local_path, 'w', encoding='utf-8') as f:
                        json.dump(report_data, f, indent=2, ensure_ascii=False)
                    logger.info(f"✅ Saved {report_name} locally (GCS error fallback)")
                    return True
                except Exception as local_error:
                    logger.error(f"Local fallback also failed: {local_error}")

            return False

    def download_report(self, report_name: str) -> Optional[dict[str, Any]]:
        """
        Download rapport Guardian depuis Cloud Storage

        Args:
            report_name: Nom du fichier (e.g., 'prod_report.json')

        Returns:
            Report data as dict, or None if not found
        """
        try:
            # Try Cloud Storage first
            if self.bucket:
                blob = self.bucket.blob(f"reports/{report_name}")

                if not blob.exists():
                    logger.warning(f"Report {report_name} not found in Cloud Storage")
                    # Try local fallback
                    if self.use_local_fallback:
                        return self._load_local_report(report_name)
                    return None

                json_data = blob.download_as_text(encoding='utf-8')
                data = json.loads(json_data)
                logger.info(f"✅ Downloaded {report_name} from Cloud Storage")
                return cast(dict[str, Any], data)

            # Use local fallback
            elif self.use_local_fallback:
                return self._load_local_report(report_name)

            else:
                logger.error(f"Cannot download {report_name} - no storage backend available")
                return None

        except Exception as e:
            logger.error(f"Error downloading {report_name}: {e}", exc_info=True)

            # Fallback to local on error
            if self.use_local_fallback:
                return self._load_local_report(report_name)

            return None

    def _load_local_report(self, report_name: str) -> Optional[dict[str, Any]]:
        """Load rapport depuis filesystem local (fallback)"""
        local_path = self.local_reports_dir / report_name

        if not local_path.exists():
            logger.warning(f"Local report {report_name} not found at {local_path}")
            return None

        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"✅ Loaded {report_name} from local filesystem")
            return cast(dict[str, Any], data)
        except Exception as e:
            logger.error(f"Error loading local report {report_name}: {e}")
            return None

    def list_reports(self) -> list[str]:
        """
        Liste tous les rapports disponibles

        Returns:
            List of report filenames
        """
        reports = []

        try:
            # Try Cloud Storage first
            if self.bucket and self.client:
                blobs = self.client.list_blobs(self.bucket_name, prefix="reports/")
                for blob in blobs:
                    if blob.name.endswith('.json'):
                        filename = blob.name.replace("reports/", "")
                        reports.append(filename)
                logger.info(f"Found {len(reports)} reports in Cloud Storage")

            # Fallback to local
            elif self.use_local_fallback:
                if self.local_reports_dir.exists():
                    for file_path in self.local_reports_dir.glob("*.json"):
                        reports.append(file_path.name)
                logger.info(f"Found {len(reports)} reports in local filesystem")

        except Exception as e:
            logger.error(f"Error listing reports: {e}", exc_info=True)

        return sorted(reports)

    def delete_report(self, report_name: str) -> bool:
        """
        Supprime un rapport (use with caution!)

        Args:
            report_name: Nom du fichier à supprimer

        Returns:
            True if deleted, False otherwise
        """
        try:
            if self.bucket:
                blob = self.bucket.blob(f"reports/{report_name}")
                if blob.exists():
                    blob.delete()
                    logger.info(f"🗑️ Deleted {report_name} from Cloud Storage")
                    return True

            if self.use_local_fallback:
                local_path = self.local_reports_dir / report_name
                if local_path.exists():
                    local_path.unlink()
                    logger.info(f"🗑️ Deleted {report_name} from local filesystem")
                    return True

            logger.warning(f"Report {report_name} not found for deletion")
            return False

        except Exception as e:
            logger.error(f"Error deleting {report_name}: {e}", exc_info=True)
            return False
