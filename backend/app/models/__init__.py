# ============================================================
# SQLAlchemy Models
# ============================================================
#
# 从 models package 统一暴露 ORM Models。
#
# Alembic 需要确保所有 Model 都被 import，
# 它们才能注册到 Base.metadata。
#

from backend.app.models.paper import Paper
from backend.app.models.user import User


__all__ = [
    "Paper",
    "User",
]