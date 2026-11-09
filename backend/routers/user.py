"""真实账户登录、会话撤销、个人收藏及首页概览路由。"""

from typing import Literal
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from database import get_db, UserDB, AuthSessionDB
from dependencies import (
    get_current_user,
    get_bearer_token,
)
from schemas import (
    ResponseModel,
    UserOut,
    TokenResp,
    RegisterRequest,
    PasswordChangeRequest,
)
from services import AuthService, BookService, book_out

router = APIRouter(tags=["用户"])


@router.post("/auth/token", response_model=ResponseModel, summary="用户名密码登录")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    portal: Literal["reader", "admin"] = Form(
        default="reader", description="登录入口：reader 用户入口或 admin 管理员入口"
    ),
    db: AsyncSession = Depends(get_db),
):
    """验证 form 用户名密码及 portal 入口权限，在 db 创建真实角色会话。"""
    user, token = await AuthService.login(db, form.username, form.password, portal)
    return ResponseModel.success(
        TokenResp(access_token=token, user=UserOut.model_validate(user))
    )


@router.post("/auth/register", response_model=ResponseModel, summary="注册读者账户")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """使用 request 在 db 注册普通读者，返回公开资料且不自动登录。"""
    return ResponseModel.success(
        UserOut.model_validate(await AuthService.register(db, request))
    )


@router.put(
    "/auth/password", response_model=ResponseModel, summary="更改密码并退出全部会话"
)
async def change_password(
    request: PasswordChangeRequest,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """验证 request 旧密码并在 db 更新 user 密码，撤销全部会话。"""
    await AuthService.change_password(db, user.id, request)
    return ResponseModel.success()


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
