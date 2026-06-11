"""Foundry Agent Service backend — **persistent hosted agent**.

Uses the current **azure-ai-projects v2** SDK to create a *hosted* agent that is
registered in your Foundry project (visible in the portal) and reused across
requests, then runs it via the Responses API with an ``agent_reference``:

  * ``project.agents.create_version(agent_name, definition=PromptAgentDefinition(
        model, instructions, tools=[FunctionTool(...)]))`` — the hosted agent.
  * ``openai_client.responses.create(input=..., extra_body={"agent_reference": ...})``
    — runs the hosted agent; tool calls surface as ``function_call`` output items
    which we execute (``policy_lookup``) and feed back as ``function_call_output``.

The flow still mirrors the agent loop (reason → plan → act → observe). Azure SDK
imports are lazy so the mock backend and tests run without the Azure packages.
"""

import json
import uuid
from typing import Any

from app.agent.base import SYSTEM_INSTRUCTIONS, decide_from_policy
from app.config import get_settings
from app.schemas import (
    ClaimIntakeRequest,
    ClaimIntakeResponse,
    ExtractedClaim,
    PolicyValidation,
)
from app.tools.policy_lookup import POLICY_TOOL_SCHEMA, policy_lookup

_MAX_TOOL_ITERATIONS = 5
# Process-level cache so the hosted agent is created once and reused across requests.
_AGENT_VERSIONS: dict[str, str] = {}


class FoundryClaimsAgent:
    def __init__(self) -> None:
        self.settings = get_settings()

    def intake(self, request: ClaimIntakeRequest) -> ClaimIntakeResponse:
        try:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:  # pragma: no cover - depends on optional deps
            raise RuntimeError(
                "Foundry backend requires 'azure-ai-projects' and 'azure-identity'. "
                "Install requirements.txt, or unset FOUNDRY_PROJECT_ENDPOINT to use mock mode."
            ) from exc

        s = self.settings
        with (
            DefaultAzureCredential() as credential,
            AIProjectClient(endpoint=s.foundry_project_endpoint, credential=credential) as project,
            project.get_openai_client() as openai_client,
        ):
            agent_name = self._ensure_agent(project)
            final_text, steps = self._run(openai_client, agent_name, request)

        return self._build_response(request, final_text, steps)

    def _ensure_agent(self, project) -> str:
        """Create the hosted agent once (cached), returning its name to reference."""
        from azure.ai.projects.models import FunctionTool, PromptAgentDefinition

        name = self.settings.foundry_agent_name
        if name in _AGENT_VERSIONS:
            return name

        tool = FunctionTool(
            name="policy_lookup",
            description=POLICY_TOOL_SCHEMA["description"],
            parameters=POLICY_TOOL_SCHEMA["parameters"],
            strict=True,
        )
        agent = project.agents.create_version(
            agent_name=name,
            definition=PromptAgentDefinition(
                model=self.settings.foundry_model_name,
                instructions=SYSTEM_INSTRUCTIONS,
                tools=[tool],
            ),
        )
        _AGENT_VERSIONS[name] = agent.version
        return name

    def _run(self, openai_client, agent_name: str, request: ClaimIntakeRequest):
        """Drive the hosted agent + function-tool loop; return (final_text, steps)."""
        steps = [f"Using hosted Foundry agent '{agent_name}'."]
        ref = {"agent_reference": {"name": agent_name, "type": "agent_reference"}}

        response = openai_client.responses.create(input=self._user_prompt(request), extra_body=ref)

        for _ in range(_MAX_TOOL_ITERATIONS):
            calls = [it for it in response.output if getattr(it, "type", None) == "function_call"]
            if not calls:
                break
            tool_outputs = []
            for call in calls:
                args = json.loads(call.arguments or "{}")
                if call.name == "policy_lookup":
                    result = policy_lookup(args.get("policy_number", ""))
                    steps.append(f"Agent called policy_lookup -> status={result.get('status')}.")
                else:
                    result = {"error": f"unknown tool '{call.name}'"}
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result),
                    }
                )
            response = openai_client.responses.create(
                input=tool_outputs, previous_response_id=response.id, extra_body=ref
            )

        return (response.output_text or "{}"), steps

    @staticmethod
    def _user_prompt(request: ClaimIntakeRequest) -> str:
        hint = f"\nKnown policy number: {request.policy_number}" if request.policy_number else ""
        return f"Process this claim:\n\n{request.claim_text}{hint}"

    def _build_response(
        self, request: ClaimIntakeRequest, final_text: str, steps: list[str]
    ) -> ClaimIntakeResponse:
        data = self._parse_json(final_text)
        extracted = ExtractedClaim(
            claimant_name=data.get("claimant_name"),
            policy_number=data.get("policy_number") or request.policy_number,
            incident_date=data.get("incident_date"),
            claim_type=data.get("claim_type"),
            description=data.get("description") or request.claim_text,
            estimated_amount=_to_float(data.get("estimated_amount")),
        )

        # Re-validate the policy authoritatively (don't trust the model's tool echo).
        if extracted.policy_number:
            policy = PolicyValidation(**policy_lookup(extracted.policy_number))
        else:
            policy = PolicyValidation(valid=False, status="missing", message="No policy number provided.")

        decision = decide_from_policy(policy.valid, policy.status, bool(extracted.policy_number))
        steps.append(f"Validated policy and finalized decision: {decision}.")

        return ClaimIntakeResponse(
            case_id=f"CASE-{uuid.uuid4().hex[:8].upper()}",
            decision=decision,
            summary=data.get("summary") or "Claim processed by the Foundry hosted agent.",
            extracted=extracted,
            policy=policy,
            mode="foundry",
            agent_steps=steps,
        )

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Best-effort extraction of the JSON object from the model's reply."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1] if "```" in cleaned[3:] else cleaned[3:]
            cleaned = cleaned.removeprefix("json").strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return None
