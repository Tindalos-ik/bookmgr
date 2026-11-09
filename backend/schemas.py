"""请求校验、公开图书资料和统一响应模型。"""

from datetime import datetime, UTC
from typing import Any, Literal, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ResponseModel(BaseModel):
    code: int = Field(description="业务码，与 HTTP 状态一致")
    msg: str = Field(description="响应信息")
    data: Any = Field(default=None, description="业务数据")

    @classmethod
    def success(cls, data: Any = None, msg: str = "ok"):
        """使用 data 数据和 msg 消息生成成功响应。"""
        return cls(code=200, msg=msg, data=data)


class BookCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(
        min_length=1, max_length=100, description="书名，去除首尾空白后必填"
    )
    author: str = Field(min_length=1, max_length=60, description="作者，必填")
    category: str = Field(min_length=1, max_length=40, description="分类，必填")
    description: str = Field(min_length=1, max_length=3000, description="简介，必填")
    price: float = Field(
        ge=0, allow_inf_nan=False, description="有限非负价格，允许零元"
    )
    cover: str = Field(
        default="", max_length=500, description="封面地址，空值使用书名封面"
    )
    published: bool = Field(default=False, description="是否上架")


class BookFile(BaseModel):
    name: str = Field(description="下载文件名")
    format: Literal["TXT"] = Field(description="文件格式")
    size: int = Field(description="真实文件字节数")
    url: str = Field(description="需要身份验证的下载接口地址")


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="数据库图书编号")
    name: str = Field(description="书名")
    price: float = Field(description="价格")
    author: str | None = Field(description="作者，历史资料可为空")
    category: str | None = Field(description="分类，历史资料可为空")
    description: str | None = Field(description="简介，历史资料可为空")
    cover: str = Field(description="封面展示地址")
    created_at: datetime = Field(description="UTC 创建时间，历史缺日期使用迁移时间")
    published_at: datetime | None = Field(description="最近上架的 UTC 时间")
    published: bool = Field(description="是否上架")
    file: BookFile | None = Field(default=None, description="可选下载附件")

    @field_validator("created_at", "published_at")
    @classmethod
    def utc_timestamp(cls, value: datetime | None):
        """为数据库 UTC 时间 value 补全时区，保留空上架日期。"""
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class PageResp(BaseModel):
    list: List[BookOut] = Field(description="当前页图书")
    total: int = Field(description="筛选后总数")
    page: int = Field(description="页码，从 1 开始")
    page_size: int = Field(description="每页数量，1 到 50")


class Publication(BaseModel):
    published: bool = Field(description="目标上架状态")


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(
        min_length=3, max_length=60, description="用户名，首尾去空白后为3到60字符"
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="密码，8到128字符，保留首尾空格且不能全为空白",
    )

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value):
        """去除用户名 value 的首尾空白，保留内部字符。"""
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def meaningful_password(cls, value: str):
        """拒绝全空白密码 value，保留有效密码原文。"""
        if not value.strip():
            raise ValueError("密码不能全为空白")
        return value


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    old_password: str = Field(
        min_length=1, max_length=128, description="当前密码，保留原始空白"
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="新密码，8到128字符，不能全为空白或与旧密码相同",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str, info):
        """校验新密码 value 有有效字符且与 info 中的旧密码不同。"""
        if not value.strip():
            raise ValueError("新密码不能全为空白")
        if value == info.data.get("old_password"):
            raise ValueError("新密码不能与旧密码相同")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="真实用户编号")
    username: str = Field(description="登录用户名")
    name: str = Field(description="显示名称")
    role: str = Field(description="用户角色 reader 或 admin")


class TokenResp(BaseModel):
    access_token: str = Field(description="JWT 访问令牌")
    token_type: str = Field(default="bearer", description="认证类型")
    user: UserOut = Field(description="当前登录用户")
