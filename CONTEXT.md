# AI Agent Company — Build Context

## Project Overview
Building a multi-agent AI system: 25 agents organized in 4 layers.
Agents communicate via Jira tickets. Deployed on GCP (pcagentspace).
Using Google ADK (Python) + Vertex AI (no Anthropic API key needed).

## Tech Stack
- **Agent Framework**: Google ADK (Python) v1.27.2
- **LLM**: Vertex AI on GCP (project: pcagentspace) — Gemini models for all agents initially
- **Shared Context**: Jira Cloud (mohamdti.atlassian.net)
- **Code**: GitHub (mt-premiercloud)
- **Compute**: Local testing for now, Cloud Run later
- **Orchestration**: n8n (SKIPPED for now — will add later)
- **Infrastructure**: Terraform (later phases)

## Credentials & Access
- **GCP**: Authenticated as m.touihri@premiercloud.com, project pcagentspace
- **Jira**: mohamdti@gmail.com / mohamdti.atlassian.net / API token configured
- **GitHub**: mt-premiercloud, PAT authenticated via gh CLI

## Current Phase: Phase 1 — Layer 1: Consultant Brain (8 agents)
Starting: 2026-03-22

## Progress Tracker

### Phase 0: Infrastructure Foundation
- [x] Create project directory structure
- [ ] Create GitHub repo (ai-agent-company)
- [ ] Base ADK agent scaffold + Jira integration
- [ ] Vertex AI LLM client wrapper
- [ ] Shared tools (Jira client, web search)

### Phase 1: Consultant Brain — Layer 1 (8 agents)
- [ ] **CB-001** — Company Orchestrator: CEO brain, project intake, blueprint generation
- [ ] **CB-002** — Market Research Agent: Deep market research with web search
- [ ] **CB-003** — Technology Research Agent: Tech stack research, official docs
- [ ] **CB-004** — Architecture Decision Agent: ADR generation, system design
- [ ] **CB-005** — Project Planner Agent: Story decomposition, Jira ticket creation
- [ ] **CB-006** — Technical Verification Agent: Review stories before build
- [ ] **CB-007** — Cost Estimator Agent: Project cost estimation
- [ ] **CB-008** — Unstuck Agent: Diagnose failures, fresh approaches

### Phase 2: Builders — Layer 2 (FUTURE)
- [ ] BLD-001 through BLD-010

### Phase 3: QA & Safety — Layer 3 (FUTURE)
- [ ] QA-001 through QA-004

### Phase 4: Operations — Layer 4 (FUTURE)
- [ ] OPS-001 through OPS-003

## Key Decisions Made
- Using Vertex AI (Gemini) instead of Anthropic API — no Claude API key needed
- Skipping n8n orchestration for now — will add later
- Local testing first, deploy to Cloud Run later
- Agents communicate via Jira tickets only (no direct agent-to-agent)
- Each agent gets fresh context per invocation
- Errors are preserved in Jira comments (never hidden)
- Google ADK provides agent definition structure and tool management

## Architecture Notes
- Each agent is a standalone Python module using Google ADK
- Agent receives Jira ticket ID → reads data → does work → updates Jira → exits
- LLM calls go through Vertex AI (GCP project pcagentspace)
- Shared Jira client library used by all agents
- Web search tools for research agents (CB-002, CB-003, CB-008)

## File Structure
```
/ai-agent-company/
├── CONTEXT.md              ← This file
├── requirements.txt
├── .env                    ← Local env vars (not committed)
├── shared/                 ← Shared utilities
│   ├── jira_client.py      ← Jira API wrapper
│   ├── llm_client.py       ← Vertex AI LLM wrapper
│   ├── web_search.py       ← Web search tool
│   └── config.py           ← Configuration
├── agents/
│   ├── consultant/         ← Layer 1: CB-001 through CB-008
│   ├── builders/           ← Layer 2: BLD-001 through BLD-010
│   ├── qa/                 ← Layer 3: QA-001 through QA-004
│   └── ops/                ← Layer 4: OPS-001 through OPS-003
└── tests/                  ← Test files
```

## Known Issues / Blockers
- None yet

## Session Log
- **2026-03-22**: Project kickoff. Read build plan. Set up GitHub CLI, GCP auth. Creating Layer 1 agents.
