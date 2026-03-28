# AI Agent Company — Master Implementation Plan (Merged Architecture)

## Overview
Merging 5 proven open-source systems into one unified AI development agency.
All running locally. All using Gemini 3.1 Pro Preview via Vertex AI (global endpoint).
GCP-only stack enforced.

## Model Config
- **Model:** gemini-3.1-pro-preview
- **Location:** global (NOT us-central1 — preview models require global)
- **Project:** pcagentspace
- **Fast model:** gemini-3.1-flash-lite-preview (for cheap routing)

## Architecture Layers
1. **Paperclip** — Company OS (orchestration, dashboard, budgets, tickets)
2. **Hermes Agent** — Agent brains (memory, skills, tools, model routing)
3. **Superpowers** — Builder process (TDD, review, verification, git workflow)
4. **gstack** — QA & Security (browser testing, code review, security audit)
5. **Autoresearch** — Continuous improvement (git ratchet, trajectory collection)

---

## PHASES

### Phase 1: Foundation Setup [STATUS: COMPLETE]
- [x] 1.1 Paperclip installed via npx onboard, running on http://127.0.0.1:3100 (Node 22 required)
- [x] 1.2 Hermes Agent cloned + deps installed, configured for Vertex AI Gemini 3.1 Pro (global endpoint)
- [x] 1.3 Superpowers cloned
- [x] 1.4 gstack cloned
- [x] 1.5 Paperclip running, Hermes CLI works, Vertex AI token refresh working

### Phase 1 Notes:
- Node 22 is required for Paperclip (Node 24 has tsx/ESM issues, Node 20 has CJS issues)
- Node 22 portable at: tools/node-v22.16.0-win-x64/
- Start Paperclip: set PATH to Node 22 first, then npx paperclipai onboard --yes
- Hermes uses Vertex AI OpenAI-compatible endpoint at global location
- Token refresh: python scripts/refresh_vertex_token.py (tokens valid ~1hr)

### Phase 2: Paperclip Configuration [STATUS: COMPLETE]
- [x] 2.1 Created company "AI Development Agency" (ID: a5eb8615)
- [x] 2.2 Created 9 agents: CEO, Deep Problem Analyst, Market Research, Tech Research, Architect, Planner, Builder, QA, Security
- [x] 2.3 Set company budget ($500/mo), created goal "Deliver Production-Ready Software"
- [x] 2.4 Paperclip dashboard running at http://127.0.0.1:3100 — check it in browser

### Phase 2 Notes:
- Valid Paperclip roles: ceo, cto, cmo, cfo, engineer, designer, pm, qa, devops, researcher, general
- Agent adapter types: http, claude_local, codex_local, cursor, bash
- reportsTo field may need different API call for org chart hierarchy

### Phase 3: Hermes Agent Integration [STATUS: IN PROGRESS]
- [x] 3.1 Hermes working with Gemini 3.1 Pro via Vertex AI (global) — confirmed response
- [x] 3.2 Created Deep Problem Analyst skill (skills/deep-problem-analysis/SKILL.md)
- [x] 3.2b Created GCP-Only Stack enforcement skill (skills/gcp-only-stack/SKILL.md)
- [x] 3.3 Created Hermes-Paperclip bridge server (bridge/hermes_paperclip_bridge.py)
- [x] 3.3b CEO Agent tested via bridge — responds with GCP-enforced strategic analysis
- [ ] 3.4 Create Market Research agent
- [ ] 3.5 Create Tech Research agent
- [ ] 3.6 Create Architect agent
- [ ] 3.7 Create Planner agent
- [ ] 3.8 Create Verifier agent
- [ ] 3.9 Create Cost Estimator agent
- [ ] 3.10 Wire Hermes agents to Paperclip via adapter
- [ ] 3.11 Test planning pipeline end-to-end

### Phase 4: Builder Layer (Superpowers) [STATUS: NOT STARTED]
- [ ] 4.1 Configure Superpowers skills for builder agents
- [ ] 4.2 Create GCP-only stack enforcement skill
- [ ] 4.3 Wire builder agents to Paperclip
- [ ] 4.4 Test: ticket → brainstorm → plan → build → PR

### Phase 5: QA & Security (gstack) [STATUS: NOT STARTED]
- [ ] 5.1 Build gstack browse binary
- [ ] 5.2 Configure QA agent with browser testing
- [ ] 5.3 Configure Security agent with OWASP/STRIDE
- [ ] 5.4 Wire QA agents to Paperclip
- [ ] 5.5 Test: PR → QA → auto-fix → report

### Phase 6: Improvement Loop (Autoresearch) [STATUS: NOT STARTED]
- [ ] 6.1 Set up git ratchet for agent prompt improvement
- [ ] 6.2 Configure trajectory collection from Hermes
- [ ] 6.3 Create immutable evaluation harness
- [ ] 6.4 Test improvement loop

### Phase 7: Integration Test [STATUS: NOT STARTED]
- [ ] 7.1 Submit a real project through Paperclip UI
- [ ] 7.2 Watch full pipeline: plan → build → test → review
- [ ] 7.3 Verify all Paperclip dashboards show progress
- [ ] 7.4 Fix integration issues

---

## Error Log
- **tsx 4.21.0 + Node 24**: ERR_PACKAGE_PATH_NOT_EXPORTED — tsx register hook can't resolve ./dist/cli.mjs. Fixed by using Node 22.
- **tsx 4.19.2 + Node 20**: Same error — tsx pnpm hoisting issue on Windows long paths.
- **npx paperclipai + Node 20**: require() of ES Module encoding-lite.js. Fixed by using Node 22.
- **Paperclip migration**: "relation agent_runtime_state already exists" — fixed by deleting ~/.paperclip/instances/default/db and fresh install.
- **Gemini 3.1 Pro 404**: Preview models require location=global, not us-central1. Fixed.

---

## Session Log
- **2026-03-28**: Master plan created. Starting Phase 1.
- **2026-03-28**: Phase 1 COMPLETE — All 4 repos cloned, Paperclip running on :3100, Node 22 required.
- **2026-03-28**: Phase 2 COMPLETE — Company created, 9 agents, goal set, budgets configured.
- **2026-03-28**: Phase 3 IN PROGRESS — Hermes working with Gemini 3.1 Pro, bridge server on :8200, CEO tested OK.
