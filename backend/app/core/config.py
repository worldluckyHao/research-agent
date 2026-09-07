from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from typing import Literal, Optional

# ============================================================
# backend 目录的绝对路径
# ============================================================
#
# 当前文件：
#
# backend/app/core/config.py
#
# parents[0] -> core
# parents[1] -> app
# parents[2] -> backend
#
# 所以 BASE_DIR 最终指向：
#
# F:\PycharmProjects\research-agent\backend
#
BASE_DIR = Path(__file__).resolve().parents[2]


# ============================================================
# .env 文件路径
# ============================================================
#
# 最终指向：
#
# F:\PycharmProjects\research-agent\backend\.env
#
ENV_FILE = BASE_DIR / ".env"


# ============================================================
# 项目统一配置类
# ============================================================

class Settings(BaseSettings):
    """
    Research Agent 的统一配置中心。

    backend/.env
        ↓
    Settings()
        ↓
    settings
        ↓
    FastAPI / SQLAlchemy / Alembic
    """

    # ========================================================
    # Application
    # ========================================================

    # Swagger 中显示的项目名称。
    APP_NAME: str = "Research Agent API"

    # 当前项目版本。
    APP_VERSION: str = "0.1.0"

    # 当前运行环境。
    #
    # 只允许：
    # development
    # test
    # production
    ENVIRONMENT: Literal[
        "development",
        "test",
        "production",
    ] = "development"

    # 是否开启调试模式。
    DEBUG: bool = True


    # ========================================================
    # API
    # ========================================================

    # API v1 统一前缀。
    #
    # 最终：
    #
    # /api/v1/papers/
    #
    API_V1_PREFIX: str = "/api/v1"


    # ========================================================
    # Security
    # ========================================================

    # 项目密钥。
    #
    # Day12 JWT 登录时会使用。
    #
    # 不提供默认值，因此 backend/.env 中必须存在。
    SECRET_KEY: SecretStr

    # ========================================================
    # JWT
    # ========================================================

    # JWT 签名算法。
    #
    # Day12 当前使用：
    #
    # HS256
    #
    # 注意：
    # 这个值来自我们自己的可信配置，
    # 不是从客户端 Token 中动态决定算法。
    JWT_ALGORITHM: str = "HS256"

    # Access Token 有效时间，单位：分钟。
    #
    # 当前学习项目设置 30 分钟。
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


    # ========================================================
    # PostgreSQL
    # ========================================================

    # PostgreSQL 用户名。
    POSTGRES_USER: str

    # PostgreSQL 密码。
    #
    # SecretStr 可以避免普通 print 时直接显示明文密码。
    POSTGRES_PASSWORD: SecretStr

    # PostgreSQL 数据库名。
    POSTGRES_DB: str

    # PostgreSQL 地址。
    POSTGRES_HOST: str = "localhost"

    # PostgreSQL 默认端口。
    POSTGRES_PORT: int = 5432


    # ========================================================
    # Logging
    # ========================================================

    # 日志等级。
    #
    # 开发环境一般：
    # DEBUG
    #
    # 生产环境一般：
    # INFO
    LOG_LEVEL: str = "DEBUG"


    # ========================================================
    # CORS
    # ========================================================

    # 为以后前端 React / Next.js 调用 FastAPI 预留。
    #
    # 多个地址使用逗号分隔。
    CORS_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )

    # ========================================================
    # External HTTP Client
    # ========================================================

    # 建立 TCP/TLS 连接最长等待时间。
    HTTP_CONNECT_TIMEOUT: float = 5.0

    # 等待第三方 API 返回数据的最长时间。
    HTTP_READ_TIMEOUT: float = 10.0

    # 向第三方发送数据的最长时间。
    HTTP_WRITE_TIMEOUT: float = 10.0

    # 等待连接池空闲连接的最长时间。
    HTTP_POOL_TIMEOUT: float = 5.0

    # 整个应用允许的最大 HTTP 连接数。
    HTTP_MAX_CONNECTIONS: int = 50

    # 可保持 Keep-Alive 的连接数量。
    HTTP_MAX_KEEPALIVE_CONNECTIONS: int = 20


    # ========================================================
    # Crossref
    # ========================================================

    CROSSREF_BASE_URL: str = (
        "https://api.crossref.org/v1"
    )

    # 用于 User-Agent，便于第三方识别我们的应用。
    CROSSREF_USER_AGENT: str = (
        "Research-Agent/0.1"
    )

    # ========================================================
    # arXiv API
    # ========================================================

    # arXiv 官方查询接口。
    ARXIV_API_URL: str = (
        "https://export.arxiv.org/api/query"
    )

    # 官方建议连续 API 请求之间保留约 3 秒间隔。
    ARXIV_MIN_REQUEST_INTERVAL_SECONDS: float = 3.0

    # 我们自己的交互式搜索接口不允许一次请求过多结果。
    # arXiv 本身支持更大结果集，但 Research Agent 当前不需要。
    ARXIV_MAX_PAGE_SIZE: int = 50

    # ========================================================
    # Pydantic Settings 配置
    # ========================================================

    model_config = SettingsConfigDict(
        # 固定读取 backend/.env，
        # 不依赖 PowerShell 当前所在目录。
        env_file=ENV_FILE,

        # .env 文件编码。
        env_file_encoding="utf-8",

        # 如果 .env 中以后暂时多了一些字段，
        # 不直接导致程序启动失败。
        extra="ignore",

        # 环境变量名不区分大小写。
        case_sensitive=False,
    )


    # ========================================================
    # SQLAlchemy DATABASE_URL
    # ========================================================

    @property
    def DATABASE_URL(self) -> str:
        """
        根据 PostgreSQL 配置生成异步 SQLAlchemy URL。

        最终结构：

        postgresql+asyncpg://用户名:密码@主机:端口/数据库
        """

        # POSTGRES_PASSWORD 是 SecretStr。
        #
        # 真正连接数据库时，
        # 必须显式获取密码原始值。
        password = (
            self.POSTGRES_PASSWORD.get_secret_value()
        )

        return (
            "postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:"
            f"{password}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )


    # ========================================================
    # CORS Origins 转换
    # ========================================================

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        """
        将：

        http://localhost:3000,http://127.0.0.1:3000

        转成：

        [
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]

        后面可以直接交给 CORSMiddleware。
        """

        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def REDIS_URL(self) -> str:
        """
        Day21 Cache Redis URL。
        """

        return self._build_redis_url(
            self.REDIS_DB
        )

    def _build_redis_url(
        self,
        db: int,
    ) -> str:
        """
        为指定 Redis DB 构造连接 URL。
        """

        if self.REDIS_PASSWORD is not None:
            password = (
                self.REDIS_PASSWORD
                .get_secret_value()
            )

            return (
                f"redis://:{password}@"
                f"{self.REDIS_HOST}:"
                f"{self.REDIS_PORT}/"
                f"{db}"
            )

        return (
            f"redis://"
            f"{self.REDIS_HOST}:"
            f"{self.REDIS_PORT}/"
            f"{db}"
        )


    @property
    def CELERY_BROKER_URL(self) -> str:
        """
        Celery Broker Redis URL。
        """

        return self._build_redis_url(
            self.CELERY_BROKER_DB
        )


    @property
    def CELERY_RESULT_BACKEND_URL(self) -> str:
        """
        Celery Result Backend Redis URL。
        """

        return self._build_redis_url(
            self.CELERY_RESULT_DB
        )

    # ========================================================
    # OpenAlex
    # ========================================================

    # OpenAlex REST API 根地址。
    OPENALEX_BASE_URL: str = (
        "https://api.openalex.org"
    )

    # 可选。
    # 开发阶段不配置 API Key 也可以使用基础 API。
    OPENALEX_API_KEY: Optional[SecretStr] = None

    # 我们自己的 API 限制。
    # OpenAlex 官方最大支持 100，
    # Research Agent 当前限制 50，避免单请求过大。
    OPENALEX_MAX_PAGE_SIZE: int = 50


    # ========================================================
    # Redis
    # ========================================================

    REDIS_HOST: str = "localhost"

    REDIS_PORT: int = 6379

    REDIS_DB: int = 0

    REDIS_PASSWORD: Optional[SecretStr] = None

    # 多数据源论文搜索缓存时间。
    PAPER_SEARCH_CACHE_TTL_SECONDS: int = 300

    # ========================================================
    # Celery
    # ========================================================

    # Broker 使用 Redis DB 1。
    CELERY_BROKER_DB: int = 1

    # Result Backend 使用 Redis DB 2。
    CELERY_RESULT_DB: int = 2

    # Task result 保存时间。
    CELERY_RESULT_EXPIRES_SECONDS: int = 3600

# ============================================================
# ★ 非常重要：创建全局 Settings 实例
# ============================================================
#
# 注意：
#
# 这一行必须：
#
# 1. 存在
# 2. 写在 Settings 类外面
# 3. 顶格写
#
# 项目其他文件：
#
# from backend.app.core.config import settings
#
# 导入的就是下面这个对象。
#
settings = Settings()