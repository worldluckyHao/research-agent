from typing import (
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from backend.app.schemas.rag import (
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)


# ============================================================
# Request
# ============================================================

class PaperComparisonItemRequest(
    BaseModel
):
    """
    一篇待比较论文。

    Day38 要求显式传：

        paper_id
        document_id

    为什么不自动猜最新 Document？

    因为同一篇 Paper 以后可能存在：
        原稿
        修订稿
        Supplement
        不同 PDF

    Comparison 应明确知道
    到底比较哪个文档版本。
    """

    paper_id: int = Field(
        ge=1,
    )

    document_id: int = Field(
        ge=1,
    )


class PaperComparisonRequest(
    BaseModel
):
    """
    多论文比较请求。
    """

    # Schema 最大暂时放宽到 10。
    #
    # 真正生产限制由：
    # settings.PAPER_COMPARISON_MAX_PAPERS
    #
    # 在 Service 层统一控制。
    items: list[
        PaperComparisonItemRequest
    ] = Field(
        min_length=2,
        max_length=10,
    )


    # 用户可以指定关注点：
    #
    # "重点比较多模态融合方法"
    # "重点比较 Transformer 结构"
    #
    # 不指定则使用默认全维度比较。
    focus: Optional[str] = Field(
        default=None,
        max_length=500,
    )


    # Day38 默认中文结果。
    response_language: Literal[
        "zh",
        "en",
    ] = "zh"


    @model_validator(
        mode="after"
    )
    def validate_unique_items(
        self,
    ):
        """
        同一次比较中：

        paper_id 不能重复
        document_id 不能重复。
        """

        paper_ids = [
            item.paper_id
            for item in self.items
        ]


        document_ids = [
            item.document_id
            for item in self.items
        ]


        if (
            len(paper_ids)
            != len(set(paper_ids))
        ):

            raise ValueError(
                (
                    "Each paper can only appear "
                    "once in a comparison"
                )
            )


        if (
            len(document_ids)
            != len(set(document_ids))
        ):

            raise ValueError(
                (
                    "Each document can only appear "
                    "once in a comparison"
                )
            )


        return self


# ============================================================
# Citation
# ============================================================

class PaperComparisonCitationResponse(
    BaseModel
):
    """
    多论文引用。

    Example:

        P1-S1
        P2-S3

    防止不同 Paper 的 S1 冲突。
    """

    citation_id: str

    paper_id: int

    document_id: int

    chunk_id: int

    chunk_index: int

    start_page: int

    end_page: int


# ============================================================
# Per-Paper Analysis
# ============================================================

class PaperComparisonPaperResponse(
    BaseModel
):
    """
    一篇论文在 Comparison 中的分析结果。
    """

    # P1 / P2 / P3 ...
    label: str

    paper_id: int

    document_id: int

    title: str

    evidence_summary: str

    grounded: bool

    citations: list[
        PaperComparisonCitationResponse
    ]

    invalid_citations: list[str]


# ============================================================
# Matrix
# ============================================================

class PaperComparisonMatrixRow(
    BaseModel
):
    """
    一行 Comparison Matrix。

    Example:

        dimension = "Dataset"

        values = {
            "P1": "ERA5...",
            "P2": "Radar..."
        }
    """

    dimension: str

    values: dict[
        str,
        str,
    ]


# ============================================================
# Final Response
# ============================================================

class PaperComparisonResponse(
    BaseModel
):
    """
    Day38 最终论文比较结果。
    """

    project_id: int

    paper_count: int


    # 每篇论文自己的 Evidence Summary。
    papers: list[
        PaperComparisonPaperResponse
    ]


    # 综合比较摘要。
    overall_summary: str


    # 结构化横向比较表。
    matrix: list[
        PaperComparisonMatrixRow
    ]


    # 关键差异。
    key_differences: list[str]


    # 对研究设计有帮助的观察。
    research_takeaways: list[str]


    # 当前含义仍然只是：
    #
    # 至少存在合法引用
    # +
    # 没有未知引用 ID。
    #
    # 不代表语义级绝对事实正确。
    grounded: bool


    citations: list[
        PaperComparisonCitationResponse
    ]


    invalid_citations: list[str]


    model: Optional[
        RAGModelInfoResponse
    ] = None


    prompt: Optional[
        RAGPromptInfoResponse
    ] = None