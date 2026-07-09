"""Contract tests for the notification inbox.

Covers the four event types (view / edit / share / unshare), the self-action skip
(you are never notified about your own action), the view/edit collapse, and mark-read.
"""
import pytest

from app.security import sign_wopi_token


async def _make_file(client, fmt="docx", name="Doc"):
    return (await client.post("/api/nodes/file", json={"name": name, "format": fmt})).json()


async def _notifs(client):
    return (await client.get("/api/notifications")).json()


async def test_share_notifies_target_only(login):
    alice, _ = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    node = await _make_file(alice, name="Budget")

    await alice.put(f"/api/nodes/{node['id']}/shares", json={"user_id": str(bob_id), "role": "reader"})

    got = await _notifs(bob)
    assert got["unread"] == 1
    item = got["items"][0]
    assert item["type"] == "share"
    assert item["role"] == "reader"
    assert item["node_name"] == node["name"]  # "Budget.docx"
    assert item["actor_name"] == "Alice"
    assert item["node_id"] == node["id"]
    assert item["read"] is False

    # the actor (alice) is NOT notified about her own share
    assert (await _notifs(alice))["unread"] == 0


async def test_unshare_notifies_target(login):
    alice, _ = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    node = await _make_file(alice)

    await alice.put(f"/api/nodes/{node['id']}/shares", json={"user_id": str(bob_id), "role": "editor"})
    await alice.delete(f"/api/nodes/{node['id']}/shares/{bob_id}")

    got = await _notifs(bob)
    types = [i["type"] for i in got["items"]]
    assert "unshare" in types
    assert got["items"][0]["type"] == "unshare"  # newest first


async def test_view_notifies_owner_not_self(login, monkeypatch):
    alice, _ = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    node = await _make_file(alice)

    async def fake_urlsrc(ext, can_write):
        return "http://localhost:8088/browser/abc/cool.html?"

    monkeypatch.setattr("app.services.discovery.editor_urlsrc", fake_urlsrc)

    # owner opening her own doc must NOT notify herself
    await alice.get(f"/api/editor/{node['id']}")
    assert (await _notifs(alice))["unread"] == 0

    # collaborator opening it notifies the owner
    await alice.put(f"/api/nodes/{node['id']}/shares", json={"user_id": str(bob_id), "role": "reader"})
    await bob.get(f"/api/editor/{node['id']}")

    got = await _notifs(alice)
    view = [i for i in got["items"] if i["type"] == "view"]
    assert len(view) == 1
    assert view[0]["actor_name"] == "Bob"


async def test_edit_collapses_into_one_unread(login):
    alice, alice_id = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    node = await _make_file(alice)
    nid = node["id"]

    tok = sign_wopi_token({"u": str(bob_id), "n": nid, "w": True})
    # two saves by bob collapse into a single unread "edit" with count == 2
    await bob.post(f"/wopi/files/{nid}/contents?access_token={tok}", content=b"PK-1")
    await bob.post(f"/wopi/files/{nid}/contents?access_token={tok}", content=b"PK-2")

    got = await _notifs(alice)
    edits = [i for i in got["items"] if i["type"] == "edit"]
    assert len(edits) == 1
    assert edits[0]["count"] == 2
    assert edits[0]["actor_name"] == "Bob"

    # alice saving her own file does not notify herself
    atok = sign_wopi_token({"u": str(alice_id), "n": nid, "w": True})
    await alice.post(f"/wopi/files/{nid}/contents?access_token={atok}", content=b"PK-3")
    assert len([i for i in (await _notifs(alice))["items"] if i["type"] == "edit"]) == 1


async def test_mark_read(login):
    alice, _ = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    node = await _make_file(alice)

    await alice.put(f"/api/nodes/{node['id']}/shares", json={"user_id": str(bob_id), "role": "reader"})
    await alice.delete(f"/api/nodes/{node['id']}/shares/{bob_id}")

    got = await _notifs(bob)
    assert got["unread"] == 2
    first_id = got["items"][0]["id"]

    # mark one read
    assert (await bob.post(f"/api/notifications/{first_id}/read")).status_code == 204
    assert (await _notifs(bob))["unread"] == 1

    # mark all read
    assert (await bob.post("/api/notifications/read")).status_code == 204
    after = await _notifs(bob)
    assert after["unread"] == 0
    assert all(i["read"] for i in after["items"])
