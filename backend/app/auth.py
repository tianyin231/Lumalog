"""Small local auth helpers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

AUTH_SECRET = os.getenv("AUTH_SECRET", "lumalog-local-dev-secret")
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
bearer = HTTPBearer(auto_error=False)


def normalize_email(email: str) -> str:
    value = email.strip().lower()
    if not EMAIL_RE.match(value):
        raise HTTPException(400, "邮箱格式不正确")
    return value


def hash_password(password: str) -> str:
    if len(password) < 6:
        raise HTTPException(400, "密码至少 6 位")
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256${salt}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return hmac.compare_digest(base64.urlsafe_b64encode(check).decode(), digest)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(user: User) -> str:
    payload = {"sub": user.id, "email": user.email, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(sig)}"


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not credentials:
        raise HTTPException(401, "请先登录")
    try:
        body, sig = credentials.credentials.split(".", 1)
        expected = _b64(hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(body))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        user = db.get(User, int(payload["sub"]))
    except Exception:
        raise HTTPException(401, "登录已失效")
    if not user:
        raise HTTPException(401, "账号不存在")
    return user
