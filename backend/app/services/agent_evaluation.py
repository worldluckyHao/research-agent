import asyncio
import json
import logging
from typing import (
    Any,
    Dict,
)

from backend.app.core.config import (
    settings,
)
from backend.app.evaluations.agent import (
    evaluate_tool_execution,
    evaluate_tool_selection,
    evaluate_trajectory,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.prompts.agent_evaluation import (
    AGENT_EVALUATION_SYSTEM_PROMPT_ID,
    AGENT_EVALUATION_USER_PROMPT_ID,
)
from backend.app.prompts.registry import (
    prompt_registry,
)
from backend.app.schemas.agent_evaluation import (
    AgentEvaluationRequest,
    AgentEvaluationResponse,
    AgentJudgeEvaluation,
    AgentQualityGate,
)


logger = logging.getLogger(
    __name__
)


# ============================================================
# Score
# ============================================================

def _normalize_score(
    value: Any,
) -> float:
    """
    Judge Score 强制限制在 [0, 1]。
    """

    score = float(
        value
    )

    return round(
        max(
            0.0,
            min(
                1.0,
                score,
            ),
        ),
        4,
    )


# ============================================================
# JSON Parser
# ============================================================

def _extract_json_object(
    text: str,
) -> Dict[str, Any]:
    """
    对 Judge 输出做轻量容错。
    """

    cleaned = (
        text.strip()
    )


    if cleaned.startswith(
        "```"
    ):

        lines = (
            cleaned.splitlines()
        )

        if lines:
            lines = lines[1:]

        if (
            lines
            and lines[-1]
            .strip()
            .startswith("```")
        ):
            lines = lines[:-1]

        cleaned = (
            "\n"
            .join(lines)
            .strip()
        )


    start = cleaned.find(
        "{"
    )

    end = cleaned.rfind(
        "}"
    )


    if (
        start < 0
        or end < start
    ):

        raise ValueError(
            "Judge response does not contain JSON"
        )


    return json.loads(
        cleaned[
            start:
            end + 1
        ]
    )


# ============================================================
# Tool Trace
# ============================================================

def _format_tool_trace(
    request: AgentEvaluationRequest,
) -> str:
    """
    将 Tool Calls 转成 Judge 可读取的
    Observable Trace。
    """

    if not request.tool_calls:

        return "(no tool calls)"


    sections = []


    for call in request.tool_calls:

        arguments = json.dumps(
            call.arguments,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )


        section = (
            f"Step {call.step}\n"
            f"Tool: {call.tool_name}\n"
            f"Arguments: {arguments}\n"
            f"Status: {call.status}\n"
        )


        if call.output_summary:

            section += (
                "Output Summary: "
                f"{call.output_summary}\n"
            )


        if call.error:

            section += (
                "Error: "
                f"{call.error}\n"
            )


        sections.append(
            section.strip()
        )


    trace = "\n\n".join(
        sections
    )


    return trace[
        :
        settings
        .AGENT_EVALUATION_MAX_TRACE_CHARS
    ]


# ============================================================
# Evidence
# ============================================================

def _format_evidence(
    request: AgentEvaluationRequest,
) -> str:
    """
    Format optional evidence。
    """

    if not request.evidence:

        return "(not provided)"


    sections = []


    for item in request.evidence:

        sections.append(
            (
                f"[{item.source_id}]\n"
                f"{item.content}"
            )
        )


    return "\n\n".join(
        sections
    )


# ============================================================
# LLM Judge
# ============================================================

async def _evaluate_with_llm(
    request: AgentEvaluationRequest,

    llm_provider: LLMProvider,
) -> AgentJudgeEvaluation:
    """
    使用当前 LLM Provider：

        Bailian
        qwen3.8-flash

    对 Agent Run 做语义评价。
    """

    if not (
        settings
        .AGENT_EVALUATION_LLM_JUDGE_ENABLED
    ):

        return (
            AgentJudgeEvaluation(
                status="unavailable",

                reason=(
                    "Agent LLM judge is disabled"
                ),
            )
        )


    try:

        version = (
            settings
            .AGENT_EVALUATION_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    AGENT_EVALUATION_SYSTEM_PROMPT_ID
                ),

                version=version,
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    AGENT_EVALUATION_USER_PROMPT_ID
                ),

                version=version,

                task=(
                    request.task
                ),

                tool_trace=(
                    _format_tool_trace(
                        request
                    )
                ),

                final_answer=(
                    request.final_answer
                ),

                reference_outcome=(
                    request.reference_outcome
                    or "(not provided)"
                ),

                evidence=(
                    _format_evidence(
                        request
                    )
                ),
            )
        )


        result = (
            await asyncio.to_thread(
                llm_provider.generate,

                system_prompt,

                user_prompt,
            )
        )


        payload = (
            _extract_json_object(
                result.text
            )
        )


        groundedness_raw = (
            payload.get(
                "evidence_groundedness"
            )
        )


        if groundedness_raw is None:

            groundedness = None

        else:

            groundedness = (
                _normalize_score(
                    groundedness_raw
                )
            )


        return (
            AgentJudgeEvaluation(
                status="completed",

                goal_completion=(
                    _normalize_score(
                        payload[
                            "goal_completion"
                        ]
                    )
                ),

                final_answer_quality=(
                    _normalize_score(
                        payload[
                            "final_answer_quality"
                        ]
                    )
                ),

                trajectory_coherence=(
                    _normalize_score(
                        payload[
                            "trajectory_coherence"
                        ]
                    )
                ),

                evidence_groundedness=(
                    groundedness
                ),

                reason=str(
                    payload.get(
                        "reason",
                        "",
                    )
                ).strip(),
            )
        )


    except Exception as exc:

        logger.exception(
            (
                "Agent LLM judge failed: "
                "error_type=%s"
            ),
            type(exc).__name__,
        )


        return (
            AgentJudgeEvaluation(
                status="unavailable",

                reason=(
                    "Agent LLM judge failed: "
                    f"{type(exc).__name__}"
                ),
            )
        )


# ============================================================
# Quality Gate
# ============================================================

def _build_quality_gate(
    request,
    tool_selection,
    tool_execution,
    llm_judge,
) -> AgentQualityGate:
    """
    Agent Evaluation Quality Gate。
    """

    reasons = []


    # --------------------------------------------------------
    # Tool Selection
    # --------------------------------------------------------

    if (
        tool_selection.available
        and
        tool_selection.f1
        is not None
        and
        tool_selection.f1
        <
        settings
        .AGENT_EVALUATION_MIN_TOOL_F1
    ):

        reasons.append(
            "Tool selection F1 is below threshold"
        )


    # --------------------------------------------------------
    # Tool Execution
    # --------------------------------------------------------

    if (
        tool_execution.success_rate
        <
        settings
        .AGENT_EVALUATION_MIN_TOOL_SUCCESS_RATE
    ):

        reasons.append(
            "Tool execution success rate is below threshold"
        )


    # --------------------------------------------------------
    # Judge
    # --------------------------------------------------------

    if (
        settings
        .AGENT_EVALUATION_LLM_JUDGE_ENABLED
    ):

        if (
            llm_judge.status
            != "completed"
        ):

            reasons.append(
                "Agent LLM judge is unavailable"
            )


        else:

            if (
                llm_judge.goal_completion
                is not None
                and
                llm_judge.goal_completion
                <
                settings
                .AGENT_EVALUATION_MIN_GOAL_COMPLETION
            ):

                reasons.append(
                    "Agent goal completion is below threshold"
                )


            if (
                llm_judge.final_answer_quality
                is not None
                and
                llm_judge.final_answer_quality
                <
                settings
                .AGENT_EVALUATION_MIN_FINAL_ANSWER_QUALITY
            ):

                reasons.append(
                    "Final answer quality is below threshold"
                )


            if (
                llm_judge.trajectory_coherence
                is not None
                and
                llm_judge.trajectory_coherence
                <
                settings
                .AGENT_EVALUATION_MIN_TRAJECTORY_COHERENCE
            ):

                reasons.append(
                    "Agent trajectory coherence is below threshold"
                )


            if (
                request.evidence
                and
                llm_judge.evidence_groundedness
                is not None
                and
                llm_judge.evidence_groundedness
                <
                settings
                .AGENT_EVALUATION_MIN_GROUNDEDNESS
            ):

                reasons.append(
                    "Agent answer groundedness is below threshold"
                )


    return (
        AgentQualityGate(
            passed=(
                len(reasons)
                == 0
            ),

            reasons=reasons,
        )
    )


# ============================================================
# Public Service
# ============================================================

async def evaluate_agent(
    request: AgentEvaluationRequest,

    llm_provider: LLMProvider,
) -> AgentEvaluationResponse:
    """
    Agent Evaluation Orchestrator。

    Flow：

        Agent Run
            ↓
        Tool Selection
            ↓
        Tool Execution
            ↓
        Trajectory Metrics
            ↓
        LLM Judge
            ↓
        Quality Gate
    """

    tool_selection = (
        evaluate_tool_selection(
            actual_calls=(
                request.tool_calls
            ),

            expected_calls=(
                request.expected_tool_calls
            ),
        )
    )


    tool_execution = (
        evaluate_tool_execution(
            actual_calls=(
                request.tool_calls
            )
        )
    )


    trajectory = (
        evaluate_trajectory(
            actual_calls=(
                request.tool_calls
            )
        )
    )


    llm_judge = (
        await _evaluate_with_llm(
            request=request,

            llm_provider=(
                llm_provider
            ),
        )
    )


    quality_gate = (
        _build_quality_gate(
            request=request,

            tool_selection=(
                tool_selection
            ),

            tool_execution=(
                tool_execution
            ),

            llm_judge=(
                llm_judge
            ),
        )
    )


    return (
        AgentEvaluationResponse(
            task=(
                request.task
            ),

            tool_selection=(
                tool_selection
            ),

            tool_execution=(
                tool_execution
            ),

            trajectory=(
                trajectory
            ),

            llm_judge=(
                llm_judge
            ),

            quality_gate=(
                quality_gate
            ),
        )
    )