import pytest

from backend.app.evaluations.rag import (
    evaluate_citations,
    evaluate_retrieval,
)
from backend.app.schemas.rag_evaluation import (
    RAGEvaluationEvidence,
)


pytestmark = pytest.mark.unit


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def evidence():
    """
    三条模拟 Evidence。
    """

    return [
        RAGEvaluationEvidence(
            source_id="S1",
            content="Evidence one.",
        ),
        RAGEvaluationEvidence(
            source_id="S2",
            content="Evidence two.",
        ),
        RAGEvaluationEvidence(
            source_id="S3",
            content="Evidence three.",
        ),
    ]


# ============================================================
# Retrieval
# ============================================================

def test_retrieval_metrics_with_gold(
    evidence,
):
    """
    Retrieved:
        S1 S2 S3

    Gold:
        S1 S3

    Precision = 2 / 3
    Recall = 2 / 2
    Hit Rate = 1
    MRR = 1 / 1
    """

    result = evaluate_retrieval(
        evidence=evidence,

        gold_source_ids=[
            "S1",
            "S3",
        ],
    )


    assert result.available is True

    assert result.precision_at_k == (
        0.6667
    )

    assert result.recall_at_k == 1.0

    assert result.hit_rate == 1.0

    assert result.mrr == 1.0


def test_retrieval_without_gold_is_unavailable(
    evidence,
):
    """
    没有 Gold Label 时，
    不应该伪造 Retrieval Score。
    """

    result = evaluate_retrieval(
        evidence=evidence,

        gold_source_ids=None,
    )


    assert result.available is False

    assert result.precision_at_k is None

    assert result.recall_at_k is None

    assert result.hit_rate is None

    assert result.mrr is None


# ============================================================
# Citation
# ============================================================

def test_citation_metrics_all_valid(
    evidence,
):
    answer = (
        "Claim one [S1]. "
        "Claim two [S2]."
    )


    result = evaluate_citations(
        answer=answer,
        evidence=evidence,
    )


    assert result.total_citations == 2

    assert result.valid_citations == 2

    assert result.invalid_citations == 0

    assert result.citation_precision == 1.0

    assert (
        result.source_citation_coverage
        ==
        0.6667
    )

    assert result.invalid_source_ids == []


def test_citation_metrics_detect_invalid_source(
    evidence,
):
    answer = (
        "Supported claim [S1]. "
        "Invalid citation [S99]."
    )


    result = evaluate_citations(
        answer=answer,
        evidence=evidence,
    )


    assert result.total_citations == 2

    assert result.valid_citations == 1

    assert result.invalid_citations == 1

    assert result.citation_precision == 0.5

    assert result.invalid_source_ids == [
        "S99"
    ]