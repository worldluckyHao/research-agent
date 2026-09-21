from dataclasses import dataclass
from string import Formatter


@dataclass(frozen=True)
class PromptDefinition:
    """
    Prompt Definition（提示词定义）。

    一个 Prompt 由：

        prompt_id
        version
        template
        description

    组成。
    """

    prompt_id: str

    version: int

    template: str

    description: str


    def required_variables(
        self,
    ) -> set[str]:
        """
        从 Template 中提取需要的变量。

        Example:

            "Hello {name}"

        -> {"name"}
        """

        formatter = Formatter()


        variables = set()


        for (
            _literal_text,
            field_name,
            _format_spec,
            _conversion,
        ) in formatter.parse(
            self.template
        ):

            if field_name:

                variables.add(
                    field_name
                )


        return variables


    def render(
        self,
        **variables,
    ) -> str:
        """
        渲染 Prompt。

        对变量做严格校验：

        1. 缺变量 → 报错
        2. 多传变量允许
           （方便上层统一 payload）
        """

        required = (
            self.required_variables()
        )


        missing = (
            required
            - variables.keys()
        )


        if missing:

            missing_names = (
                ", ".join(
                    sorted(
                        missing
                    )
                )
            )


            raise ValueError(
                (
                    "Missing prompt variables: "
                    f"{missing_names}"
                )
            )


        return (
            self.template
            .format(
                **variables
            )
            .strip()
        )