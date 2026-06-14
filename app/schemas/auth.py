from app.schemas.common import ORMModel


class LoginRequest(ORMModel):
    email: str
    password: str


class RegisterRequest(ORMModel):
    name: str
    email: str
    phone: str | None = None
    password: str


class OtpRequest(ORMModel):
    email: str


class OtpVerifyRequest(ORMModel):
    email: str
    code: str
    name: str | None = None
    phone: str | None = None


class GoogleLoginRequest(ORMModel):
    credential: str


class TokenResponse(ORMModel):
    access_token: str
    token_type: str = "bearer"
    role: str | None = None
    name: str | None = None
    email: str | None = None
    refresh_token: str | None = None


class RefreshTokenRequest(ORMModel):
    refresh_token: str
