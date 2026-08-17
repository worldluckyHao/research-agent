from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pwdlib import PasswordHash

from backend.app.core.config import settings


# ============================================================
# Password Hash Manager
# ============================================================
#
# Day11 已经使用：
#
# PasswordHash.recommended()
#
# 当前推荐方案会使用安全的专用密码哈希算法。
#
password_hash = PasswordHash.recommended()


# ============================================================
# Password Hash
# ============================================================

def hash_password(
    password: str,
) -> str:
    """
    将用户注册时提交的明文密码转换成密码 Hash。

    明文：

        Password123

            ↓

        hash_password()

            ↓

        $argon2id$...

    数据库保存的只能是返回值，
    绝对不能保存原始 password。
    """

    return password_hash.hash(password)


# ============================================================
# Password Verify
# ============================================================

def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    验证登录密码。

    参数：
    ----------
    plain_password:
        用户登录时提交的明文密码。

    hashed_password:
        PostgreSQL users.hashed_password
        中保存的密码 Hash。

    返回：
    ----------
    True:
        密码正确。

    False:
        密码错误。
    """

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


# ============================================================
# Create JWT Access Token
# ============================================================

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    创建 JWT Access Token。

    subject:
        Token 属于谁。

    Day12 我们传：

        username

    例如：

        subject="hao"

    Token Payload 最终大概：

        {
            "sub": "hao",
            "exp": ...
        }

    exp:
        JWT 标准 expiration time，
        表示 Token 何时过期。
    """

    # ========================================================
    # 1. 计算 Token 过期时间
    # ========================================================

    if expires_delta is not None:
        expire = (
            datetime.now(timezone.utc)
            + expires_delta
        )
    else:
        expire = (
            datetime.now(timezone.utc)
            + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )


    # ========================================================
    # 2. JWT Payload
    # ========================================================
    #
    # sub:
    #
    # subject，表示这个 Token 属于哪个用户。
    #
    # exp:
    #
    # Token 的过期时间。
    #
    payload = {
        "sub": subject,
        "exp": expire,
    }


    # ========================================================
    # 3. 获取 SECRET_KEY 真正字符串
    # ========================================================
    #
    # settings.SECRET_KEY 是 SecretStr，
    # 因此真正签名 JWT 时需要：
    #
    # get_secret_value()
    #
    secret_key = settings.SECRET_KEY.get_secret_value()


    # ========================================================
    # 4. JWT Encode
    # ========================================================
    #
    # 返回：
    #
    # eyJhbGciOiJIUzI1NiIs...
    #
    return jwt.encode(
        payload,
        secret_key,
        algorithm=settings.JWT_ALGORITHM,
    )