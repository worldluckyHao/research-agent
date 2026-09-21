import json
from typing import (
    Any,
)

from pydantic import (
    ValidationError,
)

from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    ResearchExperimentGenerationException,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.prompts.registry import (
    prompt_registry,
)
from backend.app.prompts.research_experiment import (
    EXPERIMENT_DESIGN_SYSTEM_PROMPT_ID,
    EXPERIMENT_DESIGN_USER_PROMPT_ID,
    EXPERIMENT_REVIEW_SYSTEM_PROMPT_ID,
    EXPERIMENT_REVIEW_USER_PROMPT_ID,
)
from backend.app.rag.generation import (
    generate_rag_answer,
)
from backend.app.schemas.research_experiment import (
    ExperimentDesignReviewResponse,
    ResearchExperimentProtocolResponse,
    ResearchExperimentResponse,
)
from backend.app.schemas.research_idea import (
    ResearchIdeaResponse,
    ResearchIdeaResult,
)
from backend.app.schemas.rag import (
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)


# ============================================================
# JSON Parser
# ============================================================

def _parse_json_object(
    text: str,
) -> dict[str, Any]:
    """
    稳健解析 LLM JSON Object。
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
    # Extract Object
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
            ResearchExperimentGenerationException()
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
            ResearchExperimentGenerationException()
        ) from exc


    if not isinstance(
        payload,
        dict,
    ):

        raise (
            ResearchExperimentGenerationException()
        )


    return payload


# ============================================================
# Prompt Payload Helpers
# ============================================================

def _gap_payload(
    selected_idea: ResearchIdeaResult,
) -> str:
    """
    从 Day40 Selected Idea
    提取它对应的 Gap。
    """

    payload = {
        "gap_id":
            selected_idea.source_gap_id,

        "gap_statement":
            selected_idea
            .source_gap_statement,
    }


    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def _idea_payload(
    selected_idea: ResearchIdeaResult,
) -> str:
    """
    将 Day40 Idea 转成 Experiment Agent 输入。
    """

    payload = {
        "idea_id":
            selected_idea.idea_id,

        "title":
            selected_idea.title,

        "problem_statement":
            selected_idea
            .problem_statement,

        "core_hypothesis":
            selected_idea
            .core_hypothesis,

        "proposed_method":
            selected_idea
            .proposed_method,

        "expected_contribution":
            selected_idea
            .expected_contribution,

        "decision":
            selected_idea.decision,

        "decision_reason":
            selected_idea
            .decision_reason,

        "feasibility_review":
            selected_idea
            .feasibility_review
            .model_dump(),

        "novelty_review":
            selected_idea
            .novelty_review
            .model_dump(),
    }


    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def _initial_plan_payload(
    selected_idea: ResearchIdeaResult,
) -> str:
    """
    复用 Day40 初步 Experiment Plan。
    """

    if (
        selected_idea
        .experiment_plan
        is None
    ):

        return "{}"


    return (
        selected_idea
        .experiment_plan
        .model_dump_json(
            indent=2
        )
    )


# ============================================================
# Experiment Designer
# ============================================================

class ExperimentDesignerAgent:
    """
    Day41 Experiment Designer。

    Responsibility：

        Research Idea
            ↓
        Rigorous Experiment Protocol
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


    async def design(
        self,
        selected_idea: ResearchIdeaResult,
        constraints: str,
        experiment_focus: str,
        response_language: str,
    ) -> tuple[
        ResearchExperimentProtocolResponse,
        RAGModelInfoResponse,
    ]:
        """
        生成完整实验协议。
        """

        version = (
            settings
            .EXPERIMENT_DESIGN_PROMPT_VERSION
        )


        # ====================================================
        # Prompt
        # ====================================================

        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    EXPERIMENT_DESIGN_SYSTEM_PROMPT_ID
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
                    EXPERIMENT_DESIGN_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                response_language=(
                    language_name
                ),

                gap_payload=(
                    _gap_payload(
                        selected_idea
                    )
                ),

                idea_payload=(
                    _idea_payload(
                        selected_idea
                    )
                ),

                initial_plan=(
                    _initial_plan_payload(
                        selected_idea
                    )
                ),

                constraints=(
                    constraints
                ),

                experiment_focus=(
                    experiment_focus
                ),

                recommended_runs=(
                    settings
                    .EXPERIMENT_DEFAULT_REPEATED_RUNS
                ),

                default_alpha=(
                    settings
                    .EXPERIMENT_DEFAULT_ALPHA
                ),
            )
        )


        # ====================================================
        # Generation
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
        # Parse + Pydantic Validation
        # ====================================================

        payload = (
            _parse_json_object(
                generation.text
            )
        )


        try:

            protocol = (
                ResearchExperimentProtocolResponse
                .model_validate(
                    payload
                )
            )


        except ValidationError as exc:

            raise (
                ResearchExperimentGenerationException()
            ) from exc


        model_info = (
            RAGModelInfoResponse(
                provider=(
                    generation.provider
                ),

                model_name=(
                    generation.model_name
                ),
            )
        )


        return (
            protocol,
            model_info,
        )


# ============================================================
# Experiment Design Critic
# ============================================================

class ExperimentDesignCriticAgent:
    """
    Experiment Design Critic。

    重点检查：

        Hypothesis-Test Alignment
        Leakage
        Baseline Fairness
        Ablation Coverage
        Metrics
        Statistical Validity
        Reproducibility
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


    async def review(
        self,
        selected_idea: ResearchIdeaResult,
        protocol: ResearchExperimentProtocolResponse,
        constraints: str,
    ) -> ExperimentDesignReviewResponse:
        """
        对 Experiment Protocol
        进行独立审查。
        """

        version = (
            settings
            .EXPERIMENT_REVIEW_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    EXPERIMENT_REVIEW_SYSTEM_PROMPT_ID
                ),

                version=(
                    version
                ),
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    EXPERIMENT_REVIEW_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                idea_payload=(
                    _idea_payload(
                        selected_idea
                    )
                ),

                experiment_protocol=(
                    protocol
                    .model_dump_json(
                        indent=2
                    )
                ),

                constraints=(
                    constraints
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


        try:

            review = (
                ExperimentDesignReviewResponse
                .model_validate(
                    payload
                )
            )


        except ValidationError as exc:

            raise (
                ResearchExperimentGenerationException()
            ) from exc


        # ====================================================
        # Backend Quality Gate
        # ====================================================
        #
        # LLM 如果返回：
        #
        # status = ready
        #
        # 但自己同时列出 major issues，
        # 这是逻辑矛盾。
        #
        # Application 进行确定性修正。

        if (
            review.status == "ready"
            and review.major_issues
        ):

            review = (
                review.model_copy(
                    update={
                        "status":
                            "needs_revision",

                        "reason": (
                            "The reviewer marked the "
                            "protocol as ready but also "
                            "reported major issues. "
                            "Backend consistency guard "
                            "changed the status to "
                            "needs_revision."
                        ),
                    }
                )
            )


        return review


# ============================================================
# Coordinator
# ============================================================

class ResearchExperimentAgent:
    """
    Day41 Coordinator。

    Flow：

        Selected Idea
            ↓
        Experiment Designer
            ↓
        Protocol
            ↓
        Experiment Critic
            ↓
        Final Response
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


        self.designer = (
            ExperimentDesignerAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


        self.critic = (
            ExperimentDesignCriticAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


    async def design_experiment(
        self,
        project_id: int,
        research_idea: ResearchIdeaResponse,
        selected_idea: ResearchIdeaResult,
        constraints: str,
        experiment_focus: str,
        response_language: str,
    ) -> ResearchExperimentResponse:
        """
        执行完整 Day41 Pipeline。
        """

        # ====================================================
        # 1. Design
        # ====================================================

        (
            protocol,
            model_info,
        ) = (
            await self.designer.design(
                selected_idea=(
                    selected_idea
                ),

                constraints=(
                    constraints
                ),

                experiment_focus=(
                    experiment_focus
                ),

                response_language=(
                    response_language
                ),
            )
        )


        # ====================================================
        # 2. Review
        # ====================================================

        review = (
            await self.critic.review(
                selected_idea=(
                    selected_idea
                ),

                protocol=(
                    protocol
                ),

                constraints=(
                    constraints
                ),
            )
        )


        # ====================================================
        # 3. Scientific Scope Note
        # ====================================================

        if response_language == "zh":

            scope_note = (
                "该实验设计由系统根据当前 Research Gap、"
                "Research Idea 和用户约束生成，属于实验协议草案。"
                "统计检验、数据划分和评价指标仍应根据最终数据分布、"
                "任务假设和论文领域规范进行确认。"
                "实验结果只能提供支持或反驳研究假设的证据，"
                "不能由预设实验方案提前保证模型有效。"
            )

        else:

            scope_note = (
                "This experiment design is a protocol "
                "draft derived from the current research "
                "gap, research idea, and project constraints. "
                "Statistical tests, data splits, and metrics "
                "must still be confirmed against the final "
                "data distribution and domain assumptions. "
                "The protocol does not predetermine that the "
                "proposed method will succeed."
            )


        # ====================================================
        # 4. Response
        # ====================================================

        return (
            ResearchExperimentResponse(
                project_id=(
                    project_id
                ),

                source_gap_id=(
                    selected_idea
                    .source_gap_id
                ),

                source_idea_id=(
                    selected_idea
                    .idea_id
                ),

                research_idea=(
                    research_idea
                ),

                selected_idea=(
                    selected_idea
                ),

                experiment_protocol=(
                    protocol
                ),

                design_review=(
                    review
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
                            EXPERIMENT_DESIGN_SYSTEM_PROMPT_ID
                        ),

                        system_prompt_version=(
                            settings
                            .EXPERIMENT_DESIGN_PROMPT_VERSION
                        ),

                        user_prompt_id=(
                            EXPERIMENT_DESIGN_USER_PROMPT_ID
                        ),

                        user_prompt_version=(
                            settings
                            .EXPERIMENT_DESIGN_PROMPT_VERSION
                        ),
                    )
                ),
            )
        )