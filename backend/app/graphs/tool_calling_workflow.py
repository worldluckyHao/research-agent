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
from backend.app.agents.tool_calling import (
    ToolCallDecision,
    select_research_tool,
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
from backend.app.tools.base import (
    ToolResult,
)
from backend.app.tools.local_document import (
    LocalDocumentSearchTool,
)
from backend.app.tools.registry import (
    ToolRegistry,
)


logger = logging.getLogger(
    __name__
)


# ============================================================
# Tool Agent State
# ============================================================

class ToolCallingAgentState(
    TypedDict,
    total=False,
):
    """
    Day36 Tool Calling Agent State。
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
    # Query Understanding
    # --------------------------------------------------------

    query_analysis: QueryAnalysis

    retrieval_query: str


    # --------------------------------------------------------
    # Tool Calling
    # --------------------------------------------------------

    tool_decision: ToolCallDecision

    tool_result: ToolResult

    tool_call_count: int

    max_tool_calls: int

    tool_feedback: str


    # --------------------------------------------------------
    # Retrieval / Evidence
    # --------------------------------------------------------

    candidates: list[
        RetrievalCandidate
    ]

    retrieval: HybridSearchResponse

    evidence_evaluation: (
        EvidenceEvaluation
    )

    retrieval_attempt: int

    max_retrieval_attempts: int


    # --------------------------------------------------------
    # Final RAG
    # --------------------------------------------------------

    rag_context: RAGContext

    rendered_prompts: (
        RenderedRAGPrompts
    )

    generation: RAGChainResult

    answer: str

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
# Tool Registry Factory
# ============================================================

def create_tool_registry(
    db: AsyncSession,
    document: PaperDocument,
    embedding_provider: EmbeddingProvider,
    use_reranker: bool,
) -> ToolRegistry:
    """
    为当前 Request 创建 Tool Registry。

    重要：

    Registry 是 Request-Scoped。

    因为 Tool 持有：
        AsyncSession
        当前 Document
        Provider
    """

    registry = (
        ToolRegistry()
    )


    registry.register(
        LocalDocumentSearchTool(
            db=(
                db
            ),

            document=(
                document
            ),

            embedding_provider=(
                embedding_provider
            ),

            use_reranker=(
                use_reranker
            ),
        )
    )


    # ========================================================
    # Future External Tools
    # ========================================================
    #
    # Day16-Day19 已经存在：
    #   Crossref
    #   arXiv
    #   OpenAlex
    #
    # 后续只需要：
    #
    # registry.register(
    #     CrossrefSearchTool(...)
    # )
    #
    # registry.register(
    #     ArxivSearchTool(...)
    # )
    #
    # registry.register(
    #     OpenAlexSearchTool(...)
    # )
    #
    # Agent Graph 本身无需修改。


    return registry


# ============================================================
# Workflow Factory
# ============================================================

def create_tool_calling_workflow(
    db: AsyncSession,
    document: PaperDocument,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
    use_reranker: bool,
):
    """
    创建 Day36 Tool Calling Research Agent。
    """

    registry = (
        create_tool_registry(
            db=db,

            document=(
                document
            ),

            embedding_provider=(
                embedding_provider
            ),

            use_reranker=(
                use_reranker
            ),
        )
    )


    # ========================================================
    # Node 1: Analyze Query
    # ========================================================

    async def analyze_query_node(
        state: ToolCallingAgentState,
    ) -> dict:

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


        return {
            "query_analysis":
                analysis,

            "retrieval_query":
                retrieval_query,

            "retrieval_attempt":
                1,

            "max_retrieval_attempts":
                settings
                .RESEARCH_AGENT_MAX_RETRIEVAL_ATTEMPTS,

            "tool_call_count":
                0,

            "max_tool_calls":
                settings
                .RESEARCH_AGENT_MAX_TOOL_CALLS,

            "tool_feedback":
                "(none)",

            "terminal_reason":
                None,
        }


    # ========================================================
    # Node 2: Select Tool
    # ========================================================

    async def select_tool_node(
        state: ToolCallingAgentState,
    ) -> dict:
        """
        Agent 根据：

            Question
            Query
            Tool Catalog
            Previous Feedback

        选择 Tool。
        """

        decision = (
            await select_research_tool(
                llm_provider=(
                    llm_provider
                ),

                registry=(
                    registry
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

                tool_feedback=(
                    state.get(
                        "tool_feedback",
                        "(none)",
                    )
                ),
            )
        )


        return {
            "tool_decision":
                decision,
        }


    # ========================================================
    # Router: Tool Selection
    # ========================================================

    def route_after_tool_selection(
        state: ToolCallingAgentState,
    ) -> str:

        decision = (
            state[
                "tool_decision"
            ]
        )


        if (
            decision.action
            != "call_tool"
            or not decision.tool_name
        ):

            return "no_tool"


        if (
            state[
                "tool_call_count"
            ]
            >= state[
                "max_tool_calls"
            ]
        ):

            return "tool_budget_exhausted"


        return "execute_tool"


    # ========================================================
    # Node 3: Execute Tool
    # ========================================================

    async def execute_tool_node(
        state: ToolCallingAgentState,
    ) -> dict:
        """
        真正执行 Tool。

        注意：

        LLM 不执行 Tool。

        Python Application 才执行 Tool。
        """

        decision = (
            state[
                "tool_decision"
            ]
        )


        # 再进行一次 Registry 校验。
        tool = registry.get(
            decision.tool_name
        )


        internal_top_k = min(
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


        result = (
            await tool.execute(
                query=(
                    decision.query
                ),

                top_k=(
                    internal_top_k
                ),
            )
        )


        next_count = (
            state[
                "tool_call_count"
            ]
            + 1
        )


        logger.info(
            (
                "Research Agent tool call: "
                "document_id=%s "
                "tool=%s "
                "call=%s"
            ),
            document.id,
            tool.name,
            next_count,
        )


        update = {
            "tool_result":
                result,

            "tool_call_count":
                next_count,

            "candidates":
                result.candidates,
        }


        retrieval = (
            result.metadata.get(
                "retrieval_response"
            )
        )


        if retrieval is not None:

            update[
                "retrieval"
            ] = retrieval


        return update


    # ========================================================
    # Router: Tool Result
    # ========================================================

    def route_after_tool_execution(
        state: ToolCallingAgentState,
    ) -> str:
        """
        当前 Local Search Tool
        返回 Retrieval Evidence。

        如果以后加入非 Retrieval Tool，
        这里可以继续根据 Tool Result Type
        进行路由。
        """

        result = (
            state[
                "tool_result"
            ]
        )


        if (
            not result.success
            or not result.candidates
        ):

            if (
                state[
                    "tool_call_count"
                ]
                < state[
                    "max_tool_calls"
                ]
            ):

                return "rewrite_query"


            return "no_evidence"


        return "evaluate_evidence"


    # ========================================================
    # Node 4: Evidence Evaluation
    # ========================================================

    async def evaluate_evidence_node(
        state: ToolCallingAgentState,
    ) -> dict:

        retrieval = (
            state.get(
                "retrieval"
            )
        )


        if retrieval is None:

            return {
                "evidence_evaluation":
                    EvidenceEvaluation(
                        sufficient=False,

                        reason=(
                            "The selected tool did not "
                            "return retrieval evidence."
                        ),
                    ),
            }


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
                    retrieval
                ),

                max_chunks=(
                    settings
                    .RESEARCH_AGENT_EVALUATION_MAX_CHUNKS
                ),
            )
        )


        return {
            "evidence_evaluation":
                evaluation,
        }


    # ========================================================
    # Router: Evidence
    # ========================================================

    def route_after_evaluation(
        state: ToolCallingAgentState,
    ) -> str:

        evaluation = (
            state[
                "evidence_evaluation"
            ]
        )


        if evaluation.sufficient:

            return "build_context"


        if (
            state[
                "retrieval_attempt"
            ]
            <
            state[
                "max_retrieval_attempts"
            ]
            and
            state[
                "tool_call_count"
            ]
            <
            state[
                "max_tool_calls"
            ]
        ):

            return "rewrite_query"


        return "no_evidence"


    # ========================================================
    # Node 5: Rewrite Query
    # ========================================================

    async def rewrite_query_node(
        state: ToolCallingAgentState,
    ) -> dict:

        evaluation = (
            state.get(
                "evidence_evaluation"
            )
        )


        reason = (
            evaluation.reason

            if evaluation
            is not None

            else (
                state[
                    "tool_result"
                ].message
                if state.get(
                    "tool_result"
                )
                else "Tool did not return usable evidence."
            )
        )


        rewritten = (
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
                    reason
                ),

                conversation_history=(
                    state.get(
                        "conversation_history"
                    )
                ),
            )
        )


        return {
            "retrieval_query":
                rewritten,

            "retrieval_attempt": (
                state[
                    "retrieval_attempt"
                ]
                + 1
            ),

            "tool_feedback":
                reason,
        }


    # ========================================================
    # Node 6: Build Context
    # ========================================================

    async def build_context_node(
        state: ToolCallingAgentState,
    ) -> dict:

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
                    "no_usable_context",
            }


        return {
            "rag_context":
                rag_context,

            "terminal_reason":
                None,
        }


    # ========================================================
    # Router: Context
    # ========================================================

    def route_after_context(
        state: ToolCallingAgentState,
    ) -> str:

        if not state[
            "rag_context"
        ].sources:

            return "no_evidence"


        return "render_prompt"


    # ========================================================
    # Node 7: Render Final Prompt
    # ========================================================

    async def render_prompt_node(
        state: ToolCallingAgentState,
    ) -> dict:

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
        state: ToolCallingAgentState,
    ) -> dict:

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
    # Node 9: Citation Validation
    # ========================================================

    async def validate_citations_node(
        state: ToolCallingAgentState,
    ) -> dict:

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


        return {
            "citations":
                citations,

            "invalid_citations":
                invalid_ids,

            "grounded": (
                bool(
                    citations
                )
                and not invalid_ids
            ),
        }


    # ========================================================
    # Terminal Nodes
    # ========================================================

    async def no_tool_node(
        state: ToolCallingAgentState,
    ) -> dict:

        return {
            "answer": (
                "No available research tool "
                "can reliably answer this question."
            ),

            "grounded":
                False,

            "citations":
                [],

            "invalid_citations":
                [],

            "terminal_reason":
                "no_suitable_tool",
        }


    async def tool_budget_exhausted_node(
        state: ToolCallingAgentState,
    ) -> dict:

        return {
            "answer": (
                "The research tool budget "
                "was exhausted before enough "
                "evidence could be collected."
            ),

            "grounded":
                False,

            "citations":
                [],

            "invalid_citations":
                [],

            "terminal_reason":
                "tool_budget_exhausted",
        }


    async def no_evidence_node(
        state: ToolCallingAgentState,
    ) -> dict:

        return {
            "answer": (
                "The available evidence is "
                "insufficient to answer this "
                "question reliably."
            ),

            "grounded":
                False,

            "citations":
                [],

            "invalid_citations":
                [],

            "terminal_reason":
                "insufficient_evidence",
        }


    # ========================================================
    # Build Graph
    # ========================================================

    workflow = (
        StateGraph(
            ToolCallingAgentState
        )
    )


    # ========================================================
    # Nodes
    # ========================================================

    workflow.add_node(
        "analyze_query",
        analyze_query_node,
    )

    workflow.add_node(
        "select_tool",
        select_tool_node,
    )

    workflow.add_node(
        "execute_tool",
        execute_tool_node,
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
        "no_tool",
        no_tool_node,
    )

    workflow.add_node(
        "tool_budget_exhausted",
        tool_budget_exhausted_node,
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
        "select_tool",
    )


    # --------------------------------------------------------
    # Tool Selection Routing
    # --------------------------------------------------------

    workflow.add_conditional_edges(
        "select_tool",

        route_after_tool_selection,

        {
            "execute_tool":
                "execute_tool",

            "no_tool":
                "no_tool",

            "tool_budget_exhausted":
                "tool_budget_exhausted",
        },
    )


    # --------------------------------------------------------
    # Tool Result Routing
    # --------------------------------------------------------

    workflow.add_conditional_edges(
        "execute_tool",

        route_after_tool_execution,

        {
            "evaluate_evidence":
                "evaluate_evidence",

            "rewrite_query":
                "rewrite_query",

            "no_evidence":
                "no_evidence",
        },
    )


    # --------------------------------------------------------
    # Evidence Routing
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
    # Tool Loop
    # --------------------------------------------------------

    workflow.add_edge(
        "rewrite_query",
        "select_tool",
    )


    # --------------------------------------------------------
    # Context
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
    # Generation
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
    # Terminal
    # --------------------------------------------------------

    workflow.add_edge(
        "no_tool",
        END,
    )

    workflow.add_edge(
        "tool_budget_exhausted",
        END,
    )

    workflow.add_edge(
        "no_evidence",
        END,
    )


    return (
        workflow.compile()
    )


# ============================================================
# Runner
# ============================================================

async def run_tool_calling_workflow(
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
    执行 Day36 Tool Calling Agent。
    """

    normalized_question = (
        question.strip()
    )


    if not normalized_question:

        raise ValueError(
            "Question cannot be empty"
        )


    graph = (
        create_tool_calling_workflow(
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

            use_reranker=(
                use_reranker
            ),
        )
    )


    initial_state: (
        ToolCallingAgentState
    ) = {
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


    generation = (
        final_state.get(
            "generation"
        )
    )


    rendered = (
        final_state.get(
            "rendered_prompts"
        )
    )


    # ========================================================
    # Terminal without Final Generation
    # ========================================================

    if (
        generation is None
        or rendered is None
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
                            "The research agent "
                            "could not produce "
                            "a grounded answer."
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


    rag_context = (
        final_state[
            "rag_context"
        ]
    )


    # ========================================================
    # Normal Final Response
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