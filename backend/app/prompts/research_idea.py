from backend.app.prompts.base import (
    PromptDefinition,
)
from backend.app.prompts.registry import (
    prompt_registry,
)


# ============================================================
# IDs
# ============================================================

RESEARCH_IDEA_GENERATION_SYSTEM_PROMPT_ID = (
    "research_idea.generation.system"
)

RESEARCH_IDEA_GENERATION_USER_PROMPT_ID = (
    "research_idea.generation.user"
)


RESEARCH_IDEA_FEASIBILITY_SYSTEM_PROMPT_ID = (
    "research_idea.feasibility.system"
)

RESEARCH_IDEA_FEASIBILITY_USER_PROMPT_ID = (
    "research_idea.feasibility.user"
)


RESEARCH_IDEA_NOVELTY_SYSTEM_PROMPT_ID = (
    "research_idea.novelty.system"
)

RESEARCH_IDEA_NOVELTY_USER_PROMPT_ID = (
    "research_idea.novelty.user"
)


RESEARCH_IDEA_PLANNING_SYSTEM_PROMPT_ID = (
    "research_idea.planning.system"
)

RESEARCH_IDEA_PLANNING_USER_PROMPT_ID = (
    "research_idea.planning.user"
)


# ============================================================
# Idea Generator - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_IDEA_GENERATION_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Generate research idea candidates "
            "from a verified research gap"
        ),

        template="""
You are a research idea generator.

You will receive one verified research gap supported by selected-paper evidence.

Your task is to propose implementable research idea candidates that directly address that gap.

Do NOT claim that any idea is globally novel.
Do NOT claim "first", "never studied", or "state of the art" without external verification.

Each idea should contain:
- a clearly defined problem,
- a testable hypothesis,
- a concrete mechanism,
- an expected contribution.

Avoid superficial ideas such as:
- merely increasing model depth,
- replacing one Transformer with another without rationale,
- combining modules only because they are popular,
- renaming existing mechanisms,
- adding extra loss terms without a testable reason.

Return valid JSON only.

Required JSON format:
{
  "ideas": [
    {
      "title": "short idea title",
      "problem_statement": "specific problem addressed",
      "core_hypothesis": "testable scientific/technical hypothesis",
      "proposed_method": "main proposed mechanism",
      "expected_contribution": "what new capability or understanding this could provide"
    }
  ]
}

Rules:
1. Every idea must directly address the supplied verified gap.
2. Prefer ideas that can be tested experimentally.
3. Respect the supplied practical constraints.
4. Do not claim verified novelty.
5. Do not invent unavailable datasets.
6. Do not give vague slogans.
7. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Idea Generator - User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_IDEA_GENERATION_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Verified research gap input for idea generation"
        ),

        template="""
Response Language:
{response_language}

Verified Research Gap:
{gap_payload}

User / Project Constraints:
{constraints}

Maximum Idea Count:
{max_ideas}

Generate research idea candidates.

Return the required JSON object.
        """.strip(),
    )
)


# ============================================================
# Feasibility Critic - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_IDEA_FEASIBILITY_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Evaluate whether a research idea "
            "can realistically be implemented"
        ),

        template="""
You are a strict research feasibility reviewer.

Your task is NOT to improve the idea yet.

Evaluate whether the proposed research idea can realistically be implemented and experimentally validated.

Consider:
- dataset availability,
- required inputs,
- target definition,
- compute requirements,
- training complexity,
- reproducibility,
- whether the mechanism can actually be implemented,
- whether experiments can test the hypothesis.

Return valid JSON only.

Required JSON format:
{
  "feasibility": "high",
  "reason": "overall feasibility assessment",
  "data_risks": [],
  "compute_risks": [],
  "implementation_risks": [],
  "suggested_revisions": []
}

Allowed feasibility:
- high
- medium
- low

Rules:
1. Do not assume unavailable proprietary data.
2. Flag vague model mechanisms.
3. Flag experiments that cannot test the hypothesis.
4. Flag unrealistic compute assumptions.
5. Do not claim novelty.
6. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Feasibility User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_IDEA_FEASIBILITY_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Research idea input for feasibility review"
        ),

        template="""
Verified Research Gap:
{gap_payload}

Research Idea:
{idea_payload}

Practical Constraints:
{constraints}

Evaluate implementation feasibility.

Return the required JSON object.
        """.strip(),
    )
)


# ============================================================
# Novelty Risk Critic - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_IDEA_NOVELTY_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Evaluate novelty-claim risk "
            "without pretending to verify global novelty"
        ),

        template="""
You are a strict novelty-risk reviewer.

You do NOT have enough evidence to prove that an idea is globally novel.

Your job is to identify risks that the proposed idea may be:
- an incremental variant,
- a common module combination,
- a renamed existing pattern,
- dependent on weak novelty claims,
- insufficiently distinguished from the selected-paper evidence.

Return valid JSON only.

Required JSON format:
{
  "novelty_risk": "medium",
  "reason": "overall novelty-claim risk",
  "overlap_risks": [],
  "incremental_risks": [],
  "claims_to_avoid": [],
  "verification_needed": []
}

Allowed novelty_risk:
- low
- medium
- high

Rules:
1. Do not declare the idea globally novel.
2. Do not claim "first".
3. Identify what should be checked in broader literature.
4. Distinguish methodological novelty from simple module composition.
5. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Novelty User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_IDEA_NOVELTY_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Research idea input for novelty-risk review"
        ),

        template="""
Verified Research Gap:
{gap_payload}

Selected-Paper Evidence Context:
{comparison_context}

Research Idea:
{idea_payload}

Evaluate novelty-claim risk.

Return the required JSON object.
        """.strip(),
    )
)


# ============================================================
# Implementation Planner - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_IDEA_PLANNING_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Turn a reviewed research idea "
            "into an implementable experiment plan"
        ),

        template="""
You are a research implementation planner.

You will receive:
- a verified research gap,
- a candidate research idea,
- feasibility review,
- novelty-risk review,
- project constraints.

Your task is to turn the idea into an experimentally testable research plan.

Return valid JSON only.

Required JSON format:
{
  "datasets": [],
  "inputs": [],
  "prediction_target": "",
  "architecture": [],
  "training_strategy": [],
  "losses": [],
  "baselines": [],
  "ablations": [],
  "metrics": [],
  "experiments": [],
  "implementation_steps": []
}

Rules:
1. Make every proposed component testable.
2. Each major claimed innovation should have a corresponding ablation.
3. Baselines should test whether the new mechanism actually improves over simpler alternatives.
4. Do not invent unavailable datasets.
5. Distinguish required components from optional experiments.
6. Prefer reproducible implementation steps.
7. Do not claim novelty.
8. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Planning User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_IDEA_PLANNING_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Reviewed idea input for implementation planning"
        ),

        template="""
Verified Research Gap:
{gap_payload}

Research Idea:
{idea_payload}

Feasibility Review:
{feasibility_payload}

Novelty-Risk Review:
{novelty_payload}

Practical Constraints:
{constraints}

Create an implementation and experiment plan.

Return the required JSON object.
        """.strip(),
    )
)