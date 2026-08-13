import time

from fastapi import (
    FastAPI,
    Request,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.router import api_router


app = FastAPI(
    title="ResearchAgent API",
    version="0.3.0",
)


allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(
    request: Request,
    call_next,
):

    start_time = time.perf_counter()

    response = await call_next(
        request
    )

    process_time = (
        time.perf_counter()
        - start_time
    )

    response.headers[
        "X-Process-Time"
    ] = str(process_time)

    return response


@app.get(
    "/health",
    tags=["health"],
)
def health():
    return {
        "status": "ok",
        "service": "research-agent",
    }


app.include_router(
    api_router,
    prefix="/api/v1",
)