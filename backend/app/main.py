from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, ingestion, detection, batch, metrics

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
