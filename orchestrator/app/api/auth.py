from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import verify_password, create_access_token, decode_token, hash_password
from app.core.config import settings
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse, TokenRefreshRequest

router = APIRouter(prefix="/auth", tags=["auth"])
_user_repo = UserRepository()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db)):
    user = await _user_repo.get_by_username(session, body.username)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Kullanıcı adı veya şifre hatalı"},
        )
    token = create_access_token(subject=user.id, username=user.username)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: TokenRefreshRequest, session: AsyncSession = Depends(get_db)):
    from jose import JWTError
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHORIZED", "message": "Geçersiz token"},
    )
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise exc

    user = await _user_repo.get_by_username(session, payload.get("username", ""))
    if user is None:
        raise exc

    token = create_access_token(subject=user.id, username=user.username)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )
