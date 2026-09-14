import logging
from pathlib import Path
from typing import Tuple
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    PaperDocumentNotFoundException,
    PaperDocumentPaperUnavailableException,
    PaperDocumentStorageException,
    PaperDocumentTooLargeException,
    UnsupportedPaperDocumentException,
)
from backend.app.models.paper import Paper
from backend.app.models.paper_document import (
    PaperDocument,
)
from backend.app.storage.base import (
    StorageBackend,
    StorageFileTooLargeError,
)


logger = logging.getLogger(__name__)


PDF_MAGIC = b"%PDF-"


# ============================================================
# Paper Authorization
# ============================================================

async def _get_owned_paper(
    db: AsyncSession,
    paper_id: int,
    user_id: int,
) -> Paper:
    """
    获取当前用户自己的 Paper。

    不区分：
    - Paper 不存在
    - Paper 属于其他用户

    都返回 404，
    避免资源枚举。
    """

    result = await db.execute(
        select(Paper).where(
            Paper.id == paper_id,
            Paper.owner_id == user_id,
        )
    )


    paper = result.scalar_one_or_none()


    if paper is None:
        raise (
            PaperDocumentPaperUnavailableException()
        )


    return paper


# ============================================================
# PDF Validation
# ============================================================

async def _validate_pdf(
    upload_file: UploadFile,
) -> str:
    """
    PDF 上传预检查。

    注意：
    不能只信：
        content_type
        filename

    最终还检查 PDF Magic Header：
        %PDF-
    """

    filename = (
        upload_file.filename
        or "document.pdf"
    )


    # 防止客户端发送：
    # C:\\Users\\xxx\\paper.pdf
    filename = Path(
        filename
    ).name


    if not filename.lower().endswith(
        ".pdf"
    ):
        raise UnsupportedPaperDocumentException()


    # MIME 只能作为辅助判断，
    # 因为客户端可以伪造 MIME。
    if (
        upload_file.content_type
        and upload_file.content_type
        not in {
            "application/pdf",
            "application/octet-stream",
        }
    ):
        raise UnsupportedPaperDocumentException()


    # 读取文件前 5 bytes。
    magic = await upload_file.read(
        len(PDF_MAGIC)
    )


    # 之后 Storage 还要从头读取，
    # 所以必须 seek 回 0。
    await upload_file.seek(
        0
    )


    if magic != PDF_MAGIC:
        raise UnsupportedPaperDocumentException()


    # 数据库字段最大 255。
    if len(filename) > 255:

        stem = Path(filename).stem[:240]

        filename = (
            f"{stem}.pdf"
        )


    return filename


# ============================================================
# Upload
# ============================================================

async def upload_document(
    db: AsyncSession,
    storage: StorageBackend,
    paper_id: int,
    user_id: int,
    upload_file: UploadFile,
) -> Tuple[
    PaperDocument,
    bool,
]:
    """
    上传 Paper PDF。

    Returns:
        (document, created)

    created=True:
        新文件。

    created=False:
        同一篇 Paper 已经有相同 PDF。
    """

    # --------------------------------------------------------
    # 1. Ownership
    # --------------------------------------------------------

    await _get_owned_paper(
        db=db,
        paper_id=paper_id,
        user_id=user_id,
    )


    # --------------------------------------------------------
    # 2. Validate
    # --------------------------------------------------------

    original_filename = await _validate_pdf(
        upload_file
    )


    # 不使用用户 filename 作为 Storage Key。
    #
    # 避免：
    # - 重名
    # - 特殊字符
    # - 路径穿越
    key = (
        f"papers/"
        f"{paper_id}/"
        f"{uuid4().hex}.pdf"
    )


    stored = None


    try:

        # ----------------------------------------------------
        # 3. Storage Write
        # ----------------------------------------------------

        stored = await storage.save(
            reader=upload_file,
            key=key,
            max_bytes=(
                settings
                .PDF_MAX_SIZE_BYTES
            ),
        )


        # ----------------------------------------------------
        # 4. Application-level Duplicate Check
        # ----------------------------------------------------

        result = await db.execute(
            select(PaperDocument).where(
                PaperDocument.paper_id
                == paper_id,

                PaperDocument.sha256
                == stored.sha256,
            )
        )


        existing = (
            result.scalar_one_or_none()
        )


        if existing is not None:

            # 新写的临时重复文件没必要保存。
            await storage.delete(
                stored.key
            )

            return (
                existing,
                False,
            )


        # ----------------------------------------------------
        # 5. Build ORM
        # ----------------------------------------------------

        document = PaperDocument(
            paper_id=paper_id,
            uploaded_by_id=user_id,
            original_filename=original_filename,
            storage_backend=storage.name,
            storage_key=stored.key,
            mime_type="application/pdf",
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            status="uploaded",
        )


        db.add(
            document
        )


        await db.commit()


        await db.refresh(
            document
        )


        logger.info(
            (
                "Paper PDF uploaded: "
                "document_id=%s "
                "paper_id=%s "
                "size=%s"
            ),
            document.id,
            paper_id,
            document.size_bytes,
        )


        return (
            document,
            True,
        )


    except StorageFileTooLargeError:

        await db.rollback()

        raise PaperDocumentTooLargeException()


    except IntegrityError:

        # ----------------------------------------------------
        # Database Race Condition
        # ----------------------------------------------------

        await db.rollback()


        # 数据库 UNIQUE：
        #
        # (paper_id, sha256)
        #
        # 作为并发最终防线。
        if stored is not None:

            await storage.delete(
                stored.key
            )


            result = await db.execute(
                select(PaperDocument).where(
                    PaperDocument.paper_id
                    == paper_id,

                    PaperDocument.sha256
                    == stored.sha256,
                )
            )


            existing = (
                result.scalar_one_or_none()
            )


            if existing is not None:

                return (
                    existing,
                    False,
                )


        raise


    except Exception:

        await db.rollback()


        # ----------------------------------------------------
        # Compensating Action
        # ----------------------------------------------------

        # File Storage 和 PostgreSQL
        # 不是同一个 Transaction。
        #
        # 如果文件成功但 DB 失败，
        # 手动删除刚写入的文件。
        if stored is not None:

            await storage.delete(
                stored.key
            )


        raise


# ============================================================
# Query
# ============================================================

async def list_documents(
    db: AsyncSession,
    paper_id: int,
    user_id: int,
) -> list[PaperDocument]:
    """
    获取 Paper 的所有 PDF Document。
    """

    await _get_owned_paper(
        db=db,
        paper_id=paper_id,
        user_id=user_id,
    )


    result = await db.execute(
        select(PaperDocument)
        .where(
            PaperDocument.paper_id
            == paper_id
        )
        .order_by(
            PaperDocument.created_at.desc()
        )
    )


    return list(
        result.scalars().all()
    )


async def get_document(
    db: AsyncSession,
    paper_id: int,
    document_id: int,
    user_id: int,
) -> PaperDocument:
    """
    获取某个 Paper Document。
    """

    await _get_owned_paper(
        db=db,
        paper_id=paper_id,
        user_id=user_id,
    )


    result = await db.execute(
        select(PaperDocument).where(
            PaperDocument.id
            == document_id,

            PaperDocument.paper_id
            == paper_id,
        )
    )


    document = (
        result.scalar_one_or_none()
    )


    if document is None:
        raise PaperDocumentNotFoundException()


    return document


async def ensure_document_exists_in_storage(
    storage: StorageBackend,
    document: PaperDocument,
) -> None:
    """
    检查 DB Metadata 对应文件是否真实存在。

    防止数据库有记录，
    但磁盘文件已经丢失。
    """

    exists = await storage.exists(
        document.storage_key
    )


    if not exists:

        logger.error(
            (
                "Paper document missing "
                "from storage: "
                "document_id=%s key=%s"
            ),
            document.id,
            document.storage_key,
        )

        raise PaperDocumentStorageException()