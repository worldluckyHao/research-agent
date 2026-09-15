import logging
from typing import Optional

import numpy as np
import torch
from sentence_transformers import (
    SentenceTransformer,
)

from backend.app.embeddings.base import (
    EmbeddingBatch,
    EmbeddingDimensionMismatchError,
    EmbeddingInputTooLongError,
    EmbeddingProvider,
)


logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddingProvider(
    EmbeddingProvider
):
    """
    基于 Sentence Transformers
    的本地 Embedding Provider。

    当前默认模型：
        multilingual-e5-small
    """

    name = "sentence_transformer"


    def __init__(
        self,
        model_name: str,
        expected_dimension: int,
        device: str,
        batch_size: int,
        normalize: bool,
        reject_truncation: bool,
    ):
        self.model_name = model_name

        self.expected_dimension = (
            expected_dimension
        )

        self.configured_device = (
            device
        )

        self.batch_size = (
            batch_size
        )

        self.normalize = (
            normalize
        )

        self.reject_truncation = (
            reject_truncation
        )


        # Lazy Loading（延迟加载）。
        #
        # 创建 Provider 时暂时不下载模型，
        # 第一次真正 embed 时才加载。
        self._model: Optional[
            SentenceTransformer
        ] = None


        self._resolved_device: Optional[
            str
        ] = None


    # ========================================================
    # Model Lifecycle
    # ========================================================

    def _resolve_device(
        self,
    ) -> str:
        """
        解析真正运行设备。

        auto:
            CUDA 可用 → cuda
            否则     → cpu
        """

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
    ) -> SentenceTransformer:
        """
        Lazy Load Embedding Model。

        一个进程内部只加载一次。
        """

        if self._model is not None:

            return self._model


        device = (
            self._resolve_device()
        )


        logger.info(
            (
                "Loading embedding model: "
                "model=%s device=%s"
            ),
            self.model_name,
            device,
        )


        model = SentenceTransformer(
            self.model_name,
            device=device,
        )


        dimension = (
            model
            .get_sentence_embedding_dimension()
        )


        if dimension is None:

            raise RuntimeError(
                (
                    "Embedding model did not "
                    "report its dimension"
                )
            )


        if (
            dimension
            != self.expected_dimension
        ):

            raise (
                EmbeddingDimensionMismatchError(
                    actual_dimension=(
                        dimension
                    ),
                    expected_dimension=(
                        self.expected_dimension
                    ),
                )
            )


        self._model = model

        self._resolved_device = device


        logger.info(
            (
                "Embedding model loaded: "
                "model=%s dimension=%s "
                "max_seq_length=%s"
            ),
            self.model_name,
            dimension,
            model.max_seq_length,
        )


        return model


    # ========================================================
    # Input Validation
    # ========================================================

    def _validate_input_lengths(
        self,
        texts: list[str],
    ) -> None:
        """
        使用模型自己的 Tokenizer
        检查真正输入长度。

        不能完全依赖 Day25 的 tiktoken，
        因为两种 tokenizer 不同。
        """

        if not self.reject_truncation:

            return


        model = self._get_model()


        tokenizer = (
            model.tokenizer
        )


        encoded = tokenizer(
            texts,

            # 这里故意不截断，
            # 我们需要知道真实长度。
            truncation=False,

            padding=False,

            add_special_tokens=True,
        )


        input_ids = (
            encoded["input_ids"]
        )


        max_allowed = (
            model.max_seq_length
        )


        for token_ids in input_ids:

            actual = len(
                token_ids
            )


            if actual > max_allowed:

                raise (
                    EmbeddingInputTooLongError(
                        actual_tokens=actual,
                        max_tokens=max_allowed,
                    )
                )


    # ========================================================
    # Internal Encode
    # ========================================================

    def _encode(
        self,
        texts: list[str],
    ) -> EmbeddingBatch:
        """
        真正执行 Batch Embedding。
        """

        if not texts:

            raise ValueError(
                "texts cannot be empty"
            )


        model = (
            self._get_model()
        )


        self._validate_input_lengths(
            texts
        )


        vectors = model.encode(
            texts,

            batch_size=(
                self.batch_size
            ),

            convert_to_numpy=True,

            normalize_embeddings=(
                self.normalize
            ),

            show_progress_bar=False,
        )


        # 确保二维矩阵：
        #
        # (batch_size, dimension)
        vectors = np.asarray(
            vectors,
            dtype=np.float32,
        )


        if vectors.ndim != 2:

            raise RuntimeError(
                (
                    "Unexpected embedding "
                    "matrix shape"
                )
            )


        if (
            vectors.shape[1]
            != self.expected_dimension
        ):

            raise (
                EmbeddingDimensionMismatchError(
                    actual_dimension=(
                        int(
                            vectors.shape[1]
                        )
                    ),
                    expected_dimension=(
                        self.expected_dimension
                    ),
                )
            )


        return EmbeddingBatch(
            vectors=(
                vectors.tolist()
            ),

            provider=self.name,

            model_name=(
                self.model_name
            ),

            dimension=(
                self.expected_dimension
            ),

            normalized=(
                self.normalize
            ),

            device=(
                self._resolved_device
                or self._resolve_device()
            ),
        )


    # ========================================================
    # Public API
    # ========================================================

    def embed_documents(
        self,
        texts: list[str],
    ) -> EmbeddingBatch:
        """
        E5 Document / Passage Embedding。

        每段文档增加：
            passage:
        """

        prepared = [
            f"passage: {text}"
            for text in texts
        ]


        return self._encode(
            prepared
        )


    def embed_query(
        self,
        text: str,
    ) -> EmbeddingBatch:
        """
        E5 Query Embedding。

        Query 增加：
            query:
        """

        if not text.strip():

            raise ValueError(
                "query text cannot be empty"
            )


        return self._encode(
            [
                f"query: {text.strip()}"
            ]
        )


    def get_dimension(
        self,
    ) -> int:

        self._get_model()

        return (
            self.expected_dimension
        )


    def get_model_name(
        self,
    ) -> str:

        return self.model_name


    def get_device(
        self,
    ) -> str:

        self._get_model()

        return (
            self._resolved_device
            or "unknown"
        )