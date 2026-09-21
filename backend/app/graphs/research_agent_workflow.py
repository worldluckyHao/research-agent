import logging
from typing import (
    Optional,
    TypedDict,
)

from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.agents.research_agent import (
    EvidenceEvaluation,
    QueryAnalysis,
    analyze_research_query,
    evaluate_research_evidence,
    rewrite_research_query,
)
from backend.app.chains.rag_generation import (
    RAGChainResult,
)
from backend.app.core.config import (
    settings,
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


logger = logging.getLogger(
    __name__
)


# ============================================================
# Agent State
# ============================================================

class ResearchAgentState(
    TypedDict,
    total=False,
):
    """
    Research Agent State（科研智能体状态）。

    State 分成几个区域：

    1. User Input
    2. Query Understanding
    3. Retrieval Planning
    4. Retrieval Result
    5. Evidence Evaluation
    6. Final RAG Generation
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
    # Query Analysis
    # --------------------------------------------------------

    query_analysis: QueryAnalysis


    # --------------------------------------------------------
    # Retrieval Plan
    # --------------------------------------------------------

    retrieval_query: str

    retrieval_top_k: int

    retrieval_attempt: int

    max_retrieval_attempts: int


    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    retrieval: HybridSearchResponse

    candidates: list[
        RetrievalCandidate
    ]


    # --------------------------------------------------------
    # Evidence Evaluation
    # --------------------------------------------------------

    evidence_evaluation: (
        EvidenceEvaluation
    )


    # --------------------------------------------------------
    # RAG Context
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
    # Terminal
    # --------------------------------------------------------

    terminal_reason: Optional[str]


# ============================================================
# Retrieval Conversion
# ============================================================

def _convert_retrieval_to_candidates(
    retrieval: HybridSearchResponse,
) -> list[
    RetrievalCandidate
]:
    """
    Hybrid Search Response
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
# Graph Factory
# ============================================================

def create_research_agent_workflow(
    db: AsyncSession,
    document: PaperDocument,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
):
    """
    创建 Day35 Research Agent Graph。

    Runtime Dependencies：

        db
        document
        embedding_provider
        llm_provider

    通过 Closure 提供给 Nodes。

    不将这些连接/Provider 对象
    放进 Graph State。
    """


    # ========================================================
    # Node 1: Analyze Query
    # ========================================================

    async def analyze_query_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        分析当前问题。

        Output：
            query_analysis
        """

        analysis = (
            await analyze_research_query(
                llm_provider=(
                    llm_provider
                ),

                question=(
                    state[
                        "question"
                    ]
                ),

                conversation_history=(
                    state.get(
                        "conversation_history"
                    )
                ),
            )
        )


        return {
            "query_analysis":
                analysis,
        }


    # ========================================================
    # Node 2: Plan Retrieval
    # ========================================================

    async def plan_retrieval_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        构建初始 Retrieval Plan。

        Day35 当前规划内容：

            retrieval_query
            retrieval_top_k
            attempt
            max_attempts

        后续可以继续加入：

            provider selection
            lexical/semantic weight
            paper scope
            tool selection
        """

        analysis = (
            state[
                "query_analysis"
            ]
        )


        retrieval_query = (
            analysis
            .standalone_query
            .strip()
        )


        if not retrieval_query:

            retrieval_query = (
                state[
                    "question"
                ]
            )


        # ----------------------------------------------------
        # Candidate Planning
        # ----------------------------------------------------
        #
        # Agent 内部可以拿比用户 final top_k
        # 更多的候选用于 Evidence Evaluation。
        retrieval_top_k = min(
            max(
                state[
                    "top_k"
                ],

                settings
                .RESEARCH_AGENT_RETRIEVAL_TOP_K,
            ),

            settings
            .RAG_MAX_TOP_K,
        )


        return {
            "retrieval_query":
                retrieval_query,

            "retrieval_top_k":
                retrieval_top_k,

            # 第一次 Retrieval。
            "retrieval_attempt":
                1,

            "max_retrieval_attempts":
                settings
                .RESEARCH_AGENT_MAX_RETRIEVAL_ATTEMPTS,

            "terminal_reason":
                None,
        }


    # ========================================================
    # Node 3: Retrieve
    # ========================================================

    async def retrieve_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        执行 Hybrid Retrieval。
        """

        logger.info(
            (
                "Research Agent retrieval: "
                "document_id=%s attempt=%s"
            ),
            document.id,
            state[
                "retrieval_attempt"
            ],
        )


        retrieval = (
            await hybrid_search_document(
                db=db,

                document=document,

                query=(
                    state[
                        "retrieval_query"
                    ]
                ),

                top_k=(
                    state[
                        "retrieval_top_k"
                    ]
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
        }


    # ========================================================
    # Node 4: Evaluate Evidence
    # ========================================================

    async def evaluate_evidence_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        判断当前 Retrieval 是否已经足够。

        这是 Day35 Agentic RAG
        最核心的新节点之一。
        """

        evaluation = (
            await evaluate_research_evidence(
                llm_provider=(
                    llm_provider
                ),

                question=(
                    state[
                        "question"
                    ]
                ),

                retrieval_query=(
                    state[
                        "retrieval_query"
                    ]
                ),

                retrieval=(
                    state[
                        "retrieval"
                    ]
                ),

                max_chunks=(
                    settings
                    .RESEARCH_AGENT_EVALUATION_MAX_CHUNKS
                ),
            )
        )


        logger.info(
            (
                "Research Agent evidence "
                "evaluation: "
                "document_id=%s "
                "attempt=%s "
                "sufficient=%s"
            ),
            document.id,
            state[
                "retrieval_attempt"
            ],
            evaluation.sufficient,
        )


        return {
            "evidence_evaluation":
                evaluation,
        }


    # ========================================================
    # Router: After Evidence Evaluation
    # ========================================================

    def route_after_evaluation(
        state: ResearchAgentState,
    ) -> str:
        """
        Evidence 足够：
            build_context

        Evidence 不够但还有预算：
            rewrite_query

        Evidence 不够且预算耗尽：
            no_evidence
        """

        evaluation = (
            state[
                "evidence_evaluation"
            ]
        )


        if evaluation.sufficient:

            return "build_context"


        current_attempt = (
            state[
                "retrieval_attempt"
            ]
        )


        max_attempts = (
            state[
                "max_retrieval_attempts"
            ]
        )


        if (
            current_attempt
            < max_attempts
        ):

            return "rewrite_query"


        return "no_evidence"


    # ========================================================
    # Node 5: Rewrite Query
    # ========================================================

    async def rewrite_query_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        Evidence 不足时，
        自动改写 Retrieval Query。

        完成后重新进入 retrieve，
        形成 Agent Loop。
        """

        evaluation = (
            state[
                "evidence_evaluation"
            ]
        )


        rewritten_query = (
            await rewrite_research_query(
                llm_provider=(
                    llm_provider
                ),

                question=(
                    state[
                        "question"
                    ]
                ),

                retrieval_query=(
                    state[
                        "retrieval_query"
                    ]
                ),

                evaluation_reason=(
                    evaluation.reason
                ),

                conversation_history=(
                    state.get(
                        "conversation_history"
                    )
                ),
            )
        )


        next_attempt = (
            state[
                "retrieval_attempt"
            ]
            + 1
        )


        return {
            "retrieval_query":
                rewritten_query,

            "retrieval_attempt":
                next_attempt,
        }


    # ========================================================
    # Node 6: Build Context
    # ========================================================

    async def build_context_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        将 Agent Retrieval Candidate
        转换成最终 RAG Context。

        注意：

        Agent Retrieval 可以内部取 8 条，

        但最终 Context 尊重用户请求的
        top_k。

        Example：

            internal retrieval = 8
            user top_k = 5

            final context = first 5
        """

        final_candidates = (
            state[
                "candidates"
            ][
                :state["top_k"]
            ]
        )


        rag_context = (
            build_rag_context(
                candidates=(
                    final_candidates
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
    # Router: After Context
    # ========================================================

    def route_after_context(
        state: ResearchAgentState,
    ) -> str:
        """
        Context 正常：
            render_prompt

        Context 为空：
            no_evidence
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
    # Node 7: Render Prompt
    # ========================================================

    async def render_prompt_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        最终 Answer Prompt。

        注意：

        Agent Analysis Prompt
        !=
        Final Answer Prompt

        最终回答仍使用 Day32
        Citation-Aware RAG Prompt。
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
    # Node 8: Generate
    # ========================================================

    async def generate_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        最终 Answer Generation。
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
    # Node 9: Validate Citations
    # ========================================================

    async def validate_citations_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        校验 [S1] / [S2] Citation。
        """

        (
            used_sources,
            invalid_ids,
        ) = resolve_used_sources(
            answer=(
                state[
                    "answer"
                ]
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
    # Node 10: No Evidence
    # ========================================================

    async def no_evidence_node(
        state: ResearchAgentState,
    ) -> dict:
        """
        Agent 已经无法获得足够 Evidence。

        不再继续调用最终 Answer Generator。
        """

        evaluation = (
            state.get(
                "evidence_evaluation"
            )
        )


        if evaluation is not None:

            reason = (
                evaluation.reason
            )

        else:

            reason = (
                "No usable evidence "
                "was available."
            )


        return {
            "answer": (
                "The available evidence in "
                "the current document is "
                "insufficient to answer "
                "this question reliably."
            ),

            "grounded":
                False,

            "citations":
                [],

            "invalid_citations":
                [],

            "terminal_reason": (
                "insufficient_evidence: "
                f"{reason}"
            ),
        }


    # ========================================================
    # Build StateGraph
    # ========================================================

    workflow = StateGraph(
        ResearchAgentState
    )


    # --------------------------------------------------------
    # Nodes
    # --------------------------------------------------------

    workflow.add_node(
        "analyze_query",
        analyze_query_node,
    )


    workflow.add_node(
        "plan_retrieval",
        plan_retrieval_node,
    )


    workflow.add_node(
        "retrieve",
        retrieve_node,
    )


    workflow.add_node(
        "evaluate_evidence",
        evaluate_evidence_node,
    )


    workflow.add_node(
        "rewrite_query",
        rewrite_query_node,
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


    # ========================================================
    # Edges
    # ========================================================

    workflow.add_edge(
        START,
        "analyze_query",
    )


    workflow.add_edge(
        "analyze_query",
        "plan_retrieval",
    )


    workflow.add_edge(
        "plan_retrieval",
        "retrieve",
    )


    workflow.add_edge(
        "retrieve",
        "evaluate_evidence",
    )


    # --------------------------------------------------------
    # Evidence Decision
    # --------------------------------------------------------

    workflow.add_conditional_edges(
        "evaluate_evidence",

        route_after_evaluation,

        {
            "build_context":
                "build_context",

            "rewrite_query":
                "rewrite_query",

            "no_evidence":
                "no_evidence",
        },
    )


    # --------------------------------------------------------
    # Retry Loop
    # --------------------------------------------------------

    workflow.add_edge(
        "rewrite_query",
        "retrieve",
    )


    # --------------------------------------------------------
    # Context Decision
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
    # Final Answer Path
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
    # Abstention Path
    # --------------------------------------------------------

    workflow.add_edge(
        "no_evidence",
        END,
    )


    return (
        workflow.compile()
    )


# ============================================================
# Run Research Agent
# ============================================================

async def run_research_agent_workflow(
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
    执行 Day35 Research Agent Workflow。
    """

    normalized_question = (
        question.strip()
    )


    if not normalized_question:

        raise ValueError(
            "Question cannot be empty"
        )


    graph = (
        create_research_agent_workflow(
            db=db,

            document=(
                document
            ),

            embedding_provider=(
                embedding_provider
            ),

            llm_provider=(
                llm_provider
            ),
        )
    )


    initial_state: ResearchAgentState = {
        "question":
            normalized_question,

        "top_k":
            top_k,

        "use_reranker":
            use_reranker,

        "conversation_history":
            conversation_history,
    }


    final_state = (
        await graph.ainvoke(
            initial_state
        )
    )


    # ========================================================
    # Abstention Result
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


    if (
        generation is None
        or rendered_prompts is None
    ):

        return (
            RAGAnswerResponse(
                document_id=(
                    document.id
                ),

                question=(
                    normalized_question
                ),

                answer=(
                    final_state.get(
                        "answer",
                        (
                            "The available evidence "
                            "is insufficient."
                        ),
                    )
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
    # Normal Result
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