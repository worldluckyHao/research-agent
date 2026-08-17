from pydantic import BaseModel


# ============================================================
# Token Response
# ============================================================

class TokenResponse(BaseModel):
    """
    登录成功以后返回给客户端的数据。

    Example:

    {
        "access_token": "eyJ...",
        "token_type": "bearer"
    }
    """

    # JWT 本身。
    access_token: str

    # OAuth2 Bearer Token 标准类型。
    token_type: str = "bearer"


# ============================================================
# Token Data
# ============================================================

class TokenData(BaseModel):
    """
    从 JWT Payload 解码出来的数据。

    当前我们只需要：

        username

    JWT 中保存：

        "sub": username

    decode 之后：

        sub
          ↓
        TokenData.username
    """

    username: str