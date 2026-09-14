from urllib.parse import quote
from fastapi import Query
from fastapi import (
    APIRouter,
    Depends,
    File,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import (
    StreamingResponse,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.dependencies import (
    get_current_user,
    get_db,
    get_storage_backend,
)
from backend.app.models.user import User
from backend.app.schemas.paper_document import (
    PaperDocumentListResponse,
    PaperDocumentPageListResponse,
    PaperDocumentResponse,
)
from backend.app.services import (
    paper_document,
    paper_document_parser,
)
from backend.app.storage.base import (
    StorageBackend,
)
from backend.app.tasks.document_parse import (
    run_document_parse_task,
)

router = APIRouter(
    prefix="/papers",
    tags=[
        "paper-documents"
    ],
)


# ============================================================
# Upload
# ============================================================

@router.post(
    "/{paper_id}/documents",
    response_model=PaperDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_paper_document(
    paper_id: int,

    response: Response,

    file: UploadFile = File(
        description="PDF file"
    ),

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),

    storage: StorageBackend = Depends(
        get_storage_backend
    ),
):
    """
    上传 Paper PDF。

    如果完全相同的 PDF 已经存在：
    返回已有 Document，HTTP 200。

    如果是新文件：
    HTTP 201。
    """

    document, created = (
        await paper_document.upload_document(
            db=db,
            storage=storage,
            paper_id=paper_id,
            user_id=current_user.id,
            upload_file=file,
        )
    )


    if not created:

        response.status_code = (
            status.HTTP_200_OK
        )


    return document


# ============================================================
# List
# ============================================================

@router.get(
    "/{paper_id}/documents",
    response_model=PaperDocumentListResponse,
)
async def list_paper_documents(
    paper_id: int,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    获取 Paper 的所有 Documents。
    """

    documents = (
        await paper_document.list_documents(
            db=db,
            paper_id=paper_id,
            user_id=current_user.id,
        )
    )


    return PaperDocumentListResponse(
        items=documents,
        total=len(documents),
    )


# ============================================================
# Metadata
# ============================================================

@router.get(
    "/{paper_id}/documents/{document_id}",
    response_model=PaperDocumentResponse,
)
async def get_paper_document(
    paper_id: int,
    document_id: int,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    获取 Document Metadata。
    """

    return await paper_document.get_document(
        db=db,
        paper_id=paper_id,
        document_id=document_id,
        user_id=current_user.id,
    )


@router.post(
    (
        "/{paper_id}/documents/"
        "{document_id}/parse"
    ),
    response_model=(
        PaperDocumentResponse
    ),
    status_code=(
        status.HTTP_202_ACCEPTED
    ),
)
async def parse_paper_document(
    paper_id: int,
    document_id: int,

    response: Response,

    force: bool = Query(
        default=False,
        description=(
            "Re-parse an already "
            "parsed PDF"
        ),
    ),

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    将 PDF Parsing Task
    提交给 Celery。

    force=false：
        已经 parsed 时复用现有结果。

    force=true：
        强制重新解析。
    """

    # 这里复用 Day23 权限检查。
    document = (
        await paper_document.get_document(
            db=db,
            paper_id=paper_id,
            document_id=document_id,
            user_id=current_user.id,
        )
    )


    document, should_enqueue = (
        await paper_document_parser
        .prepare_document_parse(
            db=db,
            document=document,
            force=force,
        )
    )


    if not should_enqueue:

        # 不需要重新提交任务。
        response.status_code = (
            status.HTTP_200_OK
        )

        return document


    # Redis Broker 中只发送 ID。
    run_document_parse_task.delay(
        document.id
    )


    return document

# ============================================================
# Download
# ============================================================

@router.get(
    (
        "/{paper_id}/documents/"
        "{document_id}/download"
    )
)
async def download_paper_document(
    paper_id: int,
    document_id: int,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),

    storage: StorageBackend = Depends(
        get_storage_backend
    ),
):
    """
    流式下载 PDF。

    不一次性把整个 PDF 读进内存。
    """

    document = await paper_document.get_document(
        db=db,
        paper_id=paper_id,
        document_id=document_id,
        user_id=current_user.id,
    )


    await (
        paper_document
        .ensure_document_exists_in_storage(
            storage=storage,
            document=document,
        )
    )


    # RFC 5987 风格 filename，
    # 支持中文文件名。
    encoded_filename = quote(
        document.original_filename
    )


    return StreamingResponse(
        storage.iter_bytes(
            document.storage_key
        ),

        media_type=(
            document.mime_type
        ),

        headers={
            "Content-Disposition": (
                "attachment; "
                "filename*=UTF-8''"
                f"{encoded_filename}"
            )
        },
    )

@router.get(
    (
        "/{paper_id}/documents/"
        "{document_id}/pages"
    ),
    response_model=(
        PaperDocumentPageListResponse
    ),
)
async def list_paper_document_pages(
    paper_id: int,
    document_id: int,

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    查看 PDF 的页级文本。
    """

    # 首先检查 Document 属于用户可访问 Paper。
    document = (
        await paper_document.get_document(
            db=db,
            paper_id=paper_id,
            document_id=document_id,
            user_id=current_user.id,
        )
    )


    pages, total = (
        await paper_document_parser
        .list_document_pages(
            db=db,
            document_id=document.id,
            page=page,
            page_size=page_size,
        )
    )


    return (
        PaperDocumentPageListResponse(
            items=pages,
            total=total,
            page=page,
            page_size=page_size,
        )
    )