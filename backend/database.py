from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from collections.abc import AsyncIterator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from config import settings

# create_async_engine() 会为当前 MySQL 配置自动创建连接池，并返回一个异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo = True, # 是否在控制台打印SQL语句
    pool_pre_ping = True, # 自动检测断开的连接
    pool_recycle = 3600, # 连接池中连接的回收时间
    pool_size = 10, # 连接池大小
    max_overflow = 10, # 连接池时，允许额外创建的临时连接数
    pool_timeout = 30 # 连接全部占用时，等待可用连接的超时时间
)

# 异步会话工厂，用于创建异步会话
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# 定义基类，所有的ORM模型类都继承自这个基类，这样就可以避免重复定义表名和字段名
class Base(DeclarativeBase):
    pass

# DB ORM 模型
# 实例化之后就是表中一条记录
class BookDB(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)


"""
AsyncSessionLocal（会话工厂）
    → 创建 session（会话）
        → 通过 engine 使用连接池
            → 借用底层数据库连接
"""
async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        """
        为什么使用 yield 而不是 return
        因为数据库会话需要覆盖整个请求处理过程，yield 会交出 session 并暂停函数，
        保持 async with 没有退出，FastAPI 完成依赖的使用后，会恢复函数，让它退出 async with，关闭会话、释放连接资源
        """
        yield session 
