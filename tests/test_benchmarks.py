import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from backend.benchmarks import (
    AgentTopology,
    OrchestrationMode,
    MemoryMode,
    BenchmarksRepository,
)
from backend.features.benchmarks.service import BenchmarksService
from backend.core.database.manager import DatabaseManager
from backend.core.database import schema

MIGRATIONS_DIR = Path('src/backend/core/migrations').resolve()


async def _run_benchmarks_flow(tmp_path):
    db_path = tmp_path / 'benchmarks.db'
    db = DatabaseManager(str(db_path))
    await db.connect()
    try:
        await schema.initialize_database(db, str(MIGRATIONS_DIR))

        repository = BenchmarksRepository(db)
        service = BenchmarksService(repository)

        matrix = await service.run_matrix('ARE', context={'trigger': 'pytest'})
        assert matrix.scenario_id == 'ARE'
        expected_runs = len(AgentTopology) * len(OrchestrationMode) * len(MemoryMode)
        assert len(matrix.results) == expected_runs
        assert all(run.cost >= 0 for run in matrix.results)

        results = await service.list_results(scenario_id='ARE', limit=1)
        assert results, 'benchmarks results should have been persisted'
        latest = results[0]
        assert latest['scenario_id'] == 'ARE'
        assert latest['summary']['runs_count'] == expected_runs
        assert len(latest['runs']) == expected_runs
        sample_run = latest['runs'][0]
        assert 'config' in sample_run and 'agent_topology' in sample_run['config']
    finally:
        await db.disconnect()


def test_benchmarks_service_persists_runs(tmp_path):
    asyncio.run(_run_benchmarks_flow(tmp_path))
