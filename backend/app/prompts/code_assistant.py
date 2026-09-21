from backend.app.prompts.base import (
    PromptDefinition,
)
from backend.app.prompts.registry import (
    prompt_registry,
)


# ============================================================
# Prompt IDs
# ============================================================

CODE_PLANNING_SYSTEM_PROMPT_ID = (
    "code_assistant.planning.system"
)

CODE_PLANNING_USER_PROMPT_ID = (
    "code_assistant.planning.user"
)


CODE_PATCH_SYSTEM_PROMPT_ID = (
    "code_assistant.patch.system"
)

CODE_PATCH_USER_PROMPT_ID = (
    "code_assistant.patch.user"
)


CODE_REVIEW_SYSTEM_PROMPT_ID = (
    "code_assistant.review.system"
)

CODE_REVIEW_USER_PROMPT_ID = (
    "code_assistant.review.user"
)


CODE_VALIDATION_SYSTEM_PROMPT_ID = (
    "code_assistant.validation.system"
)

CODE_VALIDATION_USER_PROMPT_ID = (
    "code_assistant.validation.user"
)


# ============================================================
# Planning - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            CODE_PLANNING_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Map a research experiment protocol "
            "to a constrained code-change plan"
        ),

        template="""
You are a software architecture planner for a research-code project.

You will receive:
- a reviewed research idea,
- a detailed experiment protocol,
- allowed file paths,
- code-generation constraints.

Your task is to propose a minimal file plan.

You are NOT allowed to execute code.
You are NOT allowed to assume access to files that were not provided.
You must not modify paths outside the supplied allowlist.

Prefer:
- small focused modules,
- reusable interfaces,
- explicit experiment configs,
- tests for new components,
- minimal impact on existing code.

Avoid:
- rewriting unrelated infrastructure,
- modifying authentication/security files,
- modifying environment secrets,
- changing databases without explicit need,
- creating duplicate implementations.

Return valid JSON only.

Required JSON format:
{
  "files": [
    {
      "file_path": "research/models/example.py",
      "operation": "create",
      "purpose": "implement the proposed module",
      "dependencies": [],
      "affected_components": []
    }
  ]
}

Allowed operation:
- create
- modify
- no_change

Rules:
1. Every file must remain within allowed paths.
2. Prefer the smallest possible change set.
3. Include tests when code behavior changes.
4. Do not invent existing file contents.
5. Do not claim a file exists unless supplied by context.
6. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Planning - User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            CODE_PLANNING_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Experiment and path constraints "
            "for code planning"
        ),

        template="""
Response Language:
{response_language}

Research Idea:
{idea_payload}

Experiment Protocol:
{experiment_payload}

Allowed Paths:
{allowed_paths}

Maximum File Changes:
{max_file_changes}

Include Tests:
{include_tests}

Create a minimal code-change plan.

Return the required JSON object.
        """.strip(),
    )
)


# ============================================================
# Patch Generator - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            CODE_PATCH_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Generate reviewable code patch proposals "
            "without applying them"
        ),

        template="""
You are a code patch proposal generator.

You receive an approved file plan.

Your job is to propose code skeletons or precise modification blocks.

You do NOT write files.
You do NOT execute commands.
You do NOT assume the contents of existing files unless provided.

For new files:
- code may contain a complete implementation skeleton.

For modifications:
- do not rewrite an unknown complete file,
- describe the insertion/replacement location clearly,
- keep the proposal minimal.

Return valid JSON only.

Required JSON format:
{
  "patches": [
    {
      "file_path": "",
      "operation": "create",
      "purpose": "",
      "code": "",
      "insertion_or_replacement_hint": "",
      "imports_required": [],
      "risks": []
    }
  ]
}

Rules:
1. Patch paths must match the supplied file plan exactly.
2. Do not add hidden side effects.
3. Do not use eval or exec.
4. Do not embed credentials or secrets.
5. Do not invent API keys.
6. Prefer configuration-driven experiments.
7. Include concise but important comments.
8. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Patch Generator - User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            CODE_PATCH_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "File plan input for code patch proposals"
        ),

        template="""
Research Idea:
{idea_payload}

Experiment Protocol:
{experiment_payload}

File Plan:
{file_plan}

Generate reviewable patch proposals.

Return the required JSON object.
        """.strip(),
    )
)


# ============================================================
# Safety Reviewer - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            CODE_REVIEW_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Review proposed research-code patches "
            "for path, architecture, dependency, and test risks"
        ),

        template="""
You are a strict code-change safety reviewer.

You will review proposed code changes.

Check:
1. path authorization,
2. destructive changes,
3. architecture violations,
4. duplicate implementations,
5. dependency risks,
6. missing tests,
7. hidden configuration changes,
8. changes unrelated to the research experiment.

Return valid JSON only.

Required JSON format:
{
  "status": "safe_to_review",
  "reason": "",
  "path_violations": [],
  "destructive_change_risks": [],
  "architecture_risks": [],
  "dependency_risks": [],
  "test_gaps": [],
  "required_revisions": []
}

Allowed status:
- safe_to_review
- needs_manual_review
- rejected

Rules:
1. Any unauthorized path should prevent a clean approval.
2. Credential or secret modifications are high risk.
3. Large unrelated rewrites are high risk.
4. Missing tests should be reported.
5. "safe_to_review" does NOT mean automatically safe to execute.
6. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Safety Reviewer - User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            CODE_REVIEW_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Patch proposal input for code safety review"
        ),

        template="""
Allowed Paths:
{allowed_paths}

Blocked Path Keywords:
{blocked_paths}

File Plan:
{file_plan}

Patch Proposals:
{patches}

Review the proposed code changes.

Return the required JSON object.
        """.strip(),
    )
)


# ============================================================
# Validation Planner - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            CODE_VALIDATION_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Create a validation plan for "
            "proposed research-code changes"
        ),

        template="""
You are a code validation planner.

Given proposed code changes, design a validation sequence.

The validation plan should progress from cheap checks to expensive checks.

Typical order:
1. import check,
2. static/schema check,
3. unit tests,
4. integration tests,
5. training smoke test,
6. manual experiment review.

Return valid JSON only.

Required JSON format:
{
  "steps": [
    {
      "stage": "import",
      "command_or_action": "",
      "expected_result": "",
      "purpose": ""
    }
  ]
}

Allowed stage:
- import
- unit_test
- integration_test
- api_test
- training_smoke_test
- static_check
- manual_review

Rules:
1. Do not invent commands that require unknown project tooling.
2. Prefer commands that are clearly derivable from the proposed files.
3. Include at least one import or static validation.
4. Include tests for new behavior.
5. Include a small smoke test before full training.
6. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Validation Planner - User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            CODE_VALIDATION_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Patch proposal input for validation planning"
        ),

        template="""
Research Idea:
{idea_payload}

Experiment Protocol:
{experiment_payload}

Patch Proposals:
{patches}

Create a staged validation plan.

Return the required JSON object.
        """.strip(),
    )
)