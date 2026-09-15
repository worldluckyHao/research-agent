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

    @property
    def LOCAL_STORAGE_PATH(self) -> Path:
        """
        本地 Storage 的绝对路径。

        BASE_DIR 当前指向 backend/，
        所以默认结果类似：

        F:/PycharmProjects/research-agent/backend/storage
        """

        return (
            BASE_DIR
            / self.LOCAL_STORAGE_DIR
        ).resolve()


    @property
    def PDF_MAX_SIZE_BYTES(self) -> int:
        """
        将 MB 转换成字节。

        Storage 层最终使用 bytes 判断文件大小。
        """

        return (
            self.PDF_MAX_SIZE_MB
            * 1024
            * 1024
        )

    @property
    def CHUNK_STRIDE_TOKENS(self) -> int:
        """
        Chunk 滑动窗口步长。

        stride = chunk_size - overlap

        默认：
        800 - 120 = 680
        """

        stride = (
            self.CHUNK_SIZE_TOKENS
            - self.CHUNK_OVERLAP_TOKENS
        )

        if stride <= 0:
            raise ValueError(
                "CHUNK_OVERLAP_TOKENS must "
                "be smaller than CHUNK_SIZE_TOKENS"
            )

        return stride

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

    # ========================================================
    # File Storage
    # ========================================================

    # Day23 当前实现本地文件存储。
    # 后续可以扩展为 s3 / minio。
    STORAGE_BACKEND: Literal["local"] = "local"

    # 相对于 backend/ 的目录。
    LOCAL_STORAGE_DIR: str = "storage"

    # 单个 PDF 最大 50 MB。
    PDF_MAX_SIZE_MB: int = 50

    # 文件流式读写块大小：1 MB。
    STORAGE_CHUNK_SIZE_BYTES: int = 1024 * 1024

    # ========================================================
    # PDF Parsing
    # ========================================================

    # Day24 当前使用 PyMuPDF。
    PDF_PARSER: Literal["pymupdf"] = "pymupdf"

    # 单页为空时仍保留 Page Record，
    # 保证 page_number 不发生错位。
    PDF_KEEP_EMPTY_PAGES: bool = True

    # ========================================================
    # Text Chunking
    # ========================================================

    # Day25 默认使用 Token Window Chunker。
    CHUNKER_NAME: Literal["token_window"] = "token_window"

    # tiktoken 编码器。
    CHUNK_TOKENIZER_NAME: str = "cl100k_base"

    # 每个 Chunk 的目标 Token 数。
    #
    # Day26 调整为 384，
    # 为 Embedding Model 的实际 tokenizer
    # 留出输入长度安全空间。
    CHUNK_SIZE_TOKENS: int = 384

    # 相邻 Chunk 保留一定上下文。
    CHUNK_OVERLAP_TOKENS: int = 64

    # ========================================================
    # Embedding
    # ========================================================

    # 当前使用本地 Sentence Transformer。
    EMBEDDING_PROVIDER: Literal[
        "sentence_transformer"
    ] = "sentence_transformer"

    # 多语言 E5。
    EMBEDDING_MODEL_NAME: str = (
        "intfloat/multilingual-e5-small"
    )

    # auto:
    # CUDA 可用时使用 GPU，
    # 否则使用 CPU。
    EMBEDDING_DEVICE: str = "auto"

    # 每批一次送入模型多少 Chunk。
    EMBEDDING_BATCH_SIZE: int = 32

    # E5-small 输出维度。
    #
    # Day27 pgvector 会直接使用这个值。
    EMBEDDING_DIMENSION: int = 384

    # 是否归一化到单位向量。
    EMBEDDING_NORMALIZE: bool = True

    # 不允许模型悄悄截断 Chunk。
    # 输入过长时直接报错，
    # 便于及时调整 Chunk 策略。
    EMBEDDING_REJECT_TRUNCATION: bool = True

    # Swagger Preview 最多一次计算几个 Chunk。
    EMBEDDING_PREVIEW_MAX_CHUNKS: int = 10

    # ========================================================
    # Vector Persistence
    # ========================================================

    # 一个 Document 的 Embedding Job
    # 每批读取多少 Chunk。
    EMBEDDING_JOB_BATCH_SIZE: int = 64

    # HNSW Index 参数。
    #
    # m：
    # 每个节点构建多少连接。
    VECTOR_HNSW_M: int = 16

    # 构建索引时的搜索宽度。
    VECTOR_HNSW_EF_CONSTRUCTION: int = 64

    # ========================================================
    # Semantic Retrieval
    # ========================================================

    # 默认返回最相关的 5 个 Chunk。
    RETRIEVAL_DEFAULT_TOP_K: int = 5

    # 单次最大返回数量，
    # 防止客户端一次请求大量 Chunk。
    RETRIEVAL_MAX_TOP_K: int = 20

    # 默认最低相似度。
    #
    # 0 表示默认不进行硬过滤，
    # Day44 RAG Evaluation 后再根据实验调整。
    RETRIEVAL_DEFAULT_MIN_SCORE: float = 0.0

    # Query 最大长度。
    RETRIEVAL_MAX_QUERY_LENGTH: int = 1000

    # ========================================================
    # Hybrid Retrieval
    # ========================================================

    # Semantic Branch
    # 第一阶段向量检索候选数。
    HYBRID_SEMANTIC_CANDIDATES: int = 20

    # Lexical Branch
    # 第一阶段关键词候选数。
    HYBRID_LEXICAL_CANDIDATES: int = 20

    # Fusion 后最多送多少候选给 Reranker。
    HYBRID_FUSION_CANDIDATES: int = 20

    # 最终默认返回数量。
    HYBRID_DEFAULT_TOP_K: int = 5

    # 最大最终返回数量。
    HYBRID_MAX_TOP_K: int = 20

    # RRF 常数。
    # 常用起点是 60。
    HYBRID_RRF_K: int = 60

    # PostgreSQL FTS 配置。
    #
    # simple 不进行英语词干化，
    # 对 ERA5、PWformer、RMSE 等
    # 科研专有词更加可控。
    HYBRID_FTS_CONFIG: str = "simple"

    # ========================================================
    # Reranker
    # ========================================================

    RERANKER_ENABLED: bool = True

    RERANKER_MODEL_NAME: str = (
        "cross-encoder/"
        "mmarco-mMiniLMv2-L12-H384-v1"
    )

    # auto:
    # CUDA 可用 → GPU
    # 否则 CPU。
    RERANKER_DEVICE: str = "auto"

    RERANKER_BATCH_SIZE: int = 16

    # 最终 Candidate 文本过长时，
    # CrossEncoder 会自行进行 tokenizer 截断。
    # 由于 Day26 已经将 Chunk 控制在较小范围，
    # 当前可以接受。

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