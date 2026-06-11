"""Week 2 — Microsoft Foundry & Foundry Agent Service.

Insurance Claims Intake Agent exposed as a FastAPI service. Runs in MOCK mode
out of the box; set FOUNDRY_PROJECT_ENDPOINT (+ `az login`) to use the real
Foundry Agent Service backend. Run:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.config import get_settings
from app.routers import claims

settings = get_settings()

app = FastAPI(
    title="Week 2 — Foundry Claims Intake Agent",
    description="Insurance Claims Intake Agent on Microsoft Foundry Agent Service.",
    version="0.2.0",
)

app.include_router(claims.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "week": "2",
        "use_case": "Insurance Claims Intake Agent",
        "backend": "foundry" if settings.use_foundry else "mock",
    }


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "service": "agentic-ai-azure-week02-foundry-claims",
        "endpoint": "/api/v1/claims/intake",
        "backend": "foundry" if settings.use_foundry else "mock",
        "docs": "/docs",
    }
