"""Contract tests for the admin block (BasicAuth is enforced by nginx, not here)."""
import uuid


async def test_list_users_includes_admin(client):
    res = await client.get("/admin/api/users")
    assert res.status_code == 200
    emails = [u["email"] for u in res.json()]
    assert "admin@example.com" in emails


async def test_create_user_and_conflict(client):
    res = await client.post(
        "/admin/api/users",
        json={"email": "new@example.com", "full_name": "New Person", "locale": "fr"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "new@example.com"
    assert body["locale"] == "fr"
    assert body["files"] == 0 and body["folders"] == 0

    dup = await client.post(
        "/admin/api/users",
        json={"email": "new@example.com", "full_name": "Dup", "locale": "en"},
    )
    assert dup.status_code == 409


async def test_user_detail_stats(client):
    created = (await client.post(
        "/admin/api/users",
        json={"email": "stat@example.com", "full_name": "Stat User"},
    )).json()
    res = await client.get(f"/admin/api/users/{created['id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["stats"] == {"files": 0, "folders": 0, "shared_out": 0, "versions": 0}
    assert "created_at" in body


async def test_patch_user(client):
    created = (await client.post(
        "/admin/api/users",
        json={"email": "patch@example.com", "full_name": "Before"},
    )).json()
    res = await client.patch(
        f"/admin/api/users/{created['id']}",
        json={"full_name": "After", "bio": "hello", "locale": "de", "is_active": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["full_name"] == "After"
    assert body["bio"] == "hello"
    assert body["locale"] == "de"
    assert body["is_active"] is False


async def test_magic_link_and_password(client):
    created = (await client.post(
        "/admin/api/users",
        json={"email": "ml@example.com", "full_name": "ML User"},
    )).json()

    ml = await client.post(f"/admin/api/users/{created['id']}/magic-link")
    assert ml.status_code == 200
    assert "/login?magic=" in ml.json()["url"]

    pw = await client.post(
        f"/admin/api/users/{created['id']}/password", json={"password": "secret123"}
    )
    assert pw.status_code == 200
    assert pw.json()["has_password"] is True


async def test_delete_user_node(client):
    created = (await client.post(
        "/admin/api/users",
        json={"email": "owner@example.com", "full_name": "Owner"},
    )).json()
    uid = uuid.UUID(created["id"])

    # insert a folder node directly
    from app.db import SessionLocal
    from app.models import Node

    async with SessionLocal() as db:
        node = Node(type="folder", name="Docs", created_by=uid)
        db.add(node)
        await db.commit()
        node_id = node.id

    listed = await client.get(f"/admin/api/users/{created['id']}/nodes")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = await client.delete(f"/admin/api/users/{created['id']}/nodes/{node_id}")
    assert deleted.status_code == 204

    listed2 = await client.get(f"/admin/api/users/{created['id']}/nodes")
    assert len(listed2.json()) == 0


async def test_get_missing_user_404(client):
    res = await client.get(f"/admin/api/users/{uuid.uuid4()}")
    assert res.status_code == 404
