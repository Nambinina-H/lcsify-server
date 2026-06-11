from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Gestion des utilisateurs (admin) ---------------------------------------


class UserAdminOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    created_at: str | None = None


class UserCreateIn(BaseModel):
    email: str = Field(min_length=3)
    name: str = Field(min_length=1)
    password: str = Field(min_length=6)
    role: str = "manager"


class UserUpdateIn(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class PasswordIn(BaseModel):
    password: str = Field(min_length=6)


class VerifyPasswordIn(BaseModel):
    password: str
