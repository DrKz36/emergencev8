#!/usr/bin/env python3
"""
Script de migration : Ajout agent_id aux souvenirs existants

Ce script ajoute le champ agent_id aux items mémoire dans ChromaDB
qui n'en ont pas encore (souvenirs créés avant l'isolation mémoire).

Usage:
    python scripts/migrate_agent_memory.py --default-agent anima
    python scripts/migrate_agent_memory.py --default-agent neo --dry-run
"""

import sys
import argparse
import logging
from pathlib import Path

# Ajouter le répertoire racine au path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from backend.features.memory.vector_service import VectorService

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def migrate_agent_memory(
    default_agent_id: str = "anima",
    dry_run: bool = False,
    collection_name: str = "emergence_knowledge",
):
    """
    Migre les souvenirs existants en ajoutant agent_id.

    Args:
        default_agent_id: Agent par défaut pour items sans agent_id
        dry_run: Si True, simule sans modifier
        collection_name: Nom de la collection ChromaDB
    """
    logger.info(f"🚀 Démarrage migration agent_id (default: {default_agent_id})")
    logger.info(f"   Collection: {collection_name}")
    logger.info(f"   Dry-run: {dry_run}")
    logger.info("")

    # Initialiser VectorService
    try:
        vector_service = VectorService()
        collection = vector_service.get_or_create_collection(collection_name)
        logger.info(f"✅ Collection '{collection_name}' chargée")
    except Exception as e:
        logger.error(f"❌ Erreur chargement collection: {e}")
        return

    # Récupérer tous les items
    try:
        results = collection.get(include=["metadatas"])
        total_items = len(results.get("ids", []))
        logger.info(f"📊 Trouvé {total_items} items total")
    except Exception as e:
        logger.error(f"❌ Erreur récupération items: {e}")
        return

    # Identifier items sans agent_id
    ids_to_update = []
    metadatas_to_update = []

    for i, item_id in enumerate(results["ids"]):
        metadata = results["metadatas"][i] if i < len(results["metadatas"]) else {}

        if not isinstance(metadata, dict):
            metadata = {}

        # Vérifier si agent_id est absent ou vide
        if not metadata.get("agent_id"):
            # Stratégie d'assignation agent_id:
            # 1. Utiliser agent existant dans metadata si présent
            # 2. Sinon utiliser default_agent_id
            inferred_agent = metadata.get("agent", "").strip().lower()
            agent_id = inferred_agent if inferred_agent else default_agent_id

            updated_metadata = dict(metadata)
            updated_metadata["agent_id"] = agent_id

            ids_to_update.append(item_id)
            metadatas_to_update.append(updated_metadata)

    logger.info(f"🔍 Trouvé {len(ids_to_update)} items sans agent_id")
    logger.info("")

    if not ids_to_update:
        logger.info("✅ Aucune migration nécessaire - tous les items ont déjà agent_id")
        return

    # Afficher aperçu
    logger.info("📋 Aperçu des migrations (max 5 premiers) :")
    for i in range(min(5, len(ids_to_update))):
        item_id = ids_to_update[i]
        old_meta = results["metadatas"][results["ids"].index(item_id)]
        new_meta = metadatas_to_update[i]
        logger.info(f"   - {item_id[:20]}... → agent_id: {new_meta['agent_id']}")
    if len(ids_to_update) > 5:
        logger.info(f"   ... et {len(ids_to_update) - 5} autres")
    logger.info("")

    # Appliquer migration
    if dry_run:
        logger.info("🔍 DRY-RUN : Aucune modification appliquée")
        logger.info(f"   {len(ids_to_update)} items seraient mis à jour")
    else:
        logger.info(f"💾 Mise à jour de {len(ids_to_update)} items...")

        # Mise à jour par batches (pour éviter surcharge)
        batch_size = 100
        total_updated = 0

        for i in range(0, len(ids_to_update), batch_size):
            batch_ids = ids_to_update[i : i + batch_size]
            batch_metas = metadatas_to_update[i : i + batch_size]

            try:
                collection.update(ids=batch_ids, metadatas=batch_metas)
                total_updated += len(batch_ids)
                logger.info(
                    f"   ✅ Batch {i // batch_size + 1}: {len(batch_ids)} items mis à jour ({total_updated}/{len(ids_to_update)})"
                )
            except Exception as e:
                logger.error(f"   ❌ Erreur batch {i // batch_size + 1}: {e}")
                continue

        logger.info("")
        logger.info(
            f"✅ Migration terminée : {total_updated}/{len(ids_to_update)} items mis à jour"
        )

    # Vérification post-migration
    if not dry_run:
        logger.info("")
        logger.info("🔍 Vérification post-migration...")
        try:
            check_results = collection.get(limit=10, include=["metadatas"])
            missing_agent_id = 0

            for meta in check_results.get("metadatas", []):
                if not isinstance(meta, dict):
                    missing_agent_id += 1
                elif not meta.get("agent_id"):
                    missing_agent_id += 1

            if missing_agent_id == 0:
                logger.info("✅ Tous les items vérifiés ont agent_id")
            else:
                logger.warning(
                    f"⚠️ {missing_agent_id}/10 items échantillon n'ont toujours pas agent_id"
                )
        except Exception as e:
            logger.warning(f"⚠️ Erreur vérification: {e}")

    logger.info("")
    logger.info("🎉 Migration terminée avec succès !")


def main():
    parser = argparse.ArgumentParser(
        description="Migrer les souvenirs ChromaDB avec agent_id"
    )
    parser.add_argument(
        "--default-agent",
        type=str,
        default="anima",
        choices=["anima", "neo", "nexus"],
        help="Agent par défaut pour items sans agent_id (default: anima)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simuler sans modifier la base"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="emergence_knowledge",
        help="Nom de la collection ChromaDB (default: emergence_knowledge)",
    )

    args = parser.parse_args()

    migrate_agent_memory(
        default_agent_id=args.default_agent,
        dry_run=args.dry_run,
        collection_name=args.collection,
    )


if __name__ == "__main__":
    main()
