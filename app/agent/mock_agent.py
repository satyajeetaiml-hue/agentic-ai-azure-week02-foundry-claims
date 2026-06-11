"""Deterministic mock backend — runs with zero Azure dependencies.

It mimics what the Foundry agent does (extract fields -> call the policy tool ->
decide) using simple regex extraction, so the endpoint behaves sensibly offline
and the test-suite is hermetic.
"""

import re
import uuid

from app.agent.base import decide_from_policy
from app.schemas import (
    ClaimIntakeRequest,
    ClaimIntakeResponse,
    ExtractedClaim,
    PolicyValidation,
)
from app.tools.policy_lookup import policy_lookup

_POLICY_RE = re.compile(r"\bPOL-\d{4,6}\b", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_AMOUNT_RE = re.compile(r"\$\s?([\d,]+(?:\.\d{1,2})?)")

_CLAIM_TYPE_KEYWORDS = {
    "auto": ("car", "vehicle", "bumper", "collision", "accident", "auto"),
    "property": ("house", "home", "roof", "flood", "fire", "property", "water"),
    "health": ("hospital", "medical", "injury", "health", "treatment"),
    "travel": ("flight", "trip", "luggage", "travel", "baggage"),
}


def _extract(request: ClaimIntakeRequest) -> ExtractedClaim:
    text = request.claim_text
    policy = request.policy_number
    if not policy:
        m = _POLICY_RE.search(text)
        policy = m.group(0).upper() if m else None

    date_m = _DATE_RE.search(text)
    amount_m = _AMOUNT_RE.search(text)

    claim_type = None
    low = text.lower()
    for ctype, words in _CLAIM_TYPE_KEYWORDS.items():
        if any(w in low for w in words):
            claim_type = ctype
            break

    return ExtractedClaim(
        policy_number=policy,
        incident_date=date_m.group(1) if date_m else None,
        claim_type=claim_type,
        description=text.strip(),
        estimated_amount=float(amount_m.group(1).replace(",", "")) if amount_m else None,
    )


class MockClaimsAgent:
    def intake(self, request: ClaimIntakeRequest) -> ClaimIntakeResponse:
        steps: list[str] = []
        extracted = _extract(request)
        steps.append(f"Extracted fields (policy={extracted.policy_number}, type={extracted.claim_type}).")

        if extracted.policy_number:
            raw = policy_lookup(extracted.policy_number)
            steps.append(f"Called policy_lookup -> status={raw['status']}.")
            policy = PolicyValidation(**raw)
        else:
            steps.append("No policy number found; skipping policy_lookup.")
            policy = PolicyValidation(valid=False, status="missing", message="No policy number provided.")

        decision = decide_from_policy(policy.valid, policy.status, bool(extracted.policy_number))
        steps.append(f"Decision: {decision}.")

        summary = {
            "created": "Claim validated and a case was created.",
            "needs_review": "Claim needs human review (missing or unknown policy).",
            "rejected": "Claim rejected — policy is not active.",
        }[decision]

        return ClaimIntakeResponse(
            case_id=f"CASE-{uuid.uuid4().hex[:8].upper()}",
            decision=decision,
            summary=summary,
            extracted=extracted,
            policy=policy,
            mode="mock",
            agent_steps=steps,
        )
