"""Auth schemas."""
from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    email: str
    avatar_path: str | None = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
