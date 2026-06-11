# Week 2 — Microsoft Foundry & Foundry Agent Service

[![CI](https://github.com/satyajeetaiml-hue/agentic-ai-azure-week02-foundry-claims/actions/workflows/ci.yml/badge.svg)](https://github.com/satyajeetaiml-hue/agentic-ai-azure-week02-foundry-claims/actions/workflows/ci.yml)

> **Standalone lab** from the *Agentic AI on Azure — Enterprise Master Class* (12 weeks).
> Course hub: [azure-agentic-ai-masterclass](https://github.com/satyajeetaiml-hue/azure-agentic-ai-masterclass).

---

## 🎯 Learning goal
Create a hosted agent on **Microsoft Foundry Agent Service** and expose it through a FastAPI
REST endpoint — secured with **Managed Identity / Entra ID** (no API keys in code).

## 🏢 Enterprise use case — "Insurance Claims Intake Agent" (Insurance)
A customer submits a free-text claim. The agent:
1. **Extracts** structured fields (claimant, policy number, incident date, claim type, amount),
2. **Validates** the policy by calling a `policy_lookup` **tool** (your policy system),
3. **Decides** an outcome — create a case, send for review, or reject — and returns a typed result.

---

## ✅ What this repo implements
Unlike the other week starters (which ship a single mock stub), **this lab is built out**:

- A real **Foundry Agent Service backend** that creates a **persistent hosted agent** with the current
  **`azure-ai-projects` v2** SDK (`agents.create_version` + `PromptAgentDefinition`) — it's registered in
  your Foundry project (visible in the portal), reused across requests, and runs via the Responses API
  with an `agent_reference`, calling a custom **function tool** (`policy_lookup`) during the run.
- A deterministic **mock backend** that mirrors the same extract → tool-call → decide flow, so the
  service is **runnable and fully testable with zero Azure resources**.
- Typed **Pydantic contracts** as the trust boundary, and a clean `ClaimsAgent` interface that swaps
  backends based on config.

The backend is chosen automatically:

| Condition | Backend |
|-----------|---------|
| `FOUNDRY_PROJECT_ENDPOINT` **unset** | `mock` (default — offline, deterministic) |
| `FOUNDRY_PROJECT_ENDPOINT` **set** + `az login` | `foundry` (real Agent Service) |

---

## 🚀 Quick start (mock mode — no Azure)

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs**. Try it:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/claims/intake \
  -H "Content-Type: application/json" \
  -d '{"claim_text": "Car accident on 2026-06-03, policy POL-12345, front bumper damaged, approx $1,200."}'
```

Sample response:

```json
{
  "case_id": "CASE-9F3A1C7D",
  "decision": "created",
  "summary": "Claim validated and a case was created.",
  "extracted": {
    "policy_number": "POL-12345",
    "incident_date": "2026-06-03",
    "claim_type": "auto",
    "estimated_amount": 1200.0
  },
  "policy": {
    "policy_number": "POL-12345",
    "valid": true,
    "status": "active",
    "holder": "Jordan Avery",
    "coverage": ["collision", "liability", "roadside"],
    "deductible": 500.0
  },
  "mode": "mock",
  "agent_steps": ["Extracted fields ...", "Called policy_lookup -> status=active.", "Decision: created."]
}
```

**Test policy numbers:** `POL-12345` / `POL-67890` (active → *created*), `POL-00001` (lapsed → *rejected*),
anything else (not found → *needs_review*).

Run the tests:

```bash
pytest -q
```

---

## ☁️ Switching to the real Foundry Agent Service

### 1. Provision (one-time)
- Create a **Microsoft Foundry** project — see
  [Create a project](https://learn.microsoft.com/azure/foundry/how-to/create-projects).
- Deploy a chat model (e.g. **gpt-4o**) in that project; note its **deployment name**.
- Grant yourself the **Azure AI User** role on the project resource (Access Control / IAM).
  See [RBAC in Foundry](https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry).

### 2. Authenticate (Managed Identity / Entra ID — no keys)
This project uses `DefaultAzureCredential`, so locally just:

```bash
az login
```

In Azure (Container Apps/AKS), assign a **Managed Identity** the same role — the *exact same code* works
with no secrets, which is the point of this week.

### 3. Configure
```bash
cp .env.example .env
```
Set in `.env`:
```
FOUNDRY_PROJECT_ENDPOINT=https://<your-account>.services.ai.azure.com/api/projects/<your-project>
FOUNDRY_MODEL_NAME=gpt-4o          # your deployment name
```

### 4. Run
```bash
uvicorn app.main:app --reload
```
On first request the backend **creates a hosted agent** named by `FOUNDRY_AGENT_NAME` (default
`claims-intake-agent`) via `project.agents.create_version(...)` — it appears in your Foundry project's
**Agents** list — then reuses it for subsequent requests. `GET /health` reports `"backend": "foundry"`,
and `POST /api/v1/claims/intake` runs the hosted agent, which calls `policy_lookup` during the run.

> **How it's wired (`app/agent/foundry_agent.py`):** the hosted agent is defined with
> `PromptAgentDefinition(model, instructions, tools=[FunctionTool(...)])` and created via
> `agents.create_version`. Each request runs it with
> `openai_client.responses.create(input=..., extra_body={"agent_reference": {"name": ..., "type":
> "agent_reference"}})`; `function_call` items are executed locally and fed back as
> `function_call_output`. This is the verified **azure-ai-projects v2** Agent Service API (the older 1.x
> `create_agent` + threads/runs flow is deprecated).
>
> In production, create the agent once via IaC/CI and reference it by name (don't create per process).

---

## 🧪 The lab (extend it)
1. ✅ Wrap a Foundry agent behind a FastAPI `/claims/intake` endpoint *(done — use as your reference)*.
2. ✅ Add a `policy-lookup` tool the agent calls during the run *(done — `app/tools/policy_lookup.py`)*.
3. ✅ Secure the connection with Managed Identity / `DefaultAzureCredential` *(done)*.
4. ✅ Create the agent as a **persistent hosted agent** (appears in the Foundry portal) and reuse it across
   requests *(done — `_ensure_agent` in `app/agent/foundry_agent.py`)*.
5. 🔲 Replace the in-memory policy DB with a real call to your policy API (via APIM + Managed Identity).
6. 🔲 Add a second tool (e.g. `coverage_check`) and a guardrail for low-confidence extractions.

## 🏗️ Architect's lens
- **Hosted vs. self-orchestrated agents** — when the managed thread/state/tool-call runtime saves ops effort.
- **Quota, model routing, region selection** for data residency (claims data is regulated).
- **Identity:** Managed Identity end-to-end; the same code runs locally (`az login`) and in Azure (MI) with
  no secrets — secrets that *do* exist (downstream APIs) belong in **Key Vault**.
- **Contracts as the trust boundary:** the model's output is re-validated against the policy system before a
  decision is finalized (see `_build_response` — we never trust the model's tool echo).

## 🧰 Tech stack
Microsoft Foundry Agent Service, `azure-ai-projects` v2 (Responses API), `azure-identity`
(Managed Identity / Entra ID), FastAPI, Pydantic v2. Key Vault for downstream secrets.

---

## 📁 Project structure
```
agentic-ai-azure-week02-foundry-claims/
├── app/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # settings (FOUNDRY_* env) + backend selection
│   ├── schemas.py              # Pydantic contracts (request/response)
│   ├── routers/claims.py       # POST /api/v1/claims/intake
│   ├── agent/
│   │   ├── base.py             # ClaimsAgent interface, system prompt, decision rule
│   │   ├── mock_agent.py       # deterministic offline backend
│   │   └── foundry_agent.py    # Foundry Agent Service (Responses + function tool)
│   └── tools/policy_lookup.py  # the policy-system tool (fn + JSON schema)
├── tests/test_claims.py        # hermetic tests (mock backend)
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

## 🗺️ Where this fits
Part of **Week 2** of the [course series](https://github.com/satyajeetaiml-hue?tab=repositories&q=agentic-ai-azure).
Previous: [Week 1 — Foundations](https://github.com/satyajeetaiml-hue/agentic-ai-azure-week01-foundations).
Next: [Weeks 3–4 — Agent Framework](https://github.com/satyajeetaiml-hue/agentic-ai-azure-week03-04-agent-framework).

## 📄 License
MIT — see [`LICENSE`](LICENSE).
