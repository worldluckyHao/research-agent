import asyncio
import hashlib
import os
from pathlib import Path
from typing import AsyncIterator

import aiofiles

from backend.app.storage.base import (
    AsyncFileReader,
    StorageBackend,
    StorageFileTooLargeError,
    StoredObject,
)


class LocalStorageBackend(StorageBackend):
    """
    本地文件系统 Storage。

    当前用于开发环境。

    后续可以增加：
    - S3StorageBackend
    - MinIOStorageBackend
    """

    name = "local"


    def __init__(
        self,
        root: Path,
        chunk_size: int,
    ):
        self.root = root.resolve()

        self.chunk_size = chunk_size

        # Storage 根目录不存在则创建。
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )


    def _resolve(
        self,
        key: str,
    ) -> Path:
        """
        将 Storage Key 转换成真实本地路径。

        同时防止路径穿越：

        ../../secret.txt
        """

        path = (
            self.root
            / key
        ).resolve()


        # path 必须位于 Storage root 之内。
        if (
            path != self.root
            and self.root not in path.parents
        ):
            raise ValueError(
                "Invalid storage key"
            )


        return path


    async def save(
        self,
        reader: AsyncFileReader,
        key: str,
        max_bytes: int,
    ) -> StoredObject:
        """
        流式保存文件。

        关键设计：

        1. 不一次性读取整个 PDF
        2. 写入过程中计算 SHA-256
        3. 写入过程中检查 Size
        4. 先写 .part 临时文件
        5. 完成后原子 replace
        """

        final_path = self._resolve(
            key
        )

        temp_path = self._resolve(
            f"{key}.part"
        )


        final_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


        size_bytes = 0

        digest = hashlib.sha256()


        try:

            async with aiofiles.open(
                temp_path,
                mode="wb",
            ) as output:

                while True:

                    chunk = await reader.read(
                        self.chunk_size
                    )


                    if not chunk:
                        break


                    size_bytes += len(
                        chunk
                    )


                    if size_bytes > max_bytes:
                        raise StorageFileTooLargeError()


                    digest.update(
                        chunk
                    )


                    await output.write(
                        chunk
                    )


            # 临时文件完整写完以后，
            # 再替换成最终文件。
            await asyncio.to_thread(
                os.replace,
                temp_path,
                final_path,
            )


        except Exception:

            # 写入失败时清理残留 .part。
            if temp_path.exists():

                await asyncio.to_thread(
                    temp_path.unlink
                )

            raise


        return StoredObject(
            key=key,
            size_bytes=size_bytes,
            sha256=digest.hexdigest(),
        )


    async def delete(
        self,
        key: str,
    ) -> None:

        path = self._resolve(
            key
        )


        if path.exists():

            await asyncio.to_thread(
                path.unlink
            )


    async def exists(
        self,
        key: str,
    ) -> bool:

        path = self._resolve(
            key
        )

        return await asyncio.to_thread(
            path.is_file
        )


    async def _stream_file(
        self,
        key: str,
    ) -> AsyncIterator[bytes]:

        path = self._resolve(
            key
        )


        async with aiofiles.open(
            path,
            mode="rb",
        ) as input_file:

            while True:

                chunk = await input_file.read(
                    self.chunk_size
                )


                if not chunk:
                    break


                yield chunk


    def iter_bytes(
        self,
        key: str,
    ) -> AsyncIterator[bytes]:

        return self._stream_file(
            key
        )