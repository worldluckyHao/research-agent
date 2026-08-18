# 先加载中间表。
from backend.app.models.associations import (
    user_saved_papers,
)

# 再加载 ORM Models。
from backend.app.models.paper import Paper
from backend.app.models.user import User


__all__ = [
    "Paper",
    "User",
    "user_saved_papers",
]