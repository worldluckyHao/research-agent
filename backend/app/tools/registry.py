from backend.app.tools.base import (
    ResearchTool,
)


class ToolRegistry:
    """
    Tool Registry（工具注册表）。

    类似 Day32 的 PromptRegistry。

    Prompt Registry：
        管 Prompt。

    Tool Registry：
        管 Agent 可以执行的能力。
    """

    def __init__(
        self,
    ):
        self._tools: dict[
            str,
            ResearchTool,
        ] = {}


    def register(
        self,
        tool: ResearchTool,
    ) -> None:
        """
        注册 Tool。

        Tool Name 必须唯一。
        """

        if tool.name in self._tools:

            raise RuntimeError(
                (
                    "Tool already registered: "
                    f"{tool.name}"
                )
            )


        self._tools[
            tool.name
        ] = tool


    def get(
        self,
        tool_name: str,
    ) -> ResearchTool:
        """
        获取 Tool。

        最关键的安全边界：

        Agent 只能调用 Registry
        中真实存在的 Tool。
        """

        tool = (
            self._tools.get(
                tool_name
            )
        )


        if tool is None:

            raise ValueError(
                (
                    "Unknown research tool: "
                    f"{tool_name}"
                )
            )


        return tool


    def list_tools(
        self,
    ) -> list[
        ResearchTool
    ]:
        """
        返回所有允许 Agent 使用的 Tool。
        """

        return list(
            self._tools.values()
        )


    def specifications(
        self,
    ) -> list[dict]:
        """
        返回 Tool Catalog（工具目录）。

        给 Tool Selector LLM 使用。
        """

        return [
            tool.specification()

            for tool
            in self._tools.values()
        ]