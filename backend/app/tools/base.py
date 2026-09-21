from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import dataclass, field
from typing import Any

from backend.app.retrieval.base import (
    RetrievalCandidate,
)


# ============================================================
# Tool Result
# ============================================================

@dataclass(frozen=True)
class ToolResult:
    """
    Tool Execution Result（工具执行结果）。

    Agent 不应该直接依赖某个 Tool
    自己的内部返回结构。

    所有 Research Tool
    最终统一转换成 ToolResult。
    """

    tool_name: str

    success: bool

    message: str

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    # Search Tool 返回 Evidence Candidate。
    #
    # 非 Search Tool 可以为空。
    candidates: list[
        RetrievalCandidate
    ] = field(
        default_factory=list
    )


    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    # Tool 特有信息：
    #
    # returned_count
    # query
    # provider
    # ...
    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )


# ============================================================
# Tool Interface
# ============================================================

class ResearchTool(
    ABC
):
    """
    Research Tool（科研智能体工具）
    的统一抽象。

    每个 Tool 必须提供：

        name
        description
        execute()

    Agent 不应该知道 Tool
    的内部实现。
    """

    name: str

    description: str


    @abstractmethod
    async def execute(
        self,
        query: str,
        top_k: int,
    ) -> ToolResult:
        """
        执行 Tool。
        """


    def specification(
        self,
    ) -> dict:
        """
        给 Tool Selector 使用的
        Tool Specification（工具说明）。

        注意：

        这里不会暴露：
            database password
            API key
            implementation details

        只暴露模型做选择需要的信息。
        """

        return {
            "name":
                self.name,

            "description":
                self.description,
        }