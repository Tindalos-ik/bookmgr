"""图书列表、管理和鉴权文件下载路由。"""

from typing import Literal
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, UserDB
from schemas import ResponseModel, BookCreate, PageResp, Publication
from services import BookService, book_out
from dependencies import get_current_user, require_admin
from fastapi import HTTPException

router = APIRouter(prefix="/books", tags=["图书管理"])


@router.get("/categories", response_model=ResponseModel, summary="查询已上架图书分类")
async def categories(
    db: AsyncSession = Depends(get_db), user: UserDB = Depends(get_current_user)
):
    """返回 db 内已上架分类，user 提供身份校验。"""
    return ResponseModel.success(await BookService.categories(db))


@router.get("", response_model=ResponseModel, summary="分页搜索图书列表")
async def list_books(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=50, description="每页图书数"),
    q: str = "",
    category: str | None = None,
    sort: Literal["newest", "name", "author"] = "newest",
    scope: Literal["published", "all"] = "published",
    db: AsyncSession = Depends(get_db),
    user: UserDB = Depends(get_current_user),
):
    """依据分页、q、category、sort 和 scope 查询 db；user 决定管理范围。"""
    if scope == "all" and user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    items, total = await BookService.list_book(
        db, page, page_size, q, category, sort, scope == "all"
    )
    return ResponseModel.success(
        PageResp(
            list=[book_out(b) for b in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("", response_model=ResponseModel, summary="管理员新增图书")
async def create_book(
    book_in: BookCreate,
    db: AsyncSession = Depends(get_db),
    user: UserDB = Depends(require_admin),
):
    """管理员 user 将 book_in 新增到 db。"""
    return ResponseModel.success(book_out(await BookService.create_book(db, book_in)))


@router.put("/{book_id}", response_model=ResponseModel, summary="管理员编辑图书")
async def update_book(
    book_id: int,
    book_in: BookCreate,
    db: AsyncSession = Depends(get_db),
    user: UserDB = Depends(require_admin),
):
    """管理员 user 用 book_in 更新 db 的 book_id。"""
    return ResponseModel.success(
        book_out(await BookService.update_book(db, book_id, book_in))
    )


@router.patch(
    "/{book_id}/publication", response_model=ResponseModel, summary="管理员调整上架状态"
)
async def publication(
    book_id: int,
    body: Publication,
    db: AsyncSession = Depends(get_db),
    user: UserDB = Depends(require_admin),
):
    """管理员 user 按 body 调整 db 的 book_id 上架状态。"""
    return ResponseModel.success(
        book_out(await BookService.publish(db, book_id, body.published))
    )


@router.get("/{book_id}/download", summary="下载已上架图书的 TXT 文件")
async def download(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserDB = Depends(get_current_user),
):
    """为已登录 user 下载 db 中 book_id 的受保护 TXT。"""
    path, filename = await BookService.download(db, book_id)
    return FileResponse(
        path,
        media_type="text/plain; charset=utf-8",
        filename=filename,
        headers={"Cache-Control": "no-store, private"},
    )


@router.get("/{book_id}", response_model=ResponseModel, summary="查询单本已上架图书")
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserDB = Depends(get_current_user),
):
    """为 user 返回 db 中已上架 book_id 的资料。"""
    return ResponseModel.success(
        book_out(await BookService.get_book_by_id(db, book_id))
    )


@router.delete("/{book_id}", response_model=ResponseModel, summary="管理员删除图书")
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserDB = Depends(require_admin),
):
    """管理员 user 删除 db 中 book_id 及收藏。"""
    await BookService.delete_book(db, book_id)
    return ResponseModel.success()
