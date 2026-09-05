import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, ingestion, detection, batch, metrics

# Configure root logger format to show timestamp, level, and message clearly
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app.main")

app = FastAPI(
    title="AI Revenue Recovery Agent API",
    description="Backend API for AI Revenue Recovery Agent monorepo",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"[API INCOMING] {request.method} {request.url.path} (Query: {request.query_params})")
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    logger.info(f"[API OUTGOING] {request.method} {request.url.path} -> Status {response.status_code} ({duration_ms:.1f}ms)")
    return response

app.include_router(health.router)
app.include_router(ingestion.router)
app.include_router(detection.router)
app.include_router(batch.router)
app.include_router(metrics.router)

@app.get("/")
def read_root():
    return {
        "message": "AI Revenue Recovery Agent API is running",
        "docs": "/docs",
        "health": "/health"
    }
