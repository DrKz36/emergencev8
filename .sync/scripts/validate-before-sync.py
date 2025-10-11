#!/usr/bin/env python3
"""
Hook de validation automatique avant synchronisation
Vérifie la qualité du code et les tests avant de créer un patch
"""

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple


class ValidationLevel(Enum):
    """Niveaux de validation"""

    MINIMAL = "minimal"  # Seulement vérifier que le code compile
    STANDARD = "standard"  # Build + tests rapides
    COMPLETE = "complete"  # Build + tests + linting + type checking
    CUSTOM = "custom"  # Configuration personnalisée


@dataclass
class ValidationResult:
    """Résultat d'une validation"""

    check_name: str
    passed: bool
    message: str
    duration_seconds: float = 0.0


class ValidationHook:
    """Gestionnaire de validation avant sync"""

    def __init__(self, level: ValidationLevel = ValidationLevel.STANDARD):
        self.level = level
        self.results: List[ValidationResult] = []
        self.root = Path.cwd()

    @staticmethod
    def run_command(
        *args, cwd: Optional[Path] = None, timeout: int = 300
    ) -> Tuple[int, str, str]:
        """Exécute une commande et retourne (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                check=False,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Timeout expired"
        except Exception as e:
            return 1, "", str(e)

    def check_git_status(self) -> ValidationResult:
        """Vérifie l'état Git"""
        import time

        start = time.time()

        returncode, stdout, stderr = self.run_command("git", "status", "--short")

        if returncode != 0:
            return ValidationResult(
                check_name="Git Status",
                passed=False,
                message=f"Erreur Git: {stderr}",
                duration_seconds=time.time() - start,
            )

        # Vérifier qu'il y a des modifications
        if not stdout.strip():
            return ValidationResult(
                check_name="Git Status",
                passed=True,
                message="⚠️  Aucune modification à synchroniser",
                duration_seconds=time.time() - start,
            )

        num_files = len(stdout.strip().split("\n"))
        return ValidationResult(
            check_name="Git Status",
            passed=True,
            message=f"✓ {num_files} fichier(s) modifié(s)",
            duration_seconds=time.time() - start,
        )

    def check_python_syntax(self) -> Optional[ValidationResult]:
        """Vérifie la syntaxe Python"""
        import time

        start = time.time()

        # Trouver les fichiers Python modifiés
        returncode, stdout, _ = self.run_command("git", "diff", "--name-only", "HEAD")
        if returncode != 0:
            return None

        py_files = [
            line for line in stdout.split("\n") if line.strip().endswith(".py")
        ]

        if not py_files:
            return ValidationResult(
                check_name="Python Syntax",
                passed=True,
                message="Aucun fichier Python modifié",
                duration_seconds=time.time() - start,
            )

        # Vérifier la syntaxe de chaque fichier
        errors = []
        for py_file in py_files:
            file_path = self.root / py_file
            if not file_path.exists():
                continue

            returncode, _, stderr = self.run_command(
                sys.executable, "-m", "py_compile", str(file_path)
            )
            if returncode != 0:
                errors.append(f"{py_file}: {stderr}")

        if errors:
            return ValidationResult(
                check_name="Python Syntax",
                passed=False,
                message="❌ Erreurs de syntaxe:\n" + "\n".join(errors[:3]),
                duration_seconds=time.time() - start,
            )

        return ValidationResult(
            check_name="Python Syntax",
            passed=True,
            message=f"✓ {len(py_files)} fichier(s) Python valide(s)",
            duration_seconds=time.time() - start,
        )

    def check_npm_build(self) -> Optional[ValidationResult]:
        """Vérifie le build npm"""
        import time

        start = time.time()

        if not (self.root / "package.json").exists():
            return None

        returncode, stdout, stderr = self.run_command(
            "npm", "run", "build", timeout=600
        )

        if returncode != 0:
            return ValidationResult(
                check_name="NPM Build",
                passed=False,
                message=f"❌ Build échoué:\n{stderr[:200]}",
                duration_seconds=time.time() - start,
            )

        return ValidationResult(
            check_name="NPM Build",
            passed=True,
            message="✓ Build réussi",
            duration_seconds=time.time() - start,
        )

    def check_pytest(self) -> Optional[ValidationResult]:
        """Exécute les tests pytest"""
        import time

        start = time.time()

        # Vérifier si pytest est disponible
        returncode, _, _ = self.run_command("pytest", "--version")
        if returncode != 0:
            return None

        # Exécuter les tests
        returncode, stdout, stderr = self.run_command(
            "pytest", "tests/", "-x", "--tb=short", timeout=600
        )

        if returncode != 0:
            # Extraire le résumé des tests
            lines = stdout.split("\n")
            summary = [line for line in lines if "failed" in line.lower()]
            summary_text = "\n".join(summary[:3]) if summary else stderr[:200]

            return ValidationResult(
                check_name="Pytest",
                passed=False,
                message=f"❌ Tests échoués:\n{summary_text}",
                duration_seconds=time.time() - start,
            )

        return ValidationResult(
            check_name="Pytest",
            passed=True,
            message="✓ Tests réussis",
            duration_seconds=time.time() - start,
        )

    def check_ruff(self) -> Optional[ValidationResult]:
        """Vérifie le linting avec ruff"""
        import time

        start = time.time()

        returncode, _, _ = self.run_command("ruff", "--version")
        if returncode != 0:
            return None

        # Linting
        returncode, stdout, stderr = self.run_command(
            "ruff", "check", "src/", "tests/"
        )

        if returncode != 0:
            # Compter les erreurs
            lines = stdout.split("\n")
            errors = [line for line in lines if line.strip()]
            num_errors = len(errors)

            return ValidationResult(
                check_name="Ruff Linting",
                passed=False,
                message=f"❌ {num_errors} erreur(s) de linting:\n"
                + "\n".join(errors[:3]),
                duration_seconds=time.time() - start,
            )

        return ValidationResult(
            check_name="Ruff Linting",
            passed=True,
            message="✓ Aucune erreur de linting",
            duration_seconds=time.time() - start,
        )

    def check_mypy(self) -> Optional[ValidationResult]:
        """Vérifie le type checking avec mypy"""
        import time

        start = time.time()

        returncode, _, _ = self.run_command("mypy", "--version")
        if returncode != 0:
            return None

        # Type checking
        returncode, stdout, stderr = self.run_command("mypy", "src/")

        if returncode != 0:
            lines = stdout.split("\n")
            errors = [line for line in lines if "error:" in line.lower()]

            return ValidationResult(
                check_name="Mypy Type Checking",
                passed=False,
                message="❌ Erreurs de typage:\n" + "\n".join(errors[:3]),
                duration_seconds=time.time() - start,
            )

        return ValidationResult(
            check_name="Mypy Type Checking",
            passed=True,
            message="✓ Type checking réussi",
            duration_seconds=time.time() - start,
        )

    def validate(self) -> bool:
        """Exécute la validation selon le niveau configuré"""
        print(f"\n=== Validation Avant Synchronisation ({self.level.value}) ===\n")

        # Vérifications communes à tous les niveaux
        print("[1/N] Vérification Git...")
        result = self.check_git_status()
        self.results.append(result)
        print(f"  {result.message}")

        if not result.passed:
            self._print_summary()
            return False

        # Vérification syntaxe Python
        print("[2/N] Vérification syntaxe Python...")
        result = self.check_python_syntax()
        if result:
            self.results.append(result)
            print(f"  {result.message}")
            if not result.passed:
                self._print_summary()
                return False

        # Niveaux de validation
        if self.level in [ValidationLevel.MINIMAL, ValidationLevel.STANDARD, ValidationLevel.COMPLETE]:
            # Build npm
            print("[3/N] Build npm...")
            result = self.check_npm_build()
            if result:
                self.results.append(result)
                print(f"  {result.message}")
                if not result.passed and self.level != ValidationLevel.MINIMAL:
                    self._print_summary()
                    return False

        if self.level in [ValidationLevel.STANDARD, ValidationLevel.COMPLETE]:
            # Tests
            print("[4/N] Tests pytest...")
            result = self.check_pytest()
            if result:
                self.results.append(result)
                print(f"  {result.message}")
                if not result.passed:
                    self._print_summary()
                    return False

        if self.level == ValidationLevel.COMPLETE:
            # Linting
            print("[5/N] Linting ruff...")
            result = self.check_ruff()
            if result:
                self.results.append(result)
                print(f"  {result.message}")
                if not result.passed:
                    self._print_summary()
                    return False

            # Type checking
            print("[6/N] Type checking mypy...")
            result = self.check_mypy()
            if result:
                self.results.append(result)
                print(f"  {result.message}")
                if not result.passed:
                    self._print_summary()
                    return False

        self._print_summary()
        return all(r.passed for r in self.results)

    def _print_summary(self) -> None:
        """Affiche le résumé de validation"""
        print("\n=== Résumé Validation ===\n")

        total_duration = sum(r.duration_seconds for r in self.results)
        passed_count = sum(1 for r in self.results if r.passed)
        failed_count = len(self.results) - passed_count

        for result in self.results:
            icon = "✓" if result.passed else "❌"
            print(
                f"{icon} {result.check_name} ({result.duration_seconds:.2f}s)"
            )

        print()
        print(f"Total: {passed_count} réussi(s), {failed_count} échoué(s)")
        print(f"Durée totale: {total_duration:.2f}s")
        print()

        if failed_count > 0:
            print("❌ VALIDATION ÉCHOUÉE - Corrigez les erreurs avant de synchroniser")
            return

        print("✅ VALIDATION RÉUSSIE - Vous pouvez synchroniser en toute sécurité")


def main():
    """Point d'entrée CLI"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Valide le code avant synchronisation"
    )
    parser.add_argument(
        "--level",
        choices=["minimal", "standard", "complete"],
        default="standard",
        help="Niveau de validation (défaut: standard)",
    )

    args = parser.parse_args()
    level = ValidationLevel(args.level)

    validator = ValidationHook(level)
    success = validator.validate()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
