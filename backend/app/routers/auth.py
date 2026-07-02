"""Account auth API."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_token, current_user, hash_password, normalize_email, verify_password
from app.database import get_db
from app.models.settings import UserSettings
from app.models.user import User
from app.schemas.auth import AuthRequest, AuthResponse, ChangePasswordRequest, UserResponse
from app.upload_paths import upload_dir, upload_path_from_url, upload_url

router = APIRouter()

AVATAR_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(data: AuthRequest, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "邮箱已注册")

    user = User(email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id, nickname=email.split("@")[0]))
    db.commit()
    db.refresh(user)
    return AuthResponse(token=create_token(user), user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(data: AuthRequest, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "邮箱或密码错误")
    return AuthResponse(token=create_token(user), user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[User, Depends(current_user)]):
    return user


@router.post("/password")
def change_password(
    data: ChangePasswordRequest,
    user: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "当前密码不正确")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"ok": True}


@router.post("/avatar", response_model=UserResponse)
async def upload_avatar(
    user: Annotated[User, Depends(current_user)],
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = AVATAR_EXTENSIONS.get(avatar.content_type or "")
    if not ext:
        raise HTTPException(400, "请上传 JPG、PNG、WebP 或 GIF 图片")

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = upload_dir("avatar") / filename
    content = await avatar.read()
    with open(filepath, "wb") as f:
        f.write(content)

    _remove_old_avatar(user.avatar_path)
    user.avatar_path = upload_url("avatar", filename)
    db.commit()
    db.refresh(user)
    return user


def _remove_old_avatar(path: str | None) -> None:
    if not path or not path.startswith("/uploads/avatar/"):
        return
    filepath = upload_path_from_url(path)
    if filepath and filepath.exists():
        filepath.unlink()
