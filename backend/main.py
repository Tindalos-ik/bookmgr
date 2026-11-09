"""图书管理 API 入口，数据库结构由 Alembic 显式迁移。"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import engine
from exceptions import register_exception_handler
from routers.book import router as book_router
from routers.user import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理 app 的数据库连接池生命周期。"""
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="图书管理API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handler(app)
app.include_router(book_router)
app.include_router(user_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
