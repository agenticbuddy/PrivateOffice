"""FastAPI application entry point.

Serves the JSON API (/api), the WOPI host (/wopi) and the built Vue SPA (everything
else, with history-fallback to index.html). Routers are added per implementation block.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.routers import admin as admin_router
from app.routers import auth as auth_router
from app.routers import editor as editor_router
from app.routers import nodes as nodes_router
from app.routers import wopi as wopi_router
from app.services import auth as auth_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    _ensure_storage()
    yield


def _ensure_storage() -> None:
    """Create the MinIO bucket on boot (best-effort; tolerated if MinIO is absent)."""
    try:
        from app.storage import get_storage

        get_storage().ensure_bucket()
    except Exception:  # noqa: BLE001 — storage is optional at boot
        pass


async def _bootstrap_admin() -> None:
    """Create the admin user on first boot (idempotent)."""
    async with SessionLocal() as db:
        existing = await auth_service.get_user_by_email(db, settings.bootstrap_admin_email)
        if existing is None:
            await auth_service.create_user(
                db,
                email=settings.bootstrap_admin_email,
                full_name=settings.bootstrap_admin_name,
                locale="en",
                is_admin=True,
            )
            await db.commit()


app = FastAPI(title="PrivateOffice Workspace", lifespan=lifespan)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(nodes_router.router)
app.include_router(editor_router.router)
app.include_router(wopi_router.router)


# ---- SPA static serving with history fallback (mounted last) ----
from starlette.exceptions import HTTPException as StarletteHTTPException


class SPAStaticFiles(StaticFiles):
    """Serve hashed assets; fall back to index.html only for client-side routes.

    - Missing ``assets/*`` (or any path with a file extension) returns a clean 404 so a
      stale bundle reference fails loudly instead of being served HTML-as-JS.
    - The app shell (index.html) is sent with ``Cache-Control: no-cache`` so browsers
      always revalidate and pick up a new deploy immediately.
    """

    async def get_response(self, path: str, scope):  # type: ignore[override]
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            last = path.rsplit("/", 1)[-1]
            if exc.status_code != 404 or path.startswith("assets/") or "." in last:
                raise
            response = await super().get_response("index.html", scope)

        if response.media_type == "text/html" or path in ("", ".", "index.html"):
            response.headers["Cache-Control"] = "no-cache"
        return response


def mount_spa() -> None:
    static_dir = settings.static_dir
    if os.path.isdir(static_dir):
        app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="spa")


mount_spa()
