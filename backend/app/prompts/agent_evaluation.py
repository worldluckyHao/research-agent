from backend.app.prompts.base import (
    PromptDefinition,
)
from backend.app.prompts.registry import (
    prompt_registry,
)


# ============================================================
# Prompt IDs
# ============================================================

AGENT_EVALUATION_SYSTEM_PROMPT_ID = (
    "agent.evaluation.system"
)

AGENT_EVALUATION_USER_PROMPT_ID = (
    "agent.evaluation.user"
)


# ============================================================
# System Prompt
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            AGENT_EVALUATION_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "System prompt for "
            "agent evaluation"
        ),

        template="""
You are evaluating an academic research assistant agent.

Evaluate only the observable information supplied to you:
- user task
- tool calls
- tool results or summaries
- final answer
- optional reference outcome
- optional evidence

Do not assume access to hidden reasoning or chain-of-thought.

Evaluate:

1. goal_completion:
   Did the observable result complete the user's requested task?

2. final_answer_quality:
   Is the final answer useful, relevant, clear, and consistent with the observable execution results?

3. trajectory_coherence:
   Were the observable tool calls and results coherent with the task and final answer?

4. evidence_groundedness:
   If evidence is supplied, how well is the final answer supported by that evidence?
   If no evidence is supplied, return null.

All numeric scores must be between 0.0 and 1.0.

Return JSON only.
Do not use Markdown.
Do not use code fences.
        """.strip(),
    )
)


# ============================================================
# User Prompt
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            AGENT_EVALUATION_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "User prompt for "
            "agent evaluation"
        ),

        template="""
Task:
{task}

Observable Tool Trace:
{tool_trace}

Final Answer:
{final_answer}

Reference Outcome:
{reference_outcome}

Evidence:
{evidence}

Return exactly this JSON structure:

{{
  "goal_completion": 0.0,
  "final_answer_quality": 0.0,
  "trajectory_coherence": 0.0,
  "evidence_groundedness": null,
  "reason": "brief explanation"
}}
        """.strip(),
    )
)