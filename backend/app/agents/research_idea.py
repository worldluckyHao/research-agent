import json
from dataclasses import (
    dataclass,
)
from typing import (
    Any,
    Optional,
)

from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    ResearchIdeaGenerationException,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.prompts.registry import (
    prompt_registry,
)
from backend.app.prompts.research_idea import (
    RESEARCH_IDEA_FEASIBILITY_SYSTEM_PROMPT_ID,
    RESEARCH_IDEA_FEASIBILITY_USER_PROMPT_ID,
    RESEARCH_IDEA_GENERATION_SYSTEM_PROMPT_ID,
    RESEARCH_IDEA_GENERATION_USER_PROMPT_ID,
    RESEARCH_IDEA_NOVELTY_SYSTEM_PROMPT_ID,
    RESEARCH_IDEA_NOVELTY_USER_PROMPT_ID,
    RESEARCH_IDEA_PLANNING_SYSTEM_PROMPT_ID,
    RESEARCH_IDEA_PLANNING_USER_PROMPT_ID,
)
from backend.app.rag.generation import (
    generate_rag_answer,
)
from backend.app.schemas.research_gap import (
    ResearchGapCandidateResponse,
    ResearchGapResponse,
)
from backend.app.schemas.research_idea import (
    FeasibilityReviewResponse,
    NoveltyRiskReviewResponse,
    RejectedResearchIdeaResponse,
    ResearchIdeaCandidateResponse,
    ResearchIdeaExperimentPlan,
    ResearchIdeaResponse,
    ResearchIdeaResult,
)
from backend.app.schemas.rag import (
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)


# ============================================================
# Internal Candidate
# ============================================================

@dataclass(frozen=True)
class GeneratedResearchIdea:
    """
    Generator 原始 Idea。
    """

    title: str

    problem_statement: str

    core_hypothesis: str

    proposed_method: str

    expected_contribution: str


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
            ResearchIdeaGenerationException()
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
            ResearchIdeaGenerationException()
        ) from exc


    if not isinstance(
        payload,
        dict,
    ):

        raise (
            ResearchIdeaGenerationException()
        )


    return payload


# ============================================================
# Helpers
# ============================================================

def _normalize_string_list(
    value: Any,
) -> list[str]:
    """
    将 JSON list 安全转成 string list。
    """

    if not isinstance(
        value,
        list,
    ):

        return []


    return [
        str(item).strip()

        for item in value

        if str(item).strip()
    ]


def _gap_payload(
    gap: ResearchGapCandidateResponse,
) -> str:
    """
    将 Verified Gap 转成 Prompt JSON。
    """

    payload = {
        "gap_id":
            gap.gap_id,

        "title":
            gap.title,

        "gap_type":
            gap.gap_type,

        "gap_statement":
            gap.gap_statement,

        "evidence_basis":
            gap.evidence_basis,

        "verification_status":
            gap.verification_status,

        "verification_reason":
            gap.verification_reason,

        "evidence_strength":
            gap.evidence_strength,

        "distinct_supporting_papers":
            gap.distinct_supporting_papers,

        "scope_limitations":
            gap.scope_limitations,
    }


    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def _idea_payload(
    idea: GeneratedResearchIdea,
) -> str:
    payload = {
        "title":
            idea.title,

        "problem_statement":
            idea.problem_statement,

        "core_hypothesis":
            idea.core_hypothesis,

        "proposed_method":
            idea.proposed_method,

        "expected_contribution":
            idea.expected_contribution,
    }


    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def _comparison_context(
    research_gap: ResearchGapResponse,
) -> str:
    """
    给 Novelty Critic 使用的
    Selected-Paper Context。

    注意：
    这不是整个领域 Literature Search。
    """

    blocks = []


    for paper in (
        research_gap
        .comparison
        .papers
    ):

        blocks.append(
            (
                f"{paper.label}: "
                f"{paper.title}\n"
                f"{paper.evidence_summary}"
            )
        )


    if (
        research_gap
        .comparison
        .key_differences
    ):

        blocks.append(
            (
                "Key Differences:\n"
                +
                "\n".join(
                    (
                        f"- {item}"
                    )

                    for item
                    in research_gap
                    .comparison
                    .key_differences
                )
            )
        )


    return (
        "\n\n---\n\n".join(
            blocks
        )
    )


# ============================================================
# Parse Ideas
# ============================================================

def _parse_generated_ideas(
    payload: dict[str, Any],
    max_ideas: int,
) -> list[
    GeneratedResearchIdea
]:
    raw_ideas = (
        payload.get(
            "ideas",
            [],
        )
    )


    if not isinstance(
        raw_ideas,
        list,
    ):

        raise (
            ResearchIdeaGenerationException()
        )


    ideas = []


    for raw_idea in raw_ideas[
        :max_ideas
    ]:

        if not isinstance(
            raw_idea,
            dict,
        ):

            continue


        title = str(
            raw_idea.get(
                "title",
                "",
            )
        ).strip()


        problem_statement = str(
            raw_idea.get(
                "problem_statement",
                "",
            )
        ).strip()


        core_hypothesis = str(
            raw_idea.get(
                "core_hypothesis",
                "",
            )
        ).strip()


        proposed_method = str(
            raw_idea.get(
                "proposed_method",
                "",
            )
        ).strip()


        expected_contribution = str(
            raw_idea.get(
                "expected_contribution",
                "",
            )
        ).strip()


        if (
            not title
            or not problem_statement
            or not core_hypothesis
            or not proposed_method
        ):

            continue


        ideas.append(
            GeneratedResearchIdea(
                title=(
                    title
                ),

                problem_statement=(
                    problem_statement
                ),

                core_hypothesis=(
                    core_hypothesis
                ),

                proposed_method=(
                    proposed_method
                ),

                expected_contribution=(
                    expected_contribution
                ),
            )
        )


    return ideas


# ============================================================
# Idea Generator
# ============================================================

class ResearchIdeaGeneratorAgent:
    """
    Verified Gap
        ↓
    Candidate Ideas
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
        gap: ResearchGapCandidateResponse,
        constraints: str,
        max_ideas: int,
        response_language: str,
    ) -> tuple[
        list[GeneratedResearchIdea],
        RAGModelInfoResponse,
    ]:
        """
        生成 Candidate Idea。
        """

        version = (
            settings
            .RESEARCH_IDEA_GENERATION_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_IDEA_GENERATION_SYSTEM_PROMPT_ID
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
                    RESEARCH_IDEA_GENERATION_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                response_language=(
                    language_name
                ),

                gap_payload=(
                    _gap_payload(
                        gap
                    )
                ),

                constraints=(
                    constraints
                ),

                max_ideas=(
                    max_ideas
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


        ideas = (
            _parse_generated_ideas(
                payload=(
                    payload
                ),

                max_ideas=(
                    max_ideas
                ),
            )
        )


        return (
            ideas,

            RAGModelInfoResponse(
                provider=(
                    generation.provider
                ),

                model_name=(
                    generation.model_name
                ),
            ),
        )


# ============================================================
# Feasibility Critic
# ============================================================

class FeasibilityCriticAgent:
    """
    判断：
        能不能真正做实验。
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
        gap: ResearchGapCandidateResponse,
        idea: GeneratedResearchIdea,
        constraints: str,
    ) -> FeasibilityReviewResponse:

        version = (
            settings
            .RESEARCH_IDEA_FEASIBILITY_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_IDEA_FEASIBILITY_SYSTEM_PROMPT_ID
                ),

                version=(
                    version
                ),
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_IDEA_FEASIBILITY_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                gap_payload=(
                    _gap_payload(
                        gap
                    )
                ),

                idea_payload=(
                    _idea_payload(
                        idea
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


        feasibility = str(
            payload.get(
                "feasibility",
                "low",
            )
        ).strip()


        if feasibility not in {
            "high",
            "medium",
            "low",
        }:

            feasibility = "low"


        return (
            FeasibilityReviewResponse(
                feasibility=(
                    feasibility
                ),

                reason=str(
                    payload.get(
                        "reason",
                        "",
                    )
                ).strip()
                or (
                    "No feasibility "
                    "reason was returned."
                ),

                data_risks=(
                    _normalize_string_list(
                        payload.get(
                            "data_risks"
                        )
                    )
                ),

                compute_risks=(
                    _normalize_string_list(
                        payload.get(
                            "compute_risks"
                        )
                    )
                ),

                implementation_risks=(
                    _normalize_string_list(
                        payload.get(
                            "implementation_risks"
                        )
                    )
                ),

                suggested_revisions=(
                    _normalize_string_list(
                        payload.get(
                            "suggested_revisions"
                        )
                    )
                ),
            )
        )


# ============================================================
# Novelty Risk Critic
# ============================================================

class NoveltyRiskCriticAgent:
    """
    判断：
        Idea 的创新性主张风险。

    注意：
        不做全球 novelty verification。
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
        gap: ResearchGapCandidateResponse,
        idea: GeneratedResearchIdea,
        research_gap: ResearchGapResponse,
    ) -> NoveltyRiskReviewResponse:

        version = (
            settings
            .RESEARCH_IDEA_NOVELTY_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_IDEA_NOVELTY_SYSTEM_PROMPT_ID
                ),

                version=(
                    version
                ),
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_IDEA_NOVELTY_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                gap_payload=(
                    _gap_payload(
                        gap
                    )
                ),

                comparison_context=(
                    _comparison_context(
                        research_gap
                    )
                ),

                idea_payload=(
                    _idea_payload(
                        idea
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


        novelty_risk = str(
            payload.get(
                "novelty_risk",
                "high",
            )
        ).strip()


        if novelty_risk not in {
            "low",
            "medium",
            "high",
        }:

            novelty_risk = "high"


        return (
            NoveltyRiskReviewResponse(
                novelty_risk=(
                    novelty_risk
                ),

                reason=str(
                    payload.get(
                        "reason",
                        "",
                    )
                ).strip()
                or (
                    "No novelty-risk "
                    "reason was returned."
                ),

                overlap_risks=(
                    _normalize_string_list(
                        payload.get(
                            "overlap_risks"
                        )
                    )
                ),

                incremental_risks=(
                    _normalize_string_list(
                        payload.get(
                            "incremental_risks"
                        )
                    )
                ),

                claims_to_avoid=(
                    _normalize_string_list(
                        payload.get(
                            "claims_to_avoid"
                        )
                    )
                ),

                verification_needed=(
                    _normalize_string_list(
                        payload.get(
                            "verification_needed"
                        )
                    )
                ),
            )
        )


# ============================================================
# Planner
# ============================================================

class ImplementationPlannerAgent:
    """
    把通过 Review 的 Idea
    转成可实验计划。
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
        gap: ResearchGapCandidateResponse,
        idea: GeneratedResearchIdea,
        feasibility: FeasibilityReviewResponse,
        novelty: NoveltyRiskReviewResponse,
        constraints: str,
    ) -> ResearchIdeaExperimentPlan:

        version = (
            settings
            .RESEARCH_IDEA_PLANNING_PROMPT_VERSION
        )


        system_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_IDEA_PLANNING_SYSTEM_PROMPT_ID
                ),

                version=(
                    version
                ),
            )
        )


        user_prompt = (
            prompt_registry.render(
                prompt_id=(
                    RESEARCH_IDEA_PLANNING_USER_PROMPT_ID
                ),

                version=(
                    version
                ),

                gap_payload=(
                    _gap_payload(
                        gap
                    )
                ),

                idea_payload=(
                    _idea_payload(
                        idea
                    )
                ),

                feasibility_payload=(
                    feasibility
                    .model_dump_json(
                        indent=2
                    )
                ),

                novelty_payload=(
                    novelty
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


        return (
            ResearchIdeaExperimentPlan(
                datasets=(
                    _normalize_string_list(
                        payload.get(
                            "datasets"
                        )
                    )
                ),

                inputs=(
                    _normalize_string_list(
                        payload.get(
                            "inputs"
                        )
                    )
                ),

                prediction_target=str(
                    payload.get(
                        "prediction_target",
                        "",
                    )
                ).strip(),

                architecture=(
                    _normalize_string_list(
                        payload.get(
                            "architecture"
                        )
                    )
                ),

                training_strategy=(
                    _normalize_string_list(
                        payload.get(
                            "training_strategy"
                        )
                    )
                ),

                losses=(
                    _normalize_string_list(
                        payload.get(
                            "losses"
                        )
                    )
                ),

                baselines=(
                    _normalize_string_list(
                        payload.get(
                            "baselines"
                        )
                    )
                ),

                ablations=(
                    _normalize_string_list(
                        payload.get(
                            "ablations"
                        )
                    )
                ),

                metrics=(
                    _normalize_string_list(
                        payload.get(
                            "metrics"
                        )
                    )
                ),

                experiments=(
                    _normalize_string_list(
                        payload.get(
                            "experiments"
                        )
                    )
                ),

                implementation_steps=(
                    _normalize_string_list(
                        payload.get(
                            "implementation_steps"
                        )
                    )
                ),
            )
        )


# ============================================================
# Coordinator
# ============================================================

class ResearchIdeaAgent:
    """
    Day40 Research Idea Coordinator。

    Flow:

        Gap
         ↓
        Generator
         ↓
        Feasibility Critic
         ↓
        Novelty-Risk Critic
         ↓
        Decision
         ↓
        Planner
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
    ):
        self.llm_provider = (
            llm_provider
        )


        self.generator = (
            ResearchIdeaGeneratorAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


        self.feasibility_critic = (
            FeasibilityCriticAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


        self.novelty_critic = (
            NoveltyRiskCriticAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


        self.planner = (
            ImplementationPlannerAgent(
                llm_provider=(
                    llm_provider
                )
            )
        )


    async def generate_ideas(
        self,
        project_id: int,
        research_gap: ResearchGapResponse,
        selected_gap: ResearchGapCandidateResponse,
        constraints: str,
        max_ideas: int,
        response_language: str,
    ) -> ResearchIdeaResponse:
        """
        完整 Day40 Pipeline。
        """

        (
            generated_ideas,
            model_info,
        ) = (
            await self.generator.generate(
                gap=(
                    selected_gap
                ),

                constraints=(
                    constraints
                ),

                max_ideas=(
                    max_ideas
                ),

                response_language=(
                    response_language
                ),
            )
        )


        accepted = []

        rejected = []


        for index, idea in enumerate(
            generated_ideas,
            start=1,
        ):

            idea_id = (
                f"I{index}"
            )


            # =================================================
            # 1. Feasibility Review
            # =================================================

            feasibility = (
                await self.feasibility_critic
                .review(
                    gap=(
                        selected_gap
                    ),

                    idea=(
                        idea
                    ),

                    constraints=(
                        constraints
                    ),
                )
            )


            # =================================================
            # 2. Novelty Risk Review
            # =================================================

            novelty = (
                await self.novelty_critic
                .review(
                    gap=(
                        selected_gap
                    ),

                    idea=(
                        idea
                    ),

                    research_gap=(
                        research_gap
                    ),
                )
            )


            # =================================================
            # 3. Decision
            # =================================================
            #
            # 这里是 Backend Rule，
            # 不是交给 LLM 自己决定。
            #
            # low feasibility:
            #     reject
            #
            # high novelty risk:
            #     needs_revision
            #
            # high/medium feasibility +
            # low/medium novelty risk:
            #     experiment candidate

            if (
                feasibility.feasibility
                == "low"
            ):

                rejected.append(
                    RejectedResearchIdeaResponse(
                        idea_id=(
                            idea_id
                        ),

                        title=(
                            idea.title
                        ),

                        reason=(
                            "Rejected because the "
                            "feasibility review is low: "
                            f"{feasibility.reason}"
                        ),
                    )
                )


                continue


            if (
                novelty.novelty_risk
                == "high"
            ):

                decision = (
                    "needs_revision"
                )

                decision_reason = (
                    "The idea appears implementable "
                    "but has high novelty-claim risk. "
                    "Broader literature verification "
                    "or stronger methodological "
                    "differentiation is required."
                )

            else:

                decision = (
                    "recommended_for_experiment"
                )

                decision_reason = (
                    "The idea passed the current "
                    "feasibility review and does not "
                    "show high novelty-claim risk "
                    "within the selected evidence."
                )


            # =================================================
            # 4. Implementation Plan
            # =================================================

            experiment_plan = (
                await self.planner.plan(
                    gap=(
                        selected_gap
                    ),

                    idea=(
                        idea
                    ),

                    feasibility=(
                        feasibility
                    ),

                    novelty=(
                        novelty
                    ),

                    constraints=(
                        constraints
                    ),
                )
            )


            # =================================================
            # 5. Scope Note
            # =================================================

            if response_language == "zh":

                novelty_scope_note = (
                    "当前创新风险判断仅基于所选论文和现有证据，"
                    "不构成全球文献范围内的创新性确认。"
                    "在投稿前仍需使用 OpenAlex、Crossref、arXiv、"
                    "Google Scholar 等渠道进行更广泛的相关工作检索。"
                )

            else:

                novelty_scope_note = (
                    "The current novelty-risk review is "
                    "limited to the selected papers and "
                    "available evidence. It does not prove "
                    "global novelty. Broader literature "
                    "verification is required before "
                    "making novelty claims."
                )


            accepted.append(
                ResearchIdeaResult(
                    idea_id=(
                        idea_id
                    ),

                    title=(
                        idea.title
                    ),

                    source_gap_id=(
                        selected_gap
                        .gap_id
                    ),

                    source_gap_statement=(
                        selected_gap
                        .gap_statement
                    ),

                    problem_statement=(
                        idea
                        .problem_statement
                    ),

                    core_hypothesis=(
                        idea
                        .core_hypothesis
                    ),

                    proposed_method=(
                        idea
                        .proposed_method
                    ),

                    expected_contribution=(
                        idea
                        .expected_contribution
                    ),

                    feasibility_review=(
                        feasibility
                    ),

                    novelty_review=(
                        novelty
                    ),

                    decision=(
                        decision
                    ),

                    decision_reason=(
                        decision_reason
                    ),

                    experiment_plan=(
                        experiment_plan
                    ),

                    novelty_scope_note=(
                        novelty_scope_note
                    ),
                )
            )


        # ====================================================
        # Final Scope Note
        # ====================================================

        if response_language == "zh":

            scope_note = (
                "这些 Idea 是根据当前验证后的 Research Gap、"
                "所选论文证据和用户约束生成的实验候选方案。"
                "它们尚不等于已验证的论文创新点；"
                "在正式立项或投稿前仍需进行更广泛相关工作检索、"
                "小规模可行性实验和消融验证。"
            )

        else:

            scope_note = (
                "These ideas are experiment candidates "
                "derived from the verified research gap, "
                "selected-paper evidence, and project "
                "constraints. They are not verified novelty "
                "claims. Broader literature review and "
                "pilot experiments are still required."
            )


        return (
            ResearchIdeaResponse(
                project_id=(
                    project_id
                ),

                source_gap_id=(
                    selected_gap
                    .gap_id
                ),

                research_gap=(
                    research_gap
                ),

                ideas=(
                    accepted
                ),

                rejected_ideas=(
                    rejected
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
                            RESEARCH_IDEA_GENERATION_SYSTEM_PROMPT_ID
                        ),

                        system_prompt_version=(
                            settings
                            .RESEARCH_IDEA_GENERATION_PROMPT_VERSION
                        ),

                        user_prompt_id=(
                            RESEARCH_IDEA_GENERATION_USER_PROMPT_ID
                        ),

                        user_prompt_version=(
                            settings
                            .RESEARCH_IDEA_GENERATION_PROMPT_VERSION
                        ),
                    )
                ),
            )
        )