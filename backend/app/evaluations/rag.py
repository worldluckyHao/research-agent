import re
from typing import (
    List,
    Optional,
    Set,
)

from backend.app.schemas.rag_evaluation import (
    CitationEvaluationMetrics,
    RAGEvaluationEvidence,
    RetrievalEvaluationMetrics,
)


# ============================================================
# Citation Pattern
# ============================================================

_CITATION_PATTERN = re.compile(
    r"\[S(\d+)\]"
)


# ============================================================
# Source ID
# ============================================================

def _normalize_source_id(
    source_id: str,
) -> str:
    """
    Normalize：

        s1
        S1
        [S1]

    →

        S1
    """

    normalized = (
        source_id
        .strip()
        .upper()
    )


    if (
        normalized.startswith("[")
        and normalized.endswith("]")
    ):

        normalized = (
            normalized[1:-1]
        )


    return normalized


# ============================================================
# Retrieval Evaluation
# ============================================================

def evaluate_retrieval(
    evidence: List[
        RAGEvaluationEvidence
    ],

    gold_source_ids: Optional[
        List[str]
    ],
) -> RetrievalEvaluationMetrics:
    """
    Retrieval Evaluation。

    当没有 Gold Label 时：

        available=False

    因为不能凭空判断 Retriever
    找到的来源是否真的相关。
    """

    if not gold_source_ids:

        return (
            RetrievalEvaluationMetrics(
                available=False,
            )
        )


    retrieved = [
        _normalize_source_id(
            item.source_id
        )
        for item in evidence
    ]


    gold: Set[str] = {
        _normalize_source_id(
            source_id
        )
        for source_id
        in gold_source_ids
    }


    # --------------------------------------------------------
    # Intersection
    # --------------------------------------------------------

    relevant_retrieved = [
        source_id
        for source_id
        in retrieved
        if source_id in gold
    ]


    # --------------------------------------------------------
    # Precision@K
    # --------------------------------------------------------

    if retrieved:

        precision_at_k = (
            len(
                relevant_retrieved
            )
            /
            len(
                retrieved
            )
        )

    else:

        precision_at_k = 0.0


    # --------------------------------------------------------
    # Recall@K
    # --------------------------------------------------------

    if gold:

        recall_at_k = (
            len(
                set(
                    relevant_retrieved
                )
            )
            /
            len(
                gold
            )
        )

    else:

        recall_at_k = 0.0


    # --------------------------------------------------------
    # Hit Rate
    # --------------------------------------------------------

    hit_rate = (
        1.0
        if relevant_retrieved
        else 0.0
    )


    # --------------------------------------------------------
    # MRR
    # --------------------------------------------------------

    mrr = 0.0


    for rank, source_id in enumerate(
        retrieved,
        start=1,
    ):

        if source_id in gold:

            mrr = (
                1.0
                /
                float(rank)
            )

            break


    return (
        RetrievalEvaluationMetrics(
            available=True,

            precision_at_k=(
                round(
                    precision_at_k,
                    4,
                )
            ),

            recall_at_k=(
                round(
                    recall_at_k,
                    4,
                )
            ),

            hit_rate=(
                round(
                    hit_rate,
                    4,
                )
            ),

            mrr=(
                round(
                    mrr,
                    4,
                )
            ),
        )
    )


# ============================================================
# Citation Evaluation
# ============================================================

def evaluate_citations(
    answer: str,

    evidence: List[
        RAGEvaluationEvidence
    ],
) -> CitationEvaluationMetrics:
    """
    Citation Evaluation。

    Example：

        Answer:

            The method uses attention [S1].
            Training uses Adam [S2].

    Evidence：

        S1
        S2
        S3

    此时：

        total citations = 2
        valid citations = 2
        citation precision = 1.0
        source coverage = 2 / 3
    """

    matches = (
        _CITATION_PATTERN
        .findall(
            answer
        )
    )


    citations = [
        f"S{number}"
        for number in matches
    ]


    evidence_ids = {
        _normalize_source_id(
            item.source_id
        )
        for item in evidence
    }


    valid = [
        citation
        for citation in citations
        if citation in evidence_ids
    ]


    invalid = [
        citation
        for citation in citations
        if citation not in evidence_ids
    ]


    # --------------------------------------------------------
    # Citation Precision
    # --------------------------------------------------------

    if citations:

        citation_precision = (
            len(valid)
            /
            len(citations)
        )

    else:

        citation_precision = 0.0


    # --------------------------------------------------------
    # Source Citation Coverage
    # --------------------------------------------------------

    unique_valid = set(
        valid
    )


    if evidence_ids:

        source_coverage = (
            len(
                unique_valid
            )
            /
            len(
                evidence_ids
            )
        )

    else:

        source_coverage = 0.0


    return (
        CitationEvaluationMetrics(
            total_citations=(
                len(citations)
            ),

            unique_citations=(
                len(
                    set(
                        citations
                    )
                )
            ),

            valid_citations=(
                len(valid)
            ),

            invalid_citations=(
                len(invalid)
            ),

            citation_precision=(
                round(
                    citation_precision,
                    4,
                )
            ),

            source_citation_coverage=(
                round(
                    source_coverage,
                    4,
                )
            ),

            invalid_source_ids=(
                sorted(
                    set(
                        invalid
                    )
                )
            ),
        )
    )