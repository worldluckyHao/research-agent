from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    AsyncIterator,
    Protocol,
)


class AsyncFileReader(Protocol):
    """
    Storage 层需要的最小文件读取接口。

    只要求对象能够：

        await reader.read(size)

    因此 Storage 不需要直接依赖 FastAPI UploadFile。
    """

    async def read(
        self,
        size: int = -1,
    ) -> bytes:
        ...


@dataclass(frozen=True)
class StoredObject:
    """
    Storage 保存成功后的结果。
    """

    key: str

    size_bytes: int

    sha256: str


class StorageFileTooLargeError(Exception):
    """
    Storage 写入过程中发现文件超过限制。
    """


class StorageBackend(ABC):
    """
    文件存储统一抽象。

    LocalStorage、S3Storage、MinIOStorage
    都应该实现这个接口。
    """

    name: str


    @abstractmethod
    async def save(
        self,
        reader: AsyncFileReader,
        key: str,
        max_bytes: int,
    ) -> StoredObject:
        """
        保存文件。

        返回：
        - storage key
        - 文件大小
        - SHA-256
        """


    @abstractmethod
    async def delete(
        self,
        key: str,
    ) -> None:
        """删除一个对象。"""


    @abstractmethod
    async def exists(
        self,
        key: str,
    ) -> bool:
        """判断对象是否存在。"""


    @abstractmethod
    def iter_bytes(
        self,
        key: str,
    ) -> AsyncIterator[bytes]:
        """
        流式读取文件。

        下载大 PDF 时，
        不一次性把整个文件加载进内存。
        """