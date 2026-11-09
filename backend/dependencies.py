"""密码校验、JWT 签发和逐请求数据库权限检查。"""

from datetime import datetime, timedelta, UTC
from uuid import uuid4
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from database import get_db, UserDB, AuthSessionDB

password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


async def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """提取 credentials 中的 Bearer 令牌，缺失或错误类型返回 401。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            401, "请提供 Bearer 登录令牌", headers={"WWW-Authenticate": "Bearer"}
        )
    return credentials.credentials


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """为 data 声明签发 JWT，expires_delta 指定有效期。"""
    claims = data.copy()
    claims["exp"] = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def issue_token(db: AsyncSession, user: UserDB) -> str:
    """为 db 内的 user 创建持久会话并返回 JWT。"""
    jti = uuid4().hex
    duration = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    db.add(
        AuthSessionDB(
            jti=jti,
            user_id=user.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + duration,
        )
    )
    await db.commit()
    return create_access_token({"sub": str(user.id), "jti": jti}, duration)


async def get_current_user(
    token: str = Depends(get_bearer_token), db: AsyncSession = Depends(get_db)
) -> UserDB:
    """验证 token 和 db 中的会话，返回当前真实用户。"""
    invalid = HTTPException(
        401, "登录已失效，请重新登录", headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = int(payload["sub"])
        jti = payload["jti"]
        if not isinstance(jti, str) or "exp" not in payload:
            raise invalid
    except (JWTError, KeyError, ValueError, TypeError):
        raise invalid
    session = await db.get(AuthSessionDB, jti)
    if (
        session is None
        or session.user_id != user_id
        or session.expires_at <= datetime.now(UTC).replace(tzinfo=None)
    ):
        raise invalid
    user = await db.get(UserDB, user_id)
    if user is None:
        raise invalid
    return user


async def require_admin(user: UserDB = Depends(get_current_user)) -> UserDB:
    """检查 user 的当前数据库角色具有管理权限。"""
    if user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user
