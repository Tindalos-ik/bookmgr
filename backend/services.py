"""图书查询、管理、收藏和受保护本地文件业务。"""

from datetime import datetime, UTC
from pathlib import Path
from typing import Literal
from fastapi import HTTPException
from sqlalchemy import select, delete, func, or_
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from database import BookDB, FavoriteDB, UserDB, AuthSessionDB
from dependencies import password_context, issue_token
from schemas import (
    BookCreate,
    BookOut,
    BookFile,
    RegisterRequest,
    PasswordChangeRequest,
)

RESOURCE_ROOT = (Path(__file__).parent / "resources" / "books").resolve()


def utcnow():
    """返回用于 MySQL DATETIME 的当前 UTC 时间；无参数。"""
    return datetime.now(UTC).replace(tzinfo=None)


def book_out(book: BookDB) -> BookOut:
    """将 book 转为公开资料，隐藏内部文件路径。"""
    result = BookOut.model_validate(book)
    if book.file_name is not None:
        result.file = BookFile(
            name=book.file_name,
            format=book.file_format,
            size=book.file_size,
            url=f"/books/{book.id}/download",
        )
    return result


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, request: RegisterRequest) -> UserDB:
        """在 db 注册 request 指定的普通读者，唯一用户名冲突返回409。"""
        user = UserDB(
            username=request.username,
            name=request.username,
            role="reader",
            password_hash=password_context.hash(request.password),
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError as error:
            await db.rollback()
            if error.orig.args and error.orig.args[0] == 1062:
                raise HTTPException(409, "用户名已存在") from error
            raise
        await db.refresh(user)
        return user

    @staticmethod
    async def login(
        db: AsyncSession,
        username: str,
        password: str,
        portal: Literal["reader", "admin"] = "reader",
    ):
        """锁定 db 中 username，验证 password 和 portal 权限后按数据库角色签发会话。"""
        user = await db.scalar(
            select(UserDB)
            .where(UserDB.username == username)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None or not password_context.verify(password, user.password_hash):
            raise HTTPException(
                401, "用户名或密码错误", headers={"WWW-Authenticate": "Bearer"}
            )
        if portal == "admin" and user.role != "admin":
            raise HTTPException(403, "此账户无管理员入口权限")
        token = await issue_token(db, user)
        return user, token

    @staticmethod
    async def change_password(
        db: AsyncSession, user_id: int, request: PasswordChangeRequest
    ):
        """锁定 db 中 user_id 的最新密码，验证 request 后改密并撤销全部会话。"""
        user = await db.scalar(
            select(UserDB)
            .where(UserDB.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None:
            raise HTTPException(401, "登录已失效，请重新登录")
        if not password_context.verify(request.old_password, user.password_hash):
            raise HTTPException(400, "当前密码错误")
        user.password_hash = password_context.hash(request.new_password)
        await db.execute(delete(AuthSessionDB).where(AuthSessionDB.user_id == user_id))
        await db.commit()


class BookService:
    @staticmethod
    async def get_book_by_id(
        db: AsyncSession, book_id: int, include_hidden: bool = False
    ) -> BookDB:
        """按 book_id 查询 db；include_hidden 仅用于内部管理。"""
        book = await db.get(BookDB, book_id)
        if book is None or (not include_hidden and not book.published):
            raise HTTPException(404, "图书不存在")
        return book

    @staticmethod
    async def create_book(db: AsyncSession, book_in: BookCreate) -> BookDB:
        """将 book_in 图书资料写入 db。"""
        book = BookDB(
            **book_in.model_dump(),
            created_at=utcnow(),
            published_at=utcnow() if book_in.published else None,
        )
        db.add(book)
        await db.commit()
        await db.refresh(book)
        return book

    @staticmethod
    async def update_book(
        db: AsyncSession, book_id: int, book_in: BookCreate
    ) -> BookDB:
        """用 book_in 更新 db 内 book_id，保留文件和创建时间。"""
        book = await BookService.get_book_by_id(db, book_id, True)
        if book_in.published and not book.published:
            book.published_at = utcnow()
        for key, value in book_in.model_dump().items():
            setattr(book, key, value)
        await db.commit()
        return book

    @staticmethod
    async def publish(db: AsyncSession, book_id: int, published: bool) -> BookDB:
        """将 db 的 book_id 上架状态设为 published。"""
        book = await BookService.get_book_by_id(db, book_id, True)
        if published and not book.published:
            book.published_at = utcnow()
        book.published = published
        await db.commit()
        return book

    @staticmethod
    async def list_book(
        db: AsyncSession,
        page: int,
        page_size: int,
        q: str = "",
        category: str | None = None,
        sort: str = "newest",
        include_hidden: bool = False,
    ):
        """按 db、分页、q 书名作者、category 和 sort 查询；include_hidden 包含下架。"""
        stmt = select(BookDB)
        if not include_hidden:
            stmt = stmt.where(BookDB.published.is_(True))
        if q.strip():
            term = (
                "%"
                + q.strip()
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
                + "%"
            )
            stmt = stmt.where(
                or_(
                    BookDB.name.like(term, escape="\\"),
                    BookDB.author.like(term, escape="\\"),
                )
            )
        if category is not None:
            stmt = stmt.where(BookDB.category == category)
        total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
        order = {
            "newest": (BookDB.published_at.desc(), BookDB.id.desc()),
            "name": (BookDB.name.asc(), BookDB.id.asc()),
            "author": (BookDB.author.asc(), BookDB.id.asc()),
        }[sort]
        items = (
            await db.scalars(
                stmt.order_by(*order).offset((page - 1) * page_size).limit(page_size)
            )
        ).all()
        return items, total

    @staticmethod
    async def delete_book(db: AsyncSession, book_id: int):
        """在 db 同一事务删除 book_id 及其全部收藏引用。"""
        await BookService.get_book_by_id(db, book_id, True)
        await db.execute(delete(FavoriteDB).where(FavoriteDB.book_id == book_id))
        await db.execute(delete(BookDB).where(BookDB.id == book_id))
        await db.commit()

    @staticmethod
    async def favorites(db: AsyncSession, user_id: int):
        """查询 db 内 user_id 的所有已上架收藏。"""
        return (
            await db.scalars(
                select(BookDB)
                .join(FavoriteDB, FavoriteDB.book_id == BookDB.id)
                .where(FavoriteDB.user_id == user_id, BookDB.published.is_(True))
                .order_by(BookDB.published_at.desc(), BookDB.id.desc())
            )
        ).all()

    @staticmethod
    async def set_favorite(db: AsyncSession, user_id: int, book_id: int, enabled: bool):
        """在 db 为 user_id 幂等设置 book_id 收藏 enabled。"""
        if enabled:
            await BookService.get_book_by_id(db, book_id)
            stmt = insert(FavoriteDB).values(user_id=user_id, book_id=book_id)
            await db.execute(
                stmt.on_duplicate_key_update(book_id=stmt.inserted.book_id)
            )
        else:
            await db.execute(
                delete(FavoriteDB).where(
                    FavoriteDB.user_id == user_id, FavoriteDB.book_id == book_id
                )
            )
        await db.commit()

    @staticmethod
    async def download(db: AsyncSession, book_id: int):
        """校验 db 中 book_id 已上架且文件在资源目录内并存在。"""
        book = await BookService.get_book_by_id(db, book_id)
        if not book.file_path or not book.file_name:
            raise HTTPException(404, "本书暂无下载文件")
        path = (RESOURCE_ROOT / book.file_path).resolve()
        if not path.is_relative_to(RESOURCE_ROOT) or not path.is_file():
            raise HTTPException(404, "下载文件不存在")
        return path, book.file_name

    @staticmethod
    async def categories(db: AsyncSession):
        """返回 db 内已上架图书的非空分类，去重并排序。"""
        return (
            await db.scalars(
                select(BookDB.category)
                .where(
                    BookDB.published.is_(True),
                    BookDB.category.is_not(None),
                    func.trim(BookDB.category) != "",
                )
                .distinct()
                .order_by(BookDB.category)
            )
        ).all()

    @staticmethod
    async def overview(db: AsyncSession, user_id: int):
        """汇总 db 上架目录及 user_id 的可见收藏，附最新四本与推荐。"""
        visible = BookDB.published.is_(True)
        count = await db.scalar(select(func.count()).select_from(BookDB).where(visible))
        downloadable = await db.scalar(
            select(func.count())
            .select_from(BookDB)
            .where(visible, BookDB.file_path.is_not(None))
        )
        favorite_count = await db.scalar(
            select(func.count())
            .select_from(FavoriteDB)
            .join(BookDB, BookDB.id == FavoriteDB.book_id)
            .where(FavoriteDB.user_id == user_id, visible)
        )
        latest = (
            await db.scalars(
                select(BookDB)
                .where(visible)
                .order_by(BookDB.published_at.desc(), BookDB.id.desc())
                .limit(4)
            )
        ).all()
        recommendation = await db.scalar(
            select(BookDB).where(visible).order_by(BookDB.id).limit(1)
        )
        return {
            "book_count": count,
            "downloadable_count": downloadable,
            "favorite_count": favorite_count,
            "latest_books": [book_out(b) for b in latest],
            "recommendation": book_out(recommendation) if recommendation else None,
        }
