import hashlib
import re

import tiktoken

from backend.app.chunkers.base import (
    ChunkInputPage,
    ChunkResult,
    DocumentChunker,
)


class TokenWindowChunker(
    DocumentChunker
):
    """
    Token-aware Sliding Window Chunker。

    特点：
    1. 使用 Token，而不是字符数量。
    2. 支持 Overlap。
    3. 保留 start_page / end_page。
    4. 同样输入始终产生同样输出。
    """

    name = "token_window"

    version = "1"


    def __init__(
        self,
        encoding_name: str,
        chunk_size: int,
        overlap: int,
    ):
        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be positive"
            )


        if overlap < 0:
            raise ValueError(
                "overlap cannot be negative"
            )


        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller "
                "than chunk_size"
            )


        self.encoding_name = (
            encoding_name
        )

        self.chunk_size = chunk_size

        self.overlap = overlap

        self.stride = (
            chunk_size
            - overlap
        )


        self.encoding = (
            tiktoken.get_encoding(
                encoding_name
            )
        )


    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        """
        做轻量 Text Normalization。

        不做过强清洗，
        避免破坏论文正文结构。
        """

        # Windows / Linux 换行统一。
        text = text.replace(
            "\r\n",
            "\n",
        ).replace(
            "\r",
            "\n",
        )


        # 连续空格 / Tab 压缩。
        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )


        # 超过两个连续空行压缩为两个。
        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )


        return text.strip()


    def chunk(
        self,
        pages: list[ChunkInputPage],
    ) -> list[ChunkResult]:
        """
        将多个 Page Flatten（展平）
        为 Token Stream（Token流），
        然后使用滑动窗口生成 Chunk。
        """

        all_tokens: list[int] = []

        token_pages: list[int] = []


        # ====================================================
        # 1. Page -> Tokens
        # ====================================================

        for page in pages:

            normalized_text = (
                self._normalize_text(
                    page.text
                )
            )


            if not normalized_text:
                continue


            tokens = self.encoding.encode(
                normalized_text
            )


            if not tokens:
                continue


            all_tokens.extend(
                tokens
            )


            # 每一个 token 都记录：
            #
            # “它来自 PDF 第几页？”
            token_pages.extend(
                [
                    page.page_number
                ] * len(tokens)
            )


        # PDF 可能是扫描件，
        # 完全没有可提取文本。
        if not all_tokens:
            return []


        chunks: list[
            ChunkResult
        ] = []


        start = 0

        chunk_index = 0


        # ====================================================
        # 2. Sliding Window
        # ====================================================

        while start < len(
            all_tokens
        ):

            end = min(
                start + self.chunk_size,
                len(all_tokens),
            )


            token_slice = (
                all_tokens[
                    start:end
                ]
            )


            content = (
                self.encoding
                .decode(
                    token_slice
                )
                .strip()
            )


            if content:

                start_page = (
                    token_pages[
                        start
                    ]
                )


                end_page = (
                    token_pages[
                        end - 1
                    ]
                )


                content_sha256 = (
                    hashlib.sha256(
                        content.encode(
                            "utf-8"
                        )
                    ).hexdigest()
                )


                chunks.append(
                    ChunkResult(
                        chunk_index=(
                            chunk_index
                        ),

                        content=content,

                        start_page=(
                            start_page
                        ),

                        end_page=(
                            end_page
                        ),

                        token_count=len(
                            token_slice
                        ),

                        content_sha256=(
                            content_sha256
                        ),
                    )
                )


                chunk_index += 1


            # 已经到达全文末尾。
            if end >= len(
                all_tokens
            ):
                break


            start += self.stride


        return chunks