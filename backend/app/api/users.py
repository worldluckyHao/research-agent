from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import (
    get_current_user,
    get_db,
)
from backend.app.models.user import User
from backend.app.schemas.user import (
    UserCreate,
    UserResponse,
)
from backend.app.services import user_service


# ============================================================
# User Router
# ============================================================

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


# ============================================================
# Register
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册。

    这是公开接口。

    不要求登录。
    """

    return await user_service.create_user(
        db=db,
        user_data=user_data,
    )


# ============================================================
# Current User
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    # ========================================================
    # 关键：
    #
    # 只要 Router 参数加入：
    #
    # Depends(get_current_user)
    #
    # 这个接口就变成“受保护接口”。
    #
    # 没 Token：
    #   无法正常访问
    #
    # Token 无效：
    #   401
    #
    # Token 有效：
    #   current_user = 当前登录 User
    #
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    返回当前登录用户信息。

    URL:

        GET /api/v1/users/me

    Header:

        Authorization:
        Bearer <access_token>
    """

    return current_user