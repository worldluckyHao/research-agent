from dataclasses import dataclass
from typing import (
    Optional,
)

from backend.app.agents.research_agent import (
    EvidenceEvaluation,
    evaluate_research_evidence,
    rewrite_research_query,
)
from backend.app.agents.tool_calling import (
    ToolCallDecision,
    select_research_tool,
)
from backend.app.llms.base import (
    LLMProvider,
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
from backend.app.chains.rag_generation import (
    RAGChainResult,
)
from backend.app.schemas.hybrid_search import (
    HybridSearchResponse,
)
from backend.app.tools.base import (
    ToolResult,
)
from backend.app.tools.registry import (
    ToolRegistry,
)


# ============================================================
# Researcher Report
# ============================================================

@dataclass(frozen=True)
class ResearcherReport:
    """
    Researcher Agent（研究员智能体）
    的结构化输出。

    Researcher 只负责：

        Tool Selection
        +
        Tool Execution

    不负责判断 Evidence 是否足够。
    """

    decision: ToolCallDecision

    tool_result: Optional[
        ToolResult
    ]


# ============================================================
# Critic Report
# ============================================================

@dataclass(frozen=True)
class CriticReport:
    """
    Critic Agent（审查智能体）
    的输出。

    accepted:
        当前 Evidence 是否允许进入最终生成。

    reason:
        为什么接受 / 拒绝。
    """

    accepted: bool

    reason: str


# ============================================================
# Synthesizer Report
# ============================================================

@dataclass(frozen=True)
class SynthesizerReport:
    """
    Synthesizer Agent（综合智能体）
    输出。

    如果 Context 无法构建：

        generation=None
        rendered_prompts=None
    """

    rag_context: RAGContext

    rendered_prompts: Optional[
        RenderedRAGPrompts
    ]

    generation: Optional[
        RAGChainResult
    ]

    answer: str


# ============================================================
# Researcher Agent
# ============================================================

class ResearcherAgent:
    """
    Researcher Agent（研究员智能体）。

    Responsibility（职责）：

        1. 阅读当前 Research Query
        2. 从 Tool Registry 选择 Tool
        3. 执行 Tool
        4. 返回 Evidence

    它不负责：

        Evidence 是否可信
        最终 Answer
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
    ):
        self.llm_provider = (
            llm_provider
        )

        self.tool_registry = (
            tool_registry
        )


    async def research(
        self,
        question: str,
        retrieval_query: str,
        top_k: int,
        tool_feedback: str = "(none)",
    ) -> ResearcherReport:
        """
        执行一次 Research Cycle。
        """

        # ====================================================
        # 1. Select Tool
        # ====================================================

        decision = (
            await select_research_tool(
                llm_provider=(
                    self.llm_provider
                ),

                registry=(
                    self.tool_registry
                ),

                question=(
                    question
                ),

                retrieval_query=(
                    retrieval_query
                ),

                tool_feedback=(
                    tool_feedback
                ),
            )
        )


        # ====================================================
        # 2. No Tool
        # ====================================================

        if (
            decision.action
            != "call_tool"
            or not decision.tool_name
        ):

            return ResearcherReport(
                decision=(
                    decision
                ),

                tool_result=None,
            )


        # ====================================================
        # 3. Tool Allowlist Validation
        # ====================================================

        tool = (
            self.tool_registry.get(
                decision.tool_name
            )
        )


        # ====================================================
        # 4. Execute Tool
        # ====================================================

        tool_result = (
            await tool.execute(
                query=(
                    decision.query
                ),

                top_k=(
                    top_k
                ),
            )
        )


        return ResearcherReport(
            decision=(
                decision
            ),

            tool_result=(
                tool_result
            ),
        )


# ============================================================
# Critic Agent
# ============================================================

class CriticAgent:
    """
    Critic Agent（审查智能体）。

    Responsibility：

        检查 Researcher Evidence
        是否足够回答用户问题。

    Critic 不负责：

        搜索
        Tool Selection
        最终 Answer
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_chunks: int,
    ):
        self.llm_provider = (
            llm_provider
        )

        self.max_chunks = (
            max_chunks
        )


    async def critique(
        self,
        question: str,
        retrieval_query: str,
        researcher_report: ResearcherReport,
    ) -> CriticReport:
        """
        审查 Researcher Result。
        """

        tool_result = (
            researcher_report
            .tool_result
        )


        # ====================================================
        # 1. Tool Failed
        # ====================================================

        if tool_result is None:

            return CriticReport(
                accepted=False,

                reason=(
                    "Researcher did not "
                    "execute a usable tool."
                ),
            )


        if not tool_result.success:

            return CriticReport(
                accepted=False,

                reason=(
                    tool_result.message
                    or "Research tool failed."
                ),
            )


        if not tool_result.candidates:

            return CriticReport(
                accepted=False,

                reason=(
                    "Researcher returned "
                    "no evidence candidates."
                ),
            )


        # ====================================================
        # 2. Resolve Retrieval Response
        # ====================================================

        retrieval = (
            tool_result
            .metadata
            .get(
                "retrieval_response"
            )
        )


        if (
            retrieval is None
            or not isinstance(
                retrieval,
                HybridSearchResponse,
            )
        ):

            return CriticReport(
                accepted=False,

                reason=(
                    "Researcher tool result "
                    "does not contain evaluable "
                    "retrieval evidence."
                ),
            )


        # ====================================================
        # 3. Evidence Evaluation
        # ====================================================

        evaluation: EvidenceEvaluation = (
            await evaluate_research_evidence(
                llm_provider=(
                    self.llm_provider
                ),

                question=(
                    question
                ),

                retrieval_query=(
                    retrieval_query
                ),

                retrieval=(
                    retrieval
                ),

                max_chunks=(
                    self.max_chunks
                ),
            )
        )


        return CriticReport(
            accepted=(
                evaluation.sufficient
            ),

            reason=(
                evaluation.reason
            ),
        )


# ============================================================
# Synthesizer Agent
# ============================================================

class SynthesizerAgent:
    """
    Synthesizer Agent（综合智能体）。

    Responsibility：

        只根据 Critic 已接受的 Evidence
        构造最终回答。

    它负责：

        Context
        Prompt
        Generation

    它不负责：

        Tool Selection
        Retrieval Retry Decision
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_context_chars: int,
    ):
        self.llm_provider = (
            llm_provider
        )

        self.max_context_chars = (
            max_context_chars
        )


    async def synthesize(
        self,
        question: str,
        candidates: list,
        top_k: int,
        conversation_history: Optional[
            list[
                tuple[str, str]
            ]
        ] = None,
    ) -> SynthesizerReport:
        """
        根据 Accepted Evidence 生成最终 Answer。
        """

        # ====================================================
        # 1. Final Candidate Selection
        # ====================================================

        final_candidates = (
            candidates[
                :top_k
            ]
        )


        # ====================================================
        # 2. Build Context
        # ====================================================

        rag_context = (
            build_rag_context(
                candidates=(
                    final_candidates
                ),

                max_chars=(
                    self.max_context_chars
                ),
            )
        )


        # ====================================================
        # 3. Empty Context
        # ====================================================

        if not rag_context.sources:

            return SynthesizerReport(
                rag_context=(
                    rag_context
                ),

                rendered_prompts=None,

                generation=None,

                answer=(
                    "No usable evidence was "
                    "available for synthesis."
                ),
            )


        # ====================================================
        # 4. Render Final RAG Prompt
        # ====================================================

        rendered = (
            render_rag_prompts(
                question=(
                    question
                ),

                context=(
                    rag_context.text
                ),

                conversation_history=(
                    conversation_history
                ),
            )
        )


        # ====================================================
        # 5. Generate
        # ====================================================

        generation = (
            await generate_rag_answer(
                llm_provider=(
                    self.llm_provider
                ),

                system_prompt=(
                    rendered
                    .system_prompt
                ),

                user_prompt=(
                    rendered
                    .user_prompt
                ),
            )
        )


        answer = (
            generation
            .text
            .strip()
        )


        return SynthesizerReport(
            rag_context=(
                rag_context
            ),

            rendered_prompts=(
                rendered
            ),

            generation=(
                generation
            ),

            answer=(
                answer
            ),
        )


# ============================================================
# Query Revision Coordinator
# ============================================================

async def revise_query_after_critique(
    llm_provider: LLMProvider,
    question: str,
    retrieval_query: str,
    critic_report: CriticReport,
    conversation_history: Optional[
        list[
            tuple[str, str]
        ]
    ] = None,
) -> str:
    """
    Critic Reject 后生成下一轮 Research Query。

    这里复用 Day35 Query Rewriter，
    避免再造一套逻辑。
    """

    return (
        await rewrite_research_query(
            llm_provider=(
                llm_provider
            ),

            question=(
                question
            ),

            retrieval_query=(
                retrieval_query
            ),

            evaluation_reason=(
                critic_report.reason
            ),

            conversation_history=(
                conversation_history
            ),
        )
    )