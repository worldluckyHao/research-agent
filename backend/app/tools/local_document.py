from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.models.paper_document import (
    PaperDocument,
)
from backend.app.retrieval.base import (
    RetrievalCandidate,
)
from backend.app.services.hybrid_retrieval import (
    hybrid_search_document,
)
from backend.app.tools.base import (
    ResearchTool,
    ToolResult,
)


class LocalDocumentSearchTool(
    ResearchTool
):
    """
    Local Document Search Tool
    （当前论文检索工具）。

    内部继续复用 Day29：

        Semantic Retrieval
        +
        PostgreSQL FTS
        +
        RRF
        +
        CrossEncoder

    Tool 层不重新实现 Retrieval。
    """

    name = (
        "local_document_search"
    )


    description = (
        "Search the currently selected research paper "
        "for passages relevant to a question. "
        "Use this tool when the answer should come from "
        "the current paper."
    )


    def __init__(
        self,
        db: AsyncSession,
        document: PaperDocument,
        embedding_provider: EmbeddingProvider,
        use_reranker: bool,
    ):
        self.db = db

        self.document = document

        self.embedding_provider = (
            embedding_provider
        )

        self.use_reranker = (
            use_reranker
        )


    async def execute(
        self,
        query: str,
        top_k: int,
    ) -> ToolResult:
        """
        执行当前 Paper 的 Hybrid Retrieval。
        """

        normalized_query = (
            query.strip()
        )


        if not normalized_query:

            return ToolResult(
                tool_name=(
                    self.name
                ),

                success=False,

                message=(
                    "Search query is empty."
                ),

                candidates=[],

                metadata={
                    "returned_count": 0,
                },
            )


        retrieval = (
            await hybrid_search_document(
                db=(
                    self.db
                ),

                document=(
                    self.document
                ),

                query=(
                    normalized_query
                ),

                top_k=(
                    top_k
                ),

                use_reranker=(
                    self.use_reranker
                ),

                embedding_provider=(
                    self.embedding_provider
                ),
            )
        )


        candidates = [
            RetrievalCandidate(
                chunk_id=(
                    item.chunk_id
                ),

                chunk_index=(
                    item.chunk_index
                ),

                content=(
                    item.content
                ),

                start_page=(
                    item.start_page
                ),

                end_page=(
                    item.end_page
                ),

                token_count=(
                    item.token_count
                ),

                semantic_rank=(
                    item.semantic_rank
                ),

                semantic_score=(
                    item.semantic_score
                ),

                lexical_rank=(
                    item.lexical_rank
                ),

                lexical_score=(
                    item.lexical_score
                ),

                rrf_score=(
                    item.rrf_score
                ),

                rerank_score=(
                    item.rerank_score
                ),
            )

            for item
            in retrieval.items
        ]


        return ToolResult(
            tool_name=(
                self.name
            ),

            success=True,

            message=(
                f"Retrieved "
                f"{len(candidates)} "
                f"candidate passages."
            ),

            candidates=(
                candidates
            ),

            metadata={
                "query":
                    normalized_query,

                "returned_count":
                    len(candidates),

                # 保留原始 Hybrid Search Response，
                # 供 Evidence Evaluator 使用。
                "retrieval_response":
                    retrieval,
            },
        )