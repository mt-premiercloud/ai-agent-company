"""CB-007 — Cost Estimator Agent

Estimates project cost: LLM API costs, GCP infrastructure, third-party services, timeline.
Conservative estimates with 30% buffer.
"""

import json
from shared.config import get_logger
from shared.llm_client import call_llm
from shared import jira_client

log = get_logger("CB-007.CostEstimator")

SYSTEM_PROMPT = """You are a project cost estimator for an AI-driven software development agency.

You receive all user stories (with complexity labels) and the Architecture Decision Record.
Estimate the TOTAL project cost.

## Cost Categories:
1. LLM API costs (based on story count and complexity)
   - Simple story (S): ~$1-2 in LLM calls
   - Medium story (M): ~$3-5 in LLM calls
   - Large story (L): ~$5-10 in LLM calls
   - Planning agents (8 agents): ~$20-40 total
2. GCP Infrastructure (monthly)
   - Cloud Run: ~$5-20/month
   - Cloud SQL: ~$10-30/month
   - Storage: ~$1-5/month
   - Other services as needed
3. Third-party services (based on ADR)
4. Timeline estimate (based on story count, 5-10 stories/day for AI agents)

## Rules:
- Be CONSERVATIVE — better to over-estimate
- Include a 30% buffer for unexpected issues
- Break down costs clearly

## Output Format (JSON):
{
    "cost_breakdown": {
        "llm_api_costs": {
            "planning_agents": {"amount": 0, "detail": "..."},
            "builder_agents": {"amount": 0, "detail": "..."},
            "qa_agents": {"amount": 0, "detail": "..."},
            "total": 0
        },
        "gcp_infrastructure_monthly": {
            "compute": {"amount": 0, "detail": "..."},
            "database": {"amount": 0, "detail": "..."},
            "storage": {"amount": 0, "detail": "..."},
            "other": {"amount": 0, "detail": "..."},
            "total_monthly": 0
        },
        "third_party_monthly": [
            {"service": "...", "amount": 0, "detail": "..."}
        ],
        "buffer_30_percent": 0,
        "total_build_cost": 0,
        "total_monthly_operating": 0
    },
    "timeline": {
        "total_stories": 0,
        "estimated_days": 0,
        "phases": [{"phase": "...", "days": 0, "stories": 0}]
    },
    "risks_to_budget": ["risk 1"],
    "cost_optimization_tips": ["tip 1"]
}

Output valid JSON only.
"""


def run(project_key: str, adr_ticket_key: str = None) -> dict:
    """Estimate project costs.

    Args:
        project_key: Jira project key.
        adr_ticket_key: Optional ADR ticket key.

    Returns:
        dict with cost estimate and created ticket key.
    """
    log.info("=" * 60)
    log.info("CB-007 Cost Estimator Agent — START")
    log.info("Project: %s", project_key)
    log.info("=" * 60)

    # Step 1: Count and categorize stories
    log.info("Step 1: Fetching stories for cost estimation...")
    stories = jira_client.search_issues(
        f'project = "{project_key}" AND issuetype = Task ORDER BY created ASC',
        max_results=200,
    )
    log.info("Found %d stories", len(stories))

    story_summary = {"S": 0, "M": 0, "L": 0, "unknown": 0}
    for s in stories:
        labels = s.get("fields", {}).get("labels", [])
        if "complexity-s" in labels:
            story_summary["S"] += 1
        elif "complexity-l" in labels:
            story_summary["L"] += 1
        elif "complexity-m" in labels:
            story_summary["M"] += 1
        else:
            story_summary["unknown"] += 1
    log.info("Story complexity breakdown: %s", story_summary)

    # Step 2: Fetch ADR
    adr_text = ""
    if adr_ticket_key:
        adr_issue = jira_client.get_issue(adr_ticket_key)
        adr_text = adr_issue["fields"].get("description", "") or ""

    # Step 3: LLM estimation
    log.info("Step 2: Generating cost estimate with LLM...")
    context = (
        f"## Story Count & Complexity\n"
        f"Total stories: {len(stories)}\n"
        f"Small (S): {story_summary['S']}\n"
        f"Medium (M): {story_summary['M']}\n"
        f"Large (L): {story_summary['L']}\n"
        f"Unknown: {story_summary['unknown']}\n\n"
        f"## Architecture Decision Record\n{adr_text[:4000]}\n"
    )

    raw_response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=context,
        temperature=0.3,
        max_tokens=4000,
    )

    # Step 4: Parse and save
    log.info("Step 3: Saving cost estimate to Jira...")
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        estimate = json.loads(cleaned)
    except json.JSONDecodeError:
        estimate = {"raw_response": raw_response}

    ticket = jira_client.create_issue(
        project_key=project_key,
        summary="Cost Estimate",
        description=json.dumps(estimate, indent=2),
        issue_type="Task",
        labels=["cost-estimate", "planning"],
    )
    ticket_key = ticket.get("key", "")

    log.info("=" * 60)
    log.info("CB-007 Cost Estimator — COMPLETE: %s", ticket_key)
    log.info("=" * 60)

    return {"estimate": estimate, "cost_ticket_key": ticket_key}
