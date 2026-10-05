import httpx
import pytest
from fastapi.testclient import (
    TestClient,
)

from backend.app.dependencies import (
    get_http_client,
)
from backend.app.main import (
    app,
)


pytestmark = pytest.mark.integration


# ============================================================
# Crossref Mock
# ============================================================

def test_crossref_work_with_mock_http():
    """
    FastAPI
      ↓
    Crossref Endpoint
      ↓
    get_http_client
      ↓
    Mock AsyncClient
      ↓
    Fake Crossref Response

    不访问 Internet。
    """

    doi = (
        "10.1234/"
        "research-agent-test"
    )


    # --------------------------------------------------------
    # Mock HTTP Handler
    # --------------------------------------------------------

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:

        # 确认代码确实准备访问 Crossref。
        assert (
            request.url.host
            ==
            "api.crossref.org"
        )


        return httpx.Response(
            status_code=200,

            json={
                "status": "ok",

                "message-type": "work",

                "message-version": "1.0.0",

                "message": {
                    "DOI": doi,

                    "title": [
                        (
                            "A Test Paper "
                            "for Research Agent"
                        )
                    ],

                    "author": [
                        {
                            "given": "Test",
                            "family": "Author",
                        }
                    ],

                    "published": {
                        "date-parts": [
                            [
                                2026
                            ]
                        ]
                    },

                    "publisher": (
                        "Test Publisher"
                    ),

                    "container-title": [
                        "Test Journal"
                    ],

                    "URL": (
                        "https://example.com/"
                        "test-paper"
                    ),

                    "type": (
                        "journal-article"
                    ),
                },
            },
        )


    transport = (
        httpx.MockTransport(
            handler
        )
    )


    mock_http_client = (
        httpx.AsyncClient(
            transport=transport
        )
    )


    # --------------------------------------------------------
    # Override Shared HTTP Client
    # --------------------------------------------------------

    async def override_http_client():
        return mock_http_client


    app.dependency_overrides[
        get_http_client
    ] = override_http_client


    client = TestClient(
        app
    )


    try:

        response = client.get(
            (
                "/api/v1/external/"
                "crossref/works/"
                f"{doi}"
            )
        )


        assert (
            response.status_code
            ==
            200
        )


        data = response.json()


        assert (
            data["doi"]
            ==
            doi
        )


        assert (
            data["title"]
            ==
            (
                "A Test Paper "
                "for Research Agent"
            )
        )


        assert (
            data["authors"]
            ==
            [
                "Test Author"
            ]
        )


        assert (
            data["year"]
            ==
            2026
        )


        assert (
            data["publisher"]
            ==
            "Test Publisher"
        )


        assert (
            data["source"]
            ==
            "crossref"
        )


    finally:

        client.close()

        app.dependency_overrides.pop(
            get_http_client,
            None,
        )


        # AsyncClient.close() 是 async，
        # 这里由独立事件循环完成清理。
        import asyncio

        asyncio.run(
            mock_http_client.aclose()
        )