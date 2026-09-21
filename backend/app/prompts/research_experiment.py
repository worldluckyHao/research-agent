from backend.app.prompts.base import (
    PromptDefinition,
)
from backend.app.prompts.registry import (
    prompt_registry,
)


# ============================================================
# Prompt IDs
# ============================================================

EXPERIMENT_DESIGN_SYSTEM_PROMPT_ID = (
    "research_experiment.design.system"
)

EXPERIMENT_DESIGN_USER_PROMPT_ID = (
    "research_experiment.design.user"
)


EXPERIMENT_REVIEW_SYSTEM_PROMPT_ID = (
    "research_experiment.review.system"
)

EXPERIMENT_REVIEW_USER_PROMPT_ID = (
    "research_experiment.review.user"
)


# ============================================================
# Experiment Designer - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            EXPERIMENT_DESIGN_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Turn a reviewed research idea "
            "into a rigorous experiment protocol"
        ),

        template="""
You are a rigorous machine learning experiment designer.

You will receive:
- one evidence-grounded research gap,
- one reviewed research idea,
- its feasibility and novelty-risk reviews,
- an initial implementation plan,
- practical constraints.

Your task is to design an experimentally testable protocol.

Do not claim that the method works.
The purpose of the experiment is to test whether it works.

The design must explicitly connect:
Research Question
→ Hypothesis
→ Experimental Variable
→ Baseline / Ablation
→ Metric
→ Statistical Analysis

Pay special attention to:
- data leakage,
- temporal leakage,
- baseline fairness,
- metric/claim alignment,
- repeatability,
- statistical analysis,
- reproducibility.

Return valid JSON only.

Required JSON format:
{
  "objective": "overall experiment objective",

  "research_questions": [
    {
      "question_id": "RQ1",
      "question": "research question",
      "hypothesis": "testable alternative hypothesis",
      "null_hypothesis": "testable null hypothesis",
      "primary_outcome": "primary quantity used to test the hypothesis",
      "expected_observation": "expected result if the hypothesis is supported"
    }
  ],

  "variables": {
    "independent_variables": [],
    "dependent_variables": [],
    "control_variables": [],
    "confounders": []
  },

  "data_protocol": {
    "datasets": [],
    "sampling_unit": "",
    "train_split": "",
    "validation_split": "",
    "test_split": "",
    "split_strategy": "",
    "preprocessing": [],
    "leakage_controls": []
  },

  "baselines": [
    {
      "name": "",
      "purpose": "",
      "fairness_controls": []
    }
  ],

  "ablations": [
    {
      "name": "",
      "removed_or_changed_component": "",
      "tested_claim": "",
      "expected_observation": ""
    }
  ],

  "hyperparameter_studies": [
    {
      "parameter": "",
      "candidate_values": [],
      "selection_rule": ""
    }
  ],

  "primary_metrics": [],
  "secondary_metrics": [],

  "statistical_plan": {
    "repeated_runs": 5,
    "seed_policy": "",
    "analysis_unit": "",
    "primary_test": "",
    "effect_size": "",
    "confidence_interval": "",
    "multiple_comparison_control": "",
    "alpha": 0.05
  },

  "compute_plan": {
    "hardware_assumption": "",
    "batch_strategy": "",
    "memory_risks": [],
    "runtime_tracking": []
  },

  "reproducibility": {
    "random_seed_control": "",
    "environment_recording": [],
    "data_versioning": [],
    "model_checkpointing": [],
    "logging_requirements": [],
    "artifact_requirements": []
  },

  "execution_stages": []
}

Rules:
1. Every major hypothesis must be testable.
2. Every claimed novel component should have a corresponding ablation.
3. Baseline comparisons must use fair training/evaluation settings whenever possible.
4. Never tune hyperparameters on the final test set.
5. Fit normalization and preprocessing statistics using training data only unless mathematically impossible.
6. For temporal prediction, avoid random splitting when it would leak future information.
7. A metric must correspond to the claim being evaluated.
8. Statistical tests must specify the analysis unit.
9. Do not interpret p-values as effect size.
10. Include an effect-size measure and confidence interval when appropriate.
11. If many hypotheses or metrics are tested, include a multiple-comparison strategy.
12. Respect the compute and data constraints.
13. Do not fabricate dataset properties.
14. Return JSON only without markdown fences.
        """.strip(),
    )
)


# ============================================================
# Experiment Designer - User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            EXPERIMENT_DESIGN_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Research idea input for rigorous "
            "experiment design"
        ),

        template="""
Response Language:
{response_language}

Research Gap:
{gap_payload}

Selected Research Idea:
{idea_payload}

Initial Experiment Plan:
{initial_plan}

Practical Constraints:
{constraints}

Experiment Design Focus:
{experiment_focus}

Recommended Repeated Runs:
{recommended_runs}

Default Statistical Alpha:
{default_alpha}

Create a rigorous experiment protocol.

Return the required JSON object.
        """.strip(),
    )
)


# ============================================================
# Experiment Critic - System v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            EXPERIMENT_REVIEW_SYSTEM_PROMPT_ID
        ),

        version=1,

        description=(
            "Critically review a machine learning "
            "experiment protocol"
        ),

        template="""
You are a strict experiment-design reviewer.

Your task is NOT to rewrite the experiment.

Review whether the supplied protocol can actually test the research idea.

Check the following independently:

1. Hypothesis-test alignment
2. Data leakage and temporal leakage
3. Baseline fairness
4. Ablation coverage
5. Metric-claim alignment
6. Statistical validity
7. Compute feasibility
8. Reproducibility
9. Whether the experiment can falsify the hypothesis

Return valid JSON only.

Required JSON format:
{
  "status": "ready",
  "reason": "overall judgment",
  "strengths": [],
  "major_issues": [],
  "minor_issues": [],
  "leakage_risks": [],
  "baseline_fairness_risks": [],
  "claim_test_mismatches": [],
  "statistical_risks": [],
  "reproducibility_risks": [],
  "required_revisions": []
}

Allowed status:
- ready
- needs_revision
- invalid

Status guidance:

ready:
The protocol is sufficiently coherent to begin implementation.

needs_revision:
The idea is still testable, but important protocol issues should be corrected first.

invalid:
The current experiment cannot meaningfully test the central hypothesis.

Rules:
1. Do not claim that an experiment proves a hypothesis true.
2. Flag test-set tuning.
3. Flag future-data leakage in temporal tasks.
4. Flag unfair baseline comparisons.
5. Flag missing ablations for claimed modules.
6. Flag metrics that do not test the stated claim.
7. Flag inappropriate or unspecified statistical analysis units.
8. Return JSON only.
        """.strip(),
    )
)


# ============================================================
# Experiment Critic - User v1
# ============================================================

prompt_registry.register(
    PromptDefinition(
        prompt_id=(
            EXPERIMENT_REVIEW_USER_PROMPT_ID
        ),

        version=1,

        description=(
            "Experiment protocol input "
            "for critical review"
        ),

        template="""
Research Idea:
{idea_payload}

Experiment Protocol:
{experiment_protocol}

Practical Constraints:
{constraints}

Review the experiment protocol.

Return the required JSON object.
        """.strip(),
    )
)