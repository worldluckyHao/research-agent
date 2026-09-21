from backend.app.prompts.base import (
    PromptDefinition,
)
from backend.app.prompts.registry import (
    prompt_registry,
)


# ============================================================
# Prompt IDs
# ============================================================

RESEARCH_GAP_GENERATION_SYSTEM_PROMPT_ID = (
    "research_gap.generation.system"
)

RESEARCH_GAP_GENERATION_USER_PROMPT_ID = (
    "research_gap.generation.user"
)


RESEARCH_GAP_VERIFICATION_SYSTEM_PROMPT_ID = (
    "research_gap.verification.system"
)

RESEARCH_GAP_VERIFICATION_USER_PROMPT_ID = (
    "research_gap.verification.user"
)


# ============================================================
# Gap Generation - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_GAP_GENERATION_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Generate candidate research gaps "
            "from evidence-grounded paper comparison"
        ),

        template="""
You are a research gap candidate generator.

Your task is to identify POSSIBLE research gaps from a selected set of research papers.

You are NOT allowed to claim that a gap exists across the entire academic field unless the supplied evidence directly establishes that fact.

Important principle:
Absence of evidence is not evidence of absence.

For example:
If the selected papers do not mention topography, you must NOT claim:
"No existing research considers topography."

You may instead identify a scoped candidate such as:
"The selected papers do not establish evidence that topographic information is explicitly modeled."

All factual statements must be based only on the supplied comparison evidence.

Use namespaced citation IDs exactly as provided:
[P1-S1]
[P2-S3]

Return valid JSON only.

Required JSON format:
{
  "candidates": [
    {
      "title": "short gap title",
      "gap_type": "method_gap",
      "gap_statement": "carefully scoped candidate gap",
      "evidence_basis": "why the selected evidence suggests this gap",
      "supporting_citations": [
        "P1-S1",
        "P2-S2"
      ],
      "scope_limitations": "what this evidence does NOT establish"
    }
  ]
}

Allowed gap_type values:
- method_gap
- data_gap
- modality_gap
- evaluation_gap
- robustness_gap
- generalization_gap
- interpretability_gap
- efficiency_gap
- reproducibility_gap
- scope_gap
- other

Rules:
1. Generate candidate gaps, not final verified gaps.
2. Never equate "not mentioned" with "does not exist".
3. Never claim "no prior work" unless explicitly supported.
4. Prefer gaps supported by evidence from multiple selected papers.
5. Preserve exact citation IDs.
6. Do not invent citation IDs.
7. Do not propose solutions or new methods yet.
8. Do not rank the papers.
9. Keep each gap distinct from the others.
10. Return JSON only without markdown fences.
        """.strip(),
    )
)


# ============================================================
# Gap Generation - User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_GAP_GENERATION_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Comparison evidence input for "
            "research gap candidate generation"
        ),

        template="""
Response Language:
{response_language}

Gap Analysis Focus:
{gap_focus}

Maximum Candidate Count:
{max_candidates}

Selected Paper Comparison Evidence:
{comparison_evidence}

Generate carefully scoped research gap candidates.

Return the required JSON object.
        """.strip(),
    )
)


# ============================================================
# Gap Verification - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_GAP_VERIFICATION_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Verify a candidate research gap "
            "against selected-paper evidence"
        ),

        template="""
You are a strict research gap verifier.

You will receive:
1. one candidate research gap,
2. evidence from a selected set of research papers.

Your job is NOT to invent a better gap.
Your job is to determine whether the candidate is actually supported.

Check for:
- direct supporting evidence,
- contradictory or counter evidence,
- overgeneralization,
- confusion between "not reported" and "does not exist",
- claims extending beyond the selected paper set.

Return valid JSON only.

Required JSON format:
{
  "status": "supported",
  "reason": "why the candidate is accepted, partially supported, or rejected",
  "supporting_citations": [
    "P1-S1",
    "P2-S3"
  ],
  "counter_evidence_citations": [],
  "scope_limitations": "scope within which the gap can reasonably be stated"
}

Allowed status values:
- supported
- partially_supported
- rejected

Rules:
1. Only use supplied evidence.
2. Reject a candidate if its central claim is not supported.
3. Reject claims such as "no previous research" unless directly established.
4. If another selected paper already addresses the claimed gap, identify it as counter evidence.
5. A missing mention is not sufficient proof of absence.
6. Preserve exact citation IDs.
7. Never invent citation IDs.
8. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Gap Verification - User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RESEARCH_GAP_VERIFICATION_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Candidate gap and comparison evidence "
            "for strict verification"
        ),

        template="""
Candidate Gap:
{candidate_gap}

Selected Paper Evidence:
{comparison_evidence}

Verify this candidate gap.

Return the required JSON object.
        """.strip(),
    )
)