#!/usr/bin/env python3
"""
Script d'export pour GPT Codex Cloud (version Python)
Génère un patch complet avec métadonnées pour synchronisation avec environnement local
Compatible: Linux, macOS, Windows
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class CloudExporter:
    """Gestionnaire d'export depuis environnement cloud"""

    def __init__(self, sync_dir: str = ".sync"):
        self.sync_dir = Path(sync_dir)
        self.patch_dir = self.sync_dir / "patches"
        self.log_dir = self.sync_dir / "logs"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.patch_name = f"sync_cloud_{self.timestamp}.patch"
        self.metadata_name = f"sync_cloud_{self.timestamp}.json"

        # Créer les dossiers
        self.patch_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run_git_command(self, *args) -> tuple[int, str, str]:
        """Exécute une commande Git et retourne (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def check_git_repository(self) -> bool:
        """Vérifie qu'on est dans un dépôt Git"""
        returncode, _, _ = self.run_git_command("rev-parse", "--git-dir")
        return returncode == 0

    def get_git_info(self) -> dict:
        """Récupère les informations Git"""
        info = {}

        # Branche courante
        returncode, stdout, _ = self.run_git_command("branch", "--show-current")
        info["branch"] = stdout.strip() if returncode == 0 else "detached"

        # Dernier commit
        returncode, stdout, _ = self.run_git_command("rev-parse", "HEAD")
        info["last_commit"] = stdout.strip() if returncode == 0 else "none"

        # Message du dernier commit
        returncode, stdout, _ = self.run_git_command("log", "-1", "--pretty=%B")
        info["last_commit_message"] = stdout.strip() if returncode == 0 else "N/A"

        # Changements non commités
        returncode, stdout, _ = self.run_git_command("status", "--short")
        info["uncommitted_changes"] = (
            len(stdout.strip().split("\n")) if stdout.strip() else 0
        )

        # Commits en avance
        returncode, stdout, _ = self.run_git_command(
            "rev-list", "--count", "@{u}..HEAD"
        )
        info["commits_ahead"] = (
            int(stdout.strip()) if returncode == 0 and stdout.strip() else 0
        )

        return info

    def generate_patch(self, git_info: dict) -> tuple[str, int]:
        """Génère le patch et retourne (type, taille)"""
        patch_path = self.patch_dir / self.patch_name

        if git_info["uncommitted_changes"] > 0:
            # Changements non commités
            returncode, stdout, _ = self.run_git_command("diff", "HEAD")
            if returncode == 0:
                patch_path.write_text(stdout, encoding="utf-8")
                patch_type = "uncommitted"
            else:
                patch_path.touch()
                patch_type = "error"
        elif git_info["commits_ahead"] > 0:
            # Commits non pushés
            returncode, stdout, _ = self.run_git_command(
                "format-patch", "@{u}", "--stdout"
            )
            if returncode == 0:
                patch_path.write_text(stdout, encoding="utf-8")
                patch_type = "commits"
            else:
                patch_path.touch()
                patch_type = "error"
        else:
            # Aucune modification
            patch_path.touch()
            patch_type = "empty"

        patch_size = patch_path.stat().st_size
        return patch_type, patch_size

    def list_modified_files(self) -> list[str]:
        """Liste les fichiers modifiés"""
        files_path = self.patch_dir / f"files_{self.timestamp}.txt"

        # Récupérer les fichiers modifiés
        _, status_output, _ = self.run_git_command("status", "--short")
        _, diff_output, _ = self.run_git_command("diff", "--name-only", "HEAD")

        all_files = set()
        if status_output:
            all_files.update(
                line.strip() for line in status_output.split("\n") if line.strip()
            )
        if diff_output:
            all_files.update(
                line.strip() for line in diff_output.split("\n") if line.strip()
            )

        files_path.write_text("\n".join(sorted(all_files)), encoding="utf-8")
        return list(all_files)

    def generate_metadata(
        self, git_info: dict, patch_type: str, patch_size: int, modified_files: list
    ) -> None:
        """Génère le fichier de métadonnées JSON"""
        metadata = {
            "export_timestamp": self.timestamp,
            "export_date": datetime.now().isoformat(),
            "agent": "GPT Codex Cloud",
            "git": {
                "branch": git_info["branch"],
                "last_commit": git_info["last_commit"],
                "last_commit_message": git_info["last_commit_message"],
                "commits_ahead": git_info["commits_ahead"],
                "uncommitted_changes": git_info["uncommitted_changes"],
            },
            "patch": {
                "filename": self.patch_name,
                "type": patch_type,
                "size_bytes": patch_size,
                "modified_files": len(modified_files),
            },
            "status": "ready_for_sync",
        }

        metadata_path = self.patch_dir / self.metadata_name
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def create_export_log(
        self, git_info: dict, patch_type: str, patch_size: int, modified_files: list
    ) -> None:
        """Crée le log d'export"""
        log_path = self.log_dir / f"export_{self.timestamp}.log"

        _, git_status, _ = self.run_git_command("status")
        _, git_log, _ = self.run_git_command("log", "--oneline", "-5")

        log_content = f"""=== Export Cloud → Local ===
Date: {datetime.now()}
Agent: GPT Codex Cloud
Patch: {self.patch_name}
Type: {patch_type}
Fichiers modifiés: {len(modified_files)}
Taille patch: {patch_size} bytes

=== État Git ===
{git_status}

=== Derniers commits ===
{git_log}

=== Fichiers modifiés ===
{chr(10).join(modified_files)}
"""
        log_path.write_text(log_content, encoding="utf-8")

    def create_instructions(
        self, git_info: dict, patch_type: str, modified_files: list
    ) -> None:
        """Crée les instructions pour l'agent local"""
        instructions_path = self.patch_dir / f"INSTRUCTIONS_{self.timestamp}.txt"

        instructions = f"""=== Instructions pour Agent Local (Claude Code) ===

Fichiers à transférer:
1. {self.patch_dir / self.patch_name}
2. {self.patch_dir / self.metadata_name}

Commande à exécuter sur la machine locale (Bash):
  cd C:\\dev\\emergenceV8
  bash .sync/scripts/local-import.sh {self.patch_name}

Commande à exécuter sur la machine locale (Python):
  cd C:\\dev\\emergenceV8
  python .sync/scripts/local-import.py {self.patch_name}

Résumé des modifications:
- Fichiers modifiés: {len(modified_files)}
- Type: {patch_type}
- Commits en avance: {git_info["commits_ahead"]}
- Branche: {git_info["branch"]}
"""
        instructions_path.write_text(instructions, encoding="utf-8")

    def export(self) -> int:
        """Exécute l'export complet"""
        print("=== GPT Codex Cloud - Export de Synchronisation ===")
        print(f"Timestamp: {self.timestamp}")
        print()

        # 1. Vérifier l'état Git
        print("[1/6] Vérification état Git...")
        if not self.check_git_repository():
            print("❌ ERREUR: Pas dans un dépôt Git")
            return 1

        # 2. Récupérer informations Git
        print("[2/6] Collecte informations Git...")
        git_info = self.get_git_info()
        print(f"  Branche: {git_info['branch']}")
        print(f"  Dernier commit: {git_info['last_commit'][:8]}")
        print(f"  Changements non commités: {git_info['uncommitted_changes']}")
        print(f"  Commits en avance: {git_info['commits_ahead']}")

        # 3. Générer le patch
        print("[3/6] Génération du patch...")
        patch_type, patch_size = self.generate_patch(git_info)
        if patch_type == "uncommitted":
            print("  ✓ Patch créé avec changements non commités")
        elif patch_type == "commits":
            print(f"  ✓ Patch créé avec {git_info['commits_ahead']} commit(s)")
        elif patch_type == "empty":
            print("  ⚠️  Aucune modification à exporter")
        else:
            print("  ❌ Erreur lors de la génération du patch")

        if patch_size == 0:
            print("  ℹ️  Le patch est vide (aucune modification)")
            patch_type = "empty"

        # 4. Lister fichiers modifiés
        print("[4/6] Liste des fichiers modifiés...")
        modified_files = self.list_modified_files()
        print(f"  Fichiers modifiés: {len(modified_files)}")

        # 5. Générer métadonnées
        print("[5/6] Génération métadonnées...")
        self.generate_metadata(git_info, patch_type, patch_size, modified_files)
        print("  ✓ Métadonnées créées")

        # 6. Créer log d'export
        print("[6/6] Création log d'export...")
        self.create_export_log(git_info, patch_type, patch_size, modified_files)
        self.create_instructions(git_info, patch_type, modified_files)
        print("  ✓ Log et instructions créés")

        # Résumé final
        print()
        print("=== ✅ Export Terminé ===")
        print(f"Patch: {self.patch_dir / self.patch_name}")
        print(f"Métadonnées: {self.patch_dir / self.metadata_name}")
        print(f"Log: {self.log_dir / f'export_{self.timestamp}.log'}")
        print()
        print("📦 Fichiers à transférer vers l'environnement local:")
        print(f"  1. {self.patch_dir / self.patch_name}")
        print(f"  2. {self.patch_dir / self.metadata_name}")
        print()
        print(
            "🚀 Prochaine étape: Transférer ces fichiers et exécuter 'local-import.py' sur la machine locale"
        )
        print()
        print(
            f"📄 Instructions: {self.patch_dir / f'INSTRUCTIONS_{self.timestamp}.txt'}"
        )

        return 0


def main():
    """Point d'entrée principal"""
    sync_dir = os.getenv("SYNC_DIR", ".sync")
    exporter = CloudExporter(sync_dir)

    try:
        sys.exit(exporter.export())
    except KeyboardInterrupt:
        print("\n⚠️  Export interrompu par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
