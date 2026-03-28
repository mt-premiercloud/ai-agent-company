"""CB-001 Company Orchestrator — ADK Agent for the web UI.

This is the CEO brain. It receives a project idea, challenges the owner,
and produces a Project Blueprint + creates a Jira project with epics and stories.
It then chains through all Consultant Brain agents (CB-002 to CB-007).
"""

import json
import sys
import os

# Add project root to path so shared modules work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# ---- Tools that the agent can call ----

def create_project_blueprint(project_idea: str) -> dict:
    """Analyze a project idea and create a full Project Blueprint in Jira.

    This tool takes a raw project idea, generates a structured blueprint using AI,
    creates a Jira project with epics, and saves the blueprint as a ticket.

    Args:
        project_idea: The raw project idea description from the client/owner.

    Returns:
        dict with blueprint data, Jira project key, and ticket keys.
    """
    from agents.consultant.cb001_orchestrator import run
    result = run(project_idea)
    return {
        "status": "success",
        "project_key": result.get("jira_project_key"),
        "blueprint_ticket": result.get("blueprint_ticket_key"),
        "epics_created": len(result.get("epic_keys", [])),
        "project_name": result.get("blueprint", {}).get("project_name", "Unknown"),
        "project_type": result.get("blueprint", {}).get("project_type", "Unknown"),
        "complexity": result.get("blueprint", {}).get("estimated_complexity", "Unknown"),
        "key_features": result.get("blueprint", {}).get("key_features", []),
        "clarifying_questions": result.get("blueprint", {}).get("clarifying_questions", []),
        "blind_spots": result.get("blueprint", {}).get("blind_spots", []),
        "recommended_phases": result.get("blueprint", {}).get("recommended_phases", []),
    }


def run_market_research(blueprint_ticket_key: str) -> dict:
    """Run deep market research for a project.

    Searches the web for market data, competitors, gaps, and target user insights.
    Saves a Market Research Report to Jira.

    Args:
        blueprint_ticket_key: The Jira ticket key containing the Project Blueprint (e.g., 'QAFW-8').

    Returns:
        dict with research findings and Jira ticket key.
    """
    from agents.consultant.cb002_market_research import run
    result = run(blueprint_ticket_key)
    research = result.get("research", {})
    return {
        "status": "success",
        "research_ticket": result.get("research_ticket_key"),
        "market_overview": research.get("market_overview", ""),
        "competitors_found": len(research.get("competitors", [])),
        "competitors": research.get("competitors", []),
        "market_gaps": research.get("market_gaps", []),
        "key_findings": research.get("key_findings", []),
        "recommendations": research.get("recommendations", []),
    }


def run_tech_research(blueprint_ticket_key: str, market_research_ticket_key: str = None) -> dict:
    """Research and recommend technologies for the project.

    Searches official docs, GitHub repos, and tech resources to recommend
    a technology stack. Saves a Technology Research Report to Jira.

    Args:
        blueprint_ticket_key: Jira ticket key with the Project Blueprint.
        market_research_ticket_key: Optional Jira ticket key with market research.

    Returns:
        dict with tech recommendations and Jira ticket key.
    """
    from agents.consultant.cb003_tech_research import run
    result = run(blueprint_ticket_key, market_research_ticket_key)
    tech = result.get("tech_research", {})
    return {
        "status": "success",
        "tech_research_ticket": result.get("tech_research_ticket_key"),
        "recommended_stack": tech.get("recommended_stack", {}),
        "rejected_alternatives": tech.get("rejected_alternatives", []),
        "technical_risks": tech.get("technical_risks", []),
        "prerequisites": tech.get("prerequisites", []),
    }


def run_architecture_decision(blueprint_ticket_key: str, market_research_key: str = None, tech_research_key: str = None) -> dict:
    """Make final architecture decisions and produce an ADR.

    Weighs all research and produces an Architecture Decision Record with
    stack choices, Mermaid diagram, and prerequisites checklist.

    Args:
        blueprint_ticket_key: Jira ticket with Project Blueprint.
        market_research_key: Optional market research ticket key.
        tech_research_key: Optional tech research ticket key.

    Returns:
        dict with ADR and Jira ticket key.
    """
    from agents.consultant.cb004_architecture import run
    result = run(blueprint_ticket_key, market_research_key, tech_research_key)
    adr = result.get("adr", {})
    return {
        "status": "success",
        "adr_ticket": result.get("adr_ticket_key"),
        "architecture_style": adr.get("architecture_style", ""),
        "stack": adr.get("stack", {}),
        "prerequisites": adr.get("prerequisites_checklist", []),
    }


def run_project_planner(blueprint_ticket_key: str, adr_ticket_key: str = None) -> dict:
    """Break down the project into Jira user stories.

    Decomposes the project into small, actionable stories with acceptance
    criteria, dependencies, and agent labels.

    Args:
        blueprint_ticket_key: Jira ticket with Project Blueprint.
        adr_ticket_key: Optional ADR ticket key.

    Returns:
        dict with story count and plan summary.
    """
    from agents.consultant.cb005_project_planner import run
    result = run(blueprint_ticket_key, adr_ticket_key)
    return {
        "status": "success",
        "plan_summary_ticket": result.get("plan_summary_key"),
        "stories_created": len(result.get("story_keys", [])),
        "story_keys": result.get("story_keys", [])[:10],  # First 10 for display
    }


def run_full_planning_pipeline(project_idea: str) -> dict:
    """Run the FULL Consultant Brain pipeline end-to-end.

    This executes all planning agents in sequence:
    CB-001 (Blueprint) → CB-002 (Market Research) → CB-003 (Tech Research) →
    CB-004 (Architecture) → CB-005 (Project Planner) → CB-006 (Verification) →
    CB-007 (Cost Estimate)

    Args:
        project_idea: The raw project idea from the client/owner.

    Returns:
        dict with all results from the full pipeline.
    """
    from run_pipeline import run_full_pipeline
    # Capture the pipeline results by running it
    from agents.consultant.cb001_orchestrator import run as run_cb001
    cb001 = run_cb001(project_idea)
    bp_key = cb001.get("blueprint_ticket_key")
    proj_key = cb001.get("jira_project_key")

    if not bp_key:
        return {"status": "error", "message": "Failed to create blueprint"}

    from agents.consultant.cb002_market_research import run as run_cb002
    cb002 = run_cb002(bp_key)
    mr_key = cb002.get("research_ticket_key")

    from agents.consultant.cb003_tech_research import run as run_cb003
    cb003 = run_cb003(bp_key, mr_key)
    tr_key = cb003.get("tech_research_ticket_key")

    from agents.consultant.cb004_architecture import run as run_cb004
    cb004 = run_cb004(bp_key, mr_key, tr_key)
    adr_key = cb004.get("adr_ticket_key")

    from agents.consultant.cb005_project_planner import run as run_cb005
    cb005 = run_cb005(bp_key, adr_key)

    from agents.consultant.cb006_tech_verification import run as run_cb006
    cb006 = run_cb006(proj_key, adr_key)

    from agents.consultant.cb007_cost_estimator import run as run_cb007
    cb007 = run_cb007(proj_key, adr_key)

    return {
        "status": "success",
        "jira_project": proj_key,
        "blueprint_ticket": bp_key,
        "market_research_ticket": mr_key,
        "tech_research_ticket": tr_key,
        "adr_ticket": adr_key,
        "stories_created": len(cb005.get("story_keys", [])),
        "verification_ticket": cb006.get("report_ticket_key"),
        "cost_estimate_ticket": cb007.get("cost_ticket_key"),
        "message": f"Full planning complete! Created Jira project {proj_key} with {len(cb005.get('story_keys', []))} stories.",
    }


# ---- ADK Agent Definition ----

root_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="company_orchestrator",
    description="AI Agent Company — Consultant Brain. Receives project ideas, conducts research, designs architecture, and creates a full project plan in Jira.",
    instruction="""You are the Company Orchestrator — the CEO brain of an AI development agency.

You help clients turn project ideas into fully planned, structured Jira projects.

## What You Can Do:
1. **Create a Project Blueprint** — Analyze a project idea, challenge assumptions, identify blind spots, and produce a structured blueprint
2. **Run Market Research** — Deep dive into the market, competitors, and target users
3. **Run Tech Research** — Evaluate and recommend technologies with official docs
4. **Make Architecture Decisions** — Produce an Architecture Decision Record (ADR)
5. **Plan the Project** — Break it down into Jira user stories with dependencies
6. **Run the Full Pipeline** — Execute ALL planning agents end-to-end in one go

## How to Interact:
- When the user gives you a project idea, start by creating a blueprint using `create_project_blueprint`
- Present the blueprint results, clarifying questions, and blind spots to the user
- If they want to continue, run market research, tech research, architecture, and planning
- Or use `run_full_planning_pipeline` to do everything at once

## Important:
- ALWAYS push back on vague ideas — ask clarifying questions
- Present blind spots the client might not have considered
- Show the Jira ticket keys so the client can check progress
- Be a senior consultant, not a yes-man
""",
    tools=[
        create_project_blueprint,
        run_market_research,
        run_tech_research,
        run_architecture_decision,
        run_project_planner,
        run_full_planning_pipeline,
    ],
)
