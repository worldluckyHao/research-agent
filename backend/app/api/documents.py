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
    get_embedding_provider,
    get_storage_backend,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.schemas.embedding import (
    DocumentEmbeddingPreviewResponse,
)
from backend.app.schemas.semantic_search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from backend.app.models.user import User
from backend.app.schemas.paper_document import (
    PaperDocumentChunkListResponse,
    PaperDocumentListResponse,
    PaperDocumentPageListResponse,
    PaperDocumentResponse,
)
from backend.app.services import (
    embedding_service,
    hybrid_retrieval,
    paper_document,
    paper_document_chunker,
    paper_document_embedder,
    paper_document_parser,
    semantic_retrieval,
)
from backend.app.storage.base import (
    StorageBackend,
)
from backend.app.tasks.document_parse import (
    run_document_parse_task,
)
from backend.app.tasks.document_chunk import (
    run_document_chunk_task,
)
from backend.app.core.config import (
    settings,
)
from backend.app.schemas.embedding import (
    DocumentEmbeddingListResponse,
    DocumentEmbeddingPreviewResponse,
    ChunkEmbeddingMetadataResponse,
)
from backend.app.tasks.document_embed import (
    run_document_embedding_task,
)
from backend.app.schemas.hybrid_search import (
    HybridSearchRequest,
    HybridSearchResponse,
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

@router.post(
    (
        "/{paper_id}/documents/"
        "{document_id}/chunk"
    ),
    response_model=(
        PaperDocumentResponse
    ),
    status_code=(
        status.HTTP_202_ACCEPTED
    ),
)
async def chunk_paper_document(
    paper_id: int,
    document_id: int,

    response: Response,

    force: bool = Query(
        default=False,
        description=(
            "Rebuild chunks for an "
            "already chunked document"
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
    将 Document Chunking Task
    提交给 Celery。

    force=false：
        chunked 时直接复用。

    force=true：
        强制重新 Chunk。
    """

    # 继续复用 Day23 的权限检查。
    document = (
        await paper_document.get_document(
            db=db,
            paper_id=paper_id,
            document_id=document_id,
            user_id=current_user.id,
        )
    )


    document, should_enqueue = (
        await paper_document_chunker
        .prepare_document_chunking(
            db=db,
            document=document,
            force=force,
        )
    )


    if not should_enqueue:

        response.status_code = (
            status.HTTP_200_OK
        )

        return document


    run_document_chunk_task.delay(
        document.id
    )


    return document

@router.get(
    (
        "/{paper_id}/documents/"
        "{document_id}/chunks"
    ),
    response_model=(
        PaperDocumentChunkListResponse
    ),
)
async def list_paper_document_chunks(
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
    分页查看 Document Chunks。
    """

    document = (
        await paper_document.get_document(
            db=db,
            paper_id=paper_id,
            document_id=document_id,
            user_id=current_user.id,
        )
    )


    chunks, total = (
        await paper_document_chunker
        .list_document_chunks(
            db=db,
            document_id=document.id,
            page=page,
            page_size=page_size,
        )
    )


    return (
        PaperDocumentChunkListResponse(
            items=chunks,
            total=total,
            page=page,
            page_size=page_size,
        )
    )

@router.post(
    (
        "/{paper_id}/documents/"
        "{document_id}/embeddings/preview"
    ),
    response_model=(
        DocumentEmbeddingPreviewResponse
    ),
)
async def preview_paper_document_embeddings(
    paper_id: int,
    document_id: int,

    limit: int = Query(
        default=3,
        ge=1,
        le=(
            settings
            .EMBEDDING_PREVIEW_MAX_CHUNKS
        ),
        description=(
            "Number of document chunks "
            "to embed for preview"
        ),
    ),

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),

    embedding_provider: EmbeddingProvider = Depends(
        get_embedding_provider
    ),
):
    """
    Day26 Embedding Preview。

    真正将 Chunk Text 转为 Vector，
    但暂时不写入数据库。

    Day27 会把 Vector
    持久化到 pgvector。
    """

    # --------------------------------------------------------
    # 1. Authorization
    # --------------------------------------------------------

    document = (
        await paper_document.get_document(
            db=db,
            paper_id=paper_id,
            document_id=document_id,
            user_id=current_user.id,
        )
    )


    # --------------------------------------------------------
    # 2. Pipeline Precondition
    # --------------------------------------------------------

    if (
        document.chunk_status
        != "chunked"
    ):

        from backend.app.core.exceptions import (
            PaperDocumentNotChunkedException,
        )

        raise (
            PaperDocumentNotChunkedException()
        )


    # --------------------------------------------------------
    # 3. Real Embedding
    # --------------------------------------------------------

    return (
        await embedding_service
        .preview_document_embeddings(
            db=db,

            document_id=(
                document.id
            ),

            provider=(
                embedding_provider
            ),

            limit=limit,
        )
    )

@router.post(
    (
        "/{paper_id}/documents/"
        "{document_id}/embed"
    ),
    response_model=(
        PaperDocumentResponse
    ),
    status_code=(
        status.HTTP_202_ACCEPTED
    ),
)
async def embed_paper_document(
    paper_id: int,
    document_id: int,

    response: Response,

    force: bool = Query(
        default=False,
        description=(
            "Rebuild embeddings for an "
            "already embedded document"
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
    将整个 Document 的 Embedding Job
    提交到 Celery。

    force=false：
        embedded 时直接复用。

    force=true：
        删除并重建当前向量。
    """

    # --------------------------------------------------------
    # 1. Authorization
    # --------------------------------------------------------

    document = (
        await paper_document.get_document(
            db=db,
            paper_id=paper_id,
            document_id=document_id,
            user_id=current_user.id,
        )
    )


    # --------------------------------------------------------
    # 2. Prepare Job
    # --------------------------------------------------------

    document, should_enqueue = (
        await paper_document_embedder
        .prepare_document_embedding(
            db=db,
            document=document,
            force=force,
        )
    )


    if not should_enqueue:

        response.status_code = (
            status.HTTP_200_OK
        )

        return document


    # --------------------------------------------------------
    # 3. Publish Celery Task
    # --------------------------------------------------------

    run_document_embedding_task.delay(
        document.id
    )


    return document

@router.get(
    (
        "/{paper_id}/documents/"
        "{document_id}/embeddings"
    ),
    response_model=(
        DocumentEmbeddingListResponse
    ),
)
async def list_paper_document_embeddings(
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
    查看已经保存到 pgvector 的
    Embedding Metadata。

    不返回完整 384 维 Vector。
    """

    document = (
        await paper_document.get_document(
            db=db,
            paper_id=paper_id,
            document_id=document_id,
            user_id=current_user.id,
        )
    )


    rows, total = (
        await paper_document_embedder
        .list_document_embeddings(
            db=db,
            document_id=document.id,
            page=page,
            page_size=page_size,
        )
    )


    items = []


    for embedding, chunk in rows:

        items.append(
            ChunkEmbeddingMetadataResponse(
                id=embedding.id,
                chunk_id=chunk.id,
                chunk_index=(
                    chunk.chunk_index
                ),
                start_page=(
                    chunk.start_page
                ),
                end_page=(
                    chunk.end_page
                ),
                provider=(
                    embedding.provider
                ),
                model_name=(
                    embedding.model_name
                ),
                dimension=(
                    embedding.dimension
                ),
                normalized=(
                    embedding.normalized
                ),
                content_sha256=(
                    embedding
                    .content_sha256
                ),
                created_at=(
                    embedding.created_at
                ),
            )
        )


    return (
        DocumentEmbeddingListResponse(
            document_id=document.id,
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )
    )

@router.post(
    (
        "/{paper_id}/documents/"
        "{document_id}/search"
    ),
    response_model=(
        SemanticSearchResponse
    ),
)
async def search_paper_document(
    paper_id: int,
    document_id: int,

    request_data: SemanticSearchRequest,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),

    embedding_provider: EmbeddingProvider = Depends(
        get_embedding_provider
    ),
):
    """
    在一个 PDF Document 内执行
    Semantic Retrieval（语义检索）。

    Flow:

        User Query
            ↓
        Query Embedding
            ↓
        pgvector
            ↓
        Cosine Distance
            ↓
        Top-K Chunk
    """

    # --------------------------------------------------------
    # 1. Authorization
    # --------------------------------------------------------

    document = (
        await paper_document.get_document(
            db=db,
            paper_id=paper_id,
            document_id=document_id,
            user_id=current_user.id,
        )
    )


    # --------------------------------------------------------
    # 2. Semantic Retrieval
    # --------------------------------------------------------

    return (
        await semantic_retrieval
        .semantic_search_document(
            db=db,

            document=document,

            query=(
                request_data.query
            ),

            top_k=(
                request_data.top_k
            ),

            min_score=(
                request_data.min_score
            ),

            provider=(
                embedding_provider
            ),
        )
    )

@router.post(
    (
        "/{paper_id}/documents/"
        "{document_id}/hybrid-search"
    ),
    response_model=(
        HybridSearchResponse
    ),
)
async def hybrid_search_paper_document(
    paper_id: int,
    document_id: int,

    request_data: HybridSearchRequest,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),

    embedding_provider: EmbeddingProvider = Depends(
        get_embedding_provider
    ),
):
    """
    Hybrid Retrieval：

        Semantic Search
            +
        Lexical Search
            ↓
        RRF Fusion
            ↓
        Optional Reranker
    """

    # --------------------------------------------------------
    # 1. Authorization
    # --------------------------------------------------------

    document = (
        await paper_document.get_document(
            db=db,

            paper_id=paper_id,

            document_id=document_id,

            user_id=(
                current_user.id
            ),
        )
    )


    # --------------------------------------------------------
    # 2. Hybrid Retrieval
    # --------------------------------------------------------

    return (
        await hybrid_retrieval
        .hybrid_search_document(
            db=db,

            document=document,

            query=(
                request_data.query
            ),

            top_k=(
                request_data.top_k
            ),

            use_reranker=(
                request_data
                .use_reranker
            ),

            embedding_provider=(
                embedding_provider
            ),
        )
    )