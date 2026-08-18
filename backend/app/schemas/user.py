from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)
from backend.app.schemas.paper import (
    PaperResponse,
)

# ============================================================
# User Registration Request
# ============================================================

class UserCreate(BaseModel):
    """
    用户注册请求 Schema。

    客户端需要提交：

    {
        "username": "...",
        "email": "...",
        "password": "..."
    }

    注意：

    UserCreate 有 password，

    因为注册时客户端当然必须提供密码。

    但是 UserResponse 绝对不能有 password。
    """

    # 不允许客户端提交未知字段。
    model_config = ConfigDict(
        extra="forbid",
    )


    # ========================================================
    # Username
    # ========================================================

    username: str = Field(
        min_length=3,
        max_length=50,
    )


    # ========================================================
    # Email
    # ========================================================
    #
    # EmailStr 会验证基本 Email 格式。
    #
    # 比普通 str 更适合。
    #
    email: EmailStr


    # ========================================================
    # Plain Password
    # ========================================================
    #
    # 这里只是 Request 中的明文密码。
    #
    # Service 收到后必须立刻进行 hash，
    # 不能原样存数据库。
    #
    # 当前学习项目先要求：
    #
    # 8 ~ 128 字符
    #
    # 后面正式产品还可以设计更完整密码策略。
    #
    password: str = Field(
        min_length=8,
        max_length=128,
    )


# ============================================================
# User API Response
# ============================================================

class UserResponse(BaseModel):
    """
    返回给客户端的 User 数据。

    特别注意：

    这里没有：

        password

    也没有：

        hashed_password

    两种密码信息都绝对不应该返回给客户端。
    """

    # 允许从 SQLAlchemy ORM 对象读取字段。
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    username: str

    email: EmailStr

    is_active: bool

    created_at: datetime

    updated_at: datetime

class UserSavedPapersResponse(BaseModel):
    """
    当前用户的收藏列表。
    """

    items: list[PaperResponse]
    total: int