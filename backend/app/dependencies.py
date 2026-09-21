from collections.abc import AsyncGenerator
import redis.asyncio as redis
import jwt
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.clients.arxiv import (
    ArxivClient,
)
from backend.app.core.config import settings
from backend.app.core.exceptions import (
    InactiveUserException,
    InvalidCredentialsException,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.user import User
from backend.app.services import user_service
import httpx

from fastapi import (
    Depends,
    Request,
)
from backend.app.clients.openalex import (
    OpenAlexClient,
)

from backend.app.providers.openalex import (
    OpenAlexProvider,
)
from backend.app.clients.crossref import (
    CrossrefClient,
)
from backend.app.providers.arxiv import (
    ArxivProvider,
)
from backend.app.providers.crossref import (
    CrossrefProvider,
)
from backend.app.storage.base import (
    StorageBackend,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.embeddings.factory import (
    create_embedding_provider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.llms.factory import (
    create_llm_provider,
)
# ============================================================
# Database Dependency
# ============================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    为每个 HTTP Request 创建一个 AsyncSession。

    Request 开始：

        AsyncSessionLocal()

    Router / Service：

        使用 db

    Request 结束：

        async with 自动关闭 Session。
    """

    async with AsyncSessionLocal() as session:
        yield session


# ============================================================
# OAuth2 Bearer Token Dependency
# ============================================================
#
# tokenUrl：
#
# 告诉 Swagger/OpenAPI：
#
# “如果需要获取 Bearer Token，
#  去哪个登录接口？”
#
# 最终：
#
# /api/v1/auth/login
#
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=(
        f"{settings.API_V1_PREFIX}/auth/login"
    )
)


# ============================================================
# Current User Dependency
# ============================================================

async def get_current_user(
    # ========================================================
    # 1. 从 Authorization Header 中提取 Bearer Token
    # ========================================================
    #
    # 客户端发送：
    #
    # Authorization: Bearer eyJ...
    #
    # OAuth2PasswordBearer 会自动：
    #
    # 取出 eyJ...
    #
    token: str = Depends(oauth2_scheme),

    # ========================================================
    # 2. 数据库 Session
    # ========================================================

    db: AsyncSession = Depends(get_db),

) -> User:
    """
    根据 JWT Token 获取当前登录用户。

    完整流程：

    Authorization Header
           ↓
    OAuth2PasswordBearer
           ↓
         token
           ↓
       jwt.decode()
           ↓
     获取 payload["sub"]
           ↓
       username
           ↓
    PostgreSQL 查 User
           ↓
      current_user
    """

    try:
        # ====================================================
        # 3. JWT Decode
        # ====================================================

        payload = jwt.decode(
            token,

            # 获取真正 SECRET_KEY。
            settings.SECRET_KEY.get_secret_value(),

            # 只允许我们配置的算法。
            algorithms=[
                settings.JWT_ALGORITHM
            ],
        )


        # ====================================================
        # 4. 获取 sub
        # ====================================================
        #
        # 我们创建 Token 时：
        #
        # "sub": user.username
        #
        username = payload.get("sub")


        # ====================================================
        # 5. Token 没有 sub
        # ====================================================

        if username is None:
            raise InvalidCredentialsException()


    # ========================================================
    # 6. JWT 无效 / JWT 已过期
    # ========================================================
    #
    # PyJWT 的各种 Token 验证问题最终都属于：
    #
    # jwt.InvalidTokenError
    #
    except jwt.InvalidTokenError:
        raise InvalidCredentialsException()


    # ========================================================
    # 7. 根据 username 查询数据库
    # ========================================================

    user = await user_service.get_user_by_username(
        db=db,
        username=username,
    )


    # ========================================================
    # 8. Token 中 username 对应的 User 不存在
    # ========================================================

    if user is None:
        raise InvalidCredentialsException()


    # ========================================================
    # 9. 用户已被禁用
    # ========================================================

    if not user.is_active:
        raise InactiveUserException()


    # ========================================================
    # 10. 返回当前用户
    # ========================================================

    return user

def get_http_client(
    request: Request,
) -> httpx.AsyncClient:
    """
    获取应用级共享 HTTPX Client。
    """

    return request.app.state.http_client

def get_arxiv_client(
    request: Request,
) -> ArxivClient:
    """
    获取应用级 arXiv Client。
    """

    return request.app.state.arxiv_client

def get_openalex_provider(
    request: Request,
) -> OpenAlexProvider:
    """
    构建 OpenAlex Provider。

    Provider 本身无长期状态，
    底层仍复用应用级 HTTPX AsyncClient。
    """

    http_client = (
        request.app.state.http_client
    )

    openalex_client = OpenAlexClient(
        client=http_client
    )

    return OpenAlexProvider(
        client=openalex_client
    )

def get_arxiv_provider(
    request: Request,
) -> ArxivProvider:
    """
    ArxivClient 必须复用应用级实例，
    因为它内部保存 Rate Limit 状态。
    """

    return ArxivProvider(
        client=request.app.state.arxiv_client
    )


def get_crossref_provider(
    request: Request,
) -> CrossrefProvider:
    """
    Crossref Client 本身无长期状态，
    底层复用共享 HTTPX AsyncClient。
    """

    client = CrossrefClient(
        client=request.app.state.http_client
    )

    return CrossrefProvider(
        client=client
    )

def get_redis(
    request: Request,
) -> redis.Redis:
    """
    获取 Application 级 Redis Client。
    """

    return request.app.state.redis

def get_storage_backend(
    request: Request,
) -> StorageBackend:
    """
    获取 Application 级 Storage Backend。
    """

    return request.app.state.storage

def get_embedding_provider(
) -> EmbeddingProvider:
    """
    获取当前进程缓存的
    Embedding Provider。
    """

    return (
        create_embedding_provider()
    )

def get_llm_provider(
) -> LLMProvider:
    """
    获取当前进程缓存的 LLM Provider。
    """

    return (
        create_llm_provider()
    )