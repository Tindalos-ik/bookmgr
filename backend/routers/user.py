"""真实账户登录、会话撤销、个人收藏及首页概览路由。"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from database import get_db, UserDB, AuthSessionDB
from dependencies import (
    get_current_user,
    get_bearer_token,
    issue_token,
    password_context,
)
from schemas import ResponseModel, UserOut, TokenResp
from services import BookService, book_out

router = APIRouter(tags=["用户"])


@router.post("/auth/token", response_model=ResponseModel, summary="用户名密码登录")
async def login(
    form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """验证 form 用户名密码并在 db 创建登录会话。"""
    user = await db.scalar(select(UserDB).where(UserDB.username == form.username))
    if user is None or not password_context.verify(form.password, user.password_hash):
        raise HTTPException(
            401, "用户名或密码错误", headers={"WWW-Authenticate": "Bearer"}
        )
    token = await issue_token(db, user)
    return ResponseModel.success(
        TokenResp(access_token=token, user=UserOut.model_validate(user))
    )


@router.get("/auth/me", response_model=ResponseModel, summary="查询当前用户")
async def me(user: UserDB = Depends(get_current_user)):
    """返回当前已验证 user 的公开账户资料。"""
    return ResponseModel.success(UserOut.model_validate(user))


@router.post(
    "/auth/logout", response_model=ResponseModel, summary="退出并撤销当前登录会话"
)
async def logout(
    token: str = Depends(get_bearer_token),
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """在 db 撤销已验证 user 的当前 token 会话。"""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    await db.execute(
        delete(AuthSessionDB).where(
            AuthSessionDB.jti == payload["jti"], AuthSessionDB.user_id == user.id
        )
    )
    await db.commit()
    return ResponseModel.success()


@router.get("/favorites", response_model=ResponseModel, summary="查询当前用户收藏")
async def favorites(
    db: AsyncSession = Depends(get_db), user: UserDB = Depends(get_current_user)
):
    """返回 db 中当前 user 的已上架收藏全列表。"""
    return ResponseModel.success(
        [book_out(b) for b in await BookService.favorites(db, user.id)]
    )


@router.put("/favorites/{book_id}", response_model=ResponseModel, summary="收藏图书")
async def add_favorite(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserDB = Depends(get_current_user),
):
    """为当前 user 在 db 幂等收藏 book_id。"""
    await BookService.set_favorite(db, user.id, book_id, True)
    return ResponseModel.success()


@router.delete("/favorites/{book_id}", response_model=ResponseModel, summary="取消收藏")
async def remove_favorite(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserDB = Depends(get_current_user),
):
    """从 db 幂等删除当前 user 的 book_id 收藏。"""
    await BookService.set_favorite(db, user.id, book_id, False)
    return ResponseModel.success()


@router.get("/overview", response_model=ResponseModel, summary="查询首页概览")
async def overview(
    db: AsyncSession = Depends(get_db), user: UserDB = Depends(get_current_user)
):
    """返回 db 上架统计、最近四本、推荐及当前 user 收藏数。"""
    return ResponseModel.success(await BookService.overview(db, user.id))
