"""Editor session: hand the SPA everything needed to embed the editor iframe."""
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import EditorSessionOut
from app.security import sign_wopi_token
from app.services import audit as audit_service
from app.services import discovery, locales
from app.services import nodes as svc
from app.util import now

settings = get_settings()
router = APIRouter(prefix="/api/editor", tags=["editor"])


@router.get("/{node_id}", response_model=EditorSessionOut)
async def editor_session(
    node_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EditorSessionOut:
    node = await svc.get_node(db, node_id)
    if node is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Node not found")
    role = await svc.effective_role(db, user.id, node)
    if role is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access")
    if node.type != "file" or not node.storage_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not an editable file")

    can_write = role in ("owner", "editor")
    urlsrc = await discovery.editor_urlsrc(node.co_format or "", can_write)

    wopi_src = f"{settings.wopi_host_url}/wopi/files/{node_id}"
    lang = locales.co_lang(user.locale or "en")
    design = getattr(user, "design", None) or "glass"
    iframe_url = f"{urlsrc}WOPISrc={quote(wopi_src, safe='')}&lang={lang}&po_design={design}"

    token = sign_wopi_token({"u": str(user.id), "n": str(node_id), "w": can_write})
    ttl_ms = int((now().timestamp() + settings.wopi_token_ttl) * 1000)

    await audit_service.record(db, actor_id=user.id, action="open", node_id=node_id)
    await db.commit()

    return EditorSessionOut(
        iframe_url=iframe_url,
        access_token=token,
        access_token_ttl=ttl_ms,
        lang=lang,
        can_write=can_write,
    )
