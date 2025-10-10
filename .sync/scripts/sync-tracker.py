#!/usr/bin/env python3
"""
Système de versioning et traçabilité des synchronisations
Enregistre l'historique complet de toutes les syncs Cloud ↔ Local
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class SyncRecord:
    """Enregistrement d'une synchronisation"""

    id: Optional[int] = None
    timestamp: str = ""
    sync_type: str = ""  # 'export' ou 'import'
    agent: str = ""  # 'GPT Codex Cloud' ou 'Claude Code (Local)'
    patch_name: str = ""
    branch_source: str = ""
    branch_target: str = ""
    commits_count: int = 0
    files_modified: int = 0
    patch_size_bytes: int = 0
    status: str = ""  # 'success', 'failed', 'partial'
    error_message: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: str = ""


class SyncTracker:
    """Gestionnaire de traçabilité des synchronisations"""

    def __init__(self, db_path: str = ".sync/sync_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self) -> None:
        """Initialise la base de données SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    sync_type TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    patch_name TEXT NOT NULL,
                    branch_source TEXT,
                    branch_target TEXT,
                    commits_count INTEGER DEFAULT 0,
                    files_modified INTEGER DEFAULT 0,
                    patch_size_bytes INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON sync_records(timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_type
                ON sync_records(sync_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent
                ON sync_records(agent)
            """)

            conn.commit()

    def record_sync(
        self,
        sync_type: str,
        agent: str,
        patch_name: str,
        branch_source: str = "",
        branch_target: str = "",
        commits_count: int = 0,
        files_modified: int = 0,
        patch_size_bytes: int = 0,
        status: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Enregistre une synchronisation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_at = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO sync_records (
                    timestamp, sync_type, agent, patch_name,
                    branch_source, branch_target, commits_count,
                    files_modified, patch_size_bytes, status,
                    error_message, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    sync_type,
                    agent,
                    patch_name,
                    branch_source,
                    branch_target,
                    commits_count,
                    files_modified,
                    patch_size_bytes,
                    status,
                    error_message,
                    metadata_json,
                    created_at,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_syncs(self, limit: int = 10) -> List[SyncRecord]:
        """Récupère les synchronisations récentes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM sync_records
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (limit,),
            )

            records = []
            for row in cursor.fetchall():
                record = SyncRecord(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    sync_type=row["sync_type"],
                    agent=row["agent"],
                    patch_name=row["patch_name"],
                    branch_source=row["branch_source"],
                    branch_target=row["branch_target"],
                    commits_count=row["commits_count"],
                    files_modified=row["files_modified"],
                    patch_size_bytes=row["patch_size_bytes"],
                    status=row["status"],
                    error_message=row["error_message"],
                    metadata_json=row["metadata_json"],
                    created_at=row["created_at"],
                )
                records.append(record)

            return records

    def get_sync_by_patch(self, patch_name: str) -> Optional[SyncRecord]:
        """Récupère une synchronisation par nom de patch"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM sync_records
                WHERE patch_name = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (patch_name,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return SyncRecord(
                id=row["id"],
                timestamp=row["timestamp"],
                sync_type=row["sync_type"],
                agent=row["agent"],
                patch_name=row["patch_name"],
                branch_source=row["branch_source"],
                branch_target=row["branch_target"],
                commits_count=row["commits_count"],
                files_modified=row["files_modified"],
                patch_size_bytes=row["patch_size_bytes"],
                status=row["status"],
                error_message=row["error_message"],
                metadata_json=row["metadata_json"],
                created_at=row["created_at"],
            )

    def get_stats(self) -> dict:
        """Récupère les statistiques de synchronisation"""
        with sqlite3.connect(self.db_path) as conn:
            # Total syncs
            cursor = conn.execute("SELECT COUNT(*) FROM sync_records")
            total_syncs = cursor.fetchone()[0]

            # Syncs par type
            cursor = conn.execute("""
                SELECT sync_type, COUNT(*) as count
                FROM sync_records
                GROUP BY sync_type
            """)
            syncs_by_type = {row[0]: row[1] for row in cursor.fetchall()}

            # Syncs par agent
            cursor = conn.execute("""
                SELECT agent, COUNT(*) as count
                FROM sync_records
                GROUP BY agent
            """)
            syncs_by_agent = {row[0]: row[1] for row in cursor.fetchall()}

            # Syncs par status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM sync_records
                GROUP BY status
            """)
            syncs_by_status = {row[0]: row[1] for row in cursor.fetchall()}

            # Total fichiers modifiés
            cursor = conn.execute("SELECT SUM(files_modified) FROM sync_records")
            total_files_modified = cursor.fetchone()[0] or 0

            # Total taille patches
            cursor = conn.execute("SELECT SUM(patch_size_bytes) FROM sync_records")
            total_patch_size = cursor.fetchone()[0] or 0

            return {
                "total_syncs": total_syncs,
                "syncs_by_type": syncs_by_type,
                "syncs_by_agent": syncs_by_agent,
                "syncs_by_status": syncs_by_status,
                "total_files_modified": total_files_modified,
                "total_patch_size_bytes": total_patch_size,
            }

    def export_history_json(self, output_path: str = ".sync/sync_history.json") -> None:
        """Exporte l'historique en JSON"""
        records = self.get_recent_syncs(limit=1000)
        output = {
            "export_date": datetime.now().isoformat(),
            "total_records": len(records),
            "records": [asdict(record) for record in records],
        }

        Path(output_path).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    def print_recent_syncs(self, limit: int = 10) -> None:
        """Affiche les synchronisations récentes"""
        records = self.get_recent_syncs(limit)

        if not records:
            print("Aucune synchronisation enregistrée")
            return

        print(f"\n=== {len(records)} Synchronisations Récentes ===\n")

        for record in records:
            status_icon = "✓" if record.status == "success" else "❌"
            print(f"{status_icon} [{record.timestamp}] {record.sync_type.upper()}")
            print(f"   Agent: {record.agent}")
            print(f"   Patch: {record.patch_name}")
            print(f"   Fichiers: {record.files_modified} | Taille: {record.patch_size_bytes} bytes")
            if record.branch_source:
                print(f"   Branche: {record.branch_source} → {record.branch_target or 'N/A'}")
            if record.error_message:
                print(f"   Erreur: {record.error_message}")
            print()

    def print_stats(self) -> None:
        """Affiche les statistiques"""
        stats = self.get_stats()

        print("\n=== Statistiques de Synchronisation ===\n")
        print(f"Total synchronisations: {stats['total_syncs']}")
        print(f"Total fichiers modifiés: {stats['total_files_modified']}")
        print(f"Taille totale patches: {stats['total_patch_size_bytes']:,} bytes")
        print()

        print("Par type:")
        for sync_type, count in stats["syncs_by_type"].items():
            print(f"  {sync_type}: {count}")
        print()

        print("Par agent:")
        for agent, count in stats["syncs_by_agent"].items():
            print(f"  {agent}: {count}")
        print()

        print("Par status:")
        for status, count in stats["syncs_by_status"].items():
            status_icon = "✓" if status == "success" else "❌"
            print(f"  {status_icon} {status}: {count}")


def main():
    """Point d'entrée CLI"""
    import sys

    tracker = SyncTracker()

    if len(sys.argv) < 2:
        print("Usage: python sync-tracker.py <command> [args]")
        print()
        print("Commandes:")
        print("  list [limit]    - Afficher les syncs récentes")
        print("  stats           - Afficher les statistiques")
        print("  export [path]   - Exporter l'historique en JSON")
        print("  find <patch>    - Trouver une sync par nom de patch")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        tracker.print_recent_syncs(limit)

    elif command == "stats":
        tracker.print_stats()

    elif command == "export":
        output_path = sys.argv[2] if len(sys.argv) > 2 else ".sync/sync_history.json"
        tracker.export_history_json(output_path)
        print(f"✓ Historique exporté vers {output_path}")

    elif command == "find":
        if len(sys.argv) < 3:
            print("❌ Erreur: patch_name requis")
            sys.exit(1)

        patch_name = sys.argv[2]
        record = tracker.get_sync_by_patch(patch_name)

        if not record:
            print(f"❌ Aucune synchronisation trouvée pour: {patch_name}")
            sys.exit(1)

        print(f"\n=== Synchronisation: {patch_name} ===\n")
        print(f"ID: {record.id}")
        print(f"Timestamp: {record.timestamp}")
        print(f"Type: {record.sync_type}")
        print(f"Agent: {record.agent}")
        print(f"Status: {record.status}")
        print(f"Fichiers modifiés: {record.files_modified}")
        print(f"Taille patch: {record.patch_size_bytes} bytes")
        print(f"Branche source: {record.branch_source}")
        print(f"Branche target: {record.branch_target}")
        print(f"Créé le: {record.created_at}")
        if record.error_message:
            print(f"Erreur: {record.error_message}")

    else:
        print(f"❌ Commande inconnue: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
