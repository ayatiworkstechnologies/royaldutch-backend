from app.schemas.common import ORMModel, Timestamped


class AdminUserCreate(ORMModel):
    name: str
    email: str
    password: str | None = None
    role: str
    is_active: bool = True


class AdminUserUpdate(ORMModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


class AdminUserRead(Timestamped):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
