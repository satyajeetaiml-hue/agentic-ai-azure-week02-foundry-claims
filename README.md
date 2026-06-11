# Week 2 — Microsoft Foundry & Foundry Agent Service

> **Standalone lab** from the *Agentic AI on Azure — Enterprise Master Class* (12 weeks).
> Each lab is an independent, runnable FastAPI starter. Part of the
> [course series](https://github.com/satyajeetaiml-hue?tab=repositories&q=agentic-ai-azure).

---

## 🎯 Learning goal
Create hosted agents in Foundry Agent Service and expose them via FastAPI.

## 🏢 Enterprise use case — "Insurance Claims Intake Agent" (Insurance)
A customer submits a claim; the agent extracts structured fields, validates the policy number, checks coverage, and creates a case. It uses a Foundry-hosted agent with a tool that calls the policy system.

---

## 🧪 What you'll build (lab)
1. Provision a Foundry project + an Agent Service agent.
2. Add a tool (policy-lookup) and test it in the Foundry playground.
3. Wrap the agent behind a FastAPI `/claims/intake` endpoint exposing it as a REST API.
4. Secure the Foundry connection from FastAPI with **Managed Identity** (no keys in code).

> This starter ships with a **runnable mock** of the endpoint so you can run and test
> immediately, then progressively replace the mock with the real Azure implementation.

## 🏗️ Architect's lens
- Hosted agents (managed runtime, threads, tool calls) vs. self-orchestrated — when does the managed thread/state model save ops effort?
- Quota, model routing, and region selection for data residency.
- Securing the Foundry connection with Managed Identity and Key Vault.

## 🧰 Tech stack
Foundry Agent Service, Azure AI Foundry SDK, FastAPI, Azure Managed Identity, Key Vault, Pydantic.

---

## 🚀 Quick start

```bash
# 1. Create & activate a virtual environment
python -m venv .venv
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) copy the env template — runs in MOCK mode without it
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

# 4. Run the API
uvicorn app.main:app --reload
```

Open the interactive docs at **http://127.0.0.1:8000/docs**.

### Try the endpoint
```bash
curl -X POST http://127.0.0.1:8000/api/v1/claims/intake \
  -H "Content-Type: application/json" \
  -d '{"claim_text": "I had a minor car accident on June 3rd, policy POL-12345, front bumper damaged."}'
```

### Run the tests
```bash
pytest -q
```

### Run with Docker
```bash
docker build -t agentic-ai-azure-week02-foundry-claims .
docker run -p 8000:8000 agentic-ai-azure-week02-foundry-claims
```

---

## 📁 Project structure
```
agentic-ai-azure-week02-foundry-claims/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI app + the /api/v1/claims/intake endpoint
├── tests/
│   └── test_smoke.py
├── requirements.txt
├── Dockerfile
├── .env.example
├── .gitignore
└── README.md
```

---

## 🗺️ Where this fits
This repo covers **Week 2 — Microsoft Foundry & Foundry Agent Service**. The full 12-week path and reference architecture
live in the master-class companion repo:
**[azure-agentic-ai-masterclass](https://github.com/satyajeetaiml-hue/azure-agentic-ai-masterclass)**.

## 📄 License
MIT — see [`LICENSE`](LICENSE).
