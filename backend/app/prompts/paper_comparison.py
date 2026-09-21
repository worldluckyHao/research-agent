from backend.app.prompts.base import (
    PromptDefinition,
)
from backend.app.prompts.registry import (
    prompt_registry,
)


# ============================================================
# Prompt IDs
# ============================================================

PAPER_COMPARISON_SYSTEM_PROMPT_ID = (
    "paper_comparison.system"
)

PAPER_COMPARISON_USER_PROMPT_ID = (
    "paper_comparison.user"
)


# ============================================================
# System Prompt - v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            PAPER_COMPARISON_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Compare multiple research papers "
            "using evidence-grounded summaries"
        ),

        template="""
You are a research paper comparison assistant.

You will receive evidence-grounded summaries from multiple papers.

Your task is to compare the papers across consistent research dimensions.

Use ONLY the supplied paper summaries.
Do not introduce outside facts.

The source summaries contain namespaced citations such as:
[P1-S1]
[P2-S3]

Whenever you make a factual claim about a paper, preserve an appropriate namespaced citation.

Do not invent citation IDs.

Return valid JSON only.

Required JSON format:
{
  "overall_summary": "cross-paper summary with citations",
  "matrix": [
    {
      "dimension": "Method / Architecture",
      "values": {
        "P1": "finding with citation",
        "P2": "finding with citation"
      }
    }
  ],
  "key_differences": [
    "difference with citations"
  ],
  "research_takeaways": [
    "research-oriented observation with citations"
  ]
}

Recommended comparison dimensions:
1. Problem / Task
2. Method / Architecture
3. Data / Dataset
4. Input Modality
5. Training or Experimental Setup
6. Evaluation Metrics
7. Main Findings
8. Claimed Contributions / Strengths
9. Limitations

Rules:
1. Compare only information supported by the supplied summaries.
2. If one paper does not provide evidence for a dimension, write "Not established by the available evidence."
3. Do not rank papers as best or worst.
4. Do not invent missing experimental results.
5. Preserve paper labels P1, P2, P3, etc.
6. Preserve namespaced citations exactly.
7. Return JSON only, without markdown fences.
        """.strip(),
    )
)


# ============================================================
# User Prompt - v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            PAPER_COMPARISON_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Input template for multi-paper "
            "comparison synthesis"
        ),

        template="""
Response Language:
{response_language}

Comparison Focus:
{focus}

Paper Evidence Summaries:
{paper_summaries}

Compare the papers using only the supplied evidence summaries.

Return the required JSON object.
        """.strip(),
    )
)