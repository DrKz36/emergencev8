# ruff: noqa: E402
import asyncio
import json
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.auth.models import AllowlistCreatePayload, SessionRevokePayload


def test_admin_allowlist_and_sessions(auth_app_factory):
    async def scenario():
        admin_email = "admin@example.com"
        admin_password = "AdminPass123!"
        member_password = "MemberPass123!"
        member_email = "member@example.com"
        ctx = await auth_app_factory(
            "auth-admin",
            admin_emails={admin_email},
        )
        await ctx.service.set_allowlist_password(
            admin_email, admin_password, actor="tests"
        )

        transport = ASGITransport(app=ctx.app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            login_resp = await client.post(
                "/api/auth/login",
                json={"email": admin_email, "password": admin_password},
            )
            assert login_resp.status_code == 200
            admin_token = login_resp.json()["token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            payload = AllowlistCreatePayload(
                email=member_email, role="member", note="pytest"
            ).model_dump()
            create_resp = await client.post(
                "/api/auth/admin/allowlist", json=payload, headers=headers
            )
            assert create_resp.status_code == 201
            create_body = create_resp.json()
            assert create_body["entry"]["email"] == member_email
            assert create_body["clear_password"] is None
            assert create_body["generated"] is False

            set_resp = await client.post(
                "/api/auth/admin/allowlist",
                json={
                    "email": member_email,
                    "role": "member",
                    "password": member_password,
                },
                headers=headers,
            )
            assert set_resp.status_code == 201
            set_body = set_resp.json()
            assert set_body["entry"]["email"] == member_email
            assert set_body["entry"]["password_updated_at"] is not None
            assert set_body["clear_password"] is None
            assert set_body["generated"] is False

            list_resp = await client.get("/api/auth/admin/allowlist", headers=headers)
            assert list_resp.status_code == 200
            list_body = list_resp.json()
            assert list_body["status"] == "active"
            assert list_body["page"] == 1
            assert list_body["page_size"] == 20
            assert isinstance(list_body["has_more"], bool)
            assert list_body["total"] >= 1
            emails = [item["email"] for item in list_body["items"]]
            assert member_email in emails

            extra_entries = [
                ("qa1@example.com", "auto QA 1"),
                ("qa2@example.com", "auto QA 2"),
                ("qa3@example.com", "auto QA 3"),
            ]
            for extra_email, note in extra_entries:
                payload_extra = AllowlistCreatePayload(
                    email=extra_email, role="member", note=note
                ).model_dump()
                extra_resp = await client.post(
                    "/api/auth/admin/allowlist",
                    json=payload_extra,
                    headers=headers,
                )
                assert extra_resp.status_code == 201

            paged_resp = await client.get(
                "/api/auth/admin/allowlist",
                params={"page_size": 2, "page": 1},
                headers=headers,
            )
            assert paged_resp.status_code == 200
            paged_body = paged_resp.json()
            assert paged_body["page"] == 1
            assert paged_body["page_size"] == 2
            assert paged_body["total"] >= len(extra_entries) + 2
            assert paged_body["has_more"] is True

            paged_resp_2 = await client.get(
                "/api/auth/admin/allowlist",
                params={"page_size": 2, "page": 2},
                headers=headers,
            )
            assert paged_resp_2.status_code == 200
            paged_body_2 = paged_resp_2.json()
            assert paged_body_2["page"] == 2
            assert paged_body_2["page_size"] == 2
            assert isinstance(paged_body_2["has_more"], bool)

            search_resp = await client.get(
                "/api/auth/admin/allowlist",
                params={"search": "auto qa 1"},
                headers=headers,
            )
            assert search_resp.status_code == 200
            search_body = search_resp.json()
            assert search_body["status"] == "active"
            assert search_body["query"] == "auto qa 1"
            assert all(
                "auto qa 1" in (item.get("note") or "").lower()
                or "auto qa 1" in item["email"]
                for item in search_body["items"]
            )

            regen_resp = await client.post(
                "/api/auth/admin/allowlist",
                json={"email": member_email, "generate_password": True},
                headers=headers,
            )
            assert regen_resp.status_code == 201
            regen_body = regen_resp.json()
            assert regen_body["generated"] is True
            assert isinstance(regen_body["clear_password"], str)
            assert len(regen_body["clear_password"]) >= 8
            assert regen_body["entry"]["password_updated_at"] is not None
            regen_password = regen_body["clear_password"]

            audit_rows = await ctx.db.fetch_all(
                "SELECT event_type, metadata FROM auth_audit_log WHERE email = ?",
                (member_email,),
            )
            assert any(
                row["event_type"] == "allowlist:password_generated"
                for row in audit_rows
            )
            for row in audit_rows:
                if row["event_type"] == "allowlist:password_generated":
                    metadata = json.loads(row["metadata"] or "{}")
                    assert metadata.get("password_length", 0) >= 8

            member_login = await client.post(
                "/api/auth/login",
                json={"email": member_email, "password": regen_password},
            )
            assert member_login.status_code == 200
            member_body = member_login.json()
            member_session = member_body["session_id"]

            sessions_resp = await client.get(
                "/api/auth/admin/sessions",
                params={"status_filter": "active"},
                headers=headers,
            )
            assert sessions_resp.status_code == 200
            sessions = sessions_resp.json()["items"]
            assert any(item["id"] == member_session for item in sessions)

            revoke_payload = SessionRevokePayload(
                session_id=member_session
            ).model_dump()
            revoke_resp = await client.post(
                "/api/auth/admin/sessions/revoke",
                json=revoke_payload,
                headers=headers,
            )
            assert revoke_resp.status_code == 200
            assert revoke_resp.json()["updated"] == 1

            row = await ctx.db.fetch_one(
                "SELECT revoked_at FROM auth_sessions WHERE id = ?",
                (member_session,),
            )
            assert row is not None and row["revoked_at"] is not None

            delete_resp = await client.delete(
                f"/api/auth/admin/allowlist/{member_email}",
                headers=headers,
            )
            assert delete_resp.status_code == 204

            denied_resp = await client.post(
                "/api/auth/login",
                json={"email": member_email, "password": regen_password},
            )
            assert denied_resp.status_code == 423

            revoked_only = await client.get(
                "/api/auth/admin/allowlist",
                params={"status": "revoked"},
                headers=headers,
            )
            assert revoked_only.status_code == 200
            revoked_body = revoked_only.json()
            assert revoked_body["status"] == "revoked"
            assert any(item["email"] == member_email for item in revoked_body["items"])

            revoked_list = await client.get(
                "/api/auth/admin/allowlist",
                params={"include_revoked": "true"},
                headers=headers,
            )
            assert revoked_list.status_code == 200
            revoked_emails = [item["email"] for item in revoked_list.json()["items"]]
            assert member_email in revoked_emails

    asyncio.run(scenario())
