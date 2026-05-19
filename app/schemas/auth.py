from app.schemas.common import ORMModel


class LoginRequest(ORMModel):
    email: str
    password: str


class TokenResponse(ORMModel):
    access_token: str
    token_type: str = "bearer"
