from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    PaperNotFoundException,
)
from backend.app.dependencies import (
    get_current_user,
    get_db,
)
from backend.app.models.user import User
from backend.app.schemas.user import (
    UserCreate,
    UserResponse,
    UserSavedPapersResponse,
)
from backend.app.services import (
    paper_service,
    user_service,
)

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

# ============================================================
# 收藏 Paper
# ============================================================

@router.post(
    "/me/saved-papers/{paper_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def save_paper(
    paper_id: int,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    当前登录用户收藏 Paper。
    """

    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
    )

    if paper is None:
        raise PaperNotFoundException()

    await user_service.save_paper(
        db=db,
        user=current_user,
        paper=paper,
    )


# ============================================================
# 取消收藏
# ============================================================

@router.delete(
    "/me/saved-papers/{paper_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unsave_paper(
    paper_id: int,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    当前登录用户取消收藏 Paper。
    """

    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
    )

    if paper is None:
        raise PaperNotFoundException()

    await user_service.unsave_paper(
        db=db,
        user=current_user,
        paper=paper,
    )

# ============================================================
# 获取收藏列表
# ============================================================

@router.get(
    "/me/saved-papers",
    response_model=UserSavedPapersResponse,
)
async def get_saved_papers(
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    返回当前用户收藏的 Papers。
    """

    return {
        "items": current_user.saved_papers,
        "total": len(
            current_user.saved_papers
        ),
    }