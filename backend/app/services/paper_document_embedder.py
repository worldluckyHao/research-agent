import asyncio
import logging
from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import (
    delete,
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.core.exceptions import (
    DocumentEmbeddingNotReadyException,
)
from backend.app.db.session import (
    AsyncSessionLocal,
)
from backend.app.embeddings.factory import (
    create_embedding_provider,
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


logger = logging.getLogger(__name__)


# ============================================================
# Prepare
# ============================================================

async def prepare_document_embedding(
    db: AsyncSession,
    document: PaperDocument,
    force: bool = False,
) -> tuple[
    PaperDocument,
    bool,
]:
    """
    在 API 发布 Celery Task 前，
    判断是否应该执行 Embedding。

    Returns:
        (document, should_enqueue)
    """

    # Embedding 必须基于已经完成的 Chunk。
    if document.chunk_status != "chunked":

        raise (
            DocumentEmbeddingNotReadyException()
        )


    # 已在 Queue 或正在执行，
    # 不重复提交任务。
    if document.embedding_status in {
        "queued",
        "embedding",
    }:

        return (
            document,
            False,
        )


    # 已经完成且不强制重做。
    if (
        document.embedding_status
        == "embedded"
        and not force
    ):

        return (
            document,
            False,
        )


    document.embedding_status = (
        "queued"
    )

    document.embedding_error = None


    await db.commit()

    await db.refresh(
        document
    )


    return (
        document,
        True,
    )


# ============================================================
# Worker Job
# ============================================================

async def run_document_embedding_job(
    document_id: int,
) -> None:
    """
    对 Document 所有 Chunk
    生成并持久化 Embedding。

    State Machine:

        queued
          ↓
       embedding
          ↓
       ┌───────┐
       ↓       ↓
    embedded  failed
    """

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(
                PaperDocument
            ).where(
                PaperDocument.id
                == document_id
            )
        )


        document = (
            result.scalar_one_or_none()
        )


        if document is None:

            logger.error(
                (
                    "Document embedding skipped: "
                    "document_id=%s not found"
                ),
                document_id,
            )

            return


        try:

            # =================================================
            # 1. Validate Upstream Stage
            # =================================================

            if (
                document.chunk_status
                != "chunked"
            ):

                raise (
                    DocumentEmbeddingNotReadyException()
                )


            # =================================================
            # 2. queued -> embedding
            # =================================================

            document.embedding_status = (
                "embedding"
            )

            document.embedding_error = None


            await db.commit()


            # =================================================
            # 3. Load Chunks
            # =================================================

            chunk_result = await db.execute(
                select(
                    PaperDocumentChunk
                )
                .where(
                    PaperDocumentChunk
                    .document_id
                    == document_id
                )
                .order_by(
                    PaperDocumentChunk
                    .chunk_index
                )
            )


            chunks = list(
                chunk_result.scalars().all()
            )


            if not chunks:

                raise ValueError(
                    "Document has no chunks"
                )


            texts = [
                chunk.content
                for chunk in chunks
            ]


            # =================================================
            # 4. Create Provider
            # =================================================

            provider = (
                create_embedding_provider()
            )


            # =================================================
            # 5. Batch Embedding
            # =================================================

            # SentenceTransformer 是同步推理，
            # 放到工作线程。
            batch = await asyncio.to_thread(
                provider.embed_documents,
                texts,
            )


            if (
                len(batch.vectors)
                != len(chunks)
            ):

                raise RuntimeError(
                    (
                        "Embedding result count "
                        "does not match chunk count"
                    )
                )


            # =================================================
            # 6. Rebuild Embeddings
            # =================================================

            chunk_ids = [
                chunk.id
                for chunk in chunks
            ]


            # force re-embedding 或任务重试时，
            # 先清除当前 Document 的旧向量。
            await db.execute(
                delete(
                    PaperDocumentChunkEmbedding
                ).where(
                    PaperDocumentChunkEmbedding
                    .chunk_id
                    .in_(
                        chunk_ids
                    )
                )
            )


            embedding_models = []


            for chunk, vector in zip(
                chunks,
                batch.vectors,
            ):

                embedding_models.append(
                    PaperDocumentChunkEmbedding(
                        chunk_id=(
                            chunk.id
                        ),

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

                        content_sha256=(
                            chunk
                            .content_sha256
                        ),

                        embedding=vector,
                    )
                )


            db.add_all(
                embedding_models
            )


            # =================================================
            # 7. Update Document Metadata
            # =================================================

            document.embedding_status = (
                "embedded"
            )

            document.embedding_count = len(
                embedding_models
            )

            document.embedding_provider = (
                batch.provider
            )

            document.embedding_model = (
                batch.model_name
            )

            document.embedding_dimension = (
                batch.dimension
            )

            document.embedding_normalized = (
                batch.normalized
            )

            document.embedding_error = None

            document.embedded_at = (
                datetime.now(
                    timezone.utc
                )
            )


            # Vector Rows + Document Metadata
            # 同一 Transaction 提交。
            await db.commit()


            logger.info(
                (
                    "Document embedded: "
                    "document_id=%s "
                    "embeddings=%s "
                    "model=%s"
                ),
                document_id,
                len(embedding_models),
                batch.model_name,
            )


        except Exception:

            await db.rollback()


            logger.exception(
                (
                    "Document embedding failed: "
                    "document_id=%s"
                ),
                document_id,
            )


            # Rollback 后重新获取
            # 干净 ORM State。
            result = await db.execute(
                select(
                    PaperDocument
                ).where(
                    PaperDocument.id
                    == document_id
                )
            )


            failed_document = (
                result.scalar_one_or_none()
            )


            if failed_document is not None:

                failed_document.embedding_status = (
                    "failed"
                )

                failed_document.embedding_error = (
                    "Document embedding failed"
                )


                await db.commit()


            raise


# ============================================================
# Query Metadata
# ============================================================

async def list_document_embeddings(
    db: AsyncSession,
    document_id: int,
    page: int,
    page_size: int,
) -> tuple[
    list[
        tuple[
            PaperDocumentChunkEmbedding,
            PaperDocumentChunk,
        ]
    ],
    int,
]:
    """
    分页查看已持久化 Embedding Metadata。

    不向 API 返回完整 Vector。
    """

    offset = (
        page - 1
    ) * page_size


    count_result = await db.execute(
        select(
            func.count(
                PaperDocumentChunkEmbedding.id
            )
        )
        .join(
            PaperDocumentChunk,
            PaperDocumentChunk.id
            == PaperDocumentChunkEmbedding.chunk_id,
        )
        .where(
            PaperDocumentChunk.document_id
            == document_id
        )
    )


    total = (
        count_result.scalar_one()
    )


    result = await db.execute(
        select(
            PaperDocumentChunkEmbedding,
            PaperDocumentChunk,
        )
        .join(
            PaperDocumentChunk,
            PaperDocumentChunk.id
            == PaperDocumentChunkEmbedding.chunk_id,
        )
        .where(
            PaperDocumentChunk.document_id
            == document_id
        )
        .order_by(
            PaperDocumentChunk.chunk_index
        )
        .offset(
            offset
        )
        .limit(
            page_size
        )
    )


    rows = list(
        result.all()
    )


    return (
        rows,
        total,
    )