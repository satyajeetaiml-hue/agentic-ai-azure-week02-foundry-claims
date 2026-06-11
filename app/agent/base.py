"""Shared agent interface and helpers."""

from typing import Protocol

from app.schemas import ClaimIntakeRequest, ClaimIntakeResponse


class ClaimsAgent(Protocol):
    """Both the mock and Foundry backends implement this."""

    def intake(self, request: ClaimIntakeRequest) -> ClaimIntakeResponse: ...


# Shared system prompt — the agent's "contract" (Week 1 concept applied here).
SYSTEM_INSTRUCTIONS = (
    "You are an insurance Claims Intake Agent. Given a customer's free-text claim, "
    "you must: (1) extract structured fields (claimant_name, policy_number, "
    "incident_date as YYYY-MM-DD, claim_type, description, estimated_amount); "
    "(2) validate the policy by calling the `policy_lookup` tool with the policy_number; "
    "(3) decide an outcome. Decision rules: if the policy is valid/active -> 'created'; "
    "if the policy is not found or no policy_number could be determined -> 'needs_review'; "
    "if the policy is lapsed/inactive -> 'rejected'. "
    "Always call policy_lookup before deciding when a policy number is present. "
    "Return ONLY a JSON object with keys: claimant_name, policy_number, incident_date, "
    "claim_type, description, estimated_amount, decision, summary."
)


def decide_from_policy(policy_valid: bool, policy_status: str, has_policy_number: bool) -> str:
    """Deterministic decision rule shared by both backends."""
    if not has_policy_number:
        return "needs_review"
    if policy_status == "not_found":
        return "needs_review"
    if policy_valid:
        return "created"
    return "rejected"
