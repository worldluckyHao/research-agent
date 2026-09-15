import asyncio
import math

from sqlalchemy import (
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.core.exceptions import (
    EmbeddingConfigurationException,
    EmbeddingInputTooLongException,
)
from backend.app.embeddings.base import (
    EmbeddingDimensionMismatchError,
    EmbeddingInputTooLongError,
    EmbeddingProvider,
)
from backend.app.models.paper_document_chunk import (
    PaperDocumentChunk,
)
from backend.app.schemas.embedding import (
    ChunkEmbeddingPreviewItem,
    DocumentEmbeddingPreviewResponse,
    EmbeddingModelInfoResponse,
)


# ============================================================
# Helpers
# ============================================================

def _vector_norm(
    vector: list[float],
) -> float:
    """
    计算 Vector L2 Norm（L2范数）。

    normalize_embeddings=True 时，
    理论上应该非常接近 1。
    """

    return math.sqrt(
        sum(
            value * value
            for value in vector
        )
    )


# ============================================================
# Document Embedding Preview
# ============================================================

async def preview_document_embeddings(
    db: AsyncSession,
    document_id: int,
    provider: EmbeddingProvider,
    limit: int,
) -> DocumentEmbeddingPreviewResponse:
    """
    对 Document 前 N 个 Chunk
    执行真实 Embedding。

    Day26：
        只 Preview。

    Day27：
        会将这些 Vector
        正式写入 pgvector。
    """

    # ========================================================
    # 1. Load Chunks
    # ========================================================

    result = await db.execute(
        select(
            PaperDocumentChunk
        )
        .where(
            PaperDocumentChunk.document_id
            == document_id
        )
        .order_by(
            PaperDocumentChunk.chunk_index
        )
        .limit(
            limit
        )
    )


    chunks = list(
        result.scalars().all()
    )


    if not chunks:

        raise ValueError(
            (
                "No document chunks "
                "available for embedding"
            )
        )


    texts = [
        chunk.content
        for chunk in chunks
    ]


    try:

        # ====================================================
        # 2. Batch Embedding
        # ====================================================

        # SentenceTransformer.encode()
        # 是同步且计算密集型操作。
        #
        # 不直接阻塞 Async Event Loop。
        batch = await asyncio.to_thread(
            provider.embed_documents,
            texts,
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


    # ========================================================
    # 3. Build Preview
    # ========================================================

    items: list[
        ChunkEmbeddingPreviewItem
    ] = []


    for chunk, vector in zip(
        chunks,
        batch.vectors,
    ):

        norm = _vector_norm(
            vector
        )


        items.append(
            ChunkEmbeddingPreviewItem(
                chunk_id=(
                    chunk.id
                ),

                chunk_index=(
                    chunk.chunk_index
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

                vector_dimension=(
                    len(vector)
                ),

                vector_norm=(
                    round(
                        norm,
                        6,
                    )
                ),

                # 只展示前 8 维。
                vector_preview=[
                    round(
                        value,
                        6,
                    )
                    for value
                    in vector[:8]
                ],
            )
        )


    return (
        DocumentEmbeddingPreviewResponse(
            document_id=(
                document_id
            ),

            # 注意：
            # 这里是本次 preview 的 Chunk 数，
            # 不是文档全部 chunk_count。
            chunk_count=len(
                chunks
            ),

            preview_count=len(
                items
            ),

            model=(
                EmbeddingModelInfoResponse(
                    provider=(
                        batch.provider
                    ),

                    model_name=(
                        batch.model_name
                    ),

                    dimension=(
                        batch.dimension
                    ),

                    normalized=(
                        batch.normalized
                    ),

                    device=(
                        batch.device
                    ),
                )
            ),

            items=items,
        )
    )