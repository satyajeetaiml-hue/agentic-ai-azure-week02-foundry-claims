"""Foundry Agent Service backend.

Uses the current **azure-ai-projects v2** SDK: an ``AIProjectClient`` authenticated
with Entra ID (``DefaultAzureCredential``), from which we obtain an OpenAI client via
``get_openai_client()`` and drive the agent through the **Responses API** with a custom
``policy_lookup`` *function tool*.

The flow mirrors the agent loop:
  reason/plan  -> model decides to call the tool
  act          -> we execute ``policy_lookup`` locally and feed the result back
  observe      -> model returns the final structured JSON, which we validate.

Azure SDK imports are done lazily so the rest of the app (and the mock backend)
runs without the Azure packages installed.
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

        steps: list[str] = []
        with (
            DefaultAzureCredential() as credential,
            AIProjectClient(
                endpoint=self.settings.foundry_project_endpoint, credential=credential
            ) as project,
        ):
            steps.append("Connected to Foundry project; using Responses API agent runtime.")
            openai_client = project.get_openai_client()

            response = openai_client.responses.create(
                model=self.settings.foundry_model_name,
                input=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": self._user_prompt(request)},
                ],
                tools=[POLICY_TOOL_SCHEMA],
            )

            # Drive the function-tool calling loop until the model stops requesting tools.
            for _ in range(_MAX_TOOL_ITERATIONS):
                calls = [it for it in response.output if getattr(it, "type", None) == "function_call"]
                if not calls:
                    break
                tool_outputs = []
                for call in calls:
                    args = json.loads(call.arguments or "{}")
                    if call.name == "policy_lookup":
                        result = policy_lookup(args.get("policy_number", ""))
                        steps.append(f"Model invoked policy_lookup -> status={result.get('status')}.")
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
                    model=self.settings.foundry_model_name,
                    previous_response_id=response.id,
                    input=tool_outputs,
                    tools=[POLICY_TOOL_SCHEMA],
                )

            final_text = response.output_text or "{}"

        return self._build_response(request, final_text, steps)

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
            summary=data.get("summary") or "Claim processed by the Foundry agent.",
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
