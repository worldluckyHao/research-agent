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

from backend.app.chunkers.base import (
    ChunkInputPage,
)
from backend.app.chunkers.factory import (
    create_document_chunker,
)
from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    PaperDocumentNotParsedException,
)
from backend.app.db.session import (
    AsyncSessionLocal,
)
from backend.app.models.paper_document import (
    PaperDocument,
)
from backend.app.models.paper_document_chunk import (
    PaperDocumentChunk,
)
from backend.app.models.paper_document_page import (
    PaperDocumentPage,
)


logger = logging.getLogger(__name__)


# ============================================================
# Prepare
# ============================================================

async def prepare_document_chunking(
    db: AsyncSession,
    document: PaperDocument,
    force: bool = False,
) -> tuple[
    PaperDocument,
    bool,
]:
    """
    在 API 将任务发布到 Celery 前，
    检查 Document 是否允许 Chunk。

    Returns:
        (document, should_enqueue)
    """

    # Chunking 必须基于已经解析成功的 Page Text。
    if document.status != "parsed":

        raise (
            PaperDocumentNotParsedException()
        )


    # 已经进入队列或正在处理：
    # 不重复发布任务。
    if document.chunk_status in {
        "queued",
        "chunking",
    }:

        return (
            document,
            False,
        )


    # 已经成功 Chunk，
    # 默认直接复用。
    if (
        document.chunk_status
        == "chunked"
        and not force
    ):

        return (
            document,
            False,
        )

    # =================================================
    # Invalidate Downstream Embeddings
    # =================================================

    # Chunk 内容被重新生成以后，
    # 旧 Vector 已经失效。
    #
    # 旧 Chunk 被 DELETE 时，
    # FK ON DELETE CASCADE 会删除
    # 对应 Embedding Rows。
    #
    # 这里重置 Document 级状态。
    document.embedding_status = (
        "pending"
    )

    document.embedding_count = 0

    document.embedding_provider = None

    document.embedding_model = None

    document.embedding_dimension = None

    document.embedding_normalized = None

    document.embedding_error = None

    document.embedded_at = None


    document.chunk_status = (
        "queued"
    )

    document.chunk_error = None


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

async def run_document_chunk_job(
    document_id: int,
) -> None:
    """
    执行 Document Chunking。

    State Machine：

        queued
          ↓
       chunking
          ↓
       ┌───────┐
       ↓       ↓
    chunked   failed
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
                    "Document chunk skipped: "
                    "document_id=%s not found"
                ),
                document_id,
            )

            return


        try:

            # =================================================
            # 1. Validate Upstream Stage
            # =================================================

            if document.status != "parsed":

                raise (
                    PaperDocumentNotParsedException()
                )


            # =================================================
            # 2. queued -> chunking
            # =================================================

            document.chunk_status = (
                "chunking"
            )

            document.chunk_error = None


            await db.commit()


            # =================================================
            # 3. Load Parsed Pages
            # =================================================

            page_result = await db.execute(
                select(
                    PaperDocumentPage
                )
                .where(
                    PaperDocumentPage
                    .document_id
                    == document_id
                )
                .order_by(
                    PaperDocumentPage
                    .page_number
                )
            )


            page_models = list(
                page_result.scalars().all()
            )


            input_pages = [
                ChunkInputPage(
                    page_number=(
                        page.page_number
                    ),
                    text=page.text,
                )
                for page in page_models
            ]


            # =================================================
            # 4. Create Chunker
            # =================================================

            chunker = (
                create_document_chunker()
            )


            # Tokenization 和 Chunking 是同步 CPU 工作。
            # 放入 Thread，避免阻塞 Event Loop。
            chunk_results = (
                await asyncio.to_thread(
                    chunker.chunk,
                    input_pages,
                )
            )


            if not chunk_results:

                raise ValueError(
                    "No text chunks generated"
                )


            # =================================================
            # 5. Rebuild Chunks
            # =================================================

            # 重新 Chunk 时先删除旧数据。
            #
            # DELETE + INSERT + Document Metadata
            # 在一个 Transaction 中完成。
            await db.execute(
                delete(
                    PaperDocumentChunk
                ).where(
                    PaperDocumentChunk
                    .document_id
                    == document_id
                )
            )


            chunk_models = []


            for chunk in chunk_results:

                chunk_models.append(
                    PaperDocumentChunk(
                        document_id=(
                            document_id
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

                        char_count=len(
                            chunk.content
                        ),

                        content_sha256=(
                            chunk
                            .content_sha256
                        ),
                    )
                )


            db.add_all(
                chunk_models
            )


            # =================================================
            # 6. Update Chunk Metadata
            # =================================================

            document.chunk_status = (
                "chunked"
            )

            document.chunk_count = len(
                chunk_models
            )

            document.chunker_name = (
                chunker.name
            )

            document.chunker_version = (
                chunker.version
            )

            document.chunk_size_tokens = (
                settings
                .CHUNK_SIZE_TOKENS
            )

            document.chunk_overlap_tokens = (
                settings
                .CHUNK_OVERLAP_TOKENS
            )

            document.chunk_error = None

            document.chunked_at = (
                datetime.now(
                    timezone.utc
                )
            )


            # Chunk + Metadata 一次提交。
            await db.commit()


            logger.info(
                (
                    "Document chunked: "
                    "document_id=%s "
                    "chunks=%s"
                ),
                document_id,
                len(chunk_models),
            )


        except Exception:

            await db.rollback()


            logger.exception(
                (
                    "Document chunking failed: "
                    "document_id=%s"
                ),
                document_id,
            )


            # Rollback 后重新查询，
            # 获取干净 ORM State。
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

                failed_document.chunk_status = (
                    "failed"
                )

                # 对外只保存安全错误。
                failed_document.chunk_error = (
                    "Document chunking failed"
                )


                await db.commit()


            raise


# ============================================================
# Query
# ============================================================

async def list_document_chunks(
    db: AsyncSession,
    document_id: int,
    page: int,
    page_size: int,
) -> tuple[
    list[PaperDocumentChunk],
    int,
]:
    """
    分页查询 Document Chunks。
    """

    offset = (
        page - 1
    ) * page_size


    count_result = await db.execute(
        select(
            func.count(
                PaperDocumentChunk.id
            )
        ).where(
            PaperDocumentChunk.document_id
            == document_id
        )
    )


    total = (
        count_result.scalar_one()
    )


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
        .offset(
            offset
        )
        .limit(
            page_size
        )
    )


    chunks = list(
        result.scalars().all()
    )


    return (
        chunks,
        total,
    )