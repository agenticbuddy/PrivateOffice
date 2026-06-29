"""Pydantic request/response schemas shared across routers."""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---- Users / auth ----
class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    locale: str
    design: str = "glass"
    bio: str | None = None
    is_admin: bool
    is_active: bool
    has_password: bool

    model_config = {"from_attributes": True}


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class PasswordIn(BaseModel):
    # Internal tool: allow short passwords (e.g. "123"); just require non-empty.
    password: str = Field(min_length=1, max_length=200)


class LocaleIn(BaseModel):
    locale: str = Field(min_length=2, max_length=16)


class MePatchIn(BaseModel):
    locale: str | None = Field(default=None, min_length=2, max_length=16)
    design: str | None = Field(default=None, pattern="^(glass|classic)$")


# ---- Admin ----
class UserCreateIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    locale: str = Field(default="en", min_length=2, max_length=16)


class UserPatchIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    bio: str | None = None
    locale: str | None = Field(default=None, min_length=2, max_length=16)
    is_active: bool | None = None


class MagicLinkOut(BaseModel):
    url: str
    expires_at: datetime


class UserStats(BaseModel):
    files: int
    folders: int
    shared_out: int
    versions: int


class UserDetailOut(UserOut):
    created_at: datetime
    stats: UserStats


class UserSummaryOut(UserOut):
    files: int
    folders: int


# ---- Nodes / sharing ----
class FolderCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    parent_id: uuid.UUID | None = None


class FileCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    parent_id: uuid.UUID | None = None
    format: str = Field(pattern="^(docx|xlsx|pptx)$")


class NodePatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=512)
    parent_id: uuid.UUID | None = None


class NodeOut(BaseModel):
    id: uuid.UUID
    type: str
    name: str
    parent_id: uuid.UUID | None
    co_format: str | None
    mime: str | None
    size: int | None
    created_by: uuid.UUID
    creator_locale: str | None
    updated_at: datetime
    my_role: str | None = None

    model_config = {"from_attributes": True}


class UserDirectoryOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str

    model_config = {"from_attributes": True}


class ShareIn(BaseModel):
    user_id: uuid.UUID
    role: str = Field(pattern="^(owner|editor|reader)$")


class ShareOut(BaseModel):
    user_id: uuid.UUID
    role: str
    full_name: str
    email: str


class VersionOut(BaseModel):
    id: uuid.UUID
    size: int
    author_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EditorSessionOut(BaseModel):
    iframe_url: str
    access_token: str
    access_token_ttl: int
    lang: str
    can_write: bool
