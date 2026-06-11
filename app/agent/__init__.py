"""Agent backends for the claims-intake use case.

``get_claims_agent()`` returns the Foundry backend when configured, otherwise
the deterministic mock — so the API surface is identical either way.
"""

from app.agent.base import ClaimsAgent
from app.config import get_settings


def get_claims_agent() -> ClaimsAgent:
    settings = get_settings()
    if settings.use_foundry:
        from app.agent.foundry_agent import FoundryClaimsAgent

        return FoundryClaimsAgent()
    from app.agent.mock_agent import MockClaimsAgent

    return MockClaimsAgent()
