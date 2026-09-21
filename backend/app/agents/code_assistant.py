import json
import posixpath
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
    CodeAssistantGenerationException,
    CodeAssistantPathViolationException,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.prompts.code_assistant import (
    CODE_PATCH_SYSTEM_PROMPT_ID,
    CODE_PATCH_USER_PROMPT_ID,
    CODE_PLANNING_SYSTEM_PROMPT_ID,
    CODE_PLANNING_USER_PROMPT_ID,
    CODE_REVIEW_SYSTEM_PROMPT_ID,
    CODE_REVIEW_USER_PROMPT_ID,
    CODE_VALIDATION_SYSTEM_PROMPT_ID,
    CODE_VALIDATION_USER_PROMPT_ID,
)
from backend.app.prompts.registry import (
    prompt_registry,
)
from backend.app.rag.generation import (
    generate_rag_answer,
)
from backend.app.schemas.code_assistant import (
    CodeAssistantResponse,
    CodeFilePlanResponse,
    CodePatchProposalResponse,
    CodeSafetyReviewResponse,
    CodeValidationStepResponse,
)
from backend.app.schemas.research_experiment import (
    ResearchExperimentResponse,
)
from backend.app.schemas.research_idea import (
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
    稳健解析 LLM JSON。
    """

    cleaned = (
        text.strip()
    )


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
            CodeAssistantGenerationException()
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
            CodeAssistantGenerationException()
        ) from exc


    if not isinstance(
        payload,
        dict,
    ):

        raise (
            CodeAssistantGenerationException()
        )


    return payload


# ============================================================
# Path Helpers
# ============================================================

def _normalize_relative_path(
    path: str,
) -> str:
    """
    将模型返回的路径标准化成
    POSIX Style Relative Path。

    Example:

        \\research\\models\\a.py
        ->
        research/models/a.py
    """

    normalized = (
        path.strip()
        .replace("\\", "/")
    )


    normalized = (
        posixpath.normpath(
            normalized
        )
    )


    # 去除开头的 "./"
    while normalized.startswith(
        "./"
    ):

        normalized = (
            normalized[2:]
        )


    return normalized


def _normalize_allowed_paths(
    allowed_paths: list[str],
) -> list[str]:
    """
    规范 Allowlist Prefix。
    """

    result = []


    for path in allowed_paths:

        normalized = (
            _normalize_relative_path(
                path
            )
        )


        if not normalized.endswith(
            "/"
        ):

            normalized += "/"


        result.append(
            normalized
        )


    return result


def _is_path_allowed(
    file_path: str,
    allowed_paths: list[str],
) -> bool:
    """
    检查 File 是否位于任一允许目录下。
    """

    normalized_file = (
        _normalize_relative_path(
            file_path
        )
    )


    # 防止：
    # ../
    if (
        normalized_file == ".."
        or normalized_file.startswith(
            "../"
        )
    ):

        return False


    normalized_allowlist = (
        _normalize_allowed_paths(
            allowed_paths
        )
    )


    return any(
        normalized_file.startswith(
            prefix
        )

        for prefix
        in normalized_allowlist
    )


def _blocked_keywords() -> list[str]:
    """
    从 Settings 读取敏感路径关键词。
    """

    return [
        item.strip().lower()

        for item
        in settings
        .CODE_ASSISTANT_BLOCKED_PATH_KEYWORDS
        .split(",")

        if item.strip()
    ]


def _contains_blocked_keyword(
    file_path: str,
) -> bool:
    normalized = (
        _normalize_relative_path(
            file_path
        )
        .lower()
    )


    return any(
        keyword in normalized

        for keyword
        in _blocked_keywords()
    )


def _validate_file_path(
    file_path: str,
    allowed_paths: list[str],
) -> str:
    """
    Application-Level Path Guard。

    模型即使生成非法路径，
    后端也会拒绝。
    """

    normalized = (
        _normalize_relative_path(
            file_path
        )
    )


    if not _is_path_allowed(
        normalized,
        allowed_paths,
    ):

        raise (
            CodeAssistantPathViolationException()
        )


    if _contains_blocked_keyword(
        normalized
    ):

        raise (
            CodeAssistantPathViolationException()
        )


    return normalized


# ============================================================
# Payload Helpers
# ============================================================

def _idea_payload(
    selected_idea: ResearchIdeaResult,
) -> str:
    return (
        selected_idea
        .model_dump_json(
            indent=2
        )
    )


def _experiment_payload(
    experiment: ResearchExperimentResponse,
) -> str:
    """
    只给 Code Assistant
    真正需要的 Protocol，
    避免整个 Pipeline Context 太长。
    """

    payload = {
        "source_gap_id":
            experiment.source_gap_id,

        "source_idea_id":
            experiment.source_idea_id,

        "experiment_protocol":
            experiment
            .experiment_protocol
            .model_dump(),

        "design_review":
            experiment
            .design_review
            .model_dump(),
    }


    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


# ============================================================
# Code Planner
# ============================================================

class CodePlannerAgent:
    """
    Research Experiment
        ↓
    File Plan
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


    async def plan(
        self,
        selected_idea: ResearchIdeaResult,
        experiment: ResearchExperimentResponse,
        allowed_paths: list[str],
        max_file_changes: int,
        include_tests: bool,
        response_language: str,
    ) -> tuple[
        list[CodeFilePlanResponse],
        RAGModelInfoResponse,
    ]:
        """
        生成 File Plan。
        """

        version = (
            settings
            .CODE_ASSISTANT_PLANNING_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    CODE_PLANNING_SYSTEM_PROMPT_ID
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
                    CODE_PLANNING_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                response_language=(
                    language_name
                ),

                idea_payload=(
                    _idea_payload(
                        selected_idea
                    )
                ),

                experiment_payload=(
                    _experiment_payload(
                        experiment
                    )
                ),

                allowed_paths=(
                    json.dumps(
                        allowed_paths,
                        ensure_ascii=False,
                    )
                ),

                max_file_changes=(
                    max_file_changes
                ),

                include_tests=(
                    str(
                        include_tests
                    ).lower()
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


        raw_files = (
            payload.get(
                "files",
                [],
            )
        )


        if not isinstance(
            raw_files,
            list,
        ):

            raise (
                CodeAssistantGenerationException()
            )


        plans = []


        for raw_file in raw_files[
            :max_file_changes
        ]:

            try:

                plan = (
                    CodeFilePlanResponse
                    .model_validate(
                        raw_file
                    )
                )


            except ValidationError as exc:

                raise (
                    CodeAssistantGenerationException()
                ) from exc


            normalized_path = (
                _validate_file_path(
                    file_path=(
                        plan.file_path
                    ),

                    allowed_paths=(
                        allowed_paths
                    ),
                )
            )


            plans.append(
                plan.model_copy(
                    update={
                        "file_path":
                            normalized_path
                    }
                )
            )


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
            plans,
            model_info,
        )


# ============================================================
# Patch Generator
# ============================================================

class PatchGeneratorAgent:
    """
    File Plan
        ↓
    Patch Proposals
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
        selected_idea: ResearchIdeaResult,
        experiment: ResearchExperimentResponse,
        file_plan: list[
            CodeFilePlanResponse
        ],
        allowed_paths: list[str],
    ) -> list[
        CodePatchProposalResponse
    ]:
        """
        生成 Patch Proposal。
        """

        version = (
            settings
            .CODE_ASSISTANT_PATCH_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    CODE_PATCH_SYSTEM_PROMPT_ID
                ),

                version=(
                    version
                ),
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    CODE_PATCH_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                idea_payload=(
                    _idea_payload(
                        selected_idea
                    )
                ),

                experiment_payload=(
                    _experiment_payload(
                        experiment
                    )
                ),

                file_plan=(
                    json.dumps(
                        [
                            plan.model_dump()

                            for plan
                            in file_plan
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
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


        raw_patches = (
            payload.get(
                "patches",
                [],
            )
        )


        if not isinstance(
            raw_patches,
            list,
        ):

            raise (
                CodeAssistantGenerationException()
            )


        plan_paths = {
            plan.file_path:
                plan

            for plan
            in file_plan
        }


        patches = []


        for raw_patch in raw_patches:

            try:

                patch = (
                    CodePatchProposalResponse
                    .model_validate(
                        raw_patch
                    )
                )


            except ValidationError as exc:

                raise (
                    CodeAssistantGenerationException()
                ) from exc


            normalized_path = (
                _validate_file_path(
                    file_path=(
                        patch.file_path
                    ),

                    allowed_paths=(
                        allowed_paths
                    ),
                )
            )


            # Patch 必须对应 Planner
            # 真实批准过的 File。
            plan = plan_paths.get(
                normalized_path
            )


            if plan is None:

                raise (
                    CodeAssistantPathViolationException()
                )


            # Operation 不能偷偷改变。
            if (
                patch.operation
                != plan.operation
            ):

                raise (
                    CodeAssistantGenerationException()
                )


            patches.append(
                patch.model_copy(
                    update={
                        "file_path":
                            normalized_path
                    }
                )
            )


        return patches


# ============================================================
# Safety Reviewer
# ============================================================

class CodeSafetyReviewerAgent:
    """
    Patch Proposal
        ↓
    Safety Review
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
        file_plan: list[
            CodeFilePlanResponse
        ],
        patches: list[
            CodePatchProposalResponse
        ],
        allowed_paths: list[str],
    ) -> CodeSafetyReviewResponse:
        """
        Review Proposal。
        """

        version = (
            settings
            .CODE_ASSISTANT_REVIEW_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    CODE_REVIEW_SYSTEM_PROMPT_ID
                ),

                version=(
                    version
                ),
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    CODE_REVIEW_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                allowed_paths=(
                    json.dumps(
                        allowed_paths,
                        ensure_ascii=False,
                    )
                ),

                blocked_paths=(
                    json.dumps(
                        _blocked_keywords(),
                        ensure_ascii=False,
                    )
                ),

                file_plan=(
                    json.dumps(
                        [
                            item.model_dump()

                            for item
                            in file_plan
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
                ),

                patches=(
                    json.dumps(
                        [
                            item.model_dump()

                            for item
                            in patches
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
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
                CodeSafetyReviewResponse
                .model_validate(
                    payload
                )
            )


        except ValidationError as exc:

            raise (
                CodeAssistantGenerationException()
            ) from exc


        # ====================================================
        # Backend Consistency Guard
        # ====================================================

        if (
            review.status
            == "safe_to_review"
            and (
                review.path_violations
                or review.destructive_change_risks
            )
        ):

            review = (
                review.model_copy(
                    update={
                        "status":
                            "needs_manual_review",

                        "reason": (
                            "The reviewer reported path "
                            "or destructive-change risks, "
                            "so the backend downgraded "
                            "the proposal to manual review."
                        ),
                    }
                )
            )


        return review


# ============================================================
# Validation Planner
# ============================================================

class CodeValidationPlannerAgent:
    """
    Patch Proposals
        ↓
    Validation Sequence
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


    async def plan(
        self,
        selected_idea: ResearchIdeaResult,
        experiment: ResearchExperimentResponse,
        patches: list[
            CodePatchProposalResponse
        ],
    ) -> list[
        CodeValidationStepResponse
    ]:

        version = (
            settings
            .CODE_ASSISTANT_VALIDATION_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    CODE_VALIDATION_SYSTEM_PROMPT_ID
                ),

                version=(
                    version
                ),
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    CODE_VALIDATION_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                idea_payload=(
                    _idea_payload(
                        selected_idea
                    )
                ),

                experiment_payload=(
                    _experiment_payload(
                        experiment
                    )
                ),

                patches=(
                    json.dumps(
                        [
                            patch.model_dump()

                            for patch
                            in patches
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
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


        raw_steps = (
            payload.get(
                "steps",
                [],
            )
        )


        if not isinstance(
            raw_steps,
            list,
        ):

            raise (
                CodeAssistantGenerationException()
            )


        steps = []


        for raw_step in raw_steps:

            try:

                step = (
                    CodeValidationStepResponse
                    .model_validate(
                        raw_step
                    )
                )


            except ValidationError as exc:

                raise (
                    CodeAssistantGenerationException()
                ) from exc


            steps.append(
                step
            )


        return steps


# ============================================================
# Coordinator
# ============================================================

class ResearchCodeAssistantAgent:
    """
    Day42 Code Assistant Coordinator。

    Flow:

        Experiment
            ↓
        Code Planner
            ↓
        Patch Generator
            ↓
        Safety Reviewer
            ↓
        Validation Planner
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


        self.code_planner = (
            CodePlannerAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


        self.patch_generator = (
            PatchGeneratorAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


        self.safety_reviewer = (
            CodeSafetyReviewerAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


        self.validation_planner = (
            CodeValidationPlannerAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


    async def propose_changes(
        self,
        project_id: int,
        experiment: ResearchExperimentResponse,
        selected_idea: ResearchIdeaResult,
        allowed_paths: list[str],
        max_file_changes: int,
        include_tests: bool,
        response_language: str,
    ) -> CodeAssistantResponse:
        """
        完整 Day42 Pipeline。
        """

        # ====================================================
        # 1. Plan
        # ====================================================

        (
            file_plan,
            model_info,
        ) = (
            await self.code_planner.plan(
                selected_idea=(
                    selected_idea
                ),

                experiment=(
                    experiment
                ),

                allowed_paths=(
                    allowed_paths
                ),

                max_file_changes=(
                    max_file_changes
                ),

                include_tests=(
                    include_tests
                ),

                response_language=(
                    response_language
                ),
            )
        )


        # ====================================================
        # 2. Generate Patch Proposals
        # ====================================================

        patches = (
            await self.patch_generator
            .generate(
                selected_idea=(
                    selected_idea
                ),

                experiment=(
                    experiment
                ),

                file_plan=(
                    file_plan
                ),

                allowed_paths=(
                    allowed_paths
                ),
            )
        )


        # ====================================================
        # 3. Safety Review
        # ====================================================

        safety_review = (
            await self.safety_reviewer
            .review(
                file_plan=(
                    file_plan
                ),

                patches=(
                    patches
                ),

                allowed_paths=(
                    allowed_paths
                ),
            )
        )


        # ====================================================
        # 4. Validation Plan
        # ====================================================

        validation_plan = (
            await self.validation_planner
            .plan(
                selected_idea=(
                    selected_idea
                ),

                experiment=(
                    experiment
                ),

                patches=(
                    patches
                ),
            )
        )


        # ====================================================
        # 5. Execution Note
        # ====================================================

        if response_language == "zh":

            execution_note = (
                "Day42 仅生成代码修改提案，并未直接修改任何仓库文件、"
                "执行命令或启动训练。所有 Patch 应先进行人工 Diff Review，"
                "确认实际文件结构与 Proposal 一致后，再在受控环境中应用并"
                "按照 validation_plan 逐级验证。"
            )

        else:

            execution_note = (
                "Day42 produces code-change proposals only. "
                "It does not write repository files, execute "
                "commands, or start training. Every patch "
                "should be reviewed against the real repository "
                "before controlled application and validation."
            )


        return (
            CodeAssistantResponse(
                project_id=(
                    project_id
                ),

                source_gap_id=(
                    experiment
                    .source_gap_id
                ),

                source_idea_id=(
                    experiment
                    .source_idea_id
                ),

                experiment=(
                    experiment
                ),

                file_plan=(
                    file_plan
                ),

                patches=(
                    patches
                ),

                safety_review=(
                    safety_review
                ),

                validation_plan=(
                    validation_plan
                ),

                execution_note=(
                    execution_note
                ),

                model=(
                    model_info
                ),

                prompt=(
                    RAGPromptInfoResponse(
                        system_prompt_id=(
                            CODE_PLANNING_SYSTEM_PROMPT_ID
                        ),

                        system_prompt_version=(
                            settings
                            .CODE_ASSISTANT_PLANNING_PROMPT_VERSION
                        ),

                        user_prompt_id=(
                            CODE_PLANNING_USER_PROMPT_ID
                        ),

                        user_prompt_version=(
                            settings
                            .CODE_ASSISTANT_PLANNING_PROMPT_VERSION
                        ),
                    )
                ),
            )
        )