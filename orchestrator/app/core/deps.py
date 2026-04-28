from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repo import UserRepository

_bearer = HTTPBearer()
_user_repo = UserRepository()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHORIZED", "message": "Geçersiz veya süresi dolmuş token"},
    )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise exc
    except JWTError:
        raise exc

    user = await _user_repo.get_by_username(session, payload.get("username", ""))
    if user is None:
        raise exc
    return user
