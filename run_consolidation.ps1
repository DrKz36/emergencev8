# Script pour consolider tous les threads archivés
Write-Host "Consolidation des threads archivés..." -ForegroundColor Yellow

# Activer virtualenv
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

# Change to src/ directory (same as uvicorn --app-dir src)
Push-Location "$PSScriptRoot\src"

try {
    python -c "
import asyncio
import sys
from pathlib import Path

# Imports depuis src/ (comme uvicorn --app-dir src)
from backend.core.database.manager import DatabaseManager
from backend.features.memory.gardener import MemoryGardener
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer

async def run():
    # Setup DB (path from src/)
    db_path = Path('backend') / 'data' / 'db' / 'emergence_v7.db'
    db = DatabaseManager(str(db_path))
    await db.connect()
    print(f'Connected to {db_path}')

    # Setup services
    vector_service = VectorService()
    analyzer = MemoryAnalyzer(db, enable_offline_mode=True)
    gardener = MemoryGardener(db, vector_service, analyzer)

    # Get all archived threads
    query = 'SELECT * FROM threads WHERE archived = 1 ORDER BY created_at DESC LIMIT 1000'
    threads = await db.fetch_all(query)
    threads = [dict(t) for t in threads]

    print(f'Found {len(threads)} archived threads')

    consolidated = 0
    for i, thread in enumerate(threads, 1):
        thread_id = thread.get('id')
        print(f'[{i}/{len(threads)}] Processing {thread_id[:8]}...')

        try:
            result = await gardener._tend_single_thread(
                thread_id=thread_id,
                session_id=thread.get('session_id'),
                user_id=thread.get('user_id')
            )
            new_concepts = result.get('new_concepts', 0)
            if new_concepts > 0:
                print(f'  -> {new_concepts} concepts')
                consolidated += 1
        except Exception as e:
            print(f'  -> ERROR: {e}')

    await db.close()
    print(f'\n✅ Done! Consolidated {consolidated}/{len(threads)} threads')

asyncio.run(run())
"
} finally {
    Pop-Location
}
