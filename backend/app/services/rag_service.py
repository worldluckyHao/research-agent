from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.core.config import (
    settings,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.graphs.multi_agent_workflow import (
    run_multi_agent_workflow,
)
from backend.app.graphs.rag_workflow import (
    run_rag_workflow,
)
from backend.app.graphs.research_agent_workflow import (
    run_research_agent_workflow,
)
from backend.app.graphs.tool_calling_workflow import (
    run_tool_calling_workflow,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.models.paper_document import (
    PaperDocument,
)
from backend.app.rag.citation import (
    resolve_used_sources,
)
from backend.app.rag.context import (
    build_rag_context,
)
from backend.app.rag.generation import (
    generate_rag_answer,
)
from backend.app.rag.prompting import (
    render_rag_prompts,
)
from backend.app.retrieval.base import (
    RetrievalCandidate,
)
from backend.app.schemas.rag import (
    RAGAnswerResponse,
    RAGCitationResponse,
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)
from backend.app.services.hybrid_retrieval import (
    hybrid_search_document,
)


# ============================================================
# Retrieval Conversion
# ============================================================

def _convert_retrieval_to_candidates(
    retrieval,
) -> list[
    RetrievalCandidate
]:
    """
    Hybrid Retrieval Response
    -> Internal RetrievalCandidate。
    """

    return [
        RetrievalCandidate(
            chunk_id=(
                item.chunk_id
            ),

            chunk_index=(
                item.chunk_index
            ),

            content=(
                item.content
            ),

            start_page=(
                item.start_page
            ),

            end_page=(
                item.end_page
            ),

            token_count=(
                item.token_count
            ),

            semantic_rank=(
                item.semantic_rank
            ),

            semantic_score=(
                item.semantic_score
            ),

            lexical_rank=(
                item.lexical_rank
            ),

            lexical_score=(
                item.lexical_score
            ),

            rrf_score=(
                item.rrf_score
            ),

            rerank_score=(
                item.rerank_score
            ),
        )

        for item
        in retrieval.items
    ]


# ============================================================
# Classic Service Workflow
# ============================================================

async def _answer_with_service_workflow(
    db: AsyncSession,
    document: PaperDocument,
    question: str,
    top_k: int,
    use_reranker: bool,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
    conversation_history: Optional[
        list[
            tuple[str, str]
        ]
    ] = None,
) -> RAGAnswerResponse:
    """
    Day30-Day33 Classic RAG Baseline。
    """

    normalized_question = (
        question.strip()
    )


    if not normalized_question:

        raise ValueError(
            "Question cannot be empty"
        )


    # ========================================================
    # Retrieval
    # ========================================================

    retrieval = (
        await hybrid_search_document(
            db=db,

            document=(
                document
            ),

            query=(
                normalized_question
            ),

            top_k=(
                top_k
            ),

            use_reranker=(
                use_reranker
            ),

            embedding_provider=(
                embedding_provider
            ),
        )
    )


    if not retrieval.items:

        return (
            RAGAnswerResponse(
                document_id=(
                    document.id
                ),

                question=(
                    normalized_question
                ),

                answer=(
                    "No relevant evidence was "
                    "found in the current document."
                ),

                grounded=False,

                retrieval_count=0,

                model=None,

                prompt=None,

                citations=[],

                invalid_citations=[],
            )
        )


    # ========================================================
    # Context
    # ========================================================

    candidates = (
        _convert_retrieval_to_candidates(
            retrieval
        )
    )


    rag_context = (
        build_rag_context(
            candidates=(
                candidates
            ),

            max_chars=(
                settings
                .RAG_MAX_CONTEXT_CHARS
            ),
        )
    )


    if not rag_context.sources:

        return (
            RAGAnswerResponse(
                document_id=(
                    document.id
                ),

                question=(
                    normalized_question
                ),

                answer=(
                    "No usable evidence was "
                    "available for this question."
                ),

                grounded=False,

                retrieval_count=0,

                model=None,

                prompt=None,

                citations=[],

                invalid_citations=[],
            )
        )


    # ========================================================
    # Prompt
    # ========================================================

    rendered = (
        render_rag_prompts(
            question=(
                normalized_question
            ),

            context=(
                rag_context.text
            ),

            conversation_history=(
                conversation_history
            ),
        )
    )


    # ========================================================
    # Generation
    # ========================================================

    generation = (
        await generate_rag_answer(
            llm_provider=(
                llm_provider
            ),

            system_prompt=(
                rendered.system_prompt
            ),

            user_prompt=(
                rendered.user_prompt
            ),
        )
    )


    answer = (
        generation
        .text
        .strip()
    )


    # ========================================================
    # Citation
    # ========================================================

    (
        used_sources,
        invalid_ids,
    ) = resolve_used_sources(
        answer=(
            answer
        ),

        available_sources=(
            rag_context.sources
        ),
    )


    citations = [
        RAGCitationResponse(
            source_id=(
                source.source_id
            ),

            chunk_id=(
                source.chunk_id
            ),

            chunk_index=(
                source.chunk_index
            ),

            start_page=(
                source.start_page
            ),

            end_page=(
                source.end_page
            ),
        )

        for source
        in used_sources
    ]


    grounded = (
        bool(
            citations
        )
        and not invalid_ids
    )


    # ========================================================
    # Response
    # ========================================================

    return (
        RAGAnswerResponse(
            document_id=(
                document.id
            ),

            question=(
                normalized_question
            ),

            answer=(
                answer
            ),

            grounded=(
                grounded
            ),

            retrieval_count=len(
                rag_context.sources
            ),

            model=(
                RAGModelInfoResponse(
                    provider=(
                        generation.provider
                    ),

                    model_name=(
                        generation.model_name
                    ),
                )
            ),

            prompt=(
                RAGPromptInfoResponse(
                    system_prompt_id=(
                        rendered
                        .system_prompt_id
                    ),

                    system_prompt_version=(
                        rendered
                        .system_prompt_version
                    ),

                    user_prompt_id=(
                        rendered
                        .user_prompt_id
                    ),

                    user_prompt_version=(
                        rendered
                        .user_prompt_version
                    ),
                )
            ),

            citations=(
                citations
            ),

            invalid_citations=(
                invalid_ids
            ),
        )
    )


# ============================================================
# Unified Public Entry
# ============================================================

async def answer_document_question(
    db: AsyncSession,
    document: PaperDocument,
    question: str,
    top_k: int,
    use_reranker: bool,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
    conversation_history: Optional[
        list[
            tuple[str, str]
        ]
    ] = None,
) -> RAGAnswerResponse:
    """
    Research-Agent Unified RAG Facade。

    Evolution：

        service
            Day30-Day33

        langgraph
            Day34

        agent
            Day35

        tool_agent
            Day36

        multi_agent
            Day37
    """

    workflow_engine = (
        settings
        .RAG_WORKFLOW_ENGINE
    )


    # ========================================================
    # Day30-Day33
    # ========================================================

    if workflow_engine == "service":

        return (
            await _answer_with_service_workflow(
                db=db,

                document=(
                    document
                ),

                question=(
                    question
                ),

                top_k=(
                    top_k
                ),

                use_reranker=(
                    use_reranker
                ),

                embedding_provider=(
                    embedding_provider
                ),

                llm_provider=(
                    llm_provider
                ),

                conversation_history=(
                    conversation_history
                ),
            )
        )


    # ========================================================
    # Day34
    # ========================================================

    if workflow_engine == "langgraph":

        return (
            await run_rag_workflow(
                db=db,

                document=(
                    document
                ),

                question=(
                    question
                ),

                top_k=(
                    top_k
                ),

                use_reranker=(
                    use_reranker
                ),

                embedding_provider=(
                    embedding_provider
                ),

                llm_provider=(
                    llm_provider
                ),

                conversation_history=(
                    conversation_history
                ),
            )
        )


    # ========================================================
    # Day35
    # ========================================================

    if workflow_engine == "agent":

        return (
            await run_research_agent_workflow(
                db=db,

                document=(
                    document
                ),

                question=(
                    question
                ),

                top_k=(
                    top_k
                ),

                use_reranker=(
                    use_reranker
                ),

                embedding_provider=(
                    embedding_provider
                ),

                llm_provider=(
                    llm_provider
                ),

                conversation_history=(
                    conversation_history
                ),
            )
        )


    # ========================================================
    # Day36
    # ========================================================

    if workflow_engine == "tool_agent":

        return (
            await run_tool_calling_workflow(
                db=db,

                document=(
                    document
                ),

                question=(
                    question
                ),

                top_k=(
                    top_k
                ),

                use_reranker=(
                    use_reranker
                ),

                embedding_provider=(
                    embedding_provider
                ),

                llm_provider=(
                    llm_provider
                ),

                conversation_history=(
                    conversation_history
                ),
            )
        )


    # ========================================================
    # Day37
    # ========================================================

    if workflow_engine == "multi_agent":

        return (
            await run_multi_agent_workflow(
                db=db,

                document=(
                    document
                ),

                question=(
                    question
                ),

                top_k=(
                    top_k
                ),

                use_reranker=(
                    use_reranker
                ),

                embedding_provider=(
                    embedding_provider
                ),

                llm_provider=(
                    llm_provider
                ),

                conversation_history=(
                    conversation_history
                ),
            )
        )


    raise RuntimeError(
        (
            "Unsupported RAG workflow "
            f"engine: {workflow_engine}"
        )
    )