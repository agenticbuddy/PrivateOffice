"""Contract tests for file creation, upload, download and versions.

These exercise the real MinIO bucket reachable from the app container.
"""
import pytest


@pytest.mark.parametrize("fmt", ["docx", "xlsx", "pptx"])
async def test_create_blank_file(login, fmt):
    alice, _ = await login("alice@example.com", "Alice", locale="de")
    res = await alice.post("/api/nodes/file", json={"name": "Report", "format": fmt})
    assert res.status_code == 201
    node = res.json()
    assert node["type"] == "file"
    assert node["co_format"] == fmt
    assert node["name"] == f"Report.{fmt}"
    assert node["size"] and node["size"] > 0
    assert node["creator_locale"] == "de"  # created in creator's locale

    # download returns an OOXML (zip) payload
    dl = await alice.get(f"/api/nodes/{node['id']}/download")
    assert dl.status_code == 200
    assert dl.content[:2] == b"PK"

    # exactly one version after creation
    versions = await alice.get(f"/api/nodes/{node['id']}/versions")
    assert versions.status_code == 200
    assert len(versions.json()) == 1


async def test_upload_supported_and_rejected(login):
    alice, _ = await login("alice@example.com", "Alice")

    ok = await alice.post(
        "/api/nodes/upload",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert ok.status_code == 201
    assert ok.json()["co_format"] == "txt"

    bad = await alice.post(
        "/api/nodes/upload",
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
    )
    assert bad.status_code == 400


async def test_download_non_ascii_filename(login):
    """A Cyrillic-named file must download (RFC 6266 filename*), not 500."""
    alice, _ = await login("alice@example.com", "Alice", locale="ru")
    node = (await alice.post(
        "/api/nodes/file", json={"name": "Отчёт за июнь", "format": "xlsx"}
    )).json()
    res = await alice.get(f"/api/nodes/{node['id']}/download")
    assert res.status_code == 200
    assert res.content[:2] == b"PK"
    cd = res.headers["content-disposition"]
    assert "filename*=UTF-8''" in cd
    assert "%D0%9E" in cd  # 'О' percent-encoded


async def test_formats_endpoint(login):
    alice, _ = await login("alice@example.com", "Alice")
    res = await alice.get("/api/formats")
    assert res.status_code == 200
    body = res.json()
    assert [c["format"] for c in body["creatable"]] == ["docx", "xlsx", "pptx"]
    assert "xlsx" in body["supported_ext"]


async def test_upload_into_folder_requires_editor(login):
    alice, _ = await login("alice@example.com", "Alice")
    bob, bob_id = await login("bob@example.com", "Bob")
    folder = (await alice.post("/api/nodes/folder", json={"name": "Box"})).json()

    # bob (no access) cannot upload into alice's folder
    denied = await bob.post(
        "/api/nodes/upload",
        files={"file": ("x.txt", b"x", "text/plain")},
        data={"parent_id": folder["id"]},
    )
    assert denied.status_code == 403

    # alice can; file lands in the folder
    ok = await alice.post(
        "/api/nodes/upload",
        files={"file": ("x.txt", b"x", "text/plain")},
        data={"parent_id": folder["id"]},
    )
    assert ok.status_code == 201
    assert ok.json()["parent_id"] == folder["id"]
