FROM python:3.11-slim


# ============================================================
# Runtime Environment
# ============================================================

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app


# ============================================================
# System Dependencies
# ============================================================

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*


# ============================================================
# Python Dependencies
# ============================================================

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --upgrade pip \
    && pip install \
    --no-cache-dir \
    -r requirements.txt


# ============================================================
# Application
# ============================================================

COPY backend ./backend

COPY alembic.ini ./alembic.ini

# 如果 migrations 实际叫 alembic，
# 按你的目录名调整。
COPY alembic ./alembic


# ============================================================
# Runtime
# ============================================================

EXPOSE 8000


CMD [
    "python",
    "-m",
    "uvicorn",
    "backend.app.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
]