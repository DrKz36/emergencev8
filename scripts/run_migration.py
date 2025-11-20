import asyncio
import aiosqlite
import sys
from pathlib import Path


async def run_migration(db_path: str, mig_path: str):
    db_file = Path(db_path)
    mig_file = Path(mig_path)

    if not db_file.exists():
        print(f"[INFO] Création de la base: {db_file}")
    if not mig_file.exists():
        print(f"[ERREUR] Fichier migration introuvable: {mig_file}")
        return

    sql = mig_file.read_text(encoding="utf-8")

    async with aiosqlite.connect(db_file) as db:
        await db.executescript(sql)
        await db.commit()

    print(f"[OK] Migration exécutée depuis {mig_file} → {db_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/run_migration.py <db_path> <mig_path>")
    else:
        asyncio.run(run_migration(sys.argv[1], sys.argv[2]))
