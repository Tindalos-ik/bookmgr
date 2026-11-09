"""当前 MySQL 的异步会话及图书、用户、会话和收藏模型。"""

from collections.abc import AsyncIterator
from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from config import settings

engine = create_async_engine(
    settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=3600
)
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    """所有持久模型的元数据基类。"""


class BookDB(Base):
    """图书资料及受保护下载文件的内部元数据。"""

    __tablename__ = "books"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    author: Mapped[str | None] = mapped_column(String(60))
    category: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(String(3000))
    cover: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_format: Mapped[str | None] = mapped_column(String(10))
    file_size: Mapped[int | None] = mapped_column(Integer)
    file_path: Mapped[str | None] = mapped_column(String(255))


class UserDB(Base):
    """用户身份与密码哈希。"""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class AuthSessionDB(Base):
    """JWT jti 对应的可撤销登录会话。"""

    __tablename__ = "auth_sessions"
    jti: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class FavoriteDB(Base):
    """用户与图书的唯一收藏关系。"""

    __tablename__ = "favorites"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )


async def get_db() -> AsyncIterator[AsyncSession]:
    """为当前请求提供会话，退出时回收连接；无参数。"""
    async with AsyncSessionLocal() as session:
        yield session
