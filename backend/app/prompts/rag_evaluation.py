from backend.app.prompts.base import (
    PromptDefinition,
)
from backend.app.prompts.registry import (
    prompt_registry,
)


# ============================================================
# Prompt IDs
# ============================================================

RAG_EVALUATION_SYSTEM_PROMPT_ID = (
    "rag.evaluation.system"
)

RAG_EVALUATION_USER_PROMPT_ID = (
    "rag.evaluation.user"
)


# ============================================================
# System Prompt
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RAG_EVALUATION_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "System prompt for "
            "RAG LLM-as-a-Judge evaluation"
        ),

        template="""
You are an evaluator for an academic retrieval-augmented generation system.

Evaluate only the supplied question, answer, and evidence.

Do not introduce outside knowledge.

Evaluate two dimensions:

1. groundedness:
   How well the factual claims in the answer are supported by the supplied evidence.

2. relevance:
   How directly and completely the answer addresses the user's question.

Scores must be numbers from 0.0 to 1.0.

Return JSON only.

Do not include Markdown.
Do not include code fences.
        """.strip(),
    )
)


# ============================================================
# User Prompt
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            RAG_EVALUATION_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "User prompt for "
            "RAG LLM-as-a-Judge evaluation"
        ),

        template="""
Question:
{question}

Answer:
{answer}

Evidence:
{evidence}

Return exactly this JSON structure:

{{
  "groundedness": 0.0,
  "relevance": 0.0,
  "reason": "brief explanation"
}}
        """.strip(),
    )
)