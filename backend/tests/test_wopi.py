"""Contract tests for the WOPI host and the editor-session endpoint."""
import uuid

import pytest


async def _make_file(client, fmt="docx", name="Doc"):
    return (await client.post("/api/nodes/file", json={"name": name, "format": fmt})).json()


async def test_wopi_check_get_put_roundtrip(login):
    alice, alice_id = await login("alice@example.com", "Alice")
    node = await _make_file(alice)
    nid = node["id"]

    from app.security import sign_wopi_token

    tok = sign_wopi_token({"u": str(alice_id), "n": nid, "w": True})

    cfi = await alice.get(f"/wopi/files/{nid}?access_token={tok}")
    assert cfi.status_code == 200
    body = cfi.json()
    assert body["BaseFileName"] == "Doc.docx"
    assert body["UserCanWrite"] is True
    assert body["UserFriendlyName"] == "Alice"
    assert body["PostMessageOrigin"]

    gf = await alice.get(f"/wopi/files/{nid}/contents?access_token={tok}")
    assert gf.status_code == 200
    assert gf.content[:2] == b"PK"

    pf = await alice.post(
        f"/wopi/files/{nid}/contents?access_token={tok}", content=b"PK-new-bytes"
    )
    assert pf.status_code == 200

    # a new version was recorded and current bytes updated
    versions = await alice.get(f"/api/nodes/{nid}/versions")
    assert len(versions.json()) == 2
    gf2 = await alice.get(f"/wopi/files/{nid}/contents?access_token={tok}")
    assert gf2.content == b"PK-new-bytes"


async def test_wopi_readonly_token_cannot_put(login):
    alice, alice_id = await login("alice@example.com", "Alice")
    node = await _make_file(alice)
    nid = node["id"]

    from app.security import sign_wopi_token

    ro = sign_wopi_token({"u": str(alice_id), "n": nid, "w": False})
    cfi = await alice.get(f"/wopi/files/{nid}?access_token={ro}")
    assert cfi.json()["UserCanWrite"] is False
    pf = await alice.post(f"/wopi/files/{nid}/contents?access_token={ro}", content=b"x")
    assert pf.status_code == 403


async def test_wopi_invalid_and_mismatched_token(login):
    alice, alice_id = await login("alice@example.com", "Alice")
    node = await _make_file(alice)
    nid = node["id"]

    assert (await alice.get(f"/wopi/files/{nid}?access_token=garbage")).status_code == 401

    from app.security import sign_wopi_token

    other = sign_wopi_token({"u": str(alice_id), "n": str(uuid.uuid4()), "w": True})
    res = await alice.get(f"/wopi/files/{nid}?access_token={other}")
    assert res.status_code == 401


async def test_editor_session(login, monkeypatch):
    alice, _ = await login("alice@example.com", "Alice", locale="de")
    node = await _make_file(alice)

    async def fake_urlsrc(ext, can_write):
        return "http://localhost:8088/browser/abc/cool.html?"

    monkeypatch.setattr("app.services.discovery.editor_urlsrc", fake_urlsrc)

    res = await alice.get(f"/api/editor/{node['id']}")
    assert res.status_code == 200
    body = res.json()
    assert "WOPISrc=" in body["iframe_url"]
    assert "lang=de" in body["iframe_url"]  # viewer locale -> CO lang
    assert body["can_write"] is True
    assert body["access_token"]
    assert body["access_token_ttl"] > 0


async def test_editor_session_permissions(login, monkeypatch):
    alice, _ = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    node = await _make_file(alice)

    async def fake_urlsrc(ext, can_write):
        return "http://localhost:8088/browser/abc/cool.html?"

    monkeypatch.setattr("app.services.discovery.editor_urlsrc", fake_urlsrc)

    # outsider: 403
    assert (await bob.get(f"/api/editor/{node['id']}")).status_code == 403

    # shared as reader -> can open but read-only
    await alice.put(
        f"/api/nodes/{node['id']}/shares",
        json={"user_id": str(bob_id), "role": "reader"},
    )
    res = await bob.get(f"/api/editor/{node['id']}")
    assert res.status_code == 200
    assert res.json()["can_write"] is False
