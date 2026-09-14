from backend.app.core.config import settings
from backend.app.storage.base import (
    StorageBackend,
)
from backend.app.storage.local import (
    LocalStorageBackend,
)


def create_storage_backend() -> StorageBackend:
    """
    根据配置创建 Storage Backend。

    Day23：
        local

    Future：
        s3
        minio
    """

    if settings.STORAGE_BACKEND == "local":

        return LocalStorageBackend(
            root=settings.LOCAL_STORAGE_PATH,
            chunk_size=(
                settings
                .STORAGE_CHUNK_SIZE_BYTES
            ),
        )


    raise RuntimeError(
        "Unsupported storage backend: "
        f"{settings.STORAGE_BACKEND}"
    )