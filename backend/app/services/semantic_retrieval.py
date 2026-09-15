import asyncio
import logging

from sqlalchemy import (
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)
from backend.app.retrieval.base import (
    RetrievalCandidate,
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
from backend.app.models.paper_document_chunk import (
    PaperDocumentChunk,
)
from backend.app.models.paper_document_chunk_embedding import (
    PaperDocumentChunkEmbedding,
)
from backend.app.schemas.semantic_search import (
    SemanticSearchModelInfo,
    SemanticSearchResponse,
    SemanticSearchResultItem,
)


logger = logging.getLogger(__name__)

async def retrieve_semantic_candidates(
    db: AsyncSession,
    document: PaperDocument,
    query_vector: list[float],
    provider_name: str,
    model_name: str,
    dimension: int,
    limit: int,
) -> list[RetrievalCandidate]:
    """
    Low-level Semantic Retriever
    （底层语义召回器）。

    Day28 API 和 Day29 Hybrid Retrieval
    都可以复用。
    """

    cosine_distance = (
        PaperDocumentChunkEmbedding
        .embedding
        .cosine_distance(
            query_vector
        )
        .label(
            "cosine_distance"
        )
    )


    statement = (
        select(
            PaperDocumentChunk,
            cosine_distance,
        )

        .join(
            PaperDocumentChunkEmbedding,

            PaperDocumentChunkEmbedding
            .chunk_id
            == PaperDocumentChunk.id,
        )

        .where(
            PaperDocumentChunk.document_id
            == document.id,

            PaperDocumentChunkEmbedding.provider
            == provider_name,

            PaperDocumentChunkEmbedding.model_name
            == model_name,

            PaperDocumentChunkEmbedding.dimension
            == dimension,

            PaperDocumentChunkEmbedding
            .content_sha256
            == PaperDocumentChunk
            .content_sha256,
        )

        .order_by(
            cosine_distance.asc()
        )

        .limit(
            limit
        )
    )


    result = await db.execute(
        statement
    )


    rows = list(
        result.all()
    )


    candidates = []


    for rank, (
        chunk,
        distance,
    ) in enumerate(
        rows,
        start=1,
    ):

        distance_value = float(
            distance
        )


        similarity = (
            1.0
            - distance_value
        )


        similarity = max(
            -1.0,
            min(
                1.0,
                similarity,
            ),
        )


        candidates.append(
            RetrievalCandidate(
                chunk_id=chunk.id,

                chunk_index=(
                    chunk.chunk_index
                ),

                content=chunk.content,

                start_page=(
                    chunk.start_page
                ),

                end_page=(
                    chunk.end_page
                ),

                token_count=(
                    chunk.token_count
                ),

                semantic_rank=rank,

                semantic_score=(
                    round(
                        similarity,
                        6,
                    )
                ),
            )
        )


    return candidates

async def semantic_search_document(
    db: AsyncSession,
    document: PaperDocument,
    query: str,
    top_k: int,
    min_score: float,
    provider: EmbeddingProvider,
) -> SemanticSearchResponse:
    """
    在指定 PaperDocument 内执行
    Semantic Retrieval（语义检索）。

    Flow:

        Query Text
            ↓
        Query Embedding
            ↓
        pgvector Cosine Distance
            ↓
        Metadata Filtering
            ↓
        Top-K Chunks
            ↓
        Search Results
    """

    # ========================================================
    # 1. Validate Pipeline State
    # ========================================================

    if (
        document.embedding_status
        != "embedded"
    ):

        raise (
            DocumentEmbeddingNotAvailableException()
        )


    if document.embedding_count <= 0:

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
    # 2. Generate Query Embedding
    # ========================================================

    try:

        query_batch = (
            await asyncio.to_thread(
                provider.embed_query,
                normalized_query,
            )
        )


    except EmbeddingInputTooLongError as exc:

        raise EmbeddingInputTooLongException(
            actual_tokens=(
                exc.actual_tokens
            ),
            max_tokens=(
                exc.max_tokens
            ),
        ) from exc


    except EmbeddingDimensionMismatchError as exc:

        raise (
            EmbeddingConfigurationException()
        ) from exc


    if len(
        query_batch.vectors
    ) != 1:

        raise RuntimeError(
            (
                "Query embedding must "
                "contain exactly one vector"
            )
        )


    query_vector = (
        query_batch.vectors[0]
    )


    # ========================================================
    # 3. Verify Model Compatibility
    # ========================================================

    # Document Embedding 与当前 Query Model
    # 必须属于同一个 Vector Space。
    if (
        document.embedding_provider
        != query_batch.provider
        or
        document.embedding_model
        != query_batch.model_name
        or
        document.embedding_dimension
        != query_batch.dimension
    ):

        logger.error(
            (
                "Embedding model mismatch: "
                "document_id=%s "
                "stored=%s/%s/%s "
                "query=%s/%s/%s"
            ),
            document.id,
            document.embedding_provider,
            document.embedding_model,
            document.embedding_dimension,
            query_batch.provider,
            query_batch.model_name,
            query_batch.dimension,
        )

        raise (
            EmbeddingConfigurationException()
        )


    # ========================================================
    # 4. Build Cosine Distance Expression
    # ========================================================

    cosine_distance = (
        PaperDocumentChunkEmbedding
        .embedding
        .cosine_distance(
            query_vector
        )
        .label(
            "cosine_distance"
        )
    )


    # ========================================================
    # 5. Vector Search
    # ========================================================

    statement = (
        select(
            PaperDocumentChunk,
            PaperDocumentChunkEmbedding,
            cosine_distance,
        )

        .join(
            PaperDocumentChunkEmbedding,

            PaperDocumentChunkEmbedding
            .chunk_id
            == PaperDocumentChunk.id,
        )

        .where(
            # -----------------------------------------------
            # Scope:
            # 只搜索当前 Document。
            # -----------------------------------------------
            PaperDocumentChunk.document_id
            == document.id,


            # -----------------------------------------------
            # Model Filter:
            # 只比较同一个 Vector Space。
            # -----------------------------------------------
            PaperDocumentChunkEmbedding.provider
            == query_batch.provider,

            PaperDocumentChunkEmbedding.model_name
            == query_batch.model_name,

            PaperDocumentChunkEmbedding.dimension
            == query_batch.dimension,


            # -----------------------------------------------
            # Stale Vector Protection:
            #
            # Embedding 必须对应当前 Chunk 内容。
            # -----------------------------------------------
            PaperDocumentChunkEmbedding
            .content_sha256
            == PaperDocumentChunk
            .content_sha256,
        )

        # Distance 越小越相关。
        .order_by(
            cosine_distance.asc()
        )

        .limit(
            top_k
        )
    )


    result = await db.execute(
        statement
    )


    rows = list(
        result.all()
    )


    # ========================================================
    # 6. Convert Distance -> Similarity
    # ========================================================

    items: list[
        SemanticSearchResultItem
    ] = []


    for (
        chunk,
        embedding,
        distance,
    ) in rows:

        distance_value = float(
            distance
        )


        similarity = (
            1.0
            - distance_value
        )


        # 因为浮点计算，
        # 极端情况下可能略超出 [-1, 1]。
        similarity = max(
            -1.0,
            min(
                1.0,
                similarity,
            ),
        )


        # min_score 在应用层过滤。
        #
        # Day44 根据 Evaluation
        # 再决定是否把 Threshold
        # 下推到 SQL。
        if similarity < min_score:

            continue


        items.append(
            SemanticSearchResultItem(
                chunk_id=(
                    chunk.id
                ),

                chunk_index=(
                    chunk.chunk_index
                ),

                content=(
                    chunk.content
                ),

                start_page=(
                    chunk.start_page
                ),

                end_page=(
                    chunk.end_page
                ),

                token_count=(
                    chunk.token_count
                ),

                similarity_score=(
                    round(
                        similarity,
                        6,
                    )
                ),

                cosine_distance=(
                    round(
                        distance_value,
                        6,
                    )
                ),
            )
        )


    # ========================================================
    # 7. Response
    # ========================================================

    return (
        SemanticSearchResponse(
            document_id=(
                document.id
            ),

            query=(
                normalized_query
            ),

            top_k=top_k,

            min_score=(
                min_score
            ),

            returned_count=len(
                items
            ),

            model=(
                SemanticSearchModelInfo(
                    provider=(
                        query_batch.provider
                    ),

                    model_name=(
                        query_batch.model_name
                    ),

                    dimension=(
                        query_batch.dimension
                    ),
                )
            ),

            items=items,
        )
    )