# 业务异常与全局异常处理器
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from schemas import ResponseModel

class BusinessException(Exception):
    """
    自定义业务异常，业务主动抛出
    """
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

def register_exception_handler(app: FastAPI):
    # 业务异常
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        return JSONResponse(
            status_code=200,
            content=ResponseModel(code=exc.code, msg=exc.msg).model_dump()
        )

    # FastAPI 内置 HTTP 异常
    @app.exception_handler(FastAPIHTTPException)
    async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseModel(code=exc.status_code, msg=exc.detail).model_dump()
        )

    # Pydantic 参数校验异常
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        return JSONResponse(
            status_code=400,
            content=ResponseModel(code=400, msg=f"参数校验失败: {errors}").model_dump()
        )

    # 兜底全局异常
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=ResponseModel(code=500, msg="服务器内部错误").model_dump()
        )
