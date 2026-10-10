from backend.app.core.exceptions import (
    PromptNotFoundException,
    PromptRenderException,
)
from backend.app.prompts.base import (
    PromptDefinition,
)
import logging
logger = logging.getLogger(__name__)
class PromptRegistry:
    """
    Prompt Registry（提示词注册表）。

    Key：

        (prompt_id, version)

    Example：

        ("rag.answer.system", 1)
    """

    def __init__(
        self,
    ):
        self._prompts: dict[
            tuple[str, int],
            PromptDefinition,
        ] = {}


    def register(
        self,
        prompt: PromptDefinition,
    ) -> None:
        """
        注册 Prompt。

        不允许重复注册同一个：
            prompt_id + version
        """

        key = (
            prompt.prompt_id,
            prompt.version,
        )


        if key in self._prompts:

            raise RuntimeError(
                (
                    "Prompt already registered: "
                    f"{prompt.prompt_id} "
                    f"v{prompt.version}"
                )
            )


        self._prompts[
            key
        ] = prompt


    def get(
        self,
        prompt_id: str,
        version: int,
    ) -> PromptDefinition:
        """
        按 ID + Version 获取 Prompt。
        """

        key = (
            prompt_id,
            version,
        )


        prompt = (
            self._prompts.get(
                key
            )
        )


        if prompt is None:

            raise (
                PromptNotFoundException(
                    prompt_id=(
                        prompt_id
                    ),
                    version=(
                        version
                    ),
                )
            )


        return prompt

    def render(
            self,
            prompt_id: str,
            version: int,
            **variables,
    ) -> str:
        """
        获取并渲染 Prompt。
        """

        prompt = self.get(
            prompt_id=prompt_id,
            version=version,
        )

        try:
            return prompt.render(
                **variables
            )

        except (
                KeyError,
                ValueError,
        ) as exc:
            raise (
                PromptRenderException()
            ) from exc

prompt_registry = (
    PromptRegistry()
)