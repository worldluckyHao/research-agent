import asyncio
import logging
import os
import tempfile
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

import aiofiles
from sqlalchemy import (
    delete,
    select,
    func,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.db.session import (
    AsyncSessionLocal,
)
from backend.app.models.paper_document import (
    PaperDocument,
)
from backend.app.models.paper_document_page import (
    PaperDocumentPage,
)
from backend.app.parsers.pdf import (
    PDFParser,
)
from backend.app.storage.factory import (
    create_storage_backend,
)


logger = logging.getLogger(__name__)


# ============================================================
# Materialization
# ============================================================

async def _materialize_pdf(
    storage,
    storage_key: str,
) -> Path:
    """
    Materialize（物化）Storage 中的 PDF。

    无论原文件来自：
    - LocalStorage
    - S3
    - MinIO

    最终 Parser 都只接收一个本地 Path。
    """

    file_descriptor, temp_name = (
        tempfile.mkstemp(
            suffix=".pdf"
        )
    )


    # mkstemp 会返回打开的文件描述符。
    # Windows 下必须先关闭，
    # 否则后续重新打开可能产生文件占用问题。
    os.close(
        file_descriptor
    )


    temp_path = Path(
        temp_name
    )


    try:

        async with aiofiles.open(
            temp_path,
            mode="wb",
        ) as output:

            async for chunk in storage.iter_bytes(
                storage_key
            ):

                await output.write(
                    chunk
                )


        return temp_path


    except Exception:

        if temp_path.exists():

            temp_path.unlink(
                missing_ok=True
            )

        raise

async def prepare_document_parse(
    db: AsyncSession,
    document: PaperDocument,
    force: bool = False,
) -> tuple[
    PaperDocument,
    bool,
]:
    """
    在 API 发布 Celery Task 前，
    准备 Document 状态。

    Returns:
        (document, should_enqueue)
    """

    # 已在队列或正在执行：
    # 不重复投递。
    if document.status in {
        "queued",
        "parsing",
    }:

        return (
            document,
            False,
        )


    # 已解析成功且用户没有要求 force：
    # 直接复用现有结果。
    if (
        document.status == "parsed"
        and not force
    ):

        return (
            document,
            False,
        )


    document.status = "queued"

    document.parse_error = None


    await db.commit()

    await db.refresh(
        document
    )


    return (
        document,
        True,
    )


# ============================================================
# Parse Job
# ============================================================

async def run_document_parse_job(
    document_id: int,
) -> None:
    """
    执行 PDF Parsing。

    State Machine：

        queued
          ↓
        parsing
          ↓
       ┌───────┐
       ↓       ↓
     parsed   failed
    """

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(PaperDocument).where(
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
                    "Document parse skipped: "
                    "document_id=%s not found"
                ),
                document_id,
            )

            return


        temp_path = None


        try:

            # =================================================
            # 1. queued -> parsing
            # =================================================

            document.status = "parsing"

            document.parse_error = None


            await db.commit()


            # =================================================
            # 2. Create Storage
            # =================================================

            storage = (
                create_storage_backend()
            )


            exists = await storage.exists(
                document.storage_key
            )


            if not exists:

                raise FileNotFoundError(
                    (
                        "PDF storage object "
                        "does not exist"
                    )
                )


            # =================================================
            # 3. Materialize
            # =================================================

            temp_path = await _materialize_pdf(
                storage=storage,
                storage_key=(
                    document.storage_key
                ),
            )


            # =================================================
            # 4. Parse
            # =================================================

            parser = PDFParser()


            # PyMuPDF 是同步解析。
            #
            # 使用 to_thread：
            #
            # Event Loop
            #     ↓
            # Worker Thread
            #     ↓
            # parser.parse()
            parsed = await asyncio.to_thread(
                parser.parse,
                temp_path,
            )


            # =================================================
            # 5. Replace Old Page Data
            # =================================================

            # 重跑 Parsing 时：
            #
            # 先删除旧 Page，
            # 再写最新解析结果。
            #
            # 从而保证 Task 可重复执行。
            await db.execute(
                delete(
                    PaperDocumentPage
                ).where(
                    PaperDocumentPage
                    .document_id
                    == document_id
                )
            )


            pages = []


            for page in parsed.pages:

                pages.append(
                    PaperDocumentPage(
                        document_id=(
                            document_id
                        ),

                        page_number=(
                            page.page_number
                        ),

                        text=page.text,

                        char_count=len(
                            page.text
                        ),
                    )
                )


            db.add_all(
                pages
            )


            # =================================================
            # 6. Update Document Metadata
            # =================================================

            document.page_count = (
                parsed.page_count
            )

            document.parser_name = (
                parsed.parser_name
            )

            document.parser_version = (
                parsed.parser_version
            )

            document.status = "parsed"

            document.parse_error = None

            document.parsed_at = (
                datetime.now(
                    timezone.utc
                )
            )


            # Page 数据 + Document 状态
            # 在同一个 DB Transaction 中提交。
            await db.commit()


            logger.info(
                (
                    "PDF parsed: "
                    "document_id=%s "
                    "pages=%s"
                ),
                document_id,
                parsed.page_count,
            )


        except Exception:

            # 当前 Transaction 有异常，
            # 先回滚。
            await db.rollback()


            logger.exception(
                (
                    "PDF parsing failed: "
                    "document_id=%s"
                ),
                document_id,
            )


            # Rollback 后重新读取，
            # 保证 ORM State 干净。
            result = await db.execute(
                select(PaperDocument).where(
                    PaperDocument.id
                    == document_id
                )
            )


            failed_document = (
                result.scalar_one_or_none()
            )


            if failed_document is not None:

                failed_document.status = (
                    "failed"
                )

                # 前端只保存安全错误，
                # 不泄露服务器路径、
                # Traceback 等内部信息。
                failed_document.parse_error = (
                    "PDF parsing failed"
                )


                await db.commit()


            # 让 Celery 同样知道任务失败。
            raise


        finally:

            # 无论成功失败，
            # 临时 PDF 都必须删除。
            if (
                temp_path is not None
                and temp_path.exists()
            ):

                temp_path.unlink(
                    missing_ok=True
                )

async def list_document_pages(
    db: AsyncSession,
    document_id: int,
    page: int,
    page_size: int,
) -> tuple[
    list[PaperDocumentPage],
    int,
]:
    """
    分页读取 PDF Page Text。
    """

    offset = (
        page - 1
    ) * page_size


    count_result = await db.execute(
        select(
            func.count(
                PaperDocumentPage.id
            )
        ).where(
            PaperDocumentPage.document_id
            == document_id
        )
    )


    total = (
        count_result.scalar_one()
    )


    result = await db.execute(
        select(
            PaperDocumentPage
        )
        .where(
            PaperDocumentPage.document_id
            == document_id
        )
        .order_by(
            PaperDocumentPage.page_number
        )
        .offset(
            offset
        )
        .limit(
            page_size
        )
    )


    pages = list(
        result.scalars().all()
    )


    return (
        pages,
        total,
    )