#!/usr/bin/env python3
"""
Script d'import pour Agent Local (Claude Code) - Version Python
Applique un patch reçu de GPT Codex Cloud et synchronise avec GitHub
Compatible: Linux, macOS, Windows
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class Colors:
    """Codes couleur ANSI pour output"""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


class LocalImporter:
    """Gestionnaire d'import sur environnement local"""

    def __init__(self, patch_name: str, sync_dir: str = ".sync"):
        self.sync_dir = Path(sync_dir)
        self.patch_dir = self.sync_dir / "patches"
        self.log_dir = self.sync_dir / "logs"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.patch_name = patch_name
        self.patch_path = self.patch_dir / patch_name
        self.metadata_name = patch_name.replace(".patch", ".json")
        self.metadata_path = self.patch_dir / self.metadata_name

        self.has_metadata = False
        self.patch_applied = False
        self.patch_method = None
        self.backup_branch = f"backup/before-sync-{self.timestamp}"

    @staticmethod
    def log_info(msg: str) -> None:
        """Affiche un message d'information"""
        print(f"{Colors.BLUE}ℹ️  {msg}{Colors.NC}")

    @staticmethod
    def log_success(msg: str) -> None:
        """Affiche un message de succès"""
        print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")

    @staticmethod
    def log_warning(msg: str) -> None:
        """Affiche un avertissement"""
        print(f"{Colors.YELLOW}⚠️  {msg}{Colors.NC}")

    @staticmethod
    def log_error(msg: str) -> None:
        """Affiche une erreur"""
        print(f"{Colors.RED}❌ {msg}{Colors.NC}")

    @staticmethod
    def run_git_command(*args, check: bool = False) -> tuple[int, str, str]:
        """Exécute une commande Git et retourne (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                capture_output=True,
                text=True,
                check=check,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
        except Exception as e:
            return 1, "", str(e)

    @staticmethod
    def confirm(prompt: str, default: bool = False) -> bool:
        """Demande confirmation à l'utilisateur"""
        suffix = " (Y/n)" if default else " (y/N)"
        response = input(prompt + suffix + " ").strip().lower()

        if not response:
            return default

        return response in ("y", "yes", "oui")

    def check_prerequisites(self) -> bool:
        """Vérifie les prérequis"""
        self.log_info("[1/8] Vérifications préliminaires...")

        # Vérifier le patch
        if not self.patch_path.exists():
            self.log_error(f"Patch introuvable: {self.patch_path}")
            return False
        self.log_success("Patch trouvé")

        # Vérifier les métadonnées
        if not self.metadata_path.exists():
            self.log_warning(f"Métadonnées introuvables: {self.metadata_path}")
            self.has_metadata = False
        else:
            self.log_success("Métadonnées trouvées")
            self.has_metadata = True

        # Vérifier qu'on est dans un dépôt Git
        returncode, _, _ = self.run_git_command("rev-parse", "--git-dir")
        if returncode != 0:
            self.log_error("Pas dans un dépôt Git")
            return False
        self.log_success("Dépôt Git détecté")

        return True

    def display_metadata(self) -> None:
        """Affiche les métadonnées du patch"""
        if not self.has_metadata:
            self.log_info("[2/8] Pas de métadonnées disponibles")
            return

        self.log_info("[2/8] Lecture métadonnées...")
        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            print(f"Agent source: {metadata['agent']}")
            print(f"Date export: {metadata['export_date']}")
            print(f"Branche: {metadata['git']['branch']}")
            print(f"Type: {metadata['patch']['type']}")
            print(f"Fichiers modifiés: {metadata['patch']['modified_files']}")
        except Exception as e:
            self.log_warning(f"Erreur lecture métadonnées: {e}")
        print()

    def check_git_status(self) -> bool:
        """Vérifie l'état Git local"""
        self.log_info("[3/8] Vérification état Git local...")

        # Vérifier si working tree propre
        returncode, _, _ = self.run_git_command("diff-index", "--quiet", "HEAD", "--")
        if returncode != 0:
            self.log_warning("Working tree contient des modifications non commitées")
            if not self.confirm("Voulez-vous continuer?"):
                self.log_error("Import annulé par l'utilisateur")
                return False
        else:
            self.log_success("Working tree propre")

        # Branche courante
        returncode, stdout, _ = self.run_git_command("branch", "--show-current")
        if returncode == 0:
            current_branch = stdout.strip()
            self.log_success(f"Branche courante: {current_branch}")

        return True

    def create_backup_branch(self) -> bool:
        """Crée une branche de sécurité"""
        self.log_info("[4/8] Création branche de sécurité...")
        returncode, _, stderr = self.run_git_command("branch", self.backup_branch)

        if returncode != 0:
            self.log_warning(f"Impossible de créer branche backup: {stderr}")
            return False

        self.log_success(f"Branche backup créée: {self.backup_branch}")
        return True

    def apply_patch(self) -> bool:
        """Applique le patch"""
        self.log_info("[5/8] Application du patch...")

        patch_size = self.patch_path.stat().st_size
        if patch_size == 0:
            self.log_warning("Le patch est vide (aucune modification)")
            self.patch_applied = False
            return True

        # Essayer git apply
        returncode, _, _ = self.run_git_command("apply", "--check", str(self.patch_path))
        if returncode == 0:
            self.run_git_command("apply", str(self.patch_path), check=True)
            self.patch_applied = True
            self.patch_method = "git apply"
            self.log_success("Patch appliqué avec git apply")
            return True

        # Essayer git am
        returncode, _, _ = self.run_git_command("am", "--check", str(self.patch_path))
        if returncode == 0:
            self.run_git_command("am", str(self.patch_path), check=True)
            self.patch_applied = True
            self.patch_method = "git am"
            self.log_success("Patch appliqué avec git am")
            return True

        # Essayer git apply --3way
        self.log_info("Essai de réparation...")
        returncode, _, stderr = self.run_git_command("apply", "--3way", str(self.patch_path))
        if returncode == 0:
            self.patch_applied = True
            self.patch_method = "git apply --3way"
            self.log_success("Patch appliqué avec résolution 3-way")
            return True

        # Échec
        self.log_error("Échec de l'application du patch")
        self.log_info("Restauration de l'état précédent...")
        self.run_git_command("checkout", self.backup_branch)
        return False

    def verify_changes(self) -> int:
        """Vérifie les modifications appliquées"""
        self.log_info("[6/8] Vérification des modifications...")

        # Compter fichiers modifiés
        returncode, stdout, _ = self.run_git_command("diff", "--name-only")
        modified_files = [line for line in stdout.split("\n") if line.strip()]
        num_modified = len(modified_files)

        print(f"Fichiers modifiés: {num_modified}")

        if num_modified > 0:
            print("\nFichiers modifiés:")
            _, status_output, _ = self.run_git_command("diff", "--name-status")
            lines = status_output.split("\n")[:20]
            for line in lines:
                if line.strip():
                    print(f"  {line}")
            if num_modified > 20:
                print(f"  ... ({num_modified - 20} autres fichiers)")
        else:
            self.log_info("Aucun fichier modifié après application du patch")

        print()
        return num_modified

    def validate_changes(self) -> None:
        """Valide les changements (optionnel)"""
        self.log_info("[7/8] Validation des changements (optionnel)...")

        # Build npm si disponible
        if Path("package.json").exists():
            if self.confirm("Voulez-vous exécuter npm run build?"):
                subprocess.run(["npm", "run", "build"], check=False)

        # Tests pytest si disponible
        if self.confirm("Voulez-vous exécuter les tests?"):
            subprocess.run(["pytest", "tests/", "-x"], check=False)

    def commit_and_push(self, num_modified: int) -> None:
        """Commit et push vers GitHub (interactif)"""
        self.log_info("[8/8] Commit et push vers GitHub...")

        if not self.patch_applied or num_modified == 0:
            self.log_warning("Aucune modification à commiter")
            return

        if not self.confirm("Voulez-vous commiter et pusher vers GitHub?"):
            self.log_info("Commit annulé (modifications dans working tree)")
            return

        # Générer message de commit
        commit_msg = self._generate_commit_message(num_modified)

        # Commit
        self.run_git_command("add", "-A")
        self.run_git_command("commit", "-m", commit_msg, check=True)
        self.log_success("Modifications commitées")

        # Push
        _, current_branch, _ = self.run_git_command("branch", "--show-current")
        current_branch = current_branch.strip()

        if self.confirm(f"Voulez-vous pusher vers origin/{current_branch}?"):
            self.run_git_command("push", "origin", current_branch, check=True)
            self.log_success("Modifications pushées vers GitHub")
        else:
            self.log_info("Push annulé (vous pouvez le faire manuellement avec: git push)")

    def _generate_commit_message(self, num_modified: int) -> str:
        """Génère le message de commit"""
        if self.has_metadata:
            try:
                metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                return f"""sync: intégration modifications GPT Codex Cloud

Export: {metadata['export_timestamp']}
Type: {metadata['patch']['type']}
Fichiers: {metadata['patch']['modified_files']}
Branche source: {metadata['git']['branch']}

🤖 Synchronisation automatique Cloud → Local → GitHub"""
            except Exception:
                pass

        return f"""sync: intégration modifications GPT Codex Cloud

Patch: {self.patch_name}
Méthode: {self.patch_method}
Fichiers modifiés: {num_modified}

🤖 Synchronisation automatique Cloud → Local → GitHub"""

    def create_import_log(self, num_modified: int) -> None:
        """Crée le log d'import"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / f"import_{self.timestamp}.log"

        _, git_status, _ = self.run_git_command("status")
        _, git_log, _ = self.run_git_command("log", "--oneline", "-5")
        _, current_branch, _ = self.run_git_command("branch", "--show-current")

        log_content = f"""=== Import Local ← Cloud ===
Date: {datetime.now()}
Agent: Claude Code (Local)
Patch: {self.patch_name}
Méthode: {self.patch_method or 'N/A'}
Fichiers modifiés: {num_modified}
Branche: {current_branch.strip()}
Backup: {self.backup_branch}

=== État Git après import ===
{git_status}

=== Derniers commits ===
{git_log}
"""
        log_path.write_text(log_content, encoding="utf-8")

    def print_summary(self, num_modified: int) -> None:
        """Affiche le résumé final"""
        print()
        print("=== ✅ Import Terminé ===")
        print(f"Patch appliqué: {self.patch_name}")
        print(f"Méthode: {self.patch_method or 'N/A'}")
        print(f"Fichiers modifiés: {num_modified}")
        print(f"Branche backup: {self.backup_branch}")
        print(f"Log: {self.log_dir / f'import_{self.timestamp}.log'}")
        print()
        self.log_success("Synchronisation Cloud → Local terminée avec succès!")
        print()
        print("💡 Prochaines étapes suggérées:")
        print("  1. Vérifier les modifications: git diff HEAD~1")
        print("  2. Tester l'application localement")
        print("  3. Mettre à jour AGENT_SYNC.md et docs/passation.md")
        print(f"  4. Si problème: git checkout {self.backup_branch}")

    def import_patch(self) -> int:
        """Exécute l'import complet"""
        print("=== Agent Local (Claude Code) - Import Synchronisation ===")
        print(f"Timestamp: {self.timestamp}")
        print(f"Patch: {self.patch_name}")
        print()

        # Vérifications préliminaires
        if not self.check_prerequisites():
            return 1

        # Afficher métadonnées
        self.display_metadata()

        # Vérifier état Git
        if not self.check_git_status():
            return 1

        # Créer branche de sécurité
        self.create_backup_branch()

        # Appliquer le patch
        if not self.apply_patch():
            return 1

        # Vérifier modifications
        num_modified = self.verify_changes()

        # Valider changements
        self.validate_changes()

        # Commit et push
        self.commit_and_push(num_modified)

        # Créer log
        self.create_import_log(num_modified)

        # Résumé
        self.print_summary(num_modified)

        return 0


def list_available_patches(sync_dir: Path) -> None:
    """Liste les patches disponibles"""
    patch_dir = sync_dir / "patches"
    if not patch_dir.exists():
        print("Aucun patch trouvé")
        return

    patches = sorted(patch_dir.glob("*.patch"))
    if not patches:
        print("Aucun patch trouvé")
        return

    print("Patches disponibles:")
    for patch in patches:
        print(f"  - {patch.name}")


def main():
    """Point d'entrée principal"""
    if len(sys.argv) < 2:
        print("❌ Usage: python local-import.py <patch_name>")
        print("Exemple: python local-import.py sync_cloud_20251010_123456.patch")
        print()
        list_available_patches(Path(".sync"))
        sys.exit(1)

    patch_name = sys.argv[1]
    sync_dir = ".sync"

    importer = LocalImporter(patch_name, sync_dir)

    try:
        sys.exit(importer.import_patch())
    except KeyboardInterrupt:
        print("\n⚠️  Import interrompu par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
