"""CB-004 — Architecture Decision Agent

Makes final technology stack decisions and designs system architecture.
Produces the Architecture Decision Record (ADR) with Mermaid diagrams.
"""

import json
from shared.config import get_logger
from shared.llm_client import call_llm
from shared import jira_client

log = get_logger("CB-004.Architecture")

SYSTEM_PROMPT = """You are a senior solutions architect making final technology decisions for a software project.

You receive the Project Blueprint, Market Research, and Technology Research. You must produce an Architecture Decision Record (ADR).

## Consider:
- Project requirements and constraints
- Budget and timeline
- LLM-friendliness (will AI agents be able to work with this tech effectively?)
- Deployment simplicity
- Maintenance burden
- Team size (this will be built by AI agents)

## Output Format (JSON):
{
    "project_name": "...",
    "architecture_style": "monolith|microservices|serverless|jamstack|hybrid",
    "stack": {
        "frontend": {"choice": "...", "version": "...", "rationale": "..."},
        "backend": {"choice": "...", "version": "...", "rationale": "..."},
        "database": {"choice": "...", "version": "...", "rationale": "..."},
        "hosting": {"choice": "...", "rationale": "..."},
        "auth": {"choice": "...", "rationale": "..."},
        "ci_cd": {"choice": "...", "rationale": "..."},
        "additional": [{"name": "...", "purpose": "...", "rationale": "..."}]
    },
    "architecture_diagram_mermaid": "graph TD\\n  A[Client] --> B[API Gateway]\\n  ...",
    "data_model_overview": "Key entities and relationships",
    "api_design": {"style": "REST|GraphQL|gRPC", "rationale": "..."},
    "rejected_alternatives": [{"name": "...", "reason": "..."}],
    "risks": [{"risk": "...", "mitigation": "..."}],
    "prerequisites_checklist": [
        {"item": "...", "type": "credential|service|configuration", "status": "needed"}
    ],
    "environments": {
        "development": "Local + Docker",
        "staging": "...",
        "production": "..."
    },
    "coding_standards": {
        "language": "...",
        "style_guide": "...",
        "testing": "...",
        "documentation": "..."
    }
}

ALWAYS produce a prerequisites checklist — what access/credentials are needed before building.
Output valid JSON only.
"""


def run(blueprint_ticket_key: str, market_research_key: str = None, tech_research_key: str = None) -> dict:
    """Run architecture decision process.

    Args:
        blueprint_ticket_key: Jira ticket with Project Blueprint.
        market_research_key: Optional market research ticket.
        tech_research_key: Optional tech research ticket.

    Returns:
        dict with ADR and created ticket key.
    """
    log.info("=" * 60)
    log.info("CB-004 Architecture Decision Agent — START")
    log.info("=" * 60)

    # Step 1: Gather all inputs
    log.info("Step 1: Gathering inputs from Jira...")
    bp_issue = jira_client.get_issue(blueprint_ticket_key)
    blueprint_text = bp_issue["fields"].get("description", "") or ""
    project_key = bp_issue["fields"]["project"]["key"]

    inputs = f"## Project Blueprint\n{blueprint_text}\n\n"

    if market_research_key:
        mr_issue = jira_client.get_issue(market_research_key)
        inputs += f"## Market Research\n{mr_issue['fields'].get('description', '')}\n\n"

    if tech_research_key:
        tr_issue = jira_client.get_issue(tech_research_key)
        inputs += f"## Technology Research\n{tr_issue['fields'].get('description', '')}\n\n"

    log.debug("Total input context: %d chars", len(inputs))

    # Step 2: LLM analysis
    log.info("Step 2: Generating Architecture Decision Record with LLM...")
    raw_response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=inputs,
        temperature=0.4,
        max_tokens=6000,
    )

    # Step 3: Parse and save
    log.info("Step 3: Parsing and saving ADR to Jira...")
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        adr = json.loads(cleaned)
    except json.JSONDecodeError:
        adr = {"raw_response": raw_response}
        log.warning("Could not parse ADR as JSON")

    ticket = jira_client.create_issue(
        project_key=project_key,
        summary="Architecture Decision Record (ADR)",
        description=json.dumps(adr, indent=2),
        issue_type="Task",
        labels=["architecture", "adr", "planning"],
    )
    ticket_key = ticket.get("key", "")

    jira_client.add_comment(blueprint_ticket_key,
                            f"*CB-004 Architecture Decision Complete* — See {ticket_key}")

    log.info("=" * 60)
    log.info("CB-004 Architecture Decision — COMPLETE: %s", ticket_key)
    log.info("=" * 60)

    return {"adr": adr, "adr_ticket_key": ticket_key}
