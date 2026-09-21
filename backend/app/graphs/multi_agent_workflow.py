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

from backend.app.agents.multi_agent import (
    CriticAgent,
    CriticReport,
    ResearcherAgent,
    ResearcherReport,
    SynthesizerAgent,
    SynthesizerReport,
    revise_query_after_critique,
)
from backend.app.agents.research_agent import (
    QueryAnalysis,
    analyze_research_query,
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
from backend.app.schemas.rag import (
    RAGAnswerResponse,
    RAGCitationResponse,
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
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
# Multi-Agent State
# ============================================================

class MultiAgentState(
    TypedDict,
    total=False,
):
    """
    Day37 Multi-Agent Workflow State。

    这里保存 Agent 之间真正需要共享的
    Structured State（结构化状态）。

    不让 Agent 通过自然语言随意互聊，
    而是通过 Report 对象交换信息。
    """

    # --------------------------------------------------------
    # User Input
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
    # Query
    # --------------------------------------------------------

    query_analysis: QueryAnalysis

    retrieval_query: str


    # --------------------------------------------------------
    # Research Cycle
    # --------------------------------------------------------

    research_cycle: int

    max_research_cycles: int


    # --------------------------------------------------------
    # Tool Budget
    # --------------------------------------------------------

    tool_call_count: int

    max_tool_calls: int


    # --------------------------------------------------------
    # Agent Reports
    # --------------------------------------------------------

    researcher_report: (
        ResearcherReport
    )

    critic_report: (
        CriticReport
    )

    synthesizer_report: (
        SynthesizerReport
    )


    # --------------------------------------------------------
    # Final Output
    # --------------------------------------------------------

    citations: list[
        RAGCitationResponse
    ]

    invalid_citations: list[str]

    grounded: bool

    answer: str


    # --------------------------------------------------------
    # Control
    # --------------------------------------------------------

    tool_feedback: str

    terminal_reason: Optional[str]


# ============================================================
# Request-Scoped Tool Registry
# ============================================================

def create_multi_agent_tool_registry(
    db: AsyncSession,
    document: PaperDocument,
    embedding_provider: EmbeddingProvider,
    use_reranker: bool,
) -> ToolRegistry:
    """
    创建当前 Request 的 Tool Registry。

    Day37 当前仍注册：
        local_document_search

    将来加入：
        Crossref
        arXiv
        OpenAlex

    不需要修改 Multi-Agent Graph。
    """

    registry = ToolRegistry()


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


    return registry


# ============================================================
# Graph Factory
# ============================================================

def create_multi_agent_workflow(
    db: AsyncSession,
    document: PaperDocument,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
    use_reranker: bool,
):
    """
    创建 Day37 Multi-Agent Research Workflow。

    Agents：

        Researcher
        Critic
        Synthesizer
    """

    # ========================================================
    # Tool Registry
    # ========================================================

    registry = (
        create_multi_agent_tool_registry(
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
    # Create Agents
    # ========================================================

    researcher = (
        ResearcherAgent(
            llm_provider=(
                llm_provider
            ),

            tool_registry=(
                registry
            ),
        )
    )


    critic = (
        CriticAgent(
            llm_provider=(
                llm_provider
            ),

            max_chunks=(
                settings
                .MULTI_AGENT_CRITIC_MAX_CHUNKS
            ),
        )
    )


    synthesizer = (
        SynthesizerAgent(
            llm_provider=(
                llm_provider
            ),

            max_context_chars=(
                settings
                .RAG_MAX_CONTEXT_CHARS
            ),
        )
    )


    # ========================================================
    # Node 1: Query Analysis
    # ========================================================

    async def analyze_query_node(
        state: MultiAgentState,
    ) -> dict:
        """
        使用 Day35 Query Analyzer。

        Multi-Agent 并不重新实现
        已经存在的能力。
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

            "research_cycle":
                0,

            "max_research_cycles":
                settings
                .MULTI_AGENT_MAX_RESEARCH_CYCLES,

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
    # Node 2: Researcher Agent
    # ========================================================

    async def researcher_node(
        state: MultiAgentState,
    ) -> dict:
        """
        Researcher：

            Select Tool
            ↓
            Execute Tool
            ↓
            Produce ResearcherReport
        """

        # ----------------------------------------------------
        # Tool Budget Guard
        # ----------------------------------------------------

        if (
            state[
                "tool_call_count"
            ]
            >= state[
                "max_tool_calls"
            ]
        ):

            return {
                "terminal_reason":
                    "tool_budget_exhausted",
            }


        # ----------------------------------------------------
        # Internal Search Candidate Count
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Run Researcher
        # ----------------------------------------------------

        report = (
            await researcher.research(
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

                top_k=(
                    internal_top_k
                ),

                tool_feedback=(
                    state.get(
                        "tool_feedback",
                        "(none)",
                    )
                ),
            )
        )


        next_cycle = (
            state[
                "research_cycle"
            ]
            + 1
        )


        tool_calls = (
            state[
                "tool_call_count"
            ]
        )


        if (
            report.tool_result
            is not None
        ):

            tool_calls += 1


        logger.info(
            (
                "Multi-Agent Researcher: "
                "document_id=%s "
                "cycle=%s "
                "tool=%s"
            ),
            document.id,
            next_cycle,
            (
                report.decision.tool_name
                or "none"
            ),
        )


        return {
            "researcher_report":
                report,

            "research_cycle":
                next_cycle,

            "tool_call_count":
                tool_calls,

            "terminal_reason":
                None,
        }


    # ========================================================
    # Router: After Researcher
    # ========================================================

    def route_after_researcher(
        state: MultiAgentState,
    ) -> str:
        """
        Researcher 正常：
            Critic

        Tool Budget exhausted：
            no_evidence

        Researcher 无 Tool / Tool Failed：
            retry 或 no_evidence
        """

        if (
            state.get(
                "terminal_reason"
            )
            == "tool_budget_exhausted"
        ):

            return "no_evidence"


        report = (
            state[
                "researcher_report"
            ]
        )


        result = (
            report.tool_result
        )


        if (
            result is not None
            and result.success
            and result.candidates
        ):

            return "critic"


        # ----------------------------------------------------
        # Researcher Failed
        # ----------------------------------------------------

        if (
            state[
                "research_cycle"
            ]
            <
            state[
                "max_research_cycles"
            ]
        ):

            return "revise_query"


        return "no_evidence"


    # ========================================================
    # Node 3: Critic Agent
    # ========================================================

    async def critic_node(
        state: MultiAgentState,
    ) -> dict:
        """
        Critic 只负责审查 Researcher Evidence。
        """

        report = (
            await critic.critique(
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

                researcher_report=(
                    state[
                        "researcher_report"
                    ]
                ),
            )
        )


        logger.info(
            (
                "Multi-Agent Critic: "
                "document_id=%s "
                "cycle=%s "
                "accepted=%s"
            ),
            document.id,
            state[
                "research_cycle"
            ],
            report.accepted,
        )


        return {
            "critic_report":
                report,

            "tool_feedback":
                report.reason,
        }


    # ========================================================
    # Router: After Critic
    # ========================================================

    def route_after_critic(
        state: MultiAgentState,
    ) -> str:
        """
        Accept：
            Synthesizer

        Reject + Budget：
            Revise Query

        Reject + No Budget：
            No Evidence
        """

        report = (
            state[
                "critic_report"
            ]
        )


        if report.accepted:

            return "synthesizer"


        if (
            state[
                "research_cycle"
            ]
            <
            state[
                "max_research_cycles"
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

            return "revise_query"


        return "no_evidence"


    # ========================================================
    # Node 4: Revise Query
    # ========================================================

    async def revise_query_node(
        state: MultiAgentState,
    ) -> dict:
        """
        根据 Critic Feedback
        改写下一轮 Research Query。
        """

        critic_report = (
            state.get(
                "critic_report"
            )
        )


        # ----------------------------------------------------
        # Researcher 在 Critic 前失败
        # ----------------------------------------------------

        if critic_report is None:

            researcher_report = (
                state[
                    "researcher_report"
                ]
            )


            reason = (
                researcher_report
                .tool_result
                .message

                if (
                    researcher_report.tool_result
                    is not None
                )

                else (
                    researcher_report
                    .decision
                    .reason
                )
            )


            critic_report = (
                CriticReport(
                    accepted=False,

                    reason=(
                        reason
                        or (
                            "Researcher did not "
                            "return usable evidence."
                        )
                    ),
                )
            )


        rewritten_query = (
            await revise_query_after_critique(
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

                critic_report=(
                    critic_report
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
                rewritten_query,

            "tool_feedback":
                critic_report.reason,

            # 清掉旧 Critic，
            # 避免下一轮误使用。
            "critic_report":
                None,
        }


    # ========================================================
    # Node 5: Synthesizer Agent
    # ========================================================

    async def synthesizer_node(
        state: MultiAgentState,
    ) -> dict:
        """
        Synthesizer 只能处理 Critic Accepted Evidence。
        """

        researcher_report = (
            state[
                "researcher_report"
            ]
        )


        tool_result = (
            researcher_report
            .tool_result
        )


        candidates = (
            tool_result.candidates
            if tool_result is not None
            else []
        )


        report = (
            await synthesizer.synthesize(
                question=(
                    state[
                        "question"
                    ]
                ),

                candidates=(
                    candidates
                ),

                top_k=(
                    state[
                        "top_k"
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
            "synthesizer_report":
                report,

            "answer":
                report.answer,
        }


    # ========================================================
    # Router: After Synthesizer
    # ========================================================

    def route_after_synthesizer(
        state: MultiAgentState,
    ) -> str:
        """
        Context + Generation 正常：
            Citation Validation

        Context 为空：
            No Evidence
        """

        report = (
            state[
                "synthesizer_report"
            ]
        )


        if (
            report.generation is None
            or report.rendered_prompts is None
            or not report.rag_context.sources
        ):

            return "no_evidence"


        return "validate_citations"


    # ========================================================
    # Node 6: Citation Validation
    # ========================================================

    async def validate_citations_node(
        state: MultiAgentState,
    ) -> dict:
        """
        验证 Synthesizer 输出中的 [Sx]。
        """

        report = (
            state[
                "synthesizer_report"
            ]
        )


        (
            used_sources,
            invalid_ids,
        ) = resolve_used_sources(
            answer=(
                report.answer
            ),

            available_sources=(
                report
                .rag_context
                .sources
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
    # Node 7: No Evidence
    # ========================================================

    async def no_evidence_node(
        state: MultiAgentState,
    ) -> dict:
        """
        Multi-Agent 无法获得
        Critic Accepted Evidence。
        """

        reason = (
            state.get(
                "terminal_reason"
            )
        )


        critic_report = (
            state.get(
                "critic_report"
            )
        )


        if critic_report is not None:

            reason = (
                critic_report.reason
            )


        return {
            "answer": (
                "The research agents could "
                "not collect sufficient "
                "evidence to answer this "
                "question reliably."
            ),

            "grounded":
                False,

            "citations":
                [],

            "invalid_citations":
                [],

            "terminal_reason": (
                reason
                or "insufficient_evidence"
            ),
        }


    # ========================================================
    # Build Graph
    # ========================================================

    workflow = (
        StateGraph(
            MultiAgentState
        )
    )


    # ========================================================
    # Register Nodes
    # ========================================================

    workflow.add_node(
        "analyze_query",
        analyze_query_node,
    )


    workflow.add_node(
        "researcher",
        researcher_node,
    )


    workflow.add_node(
        "critic",
        critic_node,
    )


    workflow.add_node(
        "revise_query",
        revise_query_node,
    )


    workflow.add_node(
        "synthesizer",
        synthesizer_node,
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
    # Entry
    # ========================================================

    workflow.add_edge(
        START,
        "analyze_query",
    )


    workflow.add_edge(
        "analyze_query",
        "researcher",
    )


    # ========================================================
    # Researcher Routing
    # ========================================================

    workflow.add_conditional_edges(
        "researcher",

        route_after_researcher,

        {
            "critic":
                "critic",

            "revise_query":
                "revise_query",

            "no_evidence":
                "no_evidence",
        },
    )


    # ========================================================
    # Critic Routing
    # ========================================================

    workflow.add_conditional_edges(
        "critic",

        route_after_critic,

        {
            "synthesizer":
                "synthesizer",

            "revise_query":
                "revise_query",

            "no_evidence":
                "no_evidence",
        },
    )


    # ========================================================
    # Research Loop
    # ========================================================

    workflow.add_edge(
        "revise_query",
        "researcher",
    )


    # ========================================================
    # Synthesizer Routing
    # ========================================================

    workflow.add_conditional_edges(
        "synthesizer",

        route_after_synthesizer,

        {
            "validate_citations":
                "validate_citations",

            "no_evidence":
                "no_evidence",
        },
    )


    # ========================================================
    # Terminal
    # ========================================================

    workflow.add_edge(
        "validate_citations",
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

async def run_multi_agent_workflow(
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
    执行 Day37 Multi-Agent Workflow。
    """

    normalized_question = (
        question.strip()
    )


    if not normalized_question:

        raise ValueError(
            "Question cannot be empty"
        )


    graph = (
        create_multi_agent_workflow(
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


    initial_state: MultiAgentState = {
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


    synthesizer_report = (
        final_state.get(
            "synthesizer_report"
        )
    )


    # ========================================================
    # Abstention Path
    # ========================================================

    if (
        synthesizer_report is None
        or synthesizer_report.generation
        is None
        or synthesizer_report.rendered_prompts
        is None
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
                            "The research agents "
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


    # ========================================================
    # Successful Synthesis
    # ========================================================

    generation = (
        synthesizer_report
        .generation
    )


    rendered = (
        synthesizer_report
        .rendered_prompts
    )


    rag_context = (
        synthesizer_report
        .rag_context
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
                synthesizer_report
                .answer
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