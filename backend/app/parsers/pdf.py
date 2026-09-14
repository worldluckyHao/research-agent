from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class ParsedPDFPage:
    """
    单页 PDF 解析结果。
    """

    page_number: int

    text: str


@dataclass(frozen=True)
class ParsedPDF:
    """
    整份 PDF 的解析结果。
    """

    pages: list[ParsedPDFPage]

    page_count: int

    parser_name: str

    parser_version: str


class PDFParser:
    """
    PDF Parser（PDF 解析器）抽象。

    当前实现使用 PyMuPDF。
    """

    name = "pymupdf"


    def parse(
        self,
        file_path: Path,
    ) -> ParsedPDF:
        """
        读取本地 PDF，
        按页提取文本。

        注意：
        PyMuPDF 是同步库，
        所以 Service 层会通过 asyncio.to_thread()
        把这段逻辑放到线程执行，
        避免阻塞 FastAPI/Celery 的 Event Loop。
        """

        pages: list[ParsedPDFPage] = []


        with pymupdf.open(
            file_path
        ) as document:

            for index in range(
                document.page_count
            ):

                page = document.load_page(
                    index
                )


                text = page.get_text(
                    "text"
                )


                # 做最基础标准化：
                # - 去除首尾多余空白
                # - 保留正文内部换行
                text = text.strip()


                pages.append(
                    ParsedPDFPage(
                        # PyMuPDF index 从 0 开始，
                        # 人类页码从 1 开始。
                        page_number=index + 1,
                        text=text,
                    )
                )


            return ParsedPDF(
                pages=pages,
                page_count=(
                    document.page_count
                ),
                parser_name=self.name,
                parser_version=(
                    getattr(
                        pymupdf,
                        "__version__",
                        "unknown",
                    )
                ),
            )