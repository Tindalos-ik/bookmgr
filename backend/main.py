# 应用入口
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from config import settings
from dependencies import create_access_token
from schemas import ResponseModel, TokenResp
from routers.book import router as book_router
from exceptions import register_exception_handler
from contextlib import asynccontextmanager
from database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # 启动阶段执行
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
    finally: 
        # 关闭阶段执行
        await engine.dispose()


app = FastAPI(title="图书管理API", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS, # 允许跨域的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常注册
register_exception_handler(app)

# 路由挂载
app.include_router(book_router)


# 测试用：签发token接口，真实项目对接登录逻辑
@app.post("/auth/token", response_model=ResponseModel, tags=["认证"])
async def login_test():
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "test_user_001"}, expires_delta=access_token_expires
    )
    return ResponseModel.success(data=TokenResp(access_token=access_token))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) # 这样可以直接 uv run main.py 启动