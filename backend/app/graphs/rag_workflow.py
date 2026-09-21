from typing import (
    Optional,
    TypedDict,
)
from backend.app.core.config import (
    settings,
)
from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.chains.rag_generation import (
    RAGChainResult,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
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
    RAGContext,
    build_rag_context,
)
from backend.app.rag.generation import (
    generate_rag_answer,
)
from backend.app.rag.prompting import (
    RenderedRAGPrompts,
    render_rag_prompts,
)
from backend.app.retrieval.base import (
    RetrievalCandidate,
)
from backend.app.schemas.hybrid_search import (
    HybridSearchResponse,
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
# Graph State
# ============================================================

class RAGWorkflowState(
    TypedDict,
    total=False,
):
    """
    LangGraph RAG State（RAG工作流状态）。

    为什么使用 TypedDict？

    LangGraph 每个 Node：
        读取 State
        返回部分 State Update

    TypedDict 可以：
        1. 明确 State 有哪些字段
        2. 获得 IDE 类型提示
        3. 不需要创建复杂 ORM / Pydantic 对象

    total=False：
        表示每个字段都不是初始阶段必须存在。

    例如：
        刚进入 Graph 时还没有 generation。
    """

    # --------------------------------------------------------
    # Input
    # --------------------------------------------------------

    question: str

    top_k: int

    use_reranker: bool

    conversation_history: Optional[
        list[
            tuple[str, str]
        ]
    ]


    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    retrieval: HybridSearchResponse

    candidates: list[
        RetrievalCandidate
    ]


    # --------------------------------------------------------
    # Context
    # --------------------------------------------------------

    rag_context: RAGContext


    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    rendered_prompts: (
        RenderedRAGPrompts
    )


    # --------------------------------------------------------
    # Generation
    # --------------------------------------------------------

    generation: RAGChainResult

    answer: str


    # --------------------------------------------------------
    # Citation
    # --------------------------------------------------------

    citations: list[
        RAGCitationResponse
    ]

    invalid_citations: list[str]

    grounded: bool


    # --------------------------------------------------------
    # Terminal / Failure
    # --------------------------------------------------------

    terminal_reason: Optional[str]


# ============================================================
# Retrieval Item -> Candidate
# ============================================================

def _convert_retrieval_to_candidates(
    retrieval: HybridSearchResponse,
) -> list[
    RetrievalCandidate
]:
    """
    将 Hybrid Search API Item
    转成内部 RetrievalCandidate。

    Day35 以后可以进一步将 Hybrid Service
    拆成真正的 Domain Candidate API。

    Day34 暂时保持对 Day29 的兼容。
    """

    candidates = []


    for item in retrieval.items:

        candidates.append(
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
        )


    return candidates


# ============================================================
# Graph Factory
# ============================================================

def create_rag_workflow(
    db: AsyncSession,
    document: PaperDocument,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
):
    """
    创建一个绑定当前 Request Dependencies
    的 RAG StateGraph。

    为什么 db / provider 不直接放进 State？

    因为：

        AsyncSession
        LLMProvider
        EmbeddingProvider

    都属于 Runtime Dependency（运行时依赖），
    而不是业务 State。

    因此这里通过 Closure（闭包）
    提供给 Node。

    State 只保存真正的 RAG Workflow Data。
    """

    # ========================================================
    # Node 1: Retrieve
    # ========================================================

    async def retrieve_node(
        state: RAGWorkflowState,
    ) -> dict:
        """
        Hybrid Retrieval Node。

        Input：
            question
            top_k
            use_reranker

        Output：
            retrieval
            candidates
            terminal_reason
        """

        retrieval = (
            await hybrid_search_document(
                db=db,

                document=document,

                query=(
                    state["question"]
                ),

                top_k=(
                    state["top_k"]
                ),

                use_reranker=(
                    state[
                        "use_reranker"
                    ]
                ),

                embedding_provider=(
                    embedding_provider
                ),
            )
        )


        if not retrieval.items:

            return {
                "retrieval":
                    retrieval,

                "candidates":
                    [],

                "terminal_reason":
                    "no_retrieval_evidence",
            }


        candidates = (
            _convert_retrieval_to_candidates(
                retrieval
            )
        )


        return {
            "retrieval":
                retrieval,

            "candidates":
                candidates,

            "terminal_reason":
                None,
        }


    # ========================================================
    # Router 1: After Retrieval
    # ========================================================

    def route_after_retrieval(
        state: RAGWorkflowState,
    ) -> str:
        """
        Conditional Edge。

        如果没有 Retrieval Evidence：

            -> no_evidence

        否则：

            -> build_context
        """

        if (
            state.get(
                "terminal_reason"
            )
            == "no_retrieval_evidence"
        ):

            return "no_evidence"


        return "build_context"


    # ========================================================
    # Node 2: Build Context
    # ========================================================

    async def build_context_node(
        state: RAGWorkflowState,
    ) -> dict:
        """
        Evidence Context Construction Node。
        """

        rag_context = (
            build_rag_context(
                candidates=(
                    state[
                        "candidates"
                    ]
                ),

                max_chars=(
                    settings
                    .RAG_MAX_CONTEXT_CHARS
                ),
            )
        )


        if not rag_context.sources:

            return {
                "rag_context":
                    rag_context,

                "terminal_reason":
                    "no_usable_evidence",
            }


        return {
            "rag_context":
                rag_context,

            "terminal_reason":
                None,
        }


    # ========================================================
    # Router 2: After Context
    # ========================================================

    def route_after_context(
        state: RAGWorkflowState,
    ) -> str:
        """
        Context 构建失败：

            -> no_evidence

        正常：

            -> render_prompt
        """

        if (
            state.get(
                "terminal_reason"
            )
            == "no_usable_evidence"
        ):

            return "no_evidence"


        return "render_prompt"


    # ========================================================
    # Node 3: Render Prompt
    # ========================================================

    async def render_prompt_node(
        state: RAGWorkflowState,
    ) -> dict:
        """
        Prompt Management Node。

        使用 Day32 Prompt Registry。
        """

        rendered = (
            render_rag_prompts(
                question=(
                    state[
                        "question"
                    ]
                ),

                context=(
                    state[
                        "rag_context"
                    ].text
                ),

                conversation_history=(
                    state.get(
                        "conversation_history"
                    )
                ),
            )
        )


        return {
            "rendered_prompts":
                rendered,
        }


    # ========================================================
    # Node 4: Generate
    # ========================================================

    async def generate_node(
        state: RAGWorkflowState,
    ) -> dict:
        """
        LLM Generation Node。

        LangGraph 不关心底层：

            native
            或
            langchain

        由 Day33 Generation Router 决定。
        """

        prompts = (
            state[
                "rendered_prompts"
            ]
        )


        generation = (
            await generate_rag_answer(
                llm_provider=(
                    llm_provider
                ),

                system_prompt=(
                    prompts
                    .system_prompt
                ),

                user_prompt=(
                    prompts
                    .user_prompt
                ),
            )
        )


        return {
            "generation":
                generation,

            "answer":
                generation
                .text
                .strip(),
        }


    # ========================================================
    # Node 5: Citation Validation
    # ========================================================

    async def validate_citations_node(
        state: RAGWorkflowState,
    ) -> dict:
        """
        Citation Validation Node。

        LLM 输出：

            [S1]
            [S2]

        后端映射到：

            Chunk
            Page
        """

        (
            used_sources,
            invalid_ids,
        ) = resolve_used_sources(
            answer=(
                state["answer"]
            ),

            available_sources=(
                state[
                    "rag_context"
                ].sources
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


        return {
            "citations":
                citations,

            "invalid_citations":
                invalid_ids,

            "grounded":
                grounded,
        }


    # ========================================================
    # Node 6: No Evidence
    # ========================================================

    async def no_evidence_node(
        state: RAGWorkflowState,
    ) -> dict:
        """
        Abstention Node（拒答节点）。

        没有 Evidence 时：
            不调用 LLM。
        """

        reason = (
            state.get(
                "terminal_reason"
            )
        )


        if (
            reason
            == "no_usable_evidence"
        ):

            answer = (
                "No usable evidence was "
                "available for this question."
            )


        else:

            answer = (
                "No relevant evidence was "
                "found in the current document."
            )


        return {
            "answer":
                answer,

            "citations":
                [],

            "invalid_citations":
                [],

            "grounded":
                False,
        }


    # ========================================================
    # Build Graph
    # ========================================================

    workflow = StateGraph(
        RAGWorkflowState
    )


    # --------------------------------------------------------
    # Register Nodes
    # --------------------------------------------------------

    workflow.add_node(
        "retrieve",
        retrieve_node,
    )


    workflow.add_node(
        "build_context",
        build_context_node,
    )


    workflow.add_node(
        "render_prompt",
        render_prompt_node,
    )


    workflow.add_node(
        "generate",
        generate_node,
    )


    workflow.add_node(
        "validate_citations",
        validate_citations_node,
    )


    workflow.add_node(
        "no_evidence",
        no_evidence_node,
    )


    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    workflow.add_edge(
        START,
        "retrieve",
    )


    # --------------------------------------------------------
    # Retrieval Conditional Edge
    # --------------------------------------------------------

    workflow.add_conditional_edges(
        "retrieve",

        route_after_retrieval,

        {
            "build_context":
                "build_context",

            "no_evidence":
                "no_evidence",
        },
    )


    # --------------------------------------------------------
    # Context Conditional Edge
    # --------------------------------------------------------

    workflow.add_conditional_edges(
        "build_context",

        route_after_context,

        {
            "render_prompt":
                "render_prompt",

            "no_evidence":
                "no_evidence",
        },
    )


    # --------------------------------------------------------
    # Main Path
    # --------------------------------------------------------

    workflow.add_edge(
        "render_prompt",
        "generate",
    )


    workflow.add_edge(
        "generate",
        "validate_citations",
    )


    workflow.add_edge(
        "validate_citations",
        END,
    )


    # --------------------------------------------------------
    # Early Exit
    # --------------------------------------------------------

    workflow.add_edge(
        "no_evidence",
        END,
    )


    # ========================================================
    # Compile
    # ========================================================

    return workflow.compile()


# ============================================================
# Workflow Runner
# ============================================================

async def run_rag_workflow(
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
    执行完整 LangGraph RAG Workflow。
    """

    normalized_question = (
        question.strip()
    )


    if not normalized_question:

        raise ValueError(
            "Question cannot be empty"
        )


    graph = (
        create_rag_workflow(
            db=db,

            document=document,

            embedding_provider=(
                embedding_provider
            ),

            llm_provider=(
                llm_provider
            ),
        )
    )


    # ========================================================
    # Initial State
    # ========================================================

    initial_state: RAGWorkflowState = {
        "question":
            normalized_question,

        "top_k":
            top_k,

        "use_reranker":
            use_reranker,

        "conversation_history":
            conversation_history,
    }


    # ========================================================
    # Execute Graph
    # ========================================================

    final_state = (
        await graph.ainvoke(
            initial_state
        )
    )


    # ========================================================
    # Early Exit Response
    # ========================================================

    generation = (
        final_state.get(
            "generation"
        )
    )


    rendered_prompts = (
        final_state.get(
            "rendered_prompts"
        )
    )


    # 没有 Generation：
    #
    # 表示 Graph 在 no_evidence
    # Node 提前结束。
    if generation is None:

        return (
            RAGAnswerResponse(
                document_id=(
                    document.id
                ),

                question=(
                    normalized_question
                ),

                answer=(
                    final_state[
                        "answer"
                    ]
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
    # Normal Response
    # ========================================================

    rag_context = (
        final_state[
            "rag_context"
        ]
    )


    return (
        RAGAnswerResponse(
            document_id=(
                document.id
            ),

            question=(
                normalized_question
            ),

            answer=(
                final_state[
                    "answer"
                ]
            ),

            grounded=(
                final_state.get(
                    "grounded",
                    False,
                )
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
                        rendered_prompts
                        .system_prompt_id
                    ),

                    system_prompt_version=(
                        rendered_prompts
                        .system_prompt_version
                    ),

                    user_prompt_id=(
                        rendered_prompts
                        .user_prompt_id
                    ),

                    user_prompt_version=(
                        rendered_prompts
                        .user_prompt_version
                    ),
                )
            ),

            citations=(
                final_state.get(
                    "citations",
                    [],
                )
            ),

            invalid_citations=(
                final_state.get(
                    "invalid_citations",
                    [],
                )
            ),
        )
    )