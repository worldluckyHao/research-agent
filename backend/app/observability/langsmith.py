import asyncio
import logging
from contextlib import (
    contextmanager,
)
from functools import (
    wraps,
)
from typing import (
    Any,
    Callable,
    Optional,
)

from langsmith import (
    Client,
    trace,
    tracing_context,
)

from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    LangSmithConfigurationException,
)


logger = logging.getLogger(
    __name__
)


# ============================================================
# Client State
# ============================================================

_langsmith_client: Optional[
    Client
] = None


# ============================================================
# Configuration
# ============================================================

def is_langsmith_enabled() -> bool:
    """
    是否启用 LangSmith。

    注意：

    LANGSMITH_ENABLED
    是我们应用自己的总开关。
    """

    return bool(
        settings.LANGSMITH_ENABLED
    )


def validate_langsmith_configuration() -> None:
    """
    Startup 时检查配置。

    Disabled:
        不要求 API Key。

    Enabled:
        必须存在 API Key。
    """

    if not is_langsmith_enabled():

        return


    if not (
        settings
        .LANGSMITH_API_KEY
        and settings
        .LANGSMITH_API_KEY
        .strip()
    ):

        raise (
            LangSmithConfigurationException()
        )


# ============================================================
# Client
# ============================================================

def get_langsmith_client() -> Optional[
    Client
]:
    """
    Lazy LangSmith Client。

    为什么 Lazy？

    因为：
        LANGSMITH_ENABLED=False

    时 Research-Agent 不应该为了
    Observability 初始化外部 Client。
    """

    global _langsmith_client


    if not is_langsmith_enabled():

        return None


    if _langsmith_client is not None:

        return _langsmith_client


    validate_langsmith_configuration()


    workspace_id = (
        settings
        .LANGSMITH_WORKSPACE_ID
        or None
    )


    _langsmith_client = (
        Client(
            api_url=(
                settings
                .LANGSMITH_ENDPOINT
            ),

            api_key=(
                settings
                .LANGSMITH_API_KEY
            ),

            workspace_id=(
                workspace_id
            ),

            # --------------------------------------------
            # Privacy by Default
            # --------------------------------------------

            hide_inputs=(
                not settings
                .LANGSMITH_CAPTURE_CONTENT
            ),

            hide_outputs=(
                not settings
                .LANGSMITH_CAPTURE_CONTENT
            ),

            omit_traced_runtime_info=(
                settings
                .LANGSMITH_OMIT_RUNTIME_INFO
            ),
        )
    )


    return _langsmith_client


# ============================================================
# Excluded Paths
# ============================================================

def get_excluded_paths() -> list[str]:
    """
    HTTP Trace 排除路径。
    """

    return [
        item.strip()

        for item
        in settings
        .LANGSMITH_EXCLUDED_PATHS
        .split(",")

        if item.strip()
    ]


def should_trace_http_path(
    path: str,
) -> bool:
    """
    是否需要记录该 HTTP Path。
    """

    if not is_langsmith_enabled():

        return False


    for excluded in (
        get_excluded_paths()
    ):

        if path.startswith(
            excluded
        ):

            return False


    return True


# ============================================================
# Safe Metadata
# ============================================================

def _safe_value_summary(
    value: Any,
) -> Any:
    """
    生成安全的 Metadata 摘要。

    不把复杂 Object / Prompt / DB Session
    直接写入 Trace Metadata。
    """

    if value is None:

        return None


    if isinstance(
        value,
        (
            bool,
            int,
            float,
        ),
    ):

        return value


    if isinstance(
        value,
        str,
    ):

        # 不记录真实正文，
        # 只保留长度。
        return {
            "type":
                "str",

            "chars":
                len(value),
        }


    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        return {
            "type":
                type(value).__name__,

            "size":
                len(value),
        }


    if isinstance(
        value,
        dict,
    ):

        return {
            "type":
                "dict",

            "size":
                len(value),

            "keys":
                list(value.keys())[
                    :20
                ],
        }


    # --------------------------------------------------------
    # ORM / Pydantic / Provider 等 Object
    # --------------------------------------------------------

    result = {
        "type":
            type(value).__name__
    }


    object_id = getattr(
        value,
        "id",
        None,
    )


    if isinstance(
        object_id,
        int,
    ):

        result[
            "id"
        ] = object_id


    return result


def _build_call_metadata(
    function_name: str,
    args: tuple,
    kwargs: dict,
) -> dict:
    """
    为 Decorator 创建安全 Metadata。

    不记录 Prompt 正文。
    """

    metadata = {
        "function":
            function_name,

        "environment":
            settings
            .LANGSMITH_ENVIRONMENT,

        "arg_count":
            len(args),

        "kwarg_keys":
            list(
                kwargs.keys()
            ),
    }


    # ========================================================
    # Useful Scalar Arguments
    # ========================================================

    useful_keys = {
        "project_id",
        "paper_id",
        "document_id",
        "user_id",
        "top_k",
        "use_reranker",
        "max_candidates",
        "max_ideas",
        "response_language",
    }


    for key in useful_keys:

        if key not in kwargs:

            continue


        metadata[
            key
        ] = _safe_value_summary(
            kwargs[key]
        )


    # ========================================================
    # Content Length
    # ========================================================

    for key in (
        "question",
        "query",
        "system_prompt",
        "user_prompt",
    ):

        value = kwargs.get(
            key
        )


        if isinstance(
            value,
            str,
        ):

            metadata[
                f"{key}_chars"
            ] = len(value)


    return metadata


# ============================================================
# Tracing Context
# ============================================================

@contextmanager
def langsmith_context(
    *,
    tags: Optional[
        list[str]
    ] = None,
    metadata: Optional[
        dict[str, Any]
    ] = None,
):
    """
    Request / Workflow Level
    Tracing Context。

    tracing_context 会把：
        project
        tags
        metadata
        client

    传递给内部 Trace。
    """

    if not is_langsmith_enabled():

        yield None

        return


    client = (
        get_langsmith_client()
    )


    if client is None:

        yield None

        return


    base_tags = [
        "research-agent",

        (
            "env:"
            f"{settings.LANGSMITH_ENVIRONMENT}"
        ),
    ]


    if tags:

        base_tags.extend(
            tags
        )


    base_metadata = {
        "environment":
            settings
            .LANGSMITH_ENVIRONMENT,
    }


    if metadata:

        base_metadata.update(
            metadata
        )


    with tracing_context(
        project_name=(
            settings
            .LANGSMITH_PROJECT
        ),

        tags=(
            base_tags
        ),

        metadata=(
            base_metadata
        ),

        enabled=True,

        client=(
            client
        ),
    ):

        yield client


# ============================================================
# Span
# ============================================================

@contextmanager
def langsmith_span(
    *,
    name: str,
    run_type: str = "chain",
    inputs: Optional[
        dict[str, Any]
    ] = None,
    tags: Optional[
        list[str]
    ] = None,
    metadata: Optional[
        dict[str, Any]
    ] = None,
):
    """
    创建一个显式 Span。

    run_type 常见：

        chain
        llm
        tool
        retriever
        embedding
        prompt
        parser
    """

    if not is_langsmith_enabled():

        yield None

        return


    client = (
        get_langsmith_client()
    )


    if client is None:

        yield None

        return


    with trace(
        name=(
            name
        ),

        run_type=(
            run_type
        ),

        inputs=(
            inputs
            or {}
        ),

        project_name=(
            settings
            .LANGSMITH_PROJECT
        ),

        tags=(
            tags
            or []
        ),

        metadata=(
            metadata
            or {}
        ),

        client=(
            client
        ),
    ) as run:

        yield run


# ============================================================
# Async Decorator
# ============================================================

def observed_async(
    *,
    name: str,
    run_type: str = "chain",
    tags: Optional[
        list[str]
    ] = None,
) -> Callable:
    """
    给现有 Async Function
    增加 LangSmith Span。

    优点：

    不需要重写已有业务逻辑。

    Example:

        @observed_async(
            name="retrieval.hybrid",
            run_type="retriever",
        )
        async def hybrid_search_document(...):
            ...
    """

    def decorator(
        func: Callable,
    ) -> Callable:

        @wraps(
            func
        )
        async def wrapper(
            *args,
            **kwargs,
        ):

            # --------------------------------------------
            # Disabled:
            # 零业务影响。
            # --------------------------------------------

            if not is_langsmith_enabled():

                return await func(
                    *args,
                    **kwargs,
                )


            metadata = (
                _build_call_metadata(
                    function_name=(
                        func.__qualname__
                    ),

                    args=(
                        args
                    ),

                    kwargs=(
                        kwargs
                    ),
                )
            )


            with langsmith_span(
                name=(
                    name
                ),

                run_type=(
                    run_type
                ),

                tags=(
                    tags
                ),

                metadata=(
                    metadata
                ),
            ) as run:

                result = await func(
                    *args,
                    **kwargs,
                )


                if run is not None:

                    run.outputs = {
                        "result":
                            _safe_value_summary(
                                result
                            )
                    }


                return result


        return wrapper


    return decorator


# ============================================================
# Shutdown
# ============================================================

async def shutdown_langsmith() -> None:
    """
    FastAPI Shutdown 时：

        flush pending traces
        stop background tracing threads

    避免开发服务器退出时
    最后几条 Trace 丢失。
    """

    global _langsmith_client


    client = (
        _langsmith_client
    )


    if client is None:

        return


    try:

        await asyncio.to_thread(
            client.cleanup,
            5.0,
        )


    except Exception:

        # Observability 不应该导致
        # Application Shutdown 失败。
        logger.exception(
            "Failed to clean up LangSmith client"
        )


    finally:

        _langsmith_client = None