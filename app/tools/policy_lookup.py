"""The agent's single tool: a mock "policy system" lookup.

In a real deployment this would call your core insurance/policy API (likely via
Managed Identity through APIM). Here it's an in-memory stand-in so the lab runs
offline. The same Python function is used by:

* the **mock** backend (called directly), and
* the **Foundry** backend (registered as an OpenAI/Responses *function tool* and
  executed locally when the model decides to call it).

``POLICY_TOOL_SCHEMA`` is the JSON-schema tool definition sent to the model.
"""

from typing import Any

# In-memory policy database (stand-in for the core policy system).
_POLICIES: dict[str, dict[str, Any]] = {
    "POL-12345": {
        "holder": "Jordan Avery",
        "status": "active",
        "coverage": ["collision", "liability", "roadside"],
        "deductible": 500.0,
    },
    "POL-67890": {
        "holder": "Sam Rivera",
        "status": "active",
        "coverage": ["property", "contents", "flood"],
        "deductible": 1000.0,
    },
    "POL-00001": {
        "holder": "Lapsed Customer",
        "status": "lapsed",
        "coverage": [],
        "deductible": None,
    },
}


def policy_lookup(policy_number: str) -> dict[str, Any]:
    """Look up a policy by number and return its validation/coverage details.

    Returns a JSON-serializable dict (this is also the function-tool output that
    gets fed back to the model in the Foundry backend).
    """
    record = _POLICIES.get((policy_number or "").strip().upper())
    if record is None:
        return {
            "policy_number": policy_number,
            "valid": False,
            "status": "not_found",
            "message": "No policy found for that number.",
        }
    return {
        "policy_number": policy_number,
        "valid": record["status"] == "active",
        "status": record["status"],
        "holder": record["holder"],
        "coverage": record["coverage"],
        "deductible": record["deductible"],
        "message": "Policy found." if record["status"] == "active" else "Policy is not active.",
    }


# JSON-schema definition handed to the model as a callable tool (Responses API shape).
POLICY_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "name": "policy_lookup",
    "description": "Validate a policy number against the policy system and return "
    "its status, coverage list, and deductible.",
    "parameters": {
        "type": "object",
        "properties": {
            "policy_number": {
                "type": "string",
                "description": "The policy number to validate, e.g. 'POL-12345'.",
            }
        },
        "required": ["policy_number"],
        "additionalProperties": False,
    },
}
