"""Week 2 — Insurance Claims Intake endpoint.

Wraps the Foundry-hosted agent (or the mock backend) behind a REST API.
"""

from fastapi import APIRouter, HTTPException

from app.agent import get_claims_agent
from app.schemas import ClaimIntakeRequest, ClaimIntakeResponse

router = APIRouter(prefix="/api/v1", tags=["week02-claims-intake"])


@router.post("/claims/intake", response_model=ClaimIntakeResponse)
def claims_intake(payload: ClaimIntakeRequest) -> ClaimIntakeResponse:
    """Extract claim fields, validate the policy via the agent's tool, and decide."""
    agent = get_claims_agent()
    try:
        return agent.intake(payload)
    except RuntimeError as exc:
        # Misconfiguration (e.g. Foundry selected but SDK missing).
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface upstream/Azure failures cleanly
        raise HTTPException(status_code=502, detail=f"Agent run failed: {exc}") from exc
