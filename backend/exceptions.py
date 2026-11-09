"""将预期 HTTP 与参数错误转换为统一响应，保留未知异常原始堆栈。"""

from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from schemas import ResponseModel


def register_exception_handler(app: FastAPI):
    """向 app 注册预期错误响应处理器。"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """为 request 的 HTTP 错误 exc 保留状态码与认证头。"""
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content=ResponseModel(
                code=exc.status_code, msg=str(exc.detail)
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """将 request 的校验错误 exc 转为可读 400 响应。"""
        errors = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        return JSONResponse(
            status_code=400,
            content=ResponseModel(code=400, msg=f"参数校验失败: {errors}").model_dump(),
        )
