from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.admin import AdminUser

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")
DbSession = Annotated[Session, Depends(get_db)]


def get_current_admin(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> AdminUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        admin_id = payload.get("sub")
        if admin_id is None:
            raise credentials_error
    except JWTError as exc:
        raise credentials_error from exc

    admin = db.get(AdminUser, int(admin_id))
    if not admin or not admin.is_active:
        raise credentials_error
    return admin
