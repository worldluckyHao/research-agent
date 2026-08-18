import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    EmailAlreadyExistsException,
    UsernameAlreadyExistsException,
)
from backend.app.core.security import hash_password, verify_password
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate
from backend.app.models.paper import Paper

# ============================================================
# Logger
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# 根据 Username 查询用户
# ============================================================

async def get_user_by_username(
    db: AsyncSession,
    username: str,
) -> Optional[User]:
    """
    根据 username 查询 User。

    找到：
        return User

    没找到：
        return None
    """

    stmt = select(User).where(
        User.username == username
    )

    result = await db.execute(stmt)

    return result.scalar_one_or_none()


# ============================================================
# 根据 Email 查询用户
# ============================================================

async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> Optional[User]:
    """
    根据 email 查询 User。
    """

    stmt = select(User).where(
        User.email == email
    )

    result = await db.execute(stmt)

    return result.scalar_one_or_none()


# ============================================================
# 用户注册
# ============================================================

# ============================================================
# User Authentication
# ============================================================

async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> Optional[User]:
    """
    用户登录认证。

    完整流程：

    username
        ↓
    根据 username 查询数据库
        ↓
    User 不存在
        ↓
    return None

    User 存在
        ↓
    verify_password()
        ↓
    密码错误
        ↓
    return None

    密码正确
        ↓
    return User
    """

    # ========================================================
    # 1. 标准化 username
    # ========================================================

    normalized_username = username.strip()


    # ========================================================
    # 2. 根据 username 查询数据库
    # ========================================================

    user = await get_user_by_username(
        db=db,
        username=normalized_username,
    )


    # ========================================================
    # 3. 用户不存在
    # ========================================================

    if user is None:
        return None


    # ========================================================
    # 4. 验证密码
    # ========================================================
    #
    # 用户提交：
    #
    # password
    #
    # 数据库：
    #
    # user.hashed_password
    #
    # verify_password 不会“解密”密码，
    # 而是判断两者是否匹配。
    #
    password_is_valid = verify_password(
        plain_password=password,
        hashed_password=user.hashed_password,
    )


    # ========================================================
    # 5. 密码错误
    # ========================================================

    if not password_is_valid:
        return None


    # ========================================================
    # 6. 登录认证成功
    # ========================================================

    return user

async def create_user(
    db: AsyncSession,
    user_data: UserCreate,
) -> User:
    """
    创建新用户。

    完整流程：

    1. 标准化 username / email
    2. 检查 username 是否存在
    3. 检查 email 是否存在
    4. Hash password
    5. 创建 User ORM
    6. INSERT PostgreSQL
    7. commit
    8. refresh
    9. 返回 User

    即使应用层已经做重复检查，

    数据库仍然保留：

    uq_users_username
    uq_users_email

    作为最终一致性保护。
    """

    # ========================================================
    # 标准化 Username
    # ========================================================
    #
    # 去除用户不小心输入的首尾空格：
    #
    # "  hao  "
    #
    # 变：
    #
    # "hao"
    #
    username = user_data.username.strip()


    # ========================================================
    # 标准化 Email
    # ========================================================
    #
    # Email 一般统一转小写保存。
    #
    # Example@Email.com
    #
    # ↓
    #
    # example@email.com
    #
    email = str(
        user_data.email
    ).lower()


    # ========================================================
    # 先检查 Username
    # ========================================================

    existing_username = await get_user_by_username(
        db=db,
        username=username,
    )

    if existing_username is not None:
        raise UsernameAlreadyExistsException()


    # ========================================================
    # 再检查 Email
    # ========================================================

    existing_email = await get_user_by_email(
        db=db,
        email=email,
    )

    if existing_email is not None:
        raise EmailAlreadyExistsException()


    # ========================================================
    # Hash Password
    # ========================================================
    #
    # 非常重要：
    #
    # user_data.password
    #
    # 绝对不能直接进入：
    #
    # User(...)
    #
    hashed_password = hash_password(
        user_data.password
    )


    # ========================================================
    # 创建 ORM User
    # ========================================================

    user = User(
        username=username,
        email=email,

        # 保存的是 Hash。
        hashed_password=hashed_password,

        # 新用户默认启用。
        is_active=True,
    )


    # ========================================================
    # Database Transaction
    # ========================================================

    try:
        # 加入 Session。
        db.add(user)

        # INSERT + COMMIT。
        await db.commit()

        # 读取数据库生成的：
        #
        # id
        # created_at
        # updated_at
        await db.refresh(user)

        logger.info(
            "User created: id=%s username=%s",
            user.id,
            user.username,
        )

        return user


    # ========================================================
    # UNIQUE Race Condition 保护
    # ========================================================
    #
    # 即使前面 SELECT 查过不存在，
    #
    # 也可能两个请求同时注册：
    #
    # Request A:
    # SELECT → 不存在
    #
    # Request B:
    # SELECT → 不存在
    #
    # 然后同时 INSERT。
    #
    # 所以数据库 UNIQUE 约束仍然是最后防线。
    #
    except IntegrityError as exc:
        await db.rollback()

        error_text = str(exc.orig)


        # Username UNIQUE。
        if "uq_users_username" in error_text:
            logger.warning(
                "Duplicate username during registration: %s",
                username,
            )

            raise UsernameAlreadyExistsException() from exc


        # Email UNIQUE。
        if "uq_users_email" in error_text:
            logger.warning(
                "Duplicate email during registration: %s",
                email,
            )

            raise EmailAlreadyExistsException() from exc


        # 不是我们认识的 IntegrityError。
        logger.exception(
            "Database integrity error while creating user"
        )

        raise


    # ========================================================
    # 未知异常
    # ========================================================

    except Exception:
        await db.rollback()

        logger.exception(
            "Unexpected error while creating user"
        )

        raise

# ============================================================
# 收藏 Paper
# ============================================================

async def save_paper(
    db: AsyncSession,
    user: User,
    paper: Paper,
) -> None:
    """
    将 Paper 加入当前用户的收藏列表。
    """

    # 已收藏则无需重复添加。
    if paper in user.saved_papers:
        return

    try:
        user.saved_papers.append(paper)
        await db.commit()

        logger.info(
            "Paper saved: user_id=%s paper_id=%s",
            user.id,
            paper.id,
        )

    except Exception:
        await db.rollback()
        logger.exception(
            "Failed to save paper"
        )
        raise


# ============================================================
# 取消收藏
# ============================================================

async def unsave_paper(
    db: AsyncSession,
    user: User,
    paper: Paper,
) -> None:
    """
    从当前用户的收藏列表移除 Paper。
    """

    if paper not in user.saved_papers:
        return

    try:
        user.saved_papers.remove(paper)
        await db.commit()

        logger.info(
            "Paper unsaved: user_id=%s paper_id=%s",
            user.id,
            paper.id,
        )

    except Exception:
        await db.rollback()
        logger.exception(
            "Failed to unsave paper"
        )
        raise