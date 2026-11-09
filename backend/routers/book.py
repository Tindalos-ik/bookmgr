# 图书路由 "/books"
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import ResponseModel, BookCreate, BookOut, PageResp
from services import BookService
from dependencies import get_current_user

router = APIRouter(prefix = "/books", tags = ["图书管理"])

@router.post("", response_model = ResponseModel, summary = "新增图书")
async def create_book(
    book_in: BookCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    book = await BookService.create_book(db, book_in)
    return ResponseModel.success(data = BookOut.model_validate(book))

@router.get("", response_model = ResponseModel, summary = "分页查询图书列表")
async def list_books(
    page: int = Query(1, ge = 1, description = "页码"),
    page_size: int = Query(10, ge = 1, le = 50, description = "每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    items, total = await BookService.list_book(db, page, page_size)
    data = PageResp(
        list = [BookOut.model_validate(item) for item in items],
        total = total,
        page = page,
        page_size = page_size
    )
    return ResponseModel.success(data = data)

@router.get("/{book_id}", response_model = ResponseModel, summary = "查询单本图书")
async def get_book(
    book_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    book = await BookService.get_book_by_id(db, book_id)
    return ResponseModel.success(data = BookOut.model_validate(book))

@router.delete("/{book_id}", response_model = ResponseModel, summary = "删除图书")
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    await BookService.delete_book(db, book_id)
    return ResponseModel.success(msg = "删除成功")