import json
import re
from dataclasses import (
    dataclass,
)
from typing import (
    Any,
    Optional,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    PaperComparisonGenerationException,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.models.paper import (
    Paper,
)
from backend.app.models.paper_document import (
    PaperDocument,
)
from backend.app.prompts.paper_comparison import (
    PAPER_COMPARISON_SYSTEM_PROMPT_ID,
    PAPER_COMPARISON_USER_PROMPT_ID,
)
from backend.app.prompts.registry import (
    prompt_registry,
)
from backend.app.rag.generation import (
    generate_rag_answer,
)
from backend.app.schemas.paper_comparison import (
    PaperComparisonCitationResponse,
    PaperComparisonMatrixRow,
    PaperComparisonPaperResponse,
    PaperComparisonResponse,
)
from backend.app.schemas.rag import (
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)
from backend.app.services import (
    rag_service,
)
from backend.app.observability.langsmith import (
    observed_async,
)

# ============================================================
# Source
# ============================================================

@dataclass(frozen=True)
class ComparisonPaperSource:
    """
    一个经过 Service Authorization
    验证后的 Comparison Source。
    """

    paper: Paper

    document: PaperDocument


# ============================================================
# Extraction Question
# ============================================================

PER_PAPER_EXTRACTION_QUESTION = """
Identify the paper's:
1. research problem or forecasting task,
2. core method or architecture,
3. datasets and data sources,
4. input modalities or variables,
5. training or experimental setup,
6. evaluation metrics,
7. major reported findings,
8. claimed contributions or strengths,
9. explicitly stated or evidence-supported limitations.

Use only evidence from the document.
Cite factual statements with the available source IDs.
""".strip()


# ============================================================
# Citation Regex
# ============================================================

SINGLE_PAPER_CITATION_PATTERN = (
    re.compile(
        r"\[(S\d+)\]"
    )
)

COMPARISON_CITATION_PATTERN = (
    re.compile(
        r"\[(P\d+-S\d+)\]"
    )
)


# ============================================================
# JSON Parsing
# ============================================================

def _parse_json_object(
    text: str,
) -> dict[str, Any]:
    """
    尽量稳健解析 Comparison JSON。
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
    # Direct JSON
    # --------------------------------------------------------

    try:

        payload = (
            json.loads(
                cleaned
            )
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
    # Extract First JSON Object
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
            PaperComparisonGenerationException()
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
            PaperComparisonGenerationException()
        ) from exc


    if not isinstance(
        payload,
        dict,
    ):

        raise (
            PaperComparisonGenerationException()
        )


    return payload


# ============================================================
# Citation Namespace
# ============================================================

def _namespace_paper_answer(
    answer: str,
    paper_label: str,
    valid_source_ids: set[str],
) -> str:
    """
    将单论文：

        [S1]

    转换成：

        [P1-S1]

    如果原 Answer 引用了非法 Source：

        [S999]

    则不把它带进最终 Comparison。
    """

    def replace_match(
        match,
    ) -> str:

        source_id = (
            match.group(1)
        )


        if (
            source_id
            not in valid_source_ids
        ):

            return ""


        return (
            f"[{paper_label}-"
            f"{source_id}]"
        )


    return (
        SINGLE_PAPER_CITATION_PATTERN
        .sub(
            replace_match,
            answer,
        )
        .strip()
    )


# ============================================================
# Per-Paper Evidence Analysis
# ============================================================

async def _analyze_single_paper(
    db: AsyncSession,
    source: ComparisonPaperSource,
    paper_label: str,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
) -> PaperComparisonPaperResponse:
    """
    使用已经存在的 RAG Pipeline
    分析一篇论文。

    注意：

    这里不重新实现：
        Retrieval
        Agent
        Citation

    直接复用：
        rag_service.answer_document_question()
    """

    rag_response = (
        await rag_service
        .answer_document_question(
            db=db,

            document=(
                source.document
            ),

            question=(
                PER_PAPER_EXTRACTION_QUESTION
            ),

            top_k=(
                settings
                .PAPER_COMPARISON_PER_PAPER_TOP_K
            ),

            use_reranker=True,

            embedding_provider=(
                embedding_provider
            ),

            llm_provider=(
                llm_provider
            ),

            conversation_history=None,
        )
    )


    # ========================================================
    # Build Citation Namespace
    # ========================================================

    valid_source_ids = {
        citation.source_id

        for citation
        in rag_response.citations
    }


    evidence_summary = (
        _namespace_paper_answer(
            answer=(
                rag_response.answer
            ),

            paper_label=(
                paper_label
            ),

            valid_source_ids=(
                valid_source_ids
            ),
        )
    )


    # ========================================================
    # Convert Citation Metadata
    # ========================================================

    citations = [
        PaperComparisonCitationResponse(
            citation_id=(
                f"{paper_label}-"
                f"{citation.source_id}"
            ),

            paper_id=(
                source.paper.id
            ),

            document_id=(
                source.document.id
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

        for citation
        in rag_response.citations
    ]


    invalid_citations = [
        (
            f"{paper_label}-"
            f"{source_id}"
        )

        for source_id
        in rag_response.invalid_citations
    ]


    return (
        PaperComparisonPaperResponse(
            label=(
                paper_label
            ),

            paper_id=(
                source.paper.id
            ),

            document_id=(
                source.document.id
            ),

            title=(
                source.paper.title
            ),

            evidence_summary=(
                evidence_summary
            ),

            grounded=(
                rag_response.grounded
            ),

            citations=(
                citations
            ),

            invalid_citations=(
                invalid_citations
            ),
        )
    )


# ============================================================
# Prompt Evidence
# ============================================================

def _build_comparison_input(
    papers: list[
        PaperComparisonPaperResponse
    ],
) -> str:
    """
    将多篇 Evidence Summary
    构造成 Comparison Prompt 输入。
    """

    blocks = []


    for paper in papers:

        grounded_text = (
            "true"
            if paper.grounded
            else "false"
        )


        blocks.append(
            (
                f"Paper Label: "
                f"{paper.label}\n"
                f"Title: "
                f"{paper.title}\n"
                f"Grounded Summary: "
                f"{grounded_text}\n"
                f"Evidence Summary:\n"
                f"{paper.evidence_summary}"
            )
        )


    return "\n\n---\n\n".join(
        blocks
    )


# ============================================================
# Matrix Parser
# ============================================================

def _parse_matrix(
    payload: dict[str, Any],
) -> list[
    PaperComparisonMatrixRow
]:
    """
    将 LLM JSON Matrix
    转换成 Pydantic Response。
    """

    raw_matrix = (
        payload.get(
            "matrix",
            [],
        )
    )


    if not isinstance(
        raw_matrix,
        list,
    ):

        return []


    rows = []


    for raw_row in raw_matrix:

        if not isinstance(
            raw_row,
            dict,
        ):

            continue


        dimension = str(
            raw_row.get(
                "dimension",
                "",
            )
        ).strip()


        raw_values = (
            raw_row.get(
                "values",
                {},
            )
        )


        if (
            not dimension
            or not isinstance(
                raw_values,
                dict,
            )
        ):

            continue


        values = {
            str(key):
                str(value)

            for (
                key,
                value,
            )
            in raw_values.items()
        }


        rows.append(
            PaperComparisonMatrixRow(
                dimension=(
                    dimension
                ),

                values=(
                    values
                ),
            )
        )


    return rows


# ============================================================
# List Parser
# ============================================================

def _parse_string_list(
    payload: dict[str, Any],
    key: str,
) -> list[str]:
    """
    稳健读取 JSON string list。
    """

    raw_value = (
        payload.get(
            key,
            [],
        )
    )


    if not isinstance(
        raw_value,
        list,
    ):

        return []


    return [
        str(item).strip()

        for item in raw_value

        if str(item).strip()
    ]


# ============================================================
# Citation Extraction
# ============================================================

def _extract_comparison_citation_ids(
    overall_summary: str,
    matrix: list[
        PaperComparisonMatrixRow
    ],
    key_differences: list[str],
    research_takeaways: list[str],
) -> list[str]:
    """
    从整个 Comparison Result 中
    收集 [P1-S1] Citation IDs。
    """

    texts = [
        overall_summary,
        *key_differences,
        *research_takeaways,
    ]


    for row in matrix:

        texts.extend(
            row.values.values()
        )


    ordered_ids = []


    seen = set()


    for text in texts:

        for match in (
            COMPARISON_CITATION_PATTERN
            .finditer(
                text
            )
        ):

            citation_id = (
                match.group(1)
            )


            if citation_id in seen:

                continue


            seen.add(
                citation_id
            )


            ordered_ids.append(
                citation_id
            )


    return ordered_ids


# ============================================================
# Agent
# ============================================================

class PaperComparisonAgent:
    """
    Paper Comparison Agent
    （论文对比智能体）。

    Responsibilities：

        1. 对每篇论文运行 Evidence-Grounded RAG
        2. 给 Citation 增加 Paper Namespace
        3. 汇总多论文 Evidence
        4. 使用 Comparison Prompt 综合
        5. 验证 Cross-Paper Citation

    它不负责：

        Project Authorization
        ProjectPaper Membership

    这些由 Service Layer 负责。
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )

    @observed_async(
        name="agent.paper_comparison",
        run_type="chain",
        tags=[
            "agent",
            "paper-comparison",
        ],
    )

    async def compare(
        self,
        db: AsyncSession,
        project_id: int,
        sources: list[
            ComparisonPaperSource
        ],
        focus: Optional[str],
        response_language: str,
        embedding_provider: EmbeddingProvider,
    ) -> PaperComparisonResponse:
        """
        执行多论文比较。
        """

        # ====================================================
        # 1. Per-Paper Analysis
        # ====================================================

        paper_results = []


        # ----------------------------------------------------
        # 为什么这里暂时顺序执行？
        #
        # 因为：
        # 1. 共用同一个 AsyncSession
        # 2. 当前本地 LLMProvider 也共享模型实例
        #
        # 不应该直接：
        # asyncio.gather(...)
        #
        # 强行并发可能导致：
        # AsyncSession concurrent operation
        # GPU Memory Spike
        # ----------------------------------------------------

        for index, source in enumerate(
            sources,
            start=1,
        ):

            paper_label = (
                f"P{index}"
            )


            result = (
                await _analyze_single_paper(
                    db=db,

                    source=(
                        source
                    ),

                    paper_label=(
                        paper_label
                    ),

                    embedding_provider=(
                        embedding_provider
                    ),

                    llm_provider=(
                        self.llm_provider
                    ),
                )
            )


            paper_results.append(
                result
            )


        # ====================================================
        # 2. Comparison Evidence
        # ====================================================

        paper_summaries = (
            _build_comparison_input(
                paper_results
            )
        )


        # ====================================================
        # 3. Prompt Version
        # ====================================================

        version = (
            settings
            .PAPER_COMPARISON_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    PAPER_COMPARISON_SYSTEM_PROMPT_ID
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


        normalized_focus = (
            focus.strip()
            if focus
            else (
                "General comparison across "
                "methods, datasets, evaluation, "
                "findings, strengths, and limitations."
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    PAPER_COMPARISON_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                response_language=(
                    language_name
                ),

                focus=(
                    normalized_focus
                ),

                paper_summaries=(
                    paper_summaries
                ),
            )
        )


        # ====================================================
        # 4. Comparison Generation
        # ====================================================

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


        # ====================================================
        # 5. Parse Structured Output
        # ====================================================

        payload = (
            _parse_json_object(
                generation.text
            )
        )


        overall_summary = str(
            payload.get(
                "overall_summary",
                "",
            )
        ).strip()


        matrix = (
            _parse_matrix(
                payload
            )
        )


        key_differences = (
            _parse_string_list(
                payload=(
                    payload
                ),

                key=(
                    "key_differences"
                ),
            )
        )


        research_takeaways = (
            _parse_string_list(
                payload=(
                    payload
                ),

                key=(
                    "research_takeaways"
                ),
            )
        )


        # ====================================================
        # 6. Available Citations
        # ====================================================

        all_citations = [
            citation

            for paper
            in paper_results

            for citation
            in paper.citations
        ]


        citation_map = {
            citation.citation_id:
                citation

            for citation
            in all_citations
        }


        # ====================================================
        # 7. Validate Citations
        # ====================================================

        referenced_ids = (
            _extract_comparison_citation_ids(
                overall_summary=(
                    overall_summary
                ),

                matrix=(
                    matrix
                ),

                key_differences=(
                    key_differences
                ),

                research_takeaways=(
                    research_takeaways
                ),
            )
        )


        used_citations = []


        invalid_citations = []


        for citation_id in referenced_ids:

            citation = (
                citation_map.get(
                    citation_id
                )
            )


            if citation is None:

                invalid_citations.append(
                    citation_id
                )

                continue


            used_citations.append(
                citation
            )


        grounded = (
            bool(
                used_citations
            )
            and not invalid_citations
        )


        # ====================================================
        # 8. Final Response
        # ====================================================

        return (
            PaperComparisonResponse(
                project_id=(
                    project_id
                ),

                paper_count=len(
                    paper_results
                ),

                papers=(
                    paper_results
                ),

                overall_summary=(
                    overall_summary
                ),

                matrix=(
                    matrix
                ),

                key_differences=(
                    key_differences
                ),

                research_takeaways=(
                    research_takeaways
                ),

                grounded=(
                    grounded
                ),

                citations=(
                    used_citations
                ),

                invalid_citations=(
                    invalid_citations
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
                            PAPER_COMPARISON_SYSTEM_PROMPT_ID
                        ),

                        system_prompt_version=(
                            version
                        ),

                        user_prompt_id=(
                            PAPER_COMPARISON_USER_PROMPT_ID
                        ),

                        user_prompt_version=(
                            version
                        ),
                    )
                ),
            )
        )