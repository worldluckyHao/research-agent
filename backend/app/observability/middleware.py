from backend.app.core.config import (
    settings,
)
from backend.app.observability.langsmith import (
    get_langsmith_client,
    langsmith_context,
    langsmith_span,
    should_trace_http_path,
)


class LangSmithTracingMiddleware:
    """
    Raw ASGI Middleware。

    为什么不用 BaseHTTPMiddleware？

    因为 Trace Parent / Child
    依赖 ContextVar 传播。

    Raw ASGI Middleware
    对这种 Observability Context
    更直接、更可控。
    """

    def __init__(
        self,
        app,
    ):
        self.app = app


    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        """
        为每个 HTTP Request
        创建 Root Trace。
        """

        # ====================================================
        # Non-HTTP
        # ====================================================

        if (
            scope["type"]
            != "http"
        ):

            await self.app(
                scope,
                receive,
                send,
            )

            return


        method = (
            scope.get(
                "method",
                "UNKNOWN",
            )
        )


        path = (
            scope.get(
                "path",
                "/",
            )
        )


        # ====================================================
        # Disabled / Excluded
        # ====================================================

        if not should_trace_http_path(
            path
        ):

            await self.app(
                scope,
                receive,
                send,
            )

            return


        # ====================================================
        # Client
        # ====================================================

        client = (
            get_langsmith_client()
        )


        if client is None:

            await self.app(
                scope,
                receive,
                send,
            )

            return


        status_code = 500


        # ====================================================
        # Capture Response Status
        # ====================================================

        async def send_wrapper(
            message,
        ):
            nonlocal status_code


            if (
                message["type"]
                == "http.response.start"
            ):

                status_code = (
                    message[
                        "status"
                    ]
                )


            await send(
                message
            )


        # ====================================================
        # Request Context
        # ====================================================

        metadata = {
            "http_method":
                method,

            "http_path":
                path,

            "environment":
                settings
                .LANGSMITH_ENVIRONMENT,
        }


        with langsmith_context(
            tags=[
                "http",
            ],

            metadata=(
                metadata
            ),
        ):

            # =================================================
            # Root Trace
            # =================================================

            with langsmith_span(
                name=(
                    f"{method} {path}"
                ),

                run_type=(
                    "chain"
                ),

                inputs={
                    "method":
                        method,

                    "path":
                        path,
                },

                tags=[
                    "http-request",
                ],

                metadata=(
                    metadata
                ),
            ) as run:

                # 如果 Application 抛异常，
                # trace context 会保留异常信息。
                await self.app(
                    scope,
                    receive,
                    send_wrapper,
                )


                if run is not None:

                    run.outputs = {
                        "status_code":
                            status_code
                    }