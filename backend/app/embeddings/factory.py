from functools import lru_cache

from backend.app.core.config import (
    settings,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)


@lru_cache(
    maxsize=1
)
def create_embedding_provider(
) -> EmbeddingProvider:
    """
    创建当前进程唯一的
    Embedding Provider。

    FastAPI Process:
        一个实例

    Celery Worker Process:
        一个实例

    两个进程互相独立。
    """

    if (
        settings.EMBEDDING_PROVIDER
        == "sentence_transformer"
    ):

        return (
            SentenceTransformerEmbeddingProvider(
                model_name=(
                    settings
                    .EMBEDDING_MODEL_NAME
                ),

                expected_dimension=(
                    settings
                    .EMBEDDING_DIMENSION
                ),

                device=(
                    settings
                    .EMBEDDING_DEVICE
                ),

                batch_size=(
                    settings
                    .EMBEDDING_BATCH_SIZE
                ),

                normalize=(
                    settings
                    .EMBEDDING_NORMALIZE
                ),

                reject_truncation=(
                    settings
                    .EMBEDDING_REJECT_TRUNCATION
                ),
            )
        )


    raise RuntimeError(
        (
            "Unsupported embedding "
            "provider: "
            f"{settings.EMBEDDING_PROVIDER}"
        )
    )