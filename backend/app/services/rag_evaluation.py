import asyncio
import json
import logging
from typing import (
    Dict,
    List,
)

from backend.app.core.config import (
    settings,
)
from backend.app.evaluations.rag import (
    evaluate_citations,
    evaluate_retrieval,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.prompts.rag_evaluation import (
    RAG_EVALUATION_SYSTEM_PROMPT_ID,
    RAG_EVALUATION_USER_PROMPT_ID,
)
from backend.app.prompts.registry import (
    prompt_registry,
)
from backend.app.schemas.rag_evaluation import (
    LLMJudgeEvaluation,
    RAGEvaluationEvidence,
    RAGEvaluationRequest,
    RAGEvaluationResponse,
    RAGQualityGate,
)


logger = logging.getLogger(
    __name__
)


# ============================================================
# Evidence Formatting
# ============================================================

def _format_evidence(
    evidence: List[
        RAGEvaluationEvidence
    ],
) -> str:
    """
    将 Evidence 转换为：

        [S1]
        ...

        [S2]
        ...
    """

    sections = []


    for item in evidence:

        sections.append(
            (
                f"[{item.source_id}]\n"
                f"{item.content.strip()}"
            )
        )


    text = "\n\n".join(
        sections
    )


    max_chars = (
        settings
        .RAG_EVALUATION_MAX_EVIDENCE_CHARS
    )


    return text[:max_chars]


# ============================================================
# JSON Extraction
# ============================================================

def _extract_json_object(
    text: str,
) -> Dict:
    """
    对 LLM Judge 输出做轻量容错。

    支持：

        pure JSON

    以及错误地返回：

        ```json
        {...}
        ```
    """

    cleaned = (
        text
        .strip()
    )


    if cleaned.startswith("```"):

        lines = (
            cleaned
            .splitlines()
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


        cleaned = "\n".join(
            lines
        ).strip()


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
# Score Validation
# ============================================================

def _normalize_score(
    value,
) -> float:
    """
    确保 Judge Score ∈ [0, 1]。
    """

    score = float(
        value
    )


    if score < 0.0:

        score = 0.0


    if score > 1.0:

        score = 1.0


    return round(
        score,
        4,
    )


# ============================================================
# LLM-as-a-Judge
# ============================================================

async def _evaluate_with_llm(
    request: RAGEvaluationRequest,

    llm_provider: LLMProvider,
) -> LLMJudgeEvaluation:
    """
    使用当前项目的 LLM Provider
    执行语义评价。

    当前：
        Bailian
        qwen3.8-flash
    """

    if not (
        settings
        .RAG_EVALUATION_LLM_JUDGE_ENABLED
    ):

        return (
            LLMJudgeEvaluation(
                status="unavailable",

                reason=(
                    "LLM judge is disabled"
                ),
            )
        )


    try:

        evidence_text = (
            _format_evidence(
                request.evidence
            )
        )


        version = (
            settings
            .RAG_EVALUATION_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RAG_EVALUATION_SYSTEM_PROMPT_ID
                ),

                version=version,
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RAG_EVALUATION_USER_PROMPT_ID
                ),

                version=version,

                question=(
                    request.question
                ),

                answer=(
                    request.answer
                ),

                evidence=(
                    evidence_text
                ),
            )
        )


        # LLMProvider.generate()
        # 是同步函数，
        # 避免阻塞 Event Loop。
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


        groundedness = (
            _normalize_score(
                payload[
                    "groundedness"
                ]
            )
        )


        relevance = (
            _normalize_score(
                payload[
                    "relevance"
                ]
            )
        )


        reason = str(
            payload.get(
                "reason",
                "",
            )
        ).strip()


        return (
            LLMJudgeEvaluation(
                status="completed",

                groundedness=(
                    groundedness
                ),

                relevance=(
                    relevance
                ),

                reason=(
                    reason
                ),
            )
        )


    except Exception as exc:

        # Evaluation 不应该因为
        # Judge 临时不可用而丢失
        # Deterministic Metrics。

        logger.exception(
            (
                "RAG LLM judge failed: "
                "error_type=%s"
            ),
            type(exc).__name__,
        )


        return (
            LLMJudgeEvaluation(
                status="unavailable",

                reason=(
                    "LLM judge failed: "
                    f"{type(exc).__name__}"
                ),
            )
        )


# ============================================================
# Quality Gate
# ============================================================

def _build_quality_gate(
    retrieval,
    citation,
    llm_judge,
) -> RAGQualityGate:
    """
    将 Metrics 转换为可用于
    Regression / CI 的质量门禁。
    """

    reasons = []


    # --------------------------------------------------------
    # Citation
    # --------------------------------------------------------

    if citation.total_citations == 0:

        reasons.append(
            "Answer contains no source citations"
        )


    if (
        citation
        .citation_precision
        < 1.0
    ):

        reasons.append(
            "Answer contains invalid source citations"
        )


    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    if (
        retrieval.available
        and retrieval.recall_at_k
        is not None
        and retrieval.recall_at_k
        <
        settings
        .RAG_EVALUATION_MIN_RECALL_AT_K
    ):

        reasons.append(
            "Retrieval recall is below threshold"
        )


    # --------------------------------------------------------
    # LLM Judge
    # --------------------------------------------------------

    if (
        settings
        .RAG_EVALUATION_LLM_JUDGE_ENABLED
    ):

        if (
            llm_judge.status
            != "completed"
        ):

            reasons.append(
                "LLM judge is unavailable"
            )


        else:

            if (
                llm_judge.groundedness
                is not None
                and
                llm_judge.groundedness
                <
                settings
                .RAG_EVALUATION_MIN_GROUNDEDNESS
            ):

                reasons.append(
                    (
                        "Groundedness is "
                        "below threshold"
                    )
                )


            if (
                llm_judge.relevance
                is not None
                and
                llm_judge.relevance
                <
                settings
                .RAG_EVALUATION_MIN_RELEVANCE
            ):

                reasons.append(
                    (
                        "Answer relevance is "
                        "below threshold"
                    )
                )


    return (
        RAGQualityGate(
            passed=(
                len(reasons)
                == 0
            ),

            reasons=(
                reasons
            ),
        )
    )


# ============================================================
# Public Service
# ============================================================

async def evaluate_rag(
    request: RAGEvaluationRequest,

    llm_provider: LLMProvider,
) -> RAGEvaluationResponse:
    """
    RAG Evaluation Orchestrator。

    Flow：

        RAG Sample
            ↓
        Retrieval Metrics
            ↓
        Citation Metrics
            ↓
        LLM-as-a-Judge
            ↓
        Quality Gate
    """

    retrieval = (
        evaluate_retrieval(
            evidence=(
                request.evidence
            ),

            gold_source_ids=(
                request
                .gold_source_ids
            ),
        )
    )


    citation = (
        evaluate_citations(
            answer=(
                request.answer
            ),

            evidence=(
                request.evidence
            ),
        )
    )


    llm_judge = (
        await _evaluate_with_llm(
            request=(
                request
            ),

            llm_provider=(
                llm_provider
            ),
        )
    )


    quality_gate = (
        _build_quality_gate(
            retrieval=(
                retrieval
            ),

            citation=(
                citation
            ),

            llm_judge=(
                llm_judge
            ),
        )
    )


    return (
        RAGEvaluationResponse(
            question=(
                request.question
            ),

            retrieval=(
                retrieval
            ),

            citation=(
                citation
            ),

            llm_judge=(
                llm_judge
            ),

            quality_gate=(
                quality_gate
            ),
        )
    )