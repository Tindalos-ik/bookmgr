"""使用当前 .env 的 MySQL 连接执行 Alembic 迁移。"""

import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from config import settings
from database import Base


def run_migrations(connection):
    """通过 connection 在当前数据库执行已登记迁移。"""
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_online():
    """读取当前配置并创建仅供迁移使用的连接；无参数。"""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("请连接当前 MySQL 执行迁移")
asyncio.run(run_online())
