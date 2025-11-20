#!/usr/bin/env python3
"""
Apply Ultimate Claude Code Config

Ce script merge la config actuelle avec une config ultra-complète
qui contient toutes les permissions possibles du projet.

Usage:
    python .claude/apply_ultimate_config.py [--dry-run] [--backup]
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import argparse


def load_json(file_path: Path) -> dict:
    """Charge un fichier JSON."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path: Path, data: dict):
    """Sauvegarde un fichier JSON avec indentation."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def merge_permissions(current: dict, ultimate: dict) -> dict:
    """
    Merge les permissions en gardant celles actuelles + ajoutant les nouvelles.

    Stratégie :
    - Garde wildcard "*" en première position
    - Ajoute toutes les permissions de ultimate qui ne sont pas déjà présentes
    - Ignore les commentaires (clés commençant par "_comment")
    """
    current_allow = set(current.get("permissions", {}).get("allow", []))
    ultimate_allow = ultimate.get("permissions", {}).get("allow", [])

    # Toujours garder wildcard en premier
    merged_allow = ["*"]

    # Ajouter permissions de current (sauf wildcard déjà ajouté)
    for perm in current.get("permissions", {}).get("allow", []):
        if perm != "*" and not perm.startswith("_comment"):
            merged_allow.append(perm)

    # Ajouter permissions de ultimate qui ne sont pas déjà là
    for perm in ultimate_allow:
        if perm not in merged_allow and not perm.startswith("_comment"):
            merged_allow.append(perm)

    # Créer le résultat
    result = {
        "env": current.get("env", ultimate.get("env", {})),
        "permissions": {
            "allow": merged_allow,
            "deny": current.get("permissions", {}).get("deny", []),
            "ask": current.get("permissions", {}).get("ask", []),
        },
    }

    # Ajouter flags expérimentaux si dans ultimate
    if "_experimental" in ultimate:
        result["_experimental"] = ultimate["_experimental"]

    return result


def main():
    parser = argparse.ArgumentParser(description="Apply ultimate Claude Code config")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup before applying (default: True)",
    )
    parser.add_argument(
        "--no-backup", action="store_false", dest="backup", help="Don't create backup"
    )

    args = parser.parse_args()

    # Chemins
    base_dir = Path(__file__).parent
    current_file = base_dir / "settings.local.json"
    ultimate_file = base_dir / "settings.local.json.ULTIMATE"

    # Vérifier que les fichiers existent
    if not current_file.exists():
        print(f"[ERROR] Fichier actuel introuvable: {current_file}")
        return 1

    if not ultimate_file.exists():
        print(f"[ERROR] Fichier ultimate introuvable: {ultimate_file}")
        return 1

    # Charger les configs
    print("[*] Chargement des configurations...")
    current = load_json(current_file)
    ultimate = load_json(ultimate_file)

    # Stats avant
    current_perms = len(
        [
            p
            for p in current.get("permissions", {}).get("allow", [])
            if not p.startswith("_comment")
        ]
    )
    ultimate_perms = len(
        [
            p
            for p in ultimate.get("permissions", {}).get("allow", [])
            if not p.startswith("_comment")
        ]
    )

    print(f"    Permissions actuelles : {current_perms}")
    print(f"    Permissions ultimate  : {ultimate_perms}")

    # Merge
    print("\n[*] Merge des permissions...")
    merged = merge_permissions(current, ultimate)

    merged_perms = len(
        [
            p
            for p in merged.get("permissions", {}).get("allow", [])
            if not p.startswith("_comment")
        ]
    )
    new_perms = merged_perms - current_perms

    print(f"    Permissions merged    : {merged_perms}")
    print(f"    Nouvelles permissions : {new_perms}")

    # Flags expérimentaux
    if "_experimental" in merged:
        print("\n[!] Flags experimentaux detectes:")
        for key, value in merged["_experimental"].items():
            print(f"    - {key}: {value}")

    # Dry run
    if args.dry_run:
        print("\n[DRY-RUN] Aucune modification effectuee")
        print("\n[*] Apercu de la config merged (10 premieres permissions):")
        for i, perm in enumerate(merged["permissions"]["allow"][:10], 1):
            print(f"    {i}. {perm}")
        if len(merged["permissions"]["allow"]) > 10:
            remaining = len(merged["permissions"]["allow"]) - 10
            print(f"    ... et {remaining} autres")
        return 0

    # Backup
    if args.backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = base_dir / f"settings.local.json.backup_{timestamp}"
        print(f"\n[*] Creation backup: {backup_file.name}")
        shutil.copy2(current_file, backup_file)

    # Appliquer
    print("\n[*] Application de la config merged...")
    save_json(current_file, merged)

    print("\n[OK] Configuration ultimate appliquee avec succes !")
    print("\n[*] Resultat:")
    print(f"    - {merged_perms} permissions totales")
    print(f"    - {new_perms} nouvelles permissions ajoutees")
    print("    - Wildcard '*' conserve en premiere position")

    if "_experimental" in merged:
        print("    - [!] Flags experimentaux actives (DANGEROUSLY SKIP ALL)")

    print("\n[OK] Prochaine session Claude Code devrait etre en mode FULL AUTO !")

    return 0


if __name__ == "__main__":
    exit(main())
