import json
from dataclasses import dataclass
from typing import (
    Any,
    Optional,
)

from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.prompts.registry import (
    prompt_registry,
)
from backend.app.prompts.research_agent import (
    EVIDENCE_EVALUATION_SYSTEM_PROMPT_ID,
    EVIDENCE_EVALUATION_USER_PROMPT_ID,
    QUERY_ANALYSIS_SYSTEM_PROMPT_ID,
    QUERY_ANALYSIS_USER_PROMPT_ID,
    QUERY_REWRITE_SYSTEM_PROMPT_ID,
    QUERY_REWRITE_USER_PROMPT_ID,
)
from backend.app.rag.generation import (
    generate_rag_answer,
)
from backend.app.schemas.hybrid_search import (
    HybridSearchResponse,
)

# ============================================================
# Agent Domain Results
# ============================================================

@dataclass(frozen=True)
class QueryAnalysis:
    """
    Query Analysis Result（问题分析结果）。
    """

    intent: str

    standalone_query: str

    needs_history: bool

    key_terms: list[str]


@dataclass(frozen=True)
class EvidenceEvaluation:
    """
    Evidence Evaluation Result（证据评估结果）。
    """

    sufficient: bool

    reason: str


# ============================================================
# JSON Parsing
# ============================================================

def _parse_json_object(
    text: str,
) -> dict[str, Any]:
    """
    尽量稳健地从 LLM 输出中解析 JSON Object。

    理想输出：

        {"sufficient": true}

    但某些模型可能错误输出：

        ```json
        {...}
        ```

    所以这里进行最小清理。

    注意：
    这里不是为了“容忍任何垃圾输出”，
    只是提高本地小模型开发阶段的稳定性。
    """

    cleaned = (
        text.strip()
    )


    # --------------------------------------------------------
    # Remove Markdown Code Fence
    # --------------------------------------------------------

    if cleaned.startswith(
        "```"
    ):

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


        cleaned = (
            "\n".join(
                lines
            )
            .strip()
        )


    # --------------------------------------------------------
    # First direct attempt
    # --------------------------------------------------------

    try:

        payload = json.loads(
            cleaned
        )


        if not isinstance(
            payload,
            dict,
        ):

            raise ValueError(
                "Expected JSON object"
            )


        return payload


    except (
        json.JSONDecodeError,
        ValueError,
    ):

        pass


    # --------------------------------------------------------
    # Fallback:
    # extract text between first { and last }
    # --------------------------------------------------------

    start = cleaned.find(
        "{"
    )

    end = cleaned.rfind(
        "}"
    )


    if (
        start == -1
        or end == -1
        or end <= start
    ):

        raise ValueError(
            "LLM did not return a JSON object"
        )


    candidate = cleaned[
        start:
        end + 1
    ]


    payload = json.loads(
        candidate
    )


    if not isinstance(
        payload,
        dict,
    ):

        raise ValueError(
            "Expected JSON object"
        )


    return payload


# ============================================================
# History Formatting
# ============================================================

def _format_history(
    conversation_history: Optional[
        list[
            tuple[str, str]
        ]
    ],
) -> str:
    """
    Agent 内部使用的 History Formatter。
    """

    if not conversation_history:

        return "(none)"


    blocks = []


    for role, content in conversation_history:

        if role == "user":

            role_name = "User"

        elif role == "assistant":

            role_name = "Assistant"

        else:

            continue


        blocks.append(
            f"{role_name}:\n"
            f"{content}"
        )


    if not blocks:

        return "(none)"


    return "\n\n".join(
        blocks
    )


# ============================================================
# Query Analysis
# ============================================================

async def analyze_research_query(
    llm_provider: LLMProvider,
    question: str,
    conversation_history: Optional[
        list[
            tuple[str, str]
        ]
    ] = None,
) -> QueryAnalysis:
    """
    分析用户问题并生成 Standalone Query。

    Example：

        Question:
            "How are they fused?"

        History:
            ERA5 + radar

        Standalone:
            "How are ERA5 reanalysis data and
             radar observations fused in the paper?"
    """

    history = (
        _format_history(
            conversation_history
        )
    )


    system_prompt = (
        prompt_registry.render(
            prompt_id=(
                QUERY_ANALYSIS_SYSTEM_PROMPT_ID
            ),

            version=1,
        )
    )


    user_prompt = (
        prompt_registry.render(
            prompt_id=(
                QUERY_ANALYSIS_USER_PROMPT_ID
            ),

            version=1,

            history=(
                history
            ),

            question=(
                question
            ),
        )
    )


    generation = (
        await generate_rag_answer(
            llm_provider=(
                llm_provider
            ),

            system_prompt=(
                system_prompt
            ),

            user_prompt=(
                user_prompt
            ),
        )
    )


    try:

        payload = (
            _parse_json_object(
                generation.text
            )
        )


        standalone_query = str(
            payload.get(
                "standalone_query",
                "",
            )
        ).strip()


        if not standalone_query:

            standalone_query = (
                question.strip()
            )


        intent = str(
            payload.get(
                "intent",
                "research_question",
            )
        ).strip()


        needs_history = bool(
            payload.get(
                "needs_history",
                False,
            )
        )


        raw_terms = payload.get(
            "key_terms",
            [],
        )


        if isinstance(
            raw_terms,
            list,
        ):

            key_terms = [
                str(term).strip()

                for term in raw_terms

                if str(term).strip()
            ]

        else:

            key_terms = []


        return QueryAnalysis(
            intent=(
                intent
                or "research_question"
            ),

            standalone_query=(
                standalone_query
            ),

            needs_history=(
                needs_history
            ),

            key_terms=(
                key_terms
            ),
        )


    except (
        ValueError,
        json.JSONDecodeError,
        TypeError,
    ):

        # -----------------------------------------------
        # Graceful Fallback
        # -----------------------------------------------
        #
        # Query Analysis 失败不能让整个 RAG
        # 完全不可用。
        #
        # 回退到原始问题。
        return QueryAnalysis(
            intent="research_question",

            standalone_query=(
                question.strip()
            ),

            needs_history=False,

            key_terms=[],
        )


# ============================================================
# Evidence Text
# ============================================================

def build_evaluation_evidence(
    retrieval: HybridSearchResponse,
    max_chunks: int,
) -> str:
    """
    将 Retrieval Result
    转换成 Evidence Evaluator 可读取的文本。

    不需要把全部候选都发送给 LLM。
    """

    blocks = []


    for index, item in enumerate(
        retrieval.items[
            :max_chunks
        ],
        start=1,
    ):

        blocks.append(
            (
                f"[Candidate {index}]\n"
                f"Pages: "
                f"{item.start_page}-"
                f"{item.end_page}\n"
                f"{item.content}"
            )
        )


    if not blocks:

        return "(no evidence)"


    return "\n\n".join(
        blocks
    )


# ============================================================
# Evidence Evaluation
# ============================================================

async def evaluate_research_evidence(
    llm_provider: LLMProvider,
    question: str,
    retrieval_query: str,
    retrieval: HybridSearchResponse,
    max_chunks: int,
) -> EvidenceEvaluation:
    """
    判断 Retrieval Evidence
    是否足够支持回答。

    注意：

    Evaluator 只判断：
        sufficient / insufficient

    不负责生成最终答案。
    """

    if not retrieval.items:

        return EvidenceEvaluation(
            sufficient=False,
            reason=(
                "No retrieval candidates were returned."
            ),
        )


    evidence_text = (
        build_evaluation_evidence(
            retrieval=(
                retrieval
            ),

            max_chunks=(
                max_chunks
            ),
        )
    )


    system_prompt = (
        prompt_registry.render(
            prompt_id=(
                EVIDENCE_EVALUATION_SYSTEM_PROMPT_ID
            ),

            version=1,
        )
    )


    user_prompt = (
        prompt_registry.render(
            prompt_id=(
                EVIDENCE_EVALUATION_USER_PROMPT_ID
            ),

            version=1,

            question=(
                question
            ),

            retrieval_query=(
                retrieval_query
            ),

            evidence=(
                evidence_text
            ),
        )
    )


    generation = (
        await generate_rag_answer(
            llm_provider=(
                llm_provider
            ),

            system_prompt=(
                system_prompt
            ),

            user_prompt=(
                user_prompt
            ),
        )
    )


    try:

        payload = (
            _parse_json_object(
                generation.text
            )
        )


        sufficient = bool(
            payload.get(
                "sufficient",
                False,
            )
        )


        reason = str(
            payload.get(
                "reason",
                "",
            )
        ).strip()


        if not reason:

            reason = (
                "Evidence evaluator "
                "returned no reason."
            )


        return EvidenceEvaluation(
            sufficient=(
                sufficient
            ),

            reason=(
                reason
            ),
        )


    except (
        ValueError,
        json.JSONDecodeError,
        TypeError,
    ):

        # -----------------------------------------------
        # Availability Fallback
        # -----------------------------------------------
        #
        # 本地小模型偶尔 JSON 输出不规范。
        #
        # 这里不直接让整个请求 500。
        #
        # Retrieval 有候选时暂时允许继续，
        # 后续 Day44 再通过评估校准。
        return EvidenceEvaluation(
            sufficient=bool(
                retrieval.items
            ),

            reason=(
                "Evidence evaluation output "
                "could not be parsed; "
                "fallback used."
            ),
        )


# ============================================================
# Query Rewrite
# ============================================================

async def rewrite_research_query(
    llm_provider: LLMProvider,
    question: str,
    retrieval_query: str,
    evaluation_reason: str,
    conversation_history: Optional[
        list[
            tuple[str, str]
        ]
    ] = None,
) -> str:
    """
    Evidence 不足时生成新的 Retrieval Query。
    """

    history = (
        _format_history(
            conversation_history
        )
    )


    system_prompt = (
        prompt_registry.render(
            prompt_id=(
                QUERY_REWRITE_SYSTEM_PROMPT_ID
            ),

            version=1,
        )
    )


    user_prompt = (
        prompt_registry.render(
            prompt_id=(
                QUERY_REWRITE_USER_PROMPT_ID
            ),

            version=1,

            history=(
                history
            ),

            question=(
                question
            ),

            retrieval_query=(
                retrieval_query
            ),

            evaluation_reason=(
                evaluation_reason
            ),
        )
    )


    generation = (
        await generate_rag_answer(
            llm_provider=(
                llm_provider
            ),

            system_prompt=(
                system_prompt
            ),

            user_prompt=(
                user_prompt
            ),
        )
    )


    try:

        payload = (
            _parse_json_object(
                generation.text
            )
        )


        rewritten_query = str(
            payload.get(
                "rewritten_query",
                "",
            )
        ).strip()


        if rewritten_query:

            return rewritten_query


    except (
        ValueError,
        json.JSONDecodeError,
        TypeError,
    ):

        pass


    # Query Rewrite 失败时，
    # 至少保留当前 Retrieval Query。
    return retrieval_query