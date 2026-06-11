"""Verifies the Foundry hosted-agent run logic without a live Foundry project.

We inject a fake OpenAI client that scripts the Responses API: first a turn that
requests the `policy_lookup` tool, then a turn that returns the final JSON. This
exercises the real function-call loop and response parsing in `FoundryClaimsAgent`
(only the network SDK calls are faked).
"""

import json

from app.agent.foundry_agent import FoundryClaimsAgent
from app.schemas import ClaimIntakeRequest


class FakeCall:
    type = "function_call"

    def __init__(self, name, arguments, call_id):
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


class FakeResp:
    def __init__(self, output, output_text="", id="resp-1"):
        self.output = output
        self.output_text = output_text
        self.id = id


class FakeOpenAI:
    """Stands in for project.get_openai_client(); records calls, returns a script."""

    def __init__(self, scripted):
        self._scripted = scripted
        self.calls = []
        self.responses = self  # so `.responses.create(...)` resolves here

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._scripted.pop(0)


def test_run_executes_tool_then_returns_final_json():
    agent = FoundryClaimsAgent()
    final_json = json.dumps(
        {"policy_number": "POL-12345", "claim_type": "auto", "decision": "created", "summary": "ok"}
    )
    fake = FakeOpenAI(
        [
            FakeResp(output=[FakeCall("policy_lookup", json.dumps({"policy_number": "POL-12345"}), "c1")]),
            FakeResp(output=[], output_text=final_json),
        ]
    )
    req = ClaimIntakeRequest(claim_text="Car accident, policy POL-12345.")

    final_text, steps = agent._run(fake, "claims-intake-agent", req)

    assert "POL-12345" in final_text
    assert any("policy_lookup" in s for s in steps)
    # Second turn must feed the tool result back via previous_response_id + function_call_output.
    assert fake.calls[1]["previous_response_id"] == "resp-1"
    assert fake.calls[1]["input"][0]["type"] == "function_call_output"
    assert fake.calls[1]["input"][0]["call_id"] == "c1"
    # Both turns reference the hosted agent.
    assert fake.calls[0]["extra_body"]["agent_reference"]["name"] == "claims-intake-agent"


def test_build_response_revalidates_policy_authoritatively():
    agent = FoundryClaimsAgent()
    req = ClaimIntakeRequest(claim_text="Car accident, policy POL-12345.")
    text = json.dumps({"policy_number": "POL-12345", "decision": "created", "summary": "ok"})

    resp = agent._build_response(req, text, ["step"])

    assert resp.mode == "foundry"
    assert resp.policy.valid is True
    assert resp.decision == "created"
    assert "collision" in resp.policy.coverage


def test_build_response_lapsed_policy_rejected():
    agent = FoundryClaimsAgent()
    req = ClaimIntakeRequest(claim_text="Water damage, policy POL-00001.")
    # Even if the model claimed "created", re-validation against the policy system wins.
    text = json.dumps({"policy_number": "POL-00001", "decision": "created", "summary": "x"})

    resp = agent._build_response(req, text, [])

    assert resp.policy.status == "lapsed"
    assert resp.decision == "rejected"
