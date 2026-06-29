"""Contract tests for the node tree, permissions and sharing."""


async def test_create_and_list_folders(login):
    alice, _ = await login("alice@example.com", "Alice")
    res = await alice.post("/api/nodes/folder", json={"name": "Projects"})
    assert res.status_code == 201
    folder = res.json()
    assert folder["type"] == "folder"
    assert folder["my_role"] == "owner"

    # nested folder
    child = await alice.post(
        "/api/nodes/folder", json={"name": "2026", "parent_id": folder["id"]}
    )
    assert child.status_code == 201

    root = await alice.get("/api/nodes")
    assert root.status_code == 200
    assert [n["name"] for n in root.json()] == ["Projects"]

    children = await alice.get(f"/api/nodes?parent={folder['id']}")
    assert [n["name"] for n in children.json()] == ["2026"]


async def test_directory_lists_all_users(login):
    alice, _ = await login("alice@example.com", "Alice")
    await login("bob@example.com", "Bob")
    res = await alice.get("/api/users")
    emails = {u["email"] for u in res.json()}
    assert {"alice@example.com", "bob@example.com"} <= emails


async def test_outsider_cannot_access(login):
    alice, _ = await login("alice@example.com", "Alice")
    bob, _ = await login("bob@example.com", "Bob")
    folder = (await alice.post("/api/nodes/folder", json={"name": "Secret"})).json()

    assert (await bob.get(f"/api/nodes/{folder['id']}")).status_code == 403
    assert (await bob.get(f"/api/nodes?parent={folder['id']}")).status_code == 403


async def test_sharing_reader_and_editor(login):
    alice, _ = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    folder = (await alice.post("/api/nodes/folder", json={"name": "Shared"})).json()

    # share as reader
    put = await alice.put(
        f"/api/nodes/{folder['id']}/shares",
        json={"user_id": str(bob_id), "role": "reader"},
    )
    assert put.status_code == 200

    # bob now sees it & in shared-with-me
    detail = await bob.get(f"/api/nodes/{folder['id']}")
    assert detail.status_code == 200
    assert detail.json()["my_role"] == "reader"
    swm = await bob.get("/api/nodes/shared-with-me")
    assert [n["name"] for n in swm.json()] == ["Shared"]

    # reader cannot create inside
    denied = await bob.post(
        "/api/nodes/folder", json={"name": "X", "parent_id": folder["id"]}
    )
    assert denied.status_code == 403

    # upgrade to editor -> can create inside, inherited role
    await alice.put(
        f"/api/nodes/{folder['id']}/shares",
        json={"user_id": str(bob_id), "role": "editor"},
    )
    allowed = await bob.post(
        "/api/nodes/folder", json={"name": "X", "parent_id": folder["id"]}
    )
    assert allowed.status_code == 201
    assert allowed.json()["my_role"] == "owner"  # bob created it -> owner of child


async def test_only_owner_manages_shares_and_deletes(login):
    alice, _ = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    carol, carol_id = await login("carol@example.com", "Carol")
    folder = (await alice.post("/api/nodes/folder", json={"name": "Top"})).json()
    await alice.put(
        f"/api/nodes/{folder['id']}/shares",
        json={"user_id": str(bob_id), "role": "editor"},
    )

    # editor (bob) cannot add shares
    res = await bob.put(
        f"/api/nodes/{folder['id']}/shares",
        json={"user_id": str(carol_id), "role": "reader"},
    )
    assert res.status_code == 403

    # editor cannot delete the folder (owner only)
    assert (await bob.delete(f"/api/nodes/{folder['id']}")).status_code == 403

    # owner can list shares, then delete the node
    shares = await alice.get(f"/api/nodes/{folder['id']}/shares")
    assert any(s["user_id"] == str(bob_id) for s in shares.json())
    assert (await alice.delete(f"/api/nodes/{folder['id']}")).status_code == 204
    assert (await alice.get(f"/api/nodes/{folder['id']}")).status_code == 404


async def test_multiple_owners(login):
    alice, _ = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    folder = (await alice.post("/api/nodes/folder", json={"name": "Joint"})).json()
    await alice.put(
        f"/api/nodes/{folder['id']}/shares",
        json={"user_id": str(bob_id), "role": "owner"},
    )
    # bob, as co-owner, can delete
    assert (await bob.delete(f"/api/nodes/{folder['id']}")).status_code == 204
