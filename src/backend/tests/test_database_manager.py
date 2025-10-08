"""
Tests pour DatabaseManager - Gestion de la base de données SQLite
"""
import pytest
import aiosqlite
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os

from backend.core.database.manager import DatabaseManager


@pytest.fixture
async def temp_db_path():
    """Crée un fichier de base de données temporaire pour les tests"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = temp_file.name
    temp_file.close()

    yield temp_path

    # Cleanup après le test
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
async def db_manager(temp_db_path):
    """Instance DatabaseManager avec DB temporaire"""
    manager = DatabaseManager(temp_db_path)
    await manager.connect()
    yield manager
    await manager.disconnect()


class TestDatabaseConnection:
    """Tests de connexion à la base de données"""

    @pytest.mark.asyncio
    async def test_connect(self, temp_db_path):
        """Vérifie la connexion à la base de données"""
        manager = DatabaseManager(temp_db_path)

        await manager.connect()

        assert manager.connection is not None
        assert manager.is_connected() is True

        await manager.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect(self, temp_db_path):
        """Vérifie la déconnexion"""
        manager = DatabaseManager(temp_db_path)
        await manager.connect()

        await manager.disconnect()

        assert manager.is_connected() is False

    @pytest.mark.asyncio
    async def test_double_connect_idempotent(self, temp_db_path):
        """Vérifie que connect() multiple fois est sûr"""
        manager = DatabaseManager(temp_db_path)

        await manager.connect()
        await manager.connect()  # Ne devrait pas planter

        assert manager.is_connected() is True

        await manager.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, temp_db_path):
        """Vérifie que disconnect() sans connexion ne plante pas"""
        manager = DatabaseManager(temp_db_path)

        await manager.disconnect()  # Ne devrait pas planter


class TestDatabaseOperations:
    """Tests des opérations CRUD"""

    @pytest.mark.asyncio
    async def test_create_table(self, db_manager):
        """Vérifie la création d'une table"""
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value INTEGER
            )
        """)

        # Vérifier que la table existe
        cursor = await db_manager.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='test_table'
        """)
        result = await cursor.fetchone()

        assert result is not None
        assert result[0] == 'test_table'

    @pytest.mark.asyncio
    async def test_insert_data(self, db_manager):
        """Vérifie l'insertion de données"""
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS test_insert (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        """)

        await db_manager.execute(
            "INSERT INTO test_insert (data) VALUES (?)",
            ("test_value",)
        )
        await db_manager.commit()

        cursor = await db_manager.execute("SELECT data FROM test_insert")
        result = await cursor.fetchone()

        assert result is not None
        assert result[0] == "test_value"

    @pytest.mark.asyncio
    async def test_update_data(self, db_manager):
        """Vérifie la mise à jour de données"""
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS test_update (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)

        await db_manager.execute("INSERT INTO test_update (value) VALUES (?)", ("old",))
        await db_manager.commit()

        await db_manager.execute("UPDATE test_update SET value = ? WHERE value = ?", ("new", "old"))
        await db_manager.commit()

        cursor = await db_manager.execute("SELECT value FROM test_update")
        result = await cursor.fetchone()

        assert result[0] == "new"

    @pytest.mark.asyncio
    async def test_delete_data(self, db_manager):
        """Vérifie la suppression de données"""
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS test_delete (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        await db_manager.execute("INSERT INTO test_delete (name) VALUES (?)", ("to_delete",))
        await db_manager.commit()

        await db_manager.execute("DELETE FROM test_delete WHERE name = ?", ("to_delete",))
        await db_manager.commit()

        cursor = await db_manager.execute("SELECT COUNT(*) FROM test_delete")
        result = await cursor.fetchone()

        assert result[0] == 0


class TestTransactions:
    """Tests des transactions"""

    @pytest.mark.asyncio
    async def test_commit(self, db_manager):
        """Vérifie que commit() persiste les données"""
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS test_commit (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        """)

        await db_manager.execute("INSERT INTO test_commit (data) VALUES (?)", ("committed",))
        await db_manager.commit()

        # Vérifier que les données sont bien persistées
        cursor = await db_manager.execute("SELECT data FROM test_commit")
        result = await cursor.fetchone()

        assert result[0] == "committed"

    @pytest.mark.asyncio
    async def test_rollback(self, db_manager):
        """Vérifie que rollback() annule les changements"""
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS test_rollback (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        """)
        await db_manager.commit()

        # Insérer sans commit
        await db_manager.execute("INSERT INTO test_rollback (data) VALUES (?)", ("to_rollback",))

        # Rollback
        await db_manager.rollback()

        # Vérifier que les données n'ont PAS été persistées
        cursor = await db_manager.execute("SELECT COUNT(*) FROM test_rollback")
        result = await cursor.fetchone()

        assert result[0] == 0


class TestErrorHandling:
    """Tests de gestion d'erreurs"""

    @pytest.mark.asyncio
    async def test_invalid_sql(self, db_manager):
        """Vérifie la gestion des requêtes SQL invalides"""
        with pytest.raises(aiosqlite.Error):
            await db_manager.execute("INVALID SQL QUERY")

    @pytest.mark.asyncio
    async def test_execute_on_closed_connection(self, temp_db_path):
        """Vérifie l'erreur si exécution sans connexion"""
        manager = DatabaseManager(temp_db_path)

        # Ne pas connecter, essayer d'exécuter directement
        with pytest.raises((aiosqlite.Error, AttributeError, RuntimeError)):
            await manager.execute("SELECT 1")


class TestDatabasePath:
    """Tests de gestion du chemin de fichier"""

    @pytest.mark.asyncio
    async def test_creates_directory_if_not_exists(self):
        """Vérifie que le dossier parent est créé si nécessaire"""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "subdir" / "test.db"

        manager = DatabaseManager(str(db_path))
        await manager.connect()

        assert db_path.parent.exists()
        assert db_path.exists()

        await manager.disconnect()

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_memory_database(self):
        """Vérifie le support de la base de données en mémoire"""
        manager = DatabaseManager(":memory:")
        await manager.connect()

        await manager.execute("""
            CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)
        """)
        await manager.execute("INSERT INTO test (data) VALUES (?)", ("in_memory",))
        await manager.commit()

        cursor = await manager.execute("SELECT data FROM test")
        result = await cursor.fetchone()

        assert result[0] == "in_memory"

        await manager.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
