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

    # ========================================================
    # LLM / RAG
    # ========================================================

    # Day30 默认使用本地 Hugging Face Model。
    LLM_PROVIDER: Literal[
        "huggingface",
        "bailian",
    ] = "bailian"

    # Day30 使用较小模型，
    # 便于本地开发验证完整 RAG Pipeline。
    LLM_MODEL_NAME: str = (
         "qwen3.8-flash"
    )

    # auto:
    # CUDA 可用 → GPU
    # 否则 CPU。
    LLM_DEVICE: str = "auto"

    # 单次回答最大生成 Token。
    LLM_MAX_NEW_TOKENS: int = 512

    # RAG 更强调稳定和事实依据，
    # 因此默认低 Temperature。
    LLM_TEMPERATURE: float = 0.1

    # 是否启用 Sampling。
    #
    # Day30 默认关闭，
    # 让答案更加稳定、可复现。
    LLM_DO_SAMPLE: bool = False

    # RAG Context 最多使用多少个 Chunk。
    RAG_DEFAULT_TOP_K: int = 5

    RAG_MAX_TOP_K: int = 10

    # Context 最大字符预算。
    #
    # Day30 先用 Character Budget，
    # Day32 Prompt Management 再进一步完善。
    RAG_MAX_CONTEXT_CHARS: int = 12000

    # 如果没有任何 Retrieval Result，
    # 不调用 LLM。
    RAG_REQUIRE_EVIDENCE: bool = True

    # ========================================================
    # LLM / RAG
    # ========================================================

    LLM_PROVIDER: Literal[
        "huggingface",
        "bailian",
    ] = "bailian"

    LLM_MODEL_NAME: str = (
        "qwen3.8-flash"
    )

    # auto:
    # CUDA 可用时使用 GPU，否则 CPU。
    LLM_DEVICE: str = "auto"

    # 最大生成长度。
    LLM_MAX_NEW_TOKENS: int = 512

    # RAG 需要稳定、保守回答。
    LLM_TEMPERATURE: float = 0.1

    # Day30 默认关闭随机采样。
    LLM_DO_SAMPLE: bool = False

    # 默认检索证据数量。
    RAG_DEFAULT_TOP_K: int = 5

    RAG_MAX_TOP_K: int = 10

    # 最多送给 LLM 的 Evidence 字符数。
    RAG_MAX_CONTEXT_CHARS: int = 12000

    # 没有 Evidence 时直接拒答。
    RAG_REQUIRE_EVIDENCE: bool = True

    # ========================================================
    # Alibaba Cloud Bailian
    # ========================================================

    # 百炼 API Key。
    #
    # 使用 SecretStr，
    # 避免 Settings repr 时直接泄露。
    BAILIAN_API_KEY: Optional[
        SecretStr
    ] = None

    # OpenAI-Compatible Base URL。
    BAILIAN_BASE_URL: str = (
        "https://dashscope.aliyuncs.com/"
        "compatible-mode/v1"
    )

    # 单次 API 调用超时。
    BAILIAN_TIMEOUT_SECONDS: float = 120.0

    # OpenAI SDK 自动重试次数。
    BAILIAN_MAX_RETRIES: int = 2

    # ========================================================
    # Prompt Management
    # ========================================================

    # 当前 RAG System Prompt 版本。
    RAG_SYSTEM_PROMPT_VERSION: int = 1

    # 当前 RAG User Prompt 版本。
    RAG_USER_PROMPT_VERSION: int = 1


    # ========================================================
    # LangChain
    # ========================================================

    # RAG Generation Engine（RAG生成引擎）。
    #
    # native：
    #     使用 Day30 原生实现，
    #     直接调用 LLMProvider.generate()。
    #
    # langchain：
    #     使用 Day33 LCEL Pipeline。
    #
    # 保留 native 方便：
    #     1. 回滚
    #     2. 对比
    #     3. Debug
    RAG_GENERATION_ENGINE: Literal[
        "native",
        "langchain",
    ] = "langchain"

    # ========================================================
    # RAG Workflow Engine
    # ========================================================

    # service:
    #     Day30-Day33 Classic RAG。
    #
    # langgraph:
    #     Day34 基础 LangGraph RAG。
    #
    # agent:
    #     Day35 Agentic RAG。
    #
    # tool_agent:
    #     Day36 Tool Calling Agent。
    #
    # multi_agent:
    #     Day37 Researcher + Critic + Synthesizer。
    RAG_WORKFLOW_ENGINE: Literal[
        "service",
        "langgraph",
        "agent",
        "tool_agent",
        "multi_agent",
    ] = "multi_agent"

    # ========================================================
    # Tool Calling
    # ========================================================

    # 一次 Tool Agent Run
    # 最多允许执行多少次 Tool。
    #
    # 防止：
    # select -> execute -> rewrite
    # 无限循环。
    RESEARCH_AGENT_MAX_TOOL_CALLS: int = 3


    # Tool Selector 默认版本。
    TOOL_SELECTION_PROMPT_VERSION: int = 1


    # ========================================================
    # Research Agent
    # ========================================================

    # 一次问题最多进行多少次 Retrieval。
    #
    # 2 表示：
    #
    # 第一次：
    #     initial retrieval
    #
    # 第二次：
    #     rewritten query retrieval
    #
    # 避免 Agent 无限循环。
    RESEARCH_AGENT_MAX_RETRIEVAL_ATTEMPTS: int = 2


    # Agent 内部 Retrieval 可以比用户最终
    # top_k 多取一些候选，
    # 给 Evidence Evaluator 更多信息。
    RESEARCH_AGENT_RETRIEVAL_TOP_K: int = 8


    # Evidence Evaluation 最多把多少个 Chunk
    # 发送给 Evaluator。
    #
    # 防止评估 Prompt 过长。
    RESEARCH_AGENT_EVALUATION_MAX_CHUNKS: int = 5

    # ========================================================
    # Multi-Agent
    # ========================================================

    # Researcher -> Critic
    # 最多允许循环多少轮。
    #
    # Example:
    #
    # cycle 1:
    #     researcher
    #     critic rejects
    #
    # cycle 2:
    #     researcher
    #     critic accepts / stop
    MULTI_AGENT_MAX_RESEARCH_CYCLES: int = 2


    # Critic 每次最多评估多少个 Evidence Chunk。
    #
    # 防止 Critic Prompt 过长。
    MULTI_AGENT_CRITIC_MAX_CHUNKS: int = 5

    # ========================================================
    # Paper Comparison
    # ========================================================

    # 一次最多比较多少篇论文。
    #
    # 多论文比较会为每篇论文运行一次 RAG，
    # 数量太大会显著增加：
    #
    # Retrieval
    # LLM Calls
    # Latency
    # GPU Memory Pressure
    PAPER_COMPARISON_MAX_PAPERS: int = 5


    # 每篇 Paper Evidence Extraction
    # 使用多少个最终 Evidence Chunk。
    PAPER_COMPARISON_PER_PAPER_TOP_K: int = 5


    # Comparison Synthesizer Prompt Version。
    PAPER_COMPARISON_PROMPT_VERSION: int = 1

    # ========================================================
    # Research Gap Discovery
    # ========================================================

    # 最多生成多少个 Gap Candidate。
    #
    # 防止 LLM 一次产生大量低质量 Gap，
    # 同时避免 Verifier 调用次数过多。
    RESEARCH_GAP_MAX_CANDIDATES: int = 5


    # Gap Generator Prompt Version。
    RESEARCH_GAP_GENERATION_PROMPT_VERSION: int = 1


    # Gap Verifier Prompt Version。
    RESEARCH_GAP_VERIFICATION_PROMPT_VERSION: int = 1


    # 至少需要多少篇不同论文提供 Evidence，
    # 才能认为存在较强的 Cross-Paper Support。
    #
    # 注意：
    # 低于该值不一定 Reject，
    # 但 Evidence Strength 会被限制。
    RESEARCH_GAP_STRONG_SUPPORT_MIN_PAPERS: int = 3

    # ========================================================
    # Research Idea Generation
    # ========================================================

    # 一次最多生成多少个 Candidate Idea。
    RESEARCH_IDEA_MAX_CANDIDATES: int = 3


    # Idea Generator Prompt Version。
    RESEARCH_IDEA_GENERATION_PROMPT_VERSION: int = 1


    # Feasibility Critic Prompt Version。
    RESEARCH_IDEA_FEASIBILITY_PROMPT_VERSION: int = 1


    # Novelty Risk Critic Prompt Version。
    RESEARCH_IDEA_NOVELTY_PROMPT_VERSION: int = 1


    # Implementation Planner Prompt Version。
    RESEARCH_IDEA_PLANNING_PROMPT_VERSION: int = 1

    # ========================================================
    # Experiment Design
    # ========================================================

    # Experiment Designer Prompt Version。
    EXPERIMENT_DESIGN_PROMPT_VERSION: int = 1


    # Experiment Design Critic Prompt Version。
    EXPERIMENT_REVIEW_PROMPT_VERSION: int = 1


    # 默认建议的独立训练重复次数。
    #
    # 注意：
    # 最终 Agent 可以根据实验成本调整，
    # 但这作为设计起点。
    EXPERIMENT_DEFAULT_REPEATED_RUNS: int = 5


    # 默认统计显著性水平。
    EXPERIMENT_DEFAULT_ALPHA: float = 0.05

    # ========================================================
    # Code Assistant
    # ========================================================

    # Code Planning Prompt Version。
    CODE_ASSISTANT_PLANNING_PROMPT_VERSION: int = 1


    # Patch Proposal Prompt Version。
    CODE_ASSISTANT_PATCH_PROMPT_VERSION: int = 1


    # Code Safety Review Prompt Version。
    CODE_ASSISTANT_REVIEW_PROMPT_VERSION: int = 1


    # Validation Planning Prompt Version。
    CODE_ASSISTANT_VALIDATION_PROMPT_VERSION: int = 1


    # 一次最多允许生成多少个文件变更提案。
    CODE_ASSISTANT_MAX_FILE_CHANGES: int = 8


    # Day42 禁止建议修改的敏感路径关键词。
    #
    # 这里只用于 Proposal Validation，
    # 不是真正 OS Sandbox。
    CODE_ASSISTANT_BLOCKED_PATH_KEYWORDS: str = (
        ".env,"
        "secrets,"
        "credentials,"
        "private_key,"
        "security/"
    )


    # ========================================================
    # LangSmith Observability
    # ========================================================

    # 是否启用 LangSmith Trace。
    #
    # 开发时可以随时关闭，
    # 不影响 Research-Agent 核心业务。
    LANGSMITH_ENABLED: bool = False


    # LangSmith API Key。
    #
    # 只写 backend/.env，
    # 永远不要提交 Git。
    LANGSMITH_API_KEY: Optional[str] = None


    # 官方默认 API Endpoint。
    LANGSMITH_ENDPOINT: str = (
        "https://api.smith.langchain.com"
    )


    # LangSmith Trace Project。
    #
    # 所有 Research-Agent Trace
    # 默认归到这个 Project。
    LANGSMITH_PROJECT: str = (
        "research-agent-dev"
    )


    # 某些组织级 API Key
    # 可能需要 Workspace ID。
    LANGSMITH_WORKSPACE_ID: Optional[str] = None


    # environment tag:
    #
    # development
    # staging
    # production
    LANGSMITH_ENVIRONMENT: str = "development"


    # 是否把 Prompt / Answer 正文
    # 上传到 LangSmith。
    #
    # 默认 False：
    # 只观察结构、Metadata、Latency。
    #
    # 需要深入 Prompt Debug 时
    # 再主动开启。
    LANGSMITH_CAPTURE_CONTENT: bool = False


    # 是否隐藏 Python / OS 等
    # Runtime Information。
    LANGSMITH_OMIT_RUNTIME_INFO: bool = True


    # 不需要 Trace 的 HTTP Path。
    LANGSMITH_EXCLUDED_PATHS: str = (
        "/health,"
        "/docs,"
        "/redoc,"
        "/openapi.json"
    )


    # ========================================================
    # RAG Evaluation
    # ========================================================

    # 是否使用 LLM-as-a-Judge。
    RAG_EVALUATION_LLM_JUDGE_ENABLED: bool = True


    # Judge Prompt Version。
    RAG_EVALUATION_PROMPT_VERSION: int = 1


    # 避免把过大的 Evidence
    # 一次性发送给 Judge。
    RAG_EVALUATION_MAX_EVIDENCE_CHARS: int = (
        12000
    )


    # Groundedness Quality Gate。
    RAG_EVALUATION_MIN_GROUNDEDNESS: float = (
        0.70
    )


    # Relevance Quality Gate。
    RAG_EVALUATION_MIN_RELEVANCE: float = (
        0.70
    )


    # 当存在 Gold Label 时，
    # Retrieval Recall 最低要求。
    RAG_EVALUATION_MIN_RECALL_AT_K: float = (
        0.80
    )


    # ========================================================
    # Agent Evaluation
    # ========================================================

    # 是否启用 Agent LLM-as-a-Judge。
    AGENT_EVALUATION_LLM_JUDGE_ENABLED: bool = True


    # Agent Evaluation Prompt Version。
    AGENT_EVALUATION_PROMPT_VERSION: int = 1


    # 防止过长 Trace 全部发送给 Judge。
    AGENT_EVALUATION_MAX_TRACE_CHARS: int = 16000


    # Tool Selection F1 最低要求。
    AGENT_EVALUATION_MIN_TOOL_F1: float = 0.70


    # Tool Execution Success Rate 最低要求。
    AGENT_EVALUATION_MIN_TOOL_SUCCESS_RATE: float = 0.80


    # Agent Goal Completion 最低要求。
    AGENT_EVALUATION_MIN_GOAL_COMPLETION: float = 0.75


    # Final Answer Quality 最低要求。
    AGENT_EVALUATION_MIN_FINAL_ANSWER_QUALITY: float = 0.70


    # Observable Trajectory Coherence 最低要求。
    AGENT_EVALUATION_MIN_TRAJECTORY_COHERENCE: float = 0.70


    # 提供 Evidence 时，
    # Groundedness 最低要求。
    AGENT_EVALUATION_MIN_GROUNDEDNESS: float = 0.70

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