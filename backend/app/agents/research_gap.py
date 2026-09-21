import json
from dataclasses import (
    dataclass,
)
from typing import (
    Any,
)

from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    ResearchGapGenerationException,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.prompts.registry import (
    prompt_registry,
)
from backend.app.prompts.research_gap import (
    RESEARCH_GAP_GENERATION_SYSTEM_PROMPT_ID,
    RESEARCH_GAP_GENERATION_USER_PROMPT_ID,
    RESEARCH_GAP_VERIFICATION_SYSTEM_PROMPT_ID,
    RESEARCH_GAP_VERIFICATION_USER_PROMPT_ID,
)
from backend.app.rag.generation import (
    generate_rag_answer,
)
from backend.app.schemas.paper_comparison import (
    PaperComparisonCitationResponse,
    PaperComparisonResponse,
)
from backend.app.schemas.research_gap import (
    RejectedResearchGapResponse,
    ResearchGapCandidateResponse,
    ResearchGapEvidenceResponse,
    ResearchGapResponse,
)
from backend.app.schemas.rag import (
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)


# ============================================================
# Internal Candidate
# ============================================================

@dataclass(frozen=True)
class GeneratedGapCandidate:
    """
    Gap Generator 的原始候选。
    """

    title: str

    gap_type: str

    gap_statement: str

    evidence_basis: str

    supporting_citation_ids: list[str]

    scope_limitations: str


# ============================================================
# Internal Verification
# ============================================================

@dataclass(frozen=True)
class GapVerificationResult:
    """
    Gap Verifier 结果。
    """

    status: str

    reason: str

    supporting_citation_ids: list[str]

    counter_evidence_citation_ids: list[str]

    scope_limitations: str


# ============================================================
# JSON Parser
# ============================================================

def _parse_json_object(
    text: str,
) -> dict[str, Any]:
    """
    解析 LLM JSON。

    允许本地小模型偶尔包一层：
        ```json
        ...
        ```
    """

    cleaned = (
        text.strip()
    )


    # --------------------------------------------------------
    # Remove Markdown Fence
    # --------------------------------------------------------

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
            "\n".join(
                lines
            )
            .strip()
        )


    # --------------------------------------------------------
    # Direct Parse
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
    # Extract First Object
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

        raise (
            ResearchGapGenerationException()
        )


    try:

        payload = json.loads(
            cleaned[
                start:
                end + 1
            ]
        )


    except json.JSONDecodeError as exc:

        raise (
            ResearchGapGenerationException()
        ) from exc


    if not isinstance(
        payload,
        dict,
    ):

        raise (
            ResearchGapGenerationException()
        )


    return payload


# ============================================================
# Comparison Evidence
# ============================================================

def _build_comparison_evidence(
    comparison: PaperComparisonResponse,
) -> str:
    """
    将 Day38 PaperComparisonResponse
    转换成 Gap Agent 使用的 Evidence Text。

    包括：

        每篇 Paper Summary
        Overall Summary
        Comparison Matrix
        Key Differences
        Research Takeaways
    """

    blocks = []


    # ========================================================
    # Per-Paper Evidence
    # ========================================================

    for paper in comparison.papers:

        blocks.append(
            (
                f"Paper {paper.label}\n"
                f"Title: {paper.title}\n"
                f"Evidence Summary:\n"
                f"{paper.evidence_summary}"
            )
        )


    # ========================================================
    # Overall Summary
    # ========================================================

    blocks.append(
        (
            "Cross-Paper Overall Summary:\n"
            f"{comparison.overall_summary}"
        )
    )


    # ========================================================
    # Matrix
    # ========================================================

    matrix_blocks = []


    for row in comparison.matrix:

        values = "\n".join(
            (
                f"- {paper_label}: "
                f"{value}"
            )

            for (
                paper_label,
                value,
            )
            in row.values.items()
        )


        matrix_blocks.append(
            (
                f"Dimension: "
                f"{row.dimension}\n"
                f"{values}"
            )
        )


    if matrix_blocks:

        blocks.append(
            (
                "Comparison Matrix:\n"
                +
                "\n\n".join(
                    matrix_blocks
                )
            )
        )


    # ========================================================
    # Differences
    # ========================================================

    if comparison.key_differences:

        blocks.append(
            (
                "Key Differences:\n"
                +
                "\n".join(
                    (
                        f"- {item}"
                    )

                    for item
                    in comparison.key_differences
                )
            )
        )


    # ========================================================
    # Takeaways
    # ========================================================

    if comparison.research_takeaways:

        blocks.append(
            (
                "Research Takeaways:\n"
                +
                "\n".join(
                    (
                        f"- {item}"
                    )

                    for item
                    in comparison.research_takeaways
                )
            )
        )


    return "\n\n==========\n\n".join(
        blocks
    )


# ============================================================
# Citation Map
# ============================================================

def _build_citation_map(
    comparison: PaperComparisonResponse,
) -> dict[
    str,
    PaperComparisonCitationResponse,
]:
    """
    使用每篇 Paper 的完整 Citation。

    注意：

    不能只使用：
        comparison.citations

    因为 comparison.citations
    只包含最终 Comparison 真正引用到的部分。

    Per-Paper Evidence Summary 中
    可能还有其他合法 Citation。
    """

    citation_map = {}


    for paper in comparison.papers:

        for citation in paper.citations:

            citation_map[
                citation.citation_id
            ] = citation


    return citation_map


# ============================================================
# Citation Normalization
# ============================================================

def _normalize_citation_ids(
    raw_ids: Any,
) -> list[str]:
    """
    将 LLM Citation List
    规范化为不重复字符串。
    """

    if not isinstance(
        raw_ids,
        list,
    ):

        return []


    result = []

    seen = set()


    for raw_id in raw_ids:

        citation_id = str(
            raw_id
        ).strip()


        # 有时模型可能输出：
        # [P1-S1]
        #
        # 我们内部统一保存：
        # P1-S1
        citation_id = (
            citation_id
            .removeprefix("[")
            .removesuffix("]")
            .strip()
        )


        if not citation_id:

            continue


        if citation_id in seen:

            continue


        seen.add(
            citation_id
        )


        result.append(
            citation_id
        )


    return result


# ============================================================
# Gap Type Validation
# ============================================================

ALLOWED_GAP_TYPES = {
    "method_gap",
    "data_gap",
    "modality_gap",
    "evaluation_gap",
    "robustness_gap",
    "generalization_gap",
    "interpretability_gap",
    "efficiency_gap",
    "reproducibility_gap",
    "scope_gap",
    "other",
}


def _normalize_gap_type(
    raw_type: Any,
) -> str:
    """
    防止 LLM 生成未知 gap_type。
    """

    normalized = str(
        raw_type
        or "other"
    ).strip()


    if (
        normalized
        not in ALLOWED_GAP_TYPES
    ):

        return "other"


    return normalized


# ============================================================
# Parse Generated Candidates
# ============================================================

def _parse_generated_candidates(
    payload: dict[str, Any],
    max_candidates: int,
) -> list[
    GeneratedGapCandidate
]:
    """
    解析 Generator Output。
    """

    raw_candidates = (
        payload.get(
            "candidates",
            [],
        )
    )


    if not isinstance(
        raw_candidates,
        list,
    ):

        raise (
            ResearchGapGenerationException()
        )


    candidates = []


    for raw_candidate in raw_candidates[
        :max_candidates
    ]:

        if not isinstance(
            raw_candidate,
            dict,
        ):

            continue


        title = str(
            raw_candidate.get(
                "title",
                "",
            )
        ).strip()


        gap_statement = str(
            raw_candidate.get(
                "gap_statement",
                "",
            )
        ).strip()


        evidence_basis = str(
            raw_candidate.get(
                "evidence_basis",
                "",
            )
        ).strip()


        scope_limitations = str(
            raw_candidate.get(
                "scope_limitations",
                "",
            )
        ).strip()


        if (
            not title
            or not gap_statement
        ):

            continue


        candidates.append(
            GeneratedGapCandidate(
                title=(
                    title
                ),

                gap_type=(
                    _normalize_gap_type(
                        raw_candidate.get(
                            "gap_type"
                        )
                    )
                ),

                gap_statement=(
                    gap_statement
                ),

                evidence_basis=(
                    evidence_basis
                ),

                supporting_citation_ids=(
                    _normalize_citation_ids(
                        raw_candidate.get(
                            "supporting_citations",
                            [],
                        )
                    )
                ),

                scope_limitations=(
                    scope_limitations
                    or (
                        "This candidate is scoped "
                        "to the selected papers."
                    )
                ),
            )
        )


    return candidates


# ============================================================
# Evidence Conversion
# ============================================================

def _citation_to_gap_evidence(
    citation: PaperComparisonCitationResponse,
) -> ResearchGapEvidenceResponse:
    """
    Day38 Citation
    -> Day39 Gap Evidence。
    """

    return (
        ResearchGapEvidenceResponse(
            citation_id=(
                citation.citation_id
            ),

            paper_id=(
                citation.paper_id
            ),

            document_id=(
                citation.document_id
            ),

            chunk_id=(
                citation.chunk_id
            ),

            chunk_index=(
                citation.chunk_index
            ),

            start_page=(
                citation.start_page
            ),

            end_page=(
                citation.end_page
            ),
        )
    )


# ============================================================
# Evidence Strength
# ============================================================

def _derive_evidence_strength(
    status: str,
    supporting_evidence: list[
        ResearchGapEvidenceResponse
    ],
    counter_evidence: list[
        ResearchGapEvidenceResponse
    ],
) -> str:
    """
    Evidence Strength（证据强度）。

    注意：
    这不是概率，也不是统计置信度。

    只是 Selected Corpus 内的
    Evidence Coverage 描述。
    """

    if status == "rejected":

        return "weak"


    supporting_papers = {
        evidence.paper_id

        for evidence
        in supporting_evidence
    }


    # 有明确 Counter Evidence，
    # 不允许标 Strong。
    if counter_evidence:

        if len(
            supporting_papers
        ) >= 2:

            return "moderate"


        return "weak"


    # Strong：
    #
    # Verifier supported
    # +
    # 至少 N 篇不同论文支持。
    if (
        status == "supported"
        and len(
            supporting_papers
        )
        >= settings
        .RESEARCH_GAP_STRONG_SUPPORT_MIN_PAPERS
    ):

        return "strong"


    if (
        status
        in {
            "supported",
            "partially_supported",
        }
        and len(
            supporting_papers
        ) >= 2
    ):

        return "moderate"


    return "weak"


# ============================================================
# Gap Generator Agent
# ============================================================

class ResearchGapGeneratorAgent:
    """
    Gap Generator Agent。

    负责：

        Comparison Evidence
            ↓
        Candidate Gap

    不负责最终 Verification。
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


    async def generate(
        self,
        comparison: PaperComparisonResponse,
        gap_focus: str,
        max_candidates: int,
        response_language: str,
    ) -> tuple[
        list[GeneratedGapCandidate],
        RAGModelInfoResponse,
    ]:
        """
        生成 Gap Candidates。
        """

        evidence = (
            _build_comparison_evidence(
                comparison
            )
        )


        version = (
            settings
            .RESEARCH_GAP_GENERATION_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_GAP_GENERATION_SYSTEM_PROMPT_ID
                ),

                version=(
                    version
                ),
            )
        )


        language_name = (
            "Chinese"
            if response_language == "zh"
            else "English"
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_GAP_GENERATION_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                response_language=(
                    language_name
                ),

                gap_focus=(
                    gap_focus
                ),

                max_candidates=(
                    max_candidates
                ),

                comparison_evidence=(
                    evidence
                ),
            )
        )


        generation = (
            await generate_rag_answer(
                llm_provider=(
                    self.llm_provider
                ),

                system_prompt=(
                    system_prompt
                ),

                user_prompt=(
                    user_prompt
                ),
            )
        )


        payload = (
            _parse_json_object(
                generation.text
            )
        )


        candidates = (
            _parse_generated_candidates(
                payload=(
                    payload
                ),

                max_candidates=(
                    max_candidates
                ),
            )
        )


        return (
            candidates,

            RAGModelInfoResponse(
                provider=(
                    generation.provider
                ),

                model_name=(
                    generation.model_name
                ),
            ),
        )


# ============================================================
# Gap Verifier Agent
# ============================================================

class ResearchGapVerifierAgent:
    """
    Gap Verifier Agent。

    对 Generator Candidate 进行：

        Supporting Evidence Check
        Counter-Evidence Check
        Scope Check
        Overgeneralization Check
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


    async def verify(
        self,
        candidate: GeneratedGapCandidate,
        comparison: PaperComparisonResponse,
    ) -> GapVerificationResult:
        """
        验证一个 Candidate。
        """

        comparison_evidence = (
            _build_comparison_evidence(
                comparison
            )
        )


        candidate_payload = {
            "title":
                candidate.title,

            "gap_type":
                candidate.gap_type,

            "gap_statement":
                candidate.gap_statement,

            "evidence_basis":
                candidate.evidence_basis,

            "supporting_citations":
                candidate.supporting_citation_ids,

            "scope_limitations":
                candidate.scope_limitations,
        }


        version = (
            settings
            .RESEARCH_GAP_VERIFICATION_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_GAP_VERIFICATION_SYSTEM_PROMPT_ID
                ),

                version=(
                    version
                ),
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_GAP_VERIFICATION_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                candidate_gap=(
                    json.dumps(
                        candidate_payload,
                        ensure_ascii=False,
                        indent=2,
                    )
                ),

                comparison_evidence=(
                    comparison_evidence
                ),
            )
        )


        generation = (
            await generate_rag_answer(
                llm_provider=(
                    self.llm_provider
                ),

                system_prompt=(
                    system_prompt
                ),

                user_prompt=(
                    user_prompt
                ),
            )
        )


        payload = (
            _parse_json_object(
                generation.text
            )
        )


        status = str(
            payload.get(
                "status",
                "rejected",
            )
        ).strip()


        if status not in {
            "supported",
            "partially_supported",
            "rejected",
        }:

            status = "rejected"


        reason = str(
            payload.get(
                "reason",
                "",
            )
        ).strip()


        scope_limitations = str(
            payload.get(
                "scope_limitations",
                "",
            )
        ).strip()


        return (
            GapVerificationResult(
                status=(
                    status
                ),

                reason=(
                    reason
                    or (
                        "Verifier returned "
                        "no explanation."
                    )
                ),

                supporting_citation_ids=(
                    _normalize_citation_ids(
                        payload.get(
                            "supporting_citations",
                            [],
                        )
                    )
                ),

                counter_evidence_citation_ids=(
                    _normalize_citation_ids(
                        payload.get(
                            "counter_evidence_citations",
                            [],
                        )
                    )
                ),

                scope_limitations=(
                    scope_limitations
                    or (
                        "This conclusion is limited "
                        "to the selected paper set."
                    )
                ),
            )
        )


# ============================================================
# Main Research Gap Agent
# ============================================================

class ResearchGapAgent:
    """
    Day39 Research Gap Agent。

    Architecture：

        Gap Generator
            ↓
        Gap Verifier
            ↓
        Backend Citation Validation
            ↓
        Evidence Strength
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


        self.generator = (
            ResearchGapGeneratorAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


        self.verifier = (
            ResearchGapVerifierAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


    async def discover(
        self,
        project_id: int,
        comparison: PaperComparisonResponse,
        gap_focus: str,
        max_candidates: int,
        response_language: str,
    ) -> ResearchGapResponse:
        """
        完整 Research Gap Discovery。
        """

        citation_map = (
            _build_citation_map(
                comparison
            )
        )


        # ====================================================
        # 1. Generate Candidates
        # ====================================================

        (
            candidates,
            model_info,
        ) = (
            await self.generator.generate(
                comparison=(
                    comparison
                ),

                gap_focus=(
                    gap_focus
                ),

                max_candidates=(
                    max_candidates
                ),

                response_language=(
                    response_language
                ),
            )
        )


        accepted_gaps = []

        rejected_gaps = []


        # ====================================================
        # 2. Verify Candidates Sequentially
        # ====================================================
        #
        # 当前本地 LLM Provider 共享模型，
        # 不做 asyncio.gather。
        for index, candidate in enumerate(
            candidates,
            start=1,
        ):

            gap_id = (
                f"G{index}"
            )


            # ------------------------------------------------
            # Generator Citation Validation
            # ------------------------------------------------

            generator_valid_support = [
                citation_id

                for citation_id
                in candidate
                .supporting_citation_ids

                if citation_id
                in citation_map
            ]


            # Generator 连一条合法 Citation 都没有，
            # 没必要再浪费一次 Verifier LLM。
            if not generator_valid_support:

                rejected_gaps.append(
                    RejectedResearchGapResponse(
                        gap_id=(
                            gap_id
                        ),

                        title=(
                            candidate.title
                        ),

                        gap_statement=(
                            candidate
                            .gap_statement
                        ),

                        reason=(
                            "Candidate contains no "
                            "valid supporting citation."
                        ),
                    )
                )


                continue


            # ------------------------------------------------
            # Gap Verification
            # ------------------------------------------------

            verification = (
                await self.verifier.verify(
                    candidate=(
                        candidate
                    ),

                    comparison=(
                        comparison
                    ),
                )
            )


            # ------------------------------------------------
            # Backend Citation Allowlist
            # ------------------------------------------------

            valid_support_ids = [
                citation_id

                for citation_id
                in verification
                .supporting_citation_ids

                if citation_id
                in citation_map
            ]


            valid_counter_ids = [
                citation_id

                for citation_id
                in verification
                .counter_evidence_citation_ids

                if citation_id
                in citation_map
            ]


            supporting_evidence = [
                _citation_to_gap_evidence(
                    citation_map[
                        citation_id
                    ]
                )

                for citation_id
                in valid_support_ids
            ]


            counter_evidence = [
                _citation_to_gap_evidence(
                    citation_map[
                        citation_id
                    ]
                )

                for citation_id
                in valid_counter_ids
            ]


            supporting_papers = {
                evidence.paper_id

                for evidence
                in supporting_evidence
            }


            # ------------------------------------------------
            # Backend Hard Guard
            # ------------------------------------------------
            #
            # Verifier 即使说 supported，
            # 但实际一条合法 Evidence 都没有，
            # 后端仍然 Reject。
            if not supporting_evidence:

                verification = (
                    GapVerificationResult(
                        status="rejected",

                        reason=(
                            "Verifier marked the gap "
                            "without valid supporting "
                            "citation metadata."
                        ),

                        supporting_citation_ids=[],

                        counter_evidence_citation_ids=(
                            valid_counter_ids
                        ),

                        scope_limitations=(
                            verification
                            .scope_limitations
                        ),
                    )
                )


            # ------------------------------------------------
            # Evidence Strength
            # ------------------------------------------------

            evidence_strength = (
                _derive_evidence_strength(
                    status=(
                        verification.status
                    ),

                    supporting_evidence=(
                        supporting_evidence
                    ),

                    counter_evidence=(
                        counter_evidence
                    ),
                )
            )


            # ------------------------------------------------
            # Reject
            # ------------------------------------------------

            if (
                verification.status
                == "rejected"
            ):

                rejected_gaps.append(
                    RejectedResearchGapResponse(
                        gap_id=(
                            gap_id
                        ),

                        title=(
                            candidate.title
                        ),

                        gap_statement=(
                            candidate
                            .gap_statement
                        ),

                        reason=(
                            verification.reason
                        ),
                    )
                )


                continue


            # ------------------------------------------------
            # Accepted / Partial
            # ------------------------------------------------

            accepted_gaps.append(
                ResearchGapCandidateResponse(
                    gap_id=(
                        gap_id
                    ),

                    title=(
                        candidate.title
                    ),

                    gap_type=(
                        candidate.gap_type
                    ),

                    gap_statement=(
                        candidate
                        .gap_statement
                    ),

                    evidence_basis=(
                        candidate
                        .evidence_basis
                    ),

                    verification_status=(
                        verification.status
                    ),

                    verification_reason=(
                        verification.reason
                    ),

                    evidence_strength=(
                        evidence_strength
                    ),

                    distinct_supporting_papers=len(
                        supporting_papers
                    ),

                    supporting_evidence=(
                        supporting_evidence
                    ),

                    counter_evidence=(
                        counter_evidence
                    ),

                    scope_limitations=(
                        verification
                        .scope_limitations
                    ),
                )
            )


        # ====================================================
        # 3. Final Scope Note
        # ====================================================

        if response_language == "zh":

            scope_note = (
                "这些研究空白仅基于当前所选论文及其可检索证据建立，"
                "不能据此推断整个学术领域不存在相关研究。"
                "在将某个候选空白作为论文创新点之前，仍需要进一步进行"
                "系统性文献检索与外部数据库验证。"
            )

        else:

            scope_note = (
                "These research gaps are supported only "
                "within the selected papers and retrieved "
                "evidence. They do not establish that the "
                "entire literature lacks related work. "
                "Broader literature verification is still "
                "required before treating a candidate gap "
                "as a novel research contribution."
            )


        # ====================================================
        # 4. Response
        # ====================================================

        return (
            ResearchGapResponse(
                project_id=(
                    project_id
                ),

                paper_count=(
                    comparison.paper_count
                ),

                comparison=(
                    comparison
                ),

                gaps=(
                    accepted_gaps
                ),

                rejected_candidates=(
                    rejected_gaps
                ),

                scope_note=(
                    scope_note
                ),

                model=(
                    model_info
                ),

                prompt=(
                    RAGPromptInfoResponse(
                        system_prompt_id=(
                            RESEARCH_GAP_GENERATION_SYSTEM_PROMPT_ID
                        ),

                        system_prompt_version=(
                            settings
                            .RESEARCH_GAP_GENERATION_PROMPT_VERSION
                        ),

                        user_prompt_id=(
                            RESEARCH_GAP_GENERATION_USER_PROMPT_ID
                        ),

                        user_prompt_version=(
                            settings
                            .RESEARCH_GAP_GENERATION_PROMPT_VERSION
                        ),
                    )
                ),
            )
        )