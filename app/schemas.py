"""Pydantic contracts for the Insurance Claims Intake Agent.

These typed models are the API's trust boundary — the agent (mock or Foundry)
must produce data that validates against ``ClaimIntakeResponse``.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ClaimIntakeRequest(BaseModel):
    claim_text: str = Field(
        ...,
        min_length=1,
        description="Free-text claim description submitted by the customer.",
        examples=["I had a minor car accident on 2026-06-03, policy POL-12345, front bumper damaged."],
    )
    policy_number: str | None = Field(
        default=None,
        description="Optional policy number if known up front; otherwise the agent extracts it.",
    )


class ExtractedClaim(BaseModel):
    """Structured fields the agent extracts from the free-text claim."""

    claimant_name: str | None = None
    policy_number: str | None = None
    incident_date: str | None = Field(default=None, description="ISO date if found (YYYY-MM-DD).")
    claim_type: str | None = Field(default=None, description="e.g. auto, property, health, travel.")
    description: str | None = None
    estimated_amount: float | None = None


class PolicyValidation(BaseModel):
    """Result of calling the policy system (the agent's tool)."""

    policy_number: str | None = None
    valid: bool = False
    status: str = "unknown"
    holder: str | None = None
    coverage: list[str] = Field(default_factory=list)
    deductible: float | None = None
    message: str | None = None


class ClaimIntakeResponse(BaseModel):
    case_id: str
    decision: Literal["created", "needs_review", "rejected"]
    summary: str
    extracted: ExtractedClaim
    policy: PolicyValidation
    mode: Literal["mock", "foundry"]
    agent_steps: list[str] = Field(default_factory=list)
