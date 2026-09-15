from backend.app.chunkers.base import (
    DocumentChunker,
)
from backend.app.chunkers.token_window import (
    TokenWindowChunker,
)
from backend.app.core.config import (
    settings,
)


def create_document_chunker(
) -> DocumentChunker:
    """
    创建 Document Chunker。

    Day25：
        token_window

    Future：
        semantic
        section_aware
    """

    if (
        settings.CHUNKER_NAME
        == "token_window"
    ):

        return TokenWindowChunker(
            encoding_name=(
                settings
                .CHUNK_TOKENIZER_NAME
            ),

            chunk_size=(
                settings
                .CHUNK_SIZE_TOKENS
            ),

            overlap=(
                settings
                .CHUNK_OVERLAP_TOKENS
            ),
        )


    raise RuntimeError(
        "Unsupported chunker: "
        f"{settings.CHUNKER_NAME}"
    )