from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.models import User, UserRole
from app.modules.auth.utils import decode_token

bearer_scheme = HTTPBearer()

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise _credentials_exception

    email: str | None = payload.get("sub")
    if not email:
        raise _credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise _credentials_exception

    return user


def require_role(*roles: UserRole):
    """
    Dependency factory. Usage:
        Depends(require_role(UserRole.admin, UserRole.manager))
    """
    allowed = {r.value for r in roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker