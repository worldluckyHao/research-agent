from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.models.paper_document_chunk import (
    PaperDocumentChunk,
)
from backend.app.retrieval.base import (
    RetrievalCandidate,
)


async def lexical_search_document(
    db: AsyncSession,
    document_id: int,
    query: str,
    limit: int,
    fts_config: str,
) -> list[RetrievalCandidate]:
    """
    PostgreSQL Full-Text Search
    （PostgreSQL全文检索）。

    当前只搜索指定 Document。
    """

    normalized_query = (
        query.strip()
    )


    if not normalized_query:
        return []


    # ========================================================
    # 1. Build tsvector
    # ========================================================

    text_vector = func.to_tsvector(
        fts_config,
        PaperDocumentChunk.content,
    )


    # ========================================================
    # 2. Build tsquery
    # ========================================================

    search_query = func.websearch_to_tsquery(
        fts_config,
        normalized_query,
    )


    # ========================================================
    # 3. Keyword Score
    # ========================================================

    lexical_rank_expr = (
        func.ts_rank_cd(
            text_vector,
            search_query,
        )
        .label(
            "lexical_score"
        )
    )


    # ========================================================
    # 4. SQL Search
    # ========================================================

    statement = (
        select(
            PaperDocumentChunk,
            lexical_rank_expr,
        )

        .where(
            PaperDocumentChunk.document_id
            == document_id,

            # @@：
            # PostgreSQL全文检索匹配操作。
            text_vector.op("@@")(
                search_query
            ),
        )

        # ts_rank 越大越相关。
        .order_by(
            lexical_rank_expr.desc()
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


    # ========================================================
    # 5. Convert to Internal Candidates
    # ========================================================

    candidates = []


    for rank, (
        chunk,
        lexical_score,
    ) in enumerate(
        rows,
        start=1,
    ):

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

                lexical_rank=rank,

                lexical_score=(
                    float(
                        lexical_score
                    )
                ),
            )
        )


    return candidates