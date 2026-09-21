from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.agents.code_assistant import (
    ResearchCodeAssistantAgent,
)
from backend.app.core.config import (
    settings,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.schemas.code_assistant import (
    CodeAssistantRequest,
    CodeAssistantResponse,
)
from backend.app.schemas.research_experiment import (
    ResearchExperimentRequest,
)
from backend.app.services import (
    research_experiment,
)


# ============================================================
# Public Service
# ============================================================

async def generate_code_change_proposal(
    db: AsyncSession,
    project_id: int,
    user_id: int,
    request: CodeAssistantRequest,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
) -> CodeAssistantResponse:
    """
    Day42 Code Assistant Service。

    Flow:

        Day41 Experiment Design
            ↓
        Select Idea / Experiment
            ↓
        Code Planning
            ↓
        Patch Proposal
            ↓
        Safety Review
            ↓
        Validation Plan
    """

    # ========================================================
    # 1. Reuse Day41
    # ========================================================

    experiment_request = (
        ResearchExperimentRequest(
            items=(
                request.items
            ),

            comparison_focus=(
                request
                .comparison_focus
            ),

            gap_focus=(
                request
                .gap_focus
            ),

            selected_gap_id=(
                request
                .selected_gap_id
            ),

            selected_idea_id=(
                request
                .selected_idea_id
            ),

            constraints=(
                request
                .constraints
            ),

            experiment_focus=(
                request
                .experiment_focus
            ),

            response_language=(
                request
                .response_language
            ),
        )
    )


    experiment = (
        await research_experiment
        .design_project_research_experiment(
            db=db,

            project_id=(
                project_id
            ),

            user_id=(
                user_id
            ),

            request=(
                experiment_request
            ),

            embedding_provider=(
                embedding_provider
            ),

            llm_provider=(
                llm_provider
            ),
        )
    )


    # ========================================================
    # 2. Normalize Allowed Paths
    # ========================================================

    allowed_paths = [
        path.strip()

        for path
        in request.allowed_paths

        if path.strip()
    ]


    # ========================================================
    # 3. Max File Changes
    # ========================================================

    max_file_changes = min(
        request.max_file_changes,

        settings
        .CODE_ASSISTANT_MAX_FILE_CHANGES,
    )


    # ========================================================
    # 4. Agent
    # ========================================================

    agent = (
        ResearchCodeAssistantAgent(
            llm_provider=(
                llm_provider
            )
        )
    )


    # ========================================================
    # 5. Proposal
    # ========================================================

    return (
        await agent.propose_changes(
            project_id=(
                project_id
            ),

            experiment=(
                experiment
            ),

            selected_idea=(
                experiment
                .selected_idea
            ),

            allowed_paths=(
                allowed_paths
            ),

            max_file_changes=(
                max_file_changes
            ),

            include_tests=(
                request
                .include_tests
            ),

            response_language=(
                request
                .response_language
            ),
        )
    )