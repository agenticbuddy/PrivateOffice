"""Small shared helpers."""
import re
from datetime import datetime, timezone
from urllib.parse import quote


def content_disposition(filename: str) -> str:
    """Build an RFC 6266 Content-Disposition value safe for non-ASCII names.

    HTTP headers are latin-1; a raw UTF-8 ``filename="..."`` (e.g. a Cyrillic name)
    makes Starlette raise and the download 500s. We emit an ASCII fallback plus a
    percent-encoded ``filename*`` so every browser gets the correct, openable name.
    """
    ascii_fallback = re.sub(r"[^\x20-\x7e]", "_", filename).replace('"', "").strip()
    if not ascii_fallback:
        ascii_fallback = "download"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def now() -> datetime:
    return datetime.now(timezone.utc)


def as_aware(dt: datetime | None) -> datetime | None:
    """Normalize to tz-aware UTC. SQLite returns naive datetimes; PG returns aware."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
