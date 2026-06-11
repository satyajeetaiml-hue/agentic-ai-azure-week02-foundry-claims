"""Week 2 — Microsoft Foundry & Foundry Agent Service — starter FastAPI service.

Use case: Insurance Claims Intake Agent (Insurance).
See README.md for the full lab brief. Run:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Week 2 — Microsoft Foundry & Foundry Agent Service", version="0.1.0")


class LabRequest(BaseModel):
    claim_text: str = Field(..., min_length=1, description="Free-text claim description submitted by the customer.")


@app.get("/health")
def health():
    return {"status": "ok", "week": "2", "use_case": "Insurance Claims Intake Agent"}


@app.get("/")
def root():
    return {
        "service": "agentic-ai-azure-week02-foundry-claims",
        "week": "2",
        "endpoint": "/api/v1/claims/intake",
        "docs": "/docs",
    }


@app.post("/api/v1/claims/intake")
def handler(payload: LabRequest):
    """Mock handler for the Insurance Claims Intake Agent.

    TODO (lab): replace this stub with the real implementation described in
    README.md (the Azure services for this week are listed in the Tech Stack).
    """
    return {
        "week": "2",
        "use_case": "Insurance Claims Intake Agent",
        "received": payload.claim_text,
        "status": "accepted",
        "note": "Mock response — implement the real agent per README.md.",
    }
