"""Editor discovery: resolve the editor iframe URL for a file.

Fetches `/hosting/discovery` from CO (server-side, cached), picks the action `urlsrc`
for the file's extension/mode, and rewrites the host to the public origin so the
browser loads the editor through nginx (same origin as the SPA).
"""
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx

from app.config import get_settings

settings = get_settings()
_cache: dict[str, str | None] = {"xml": None}


async def _load_xml() -> str:
    if _cache["xml"] is None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.editor_internal_url}/hosting/discovery")
            resp.raise_for_status()
            _cache["xml"] = resp.text
    return _cache["xml"]  # type: ignore[return-value]


def clear_cache() -> None:
    _cache["xml"] = None


def _rewrite_host(urlsrc: str) -> str:
    """Swap only the scheme://host[:port] prefix, preserving the rest verbatim.

    CO's urlsrc ends with a trailing '?'; full urlparse/urlunparse would drop the
    empty query, so we replace just the prefix as a string.
    """
    src = urlparse(urlsrc)
    pub = urlparse(settings.public_origin)
    old_prefix = f"{src.scheme}://{src.netloc}"
    new_prefix = f"{pub.scheme}://{pub.netloc}"
    return new_prefix + urlsrc[len(old_prefix):]


async def editor_urlsrc(ext: str, can_write: bool) -> str:
    """Return the public iframe base `urlsrc` (ending with '?') for ext + mode."""
    root = ET.fromstring(await _load_xml())

    by_name: dict[str, str] = {}
    any_urlsrc: str | None = None
    for action in root.iter("action"):
        any_urlsrc = any_urlsrc or action.get("urlsrc")
        if action.get("ext") == ext:
            name = action.get("name") or ""
            url = action.get("urlsrc")
            if url:
                by_name[name] = url

    if can_write:
        chosen = by_name.get("edit") or by_name.get("view")
    else:
        chosen = by_name.get("view") or by_name.get("edit")
    chosen = chosen or any_urlsrc
    if not chosen:
        raise RuntimeError("No editor action urlsrc found in discovery")
    return _rewrite_host(chosen)
