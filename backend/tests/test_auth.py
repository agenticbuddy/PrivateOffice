"""Contract tests for the auth block."""
import pytest


async def _make_user(email="user@example.com", full_name="Test User", locale="en"):
    """Create a user directly via the service (admin endpoints come later)."""
    from app.db import SessionLocal
    from app.services import auth as svc

    async with SessionLocal() as db:
        user = await svc.create_user(db, email=email, full_name=full_name, locale=locale)
        await db.commit()
        return user.id


async def test_me_requires_auth(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401


async def test_login_bad_credentials(client):
    res = await client.post("/api/auth/login", json={"email": "x@y.z", "password": "nope"})
    assert res.status_code == 401


async def test_password_login_flow(client):
    from app.db import SessionLocal
    from app.services import auth as svc

    await _make_user(email="alice@example.com")
    # set a password directly
    async with SessionLocal() as db:
        user = await svc.get_user_by_email(db, "alice@example.com")
        await svc.set_password(db, user, "s3cret")
        await db.commit()

    res = await client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "s3cret"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "alice@example.com"
    assert body["has_password"] is True
    assert client.cookies.get("ws_session")

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


async def test_magic_link_single_use(client):
    from app.db import SessionLocal
    from app.services import auth as svc

    await _make_user(email="bob@example.com")
    async with SessionLocal() as db:
        user = await svc.get_user_by_email(db, "bob@example.com")
        link = await svc.create_magic_link(db, user)
        await db.commit()
        token = link.token

    res = await client.post(f"/api/auth/magic/{token}")
    assert res.status_code == 200
    assert res.json()["email"] == "bob@example.com"

    # token cannot be reused
    res2 = await client.post(f"/api/auth/magic/{token}")
    assert res2.status_code == 401


async def test_set_password_and_locale(client):
    await _make_user(email="carol@example.com")
    from app.db import SessionLocal
    from app.services import auth as svc

    async with SessionLocal() as db:
        user = await svc.get_user_by_email(db, "carol@example.com")
        link = await svc.create_magic_link(db, user)
        await db.commit()
        token = link.token

    await client.post(f"/api/auth/magic/{token}")  # authenticate via magic link

    # set own password
    res = await client.post("/api/auth/password", json={"password": "newpass"})
    assert res.status_code == 200
    assert res.json()["has_password"] is True

    # change locale
    res = await client.patch("/api/auth/me", json={"locale": "de"})
    assert res.status_code == 200
    assert res.json()["locale"] == "de"


async def test_logout_clears_session(client):
    await _make_user(email="dave@example.com")
    from app.db import SessionLocal
    from app.services import auth as svc

    async with SessionLocal() as db:
        user = await svc.get_user_by_email(db, "dave@example.com")
        link = await svc.create_magic_link(db, user)
        await db.commit()
        token = link.token

    await client.post(f"/api/auth/magic/{token}")
    assert (await client.get("/api/auth/me")).status_code == 200

    await client.post("/api/auth/logout")
    client.cookies.clear()
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_bootstrap_admin_exists(client):
    from app.db import SessionLocal
    from app.services import auth as svc

    async with SessionLocal() as db:
        admin = await svc.get_user_by_email(db, "admin@example.com")
        assert admin is not None
        assert admin.is_admin is True
