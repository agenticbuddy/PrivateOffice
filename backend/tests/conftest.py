"""Test harness: in-process app over a fresh SQLite DB per test.

Env is configured *before* importing app modules so the SQLAlchemy engine binds to
SQLite. Each test drops and recreates the schema, then runs the app lifespan (which
recreates tables idempotently and bootstraps the admin user).
"""
import os

# Force test config (the container ships a Postgres DATABASE_URL we must override).
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/test_ws.db"
os.environ["STATIC_DIR"] = "/nonexistent-static"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "admin@example.com"
os.environ["MINIO_ENDPOINT"] = "http://minio:9000"

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client():
    from app.db import Base, engine
    from app.main import app

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture
async def db_session():
    from app.db import SessionLocal

    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def login(client):
    """Factory: create (or reuse) a user and return an authenticated client + id.

    Depends on ``client`` so the DB is reset and the app lifespan is active.
    """
    from app.db import SessionLocal
    from app.main import app
    from app.services import auth as svc

    transport = ASGITransport(app=app)
    opened: list[AsyncClient] = []

    async def _login(email: str, full_name: str = "User", locale: str = "en"):
        async with SessionLocal() as db:
            user = await svc.get_user_by_email(db, email)
            if user is None:
                user = await svc.create_user(
                    db, email=email, full_name=full_name, locale=locale
                )
            link = await svc.create_magic_link(db, user)
            await db.commit()
            token, uid = link.token, user.id
        ac = AsyncClient(transport=transport, base_url="http://test")
        await ac.post(f"/api/auth/magic/{token}")
        opened.append(ac)
        return ac, uid

    yield _login
    for ac in opened:
        await ac.aclose()
