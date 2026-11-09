# 定义数据模型，用于数据校验与统一响应
from pydantic import BaseModel, Field
from typing import Optional, Any, List

# 统一响应结构
class ResponseModel(BaseModel):
    # Field 用于描述字段
    code: int = Field(description="业务码，200表示成功")
    msg: str = Field(description="响应信息")
    data: Optional[Any] = Field(default=None, description="响应数据")

    @classmethod # 类方法
    def success(cls, data: Any = None, msg: str = "ok"):
        return cls(code=200, msg=msg, data=data)

    @classmethod
    def fail(cls, code: int, msg: str, data: Any = None):
        return cls(code=code, msg=msg, data=data)

# 图书创建入参
class BookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="书名，不可为空")
    price: float = Field(gt=0, description="价格必须大于0")

# 图书返回模型，继承自图书创建入参
class BookOut(BookCreate):
    id: int = Field(description="图书ID")
    model_config = {"from_attributes" : True} 
    # model_config 是 Pydantic 的配置项，用于配置模型的行为
    # from_attributes=True 表示从实例变量中获取数据，而不是从字典中获取

# 分页封装
class PageResp(BaseModel):
    list: List[BookOut]
    total: int
    page: int
    page_size: int

# Token 返回
class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"

