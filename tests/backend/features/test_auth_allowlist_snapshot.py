import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class _StubSnapshot:
    data: Optional[Dict[str, Any]] = None
    exists: bool = True

    def to_dict(self) -> Optional[Dict[str, Any]]:
        return self.data


class _StubDocument:
    def __init__(self, store: Dict[str, Any], collection: str, name: str) -> None:
        self._store = store
        self._collection = collection
        self._name = name

    async def set(self, data: Dict[str, Any], merge: bool = False) -> None:
        writes: List[Dict[str, Any]] = self._store.setdefault("writes", [])
        writes.append(
            {
                "collection": self._collection,
                "document": self._name,
                "data": data,
                "merge": merge,
            }
        )
        self._store["latest"] = data

    async def get(self) -> _StubSnapshot:
        snapshot = self._store.get("snapshot")
        if isinstance(snapshot, _StubSnapshot):
            return snapshot
        if snapshot is None:
            return _StubSnapshot(exists=False)
        return _StubSnapshot(data=snapshot, exists=True)


class _StubCollection:
    def __init__(self, store: Dict[str, Any], name: str) -> None:
        self._store = store
        self._name = name

    def document(self, name: str) -> _StubDocument:
        self._store.setdefault("documents", []).append(
            {"collection": self._name, "document": name}
        )
        return _StubDocument(self._store, self._name, name)


class _StubFirestoreClient:
    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}

    def collection(self, name: str) -> _StubCollection:
        self.store["last_collection"] = name
        return _StubCollection(self.store, name)


def test_allowlist_snapshot_roundtrip(auth_app_factory):
    async def scenario() -> None:
        ctx = await auth_app_factory(
            "snapshot",
            admin_emails={"admin@example.com"},
        )
        service = ctx.service

        # Enable snapshot backend and inject stub Firestore client.
        service._allowlist_snapshot_backend = "firestore"
        stub_client = _StubFirestoreClient()
        service._allowlist_snapshot_client = stub_client

        # Create a new allowlist entry and ensure snapshot captured it.
        await service.upsert_allowlist(
            "member@example.com",
            "member",
            "snapshot-test",
            actor="tests",
            password="Snapshot123!",
            password_generated=False,
        )

        writes = stub_client.store.get("writes")
        assert writes, "Snapshot write expected after upsert."
        snapshot_payload = writes[-1]["data"]
        entries = snapshot_payload["entries"]
        assert entries, "Entries should be present in snapshot payload."
        entry_emails = {item.get("email") for item in entries}
        assert "member@example.com" in entry_emails

        # Remove entry from local DB to simulate fresh revision.
        await service.db.execute(
            "DELETE FROM auth_allowlist WHERE email = ?",
            ("member@example.com",),
            commit=True,
        )

        # Restore from snapshot data.
        stub_client.store["snapshot"] = snapshot_payload
        await service._restore_allowlist_from_snapshot()
        restored = await service._get_allowlist_row("member@example.com")
        assert restored is not None
        assert restored["email"] == "member@example.com"

        # Revoke entry and ensure snapshot captures revoked list.
        stub_client.store["writes"].clear()
        await service.remove_allowlist("member@example.com", actor="tests")
        revoke_writes = stub_client.store.get("writes")
        assert revoke_writes, "Snapshot write expected after removal."
        revoke_payload = revoke_writes[-1]["data"]
        revoked_entries = revoke_payload.get("revoked_entries") or []
        assert revoked_entries, "Revoked entries should be captured."
        revoke_emails = {item.get("email") for item in revoked_entries}
        assert "member@example.com" in revoke_emails

    asyncio.run(scenario())
