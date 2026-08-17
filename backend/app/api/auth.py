import logging

from fastapi import (
    APIRouter,
    Depends,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    InactiveUserException,
    InvalidCredentialsException,
)
from backend.app.core.security import (
    create_access_token,
)
from backend.app.dependencies import get_db
from backend.app.schemas.auth import TokenResponse
from backend.app.services import user_service


# ============================================================
# Logger
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# Auth Router
# ============================================================

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# ============================================================
# Login
# ============================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    # ========================================================
    # OAuth2 Login Form
    # ========================================================
    #
    # 非常重要：
    #
    # OAuth2PasswordRequestForm 读取的是 FORM DATA：
    #
    # username=...
    # password=...
    #
    # 而不是 JSON：
    #
    # {
    #   "username": "...",
    #   "password": "..."
    # }
    #
    form_data: OAuth2PasswordRequestForm = Depends(),

    # 数据库 Session。
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录接口。

    URL:

        POST /api/v1/auth/login

    登录成功：

        {
            "access_token": "...",
            "token_type": "bearer"
        }

    登录失败：

        HTTP 401
    """

    # ========================================================
    # 1. 验证 username + password
    # ========================================================

    user = await user_service.authenticate_user(
        db=db,
        username=form_data.username,
        password=form_data.password,
    )


    # ========================================================
    # 2. 用户不存在 / 密码错误
    # ========================================================

    if user is None:
        logger.warning(
            "Failed login attempt for username=%s",
            form_data.username,
        )

        raise InvalidCredentialsException()


    # ========================================================
    # 3. 用户账号是否有效
    # ========================================================

    if not user.is_active:
        logger.warning(
            "Inactive user login attempt: id=%s",
            user.id,
        )

        raise InactiveUserException()


    # ========================================================
    # 4. 创建 Access Token
    # ========================================================
    #
    # JWT 中：
    #
    # sub = username
    #
    access_token = create_access_token(
        subject=user.username
    )


    # ========================================================
    # 5. Login Success Log
    # ========================================================
    #
    # 注意：
    #
    # 不要打印：
    #
    # password
    # access_token
    # SECRET_KEY
    #
    logger.info(
        "User logged in: id=%s username=%s",
        user.id,
        user.username,
    )


    # ========================================================
    # 6. 返回 Token
    # ========================================================

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )