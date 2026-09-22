import asyncio

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    DocumentEmbeddingNotAvailableException,
    EmbeddingConfigurationException,
    EmbeddingInputTooLongException,
)
from backend.app.embeddings.base import (
    EmbeddingDimensionMismatchError,
    EmbeddingInputTooLongError,
    EmbeddingProvider,
)
from backend.app.models.paper_document import (
    PaperDocument,
)
from backend.app.retrieval.lexical import (
    lexical_search_document,
)
from backend.app.retrieval.reranker import (
    create_reranker,
)
from backend.app.retrieval.rrf import (
    reciprocal_rank_fusion,
)
from backend.app.schemas.hybrid_search import (
    HybridSearchResponse,
    HybridSearchResultItem,
)
from backend.app.services.semantic_retrieval import (
    retrieve_semantic_candidates,
)
from backend.app.observability.langsmith import (
    observed_async,
)
@observed_async(
    name="retrieval.hybrid_search",
    run_type="retriever",
    tags=[
        "retrieval",
        "hybrid",
    ],
)
async def hybrid_search_document(
    db: AsyncSession,
    document: PaperDocument,
    query: str,
    top_k: int,
    use_reranker: bool,
    embedding_provider: EmbeddingProvider,
) -> HybridSearchResponse:
    """
    Hybrid Retrieval Pipeline。

    1. Query Embedding
    2. Semantic Retrieval
    3. Lexical Retrieval
    4. RRF Fusion
    5. Optional Cross-Encoder Reranking
    6. Final Top-K
    """

    # ========================================================
    # 1. Validate Document State
    # ========================================================

    if (
        document.embedding_status
        != "embedded"
        or document.embedding_count <= 0
    ):

        raise (
            DocumentEmbeddingNotAvailableException()
        )


    normalized_query = (
        query.strip()
    )


    if not normalized_query:

        raise ValueError(
            "Search query cannot be empty"
        )


    # ========================================================
    # 2. Query Embedding
    # ========================================================

    try:

        query_batch = (
            await asyncio.to_thread(
                embedding_provider
                .embed_query,

                normalized_query,
            )
        )


    except EmbeddingInputTooLongError as exc:

        raise (
            EmbeddingInputTooLongException(
                actual_tokens=(
                    exc.actual_tokens
                ),

                max_tokens=(
                    exc.max_tokens
                ),
            )
        ) from exc


    except EmbeddingDimensionMismatchError as exc:

        raise (
            EmbeddingConfigurationException()
        ) from exc


    if (
        len(
            query_batch.vectors
        )
        != 1
    ):

        raise RuntimeError(
            "Expected one query vector"
        )


    # ========================================================
    # 3. Model Compatibility
    # ========================================================

    if (
        document.embedding_provider
        != query_batch.provider

        or document.embedding_model
        != query_batch.model_name

        or document.embedding_dimension
        != query_batch.dimension
    ):

        raise (
            EmbeddingConfigurationException()
        )


    query_vector = (
        query_batch.vectors[0]
    )


    # ========================================================
    # 4. Parallel Retrieval
    # ========================================================

    semantic_task = (
        retrieve_semantic_candidates(
            db=db,

            document=document,

            query_vector=(
                query_vector
            ),

            provider_name=(
                query_batch.provider
            ),

            model_name=(
                query_batch.model_name
            ),

            dimension=(
                query_batch.dimension
            ),

            limit=(
                settings
                .HYBRID_SEMANTIC_CANDIDATES
            ),
        )
    )


    lexical_task = (
        lexical_search_document(
            db=db,

            document_id=(
                document.id
            ),

            query=(
                normalized_query
            ),

            limit=(
                settings
                .HYBRID_LEXICAL_CANDIDATES
            ),

            fts_config=(
                settings
                .HYBRID_FTS_CONFIG
            ),
        )
    )


    # 注意：
    # 同一个 AsyncSession 不应该并发执行
    # 多个数据库操作。
    #
    # 所以这里不要 asyncio.gather()
    # 同时跑两个 DB Query。
    semantic_candidates = (
        await semantic_task
    )


    lexical_candidates = (
        await lexical_task
    )


    # ========================================================
    # 5. RRF Fusion
    # ========================================================

    fused = (
        reciprocal_rank_fusion(
            semantic_candidates=(
                semantic_candidates
            ),

            lexical_candidates=(
                lexical_candidates
            ),

            rrf_k=(
                settings
                .HYBRID_RRF_K
            ),

            limit=(
                settings
                .HYBRID_FUSION_CANDIDATES
            ),
        )
    )


    # ========================================================
    # 6. Optional Reranking
    # ========================================================

    reranker_used = (
        use_reranker
        and settings.RERANKER_ENABLED
        and bool(fused)
    )


    if reranker_used:

        reranker = (
            create_reranker()
        )


        final_candidates = (
            await asyncio.to_thread(
                reranker.rerank,

                normalized_query,

                fused,
            )
        )


    else:

        final_candidates = (
            fused
        )


    # ========================================================
    # 7. Final Top-K
    # ========================================================

    final_candidates = (
        final_candidates[
            :top_k
        ]
    )


    # ========================================================
    # 8. Response
    # ========================================================

    items = [
        HybridSearchResultItem(
            chunk_id=(
                candidate.chunk_id
            ),

            chunk_index=(
                candidate.chunk_index
            ),

            content=(
                candidate.content
            ),

            start_page=(
                candidate.start_page
            ),

            end_page=(
                candidate.end_page
            ),

            token_count=(
                candidate.token_count
            ),

            semantic_rank=(
                candidate.semantic_rank
            ),

            semantic_score=(
                candidate.semantic_score
            ),

            lexical_rank=(
                candidate.lexical_rank
            ),

            lexical_score=(
                candidate.lexical_score
            ),

            rrf_score=round(
                candidate.rrf_score,
                8,
            ),

            rerank_score=(
                round(
                    candidate.rerank_score,
                    6,
                )
                if candidate.rerank_score
                is not None
                else None
            ),
        )

        for candidate
        in final_candidates
    ]


    return HybridSearchResponse(
        document_id=(
            document.id
        ),

        query=(
            normalized_query
        ),

        top_k=(
            top_k
        ),

        reranker_used=(
            reranker_used
        ),

        semantic_candidate_count=len(
            semantic_candidates
        ),

        lexical_candidate_count=len(
            lexical_candidates
        ),

        fused_candidate_count=len(
            fused
        ),

        returned_count=len(
            items
        ),

        items=items,
    )