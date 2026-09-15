import logging
from functools import lru_cache
from typing import Optional

import numpy as np
import torch
from sentence_transformers import (
    CrossEncoder,
)

from backend.app.core.config import (
    settings,
)
from backend.app.retrieval.base import (
    RetrievalCandidate,
)


logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Cross-Encoder Reranker
    （交叉编码重排序器）。

    输入：
        Query + Candidate Chunk

    输出：
        Relevance Score
        相关性分数
    """

    def __init__(
        self,
        model_name: str,
        device: str,
        batch_size: int,
    ):
        self.model_name = model_name

        self.configured_device = device

        self.batch_size = batch_size

        self._model: Optional[
            CrossEncoder
        ] = None


    def _resolve_device(
        self,
    ) -> str:

        if (
            self.configured_device
            != "auto"
        ):
            return (
                self.configured_device
            )


        if torch.cuda.is_available():
            return "cuda"


        return "cpu"


    def _get_model(
        self,
    ) -> CrossEncoder:

        if self._model is not None:
            return self._model


        device = (
            self._resolve_device()
        )


        logger.info(
            (
                "Loading reranker model: "
                "model=%s device=%s"
            ),
            self.model_name,
            device,
        )


        self._model = CrossEncoder(
            self.model_name,
            device=device,
        )


        return self._model


    def rerank(
        self,
        query: str,
        candidates: list[
            RetrievalCandidate
        ],
    ) -> list[RetrievalCandidate]:
        """
        对 Candidate 重新排序。
        """

        if not candidates:
            return []


        model = (
            self._get_model()
        )


        pairs = [
            [
                query,
                candidate.content,
            ]
            for candidate in candidates
        ]


        scores = model.predict(
            pairs,
            batch_size=(
                self.batch_size
            ),
            show_progress_bar=False,
        )


        scores = np.asarray(
            scores,
            dtype=np.float32,
        ).reshape(-1)


        reranked = []


        for candidate, score in zip(
            candidates,
            scores,
        ):

            reranked.append(
                RetrievalCandidate(
                    chunk_id=(
                        candidate.chunk_id
                    ),

                    chunk_index=(
                        candidate.chunk_index
                    ),

                    content=(
                        candidate.content
                    ),

                    start_page=(
                        candidate.start_page
                    ),

                    end_page=(
                        candidate.end_page
                    ),

                    token_count=(
                        candidate.token_count
                    ),

                    semantic_rank=(
                        candidate.semantic_rank
                    ),

                    semantic_score=(
                        candidate.semantic_score
                    ),

                    lexical_rank=(
                        candidate.lexical_rank
                    ),

                    lexical_score=(
                        candidate.lexical_score
                    ),

                    rrf_score=(
                        candidate.rrf_score
                    ),

                    rerank_score=(
                        float(
                            score
                        )
                    ),
                )
            )


        reranked.sort(
            key=lambda item: (
                item.rerank_score
                if item.rerank_score
                is not None
                else float("-inf")
            ),
            reverse=True,
        )


        return reranked


@lru_cache(
    maxsize=1
)
def create_reranker(
) -> CrossEncoderReranker:
    """
    当前进程缓存一个 Reranker。
    """

    return CrossEncoderReranker(
        model_name=(
            settings
            .RERANKER_MODEL_NAME
        ),

        device=(
            settings
            .RERANKER_DEVICE
        ),

        batch_size=(
            settings
            .RERANKER_BATCH_SIZE
        ),
    )