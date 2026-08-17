from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from backend.app.db.base import Base


# ============================================================
# User ORM Model
# ============================================================

class User(Base):
    """
    users 数据库表对应的 SQLAlchemy ORM Model。

    一条 User 数据大概：

    {
        id: 1,
        username: "hao",
        email: "hao@example.com",
        hashed_password: "$argon2id$...",
        is_active: true,
        created_at: ...,
        updated_at: ...
    }

    注意：

    数据库永远没有：

        password

    字段。

    只有：

        hashed_password
    """

    # PostgreSQL 表名。
    __tablename__ = "users"


    # ========================================================
    # Table Constraints
    # ========================================================
    #
    # username 不能重复。
    #
    # email 也不能重复。
    #
    # 我们显式命名 UniqueConstraint，
    # 以后 Alembic 和异常判断都会更清楚。
    #
    __table_args__ = (
        UniqueConstraint(
            "username",
            name="uq_users_username",
        ),
        UniqueConstraint(
            "email",
            name="uq_users_email",
        ),
    )


    # ========================================================
    # Primary Key
    # ========================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )


    # ========================================================
    # Username
    # ========================================================
    #
    # 用户登录身份之一。
    #
    # nullable=False：
    # 必须存在。
    #
    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )


    # ========================================================
    # Email
    # ========================================================

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


    # ========================================================
    # Password Hash
    # ========================================================
    #
    # 特别注意字段名字：
    #
    # hashed_password
    #
    # 而不是：
    #
    # password
    #
    # 数据库只能保存 Hash。
    #
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


    # ========================================================
    # Account Status
    # ========================================================
    #
    # is_active=True：
    # 用户账号可以正常使用。
    #
    # 后面如果：
    #
    # 禁用账号
    #
    # 可以改成 False。
    #
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )


    # ========================================================
    # Created Time
    # ========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


    # ========================================================
    # Updated Time
    # ========================================================

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )