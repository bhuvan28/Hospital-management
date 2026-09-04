from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenUser(ORMModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    active: bool
    permissions: list[str]
    navigation: list[dict]


class LoginResponse(BaseModel):
    user: TokenUser
    token_type: str = "bearer"


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    role: UserRole
    active: bool = True


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)
    role: UserRole | None = None
    active: bool | None = None


class UserOut(ORMModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    active: bool
