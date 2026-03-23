"""Local Pipeline Runner — replaces n8n for local testing.

Runs the Consultant Brain agents (Layer 1) in sequence,
passing Jira ticket keys between agents just like n8n would.

Usage:
    python run_pipeline.py "Build a landing page for a Quebec accounting firm"
    python run_pipeline.py --step cb001 "Your project idea here"
    python run_pipeline.py --step cb002 --ticket PROJ-1
"""

import sys
import argparse
import json
from shared.config import get_logger

log = get_logger("Pipeline")


def run_full_pipeline(project_idea: str):
    """Run all Consultant Brain agents in sequence."""
    log.info("=" * 70)
    log.info("PIPELINE START — Full Consultant Brain (Layer 1)")
    log.info("Project idea: %s", project_idea)
    log.info("=" * 70)

    # --- CB-001: Company Orchestrator ---
    log.info("\n>>> STAGE 1/8: CB-001 Company Orchestrator")
    from agents.consultant.cb001_orchestrator import run as run_cb001
    cb001_result = run_cb001(project_idea)
    blueprint_key = cb001_result.get("blueprint_ticket_key", "")
    project_key = cb001_result.get("jira_project_key", "")
    log.info("CB-001 DONE — Blueprint: %s | Project: %s", blueprint_key, project_key)
    _save_state("cb001", cb001_result)

    if not blueprint_key:
        log.error("No blueprint ticket created. Stopping pipeline.")
        return

    # --- CB-002: Market Research ---
    log.info("\n>>> STAGE 2/8: CB-002 Market Research")
    from agents.consultant.cb002_market_research import run as run_cb002
    cb002_result = run_cb002(blueprint_key)
    market_key = cb002_result.get("research_ticket_key", "")
    log.info("CB-002 DONE — Market Research: %s", market_key)
    _save_state("cb002", cb002_result)

    # --- CB-003: Technology Research ---
    log.info("\n>>> STAGE 3/8: CB-003 Technology Research")
    from agents.consultant.cb003_tech_research import run as run_cb003
    cb003_result = run_cb003(blueprint_key, market_key)
    tech_key = cb003_result.get("tech_research_ticket_key", "")
    log.info("CB-003 DONE — Tech Research: %s", tech_key)
    _save_state("cb003", cb003_result)

    # --- CB-004: Architecture Decision ---
    log.info("\n>>> STAGE 4/8: CB-004 Architecture Decision")
    from agents.consultant.cb004_architecture import run as run_cb004
    cb004_result = run_cb004(blueprint_key, market_key, tech_key)
    adr_key = cb004_result.get("adr_ticket_key", "")
    log.info("CB-004 DONE — ADR: %s", adr_key)
    _save_state("cb004", cb004_result)

    # --- CB-005: Project Planner ---
    log.info("\n>>> STAGE 5/8: CB-005 Project Planner")
    from agents.consultant.cb005_project_planner import run as run_cb005
    cb005_result = run_cb005(blueprint_key, adr_key)
    plan_key = cb005_result.get("plan_summary_key", "")
    story_keys = cb005_result.get("story_keys", [])
    log.info("CB-005 DONE — Plan: %s | Stories: %d", plan_key, len(story_keys))
    _save_state("cb005", cb005_result)

    # --- CB-006: Technical Verification ---
    log.info("\n>>> STAGE 6/8: CB-006 Technical Verification")
    from agents.consultant.cb006_tech_verification import run as run_cb006
    cb006_result = run_cb006(project_key, adr_key)
    report_key = cb006_result.get("report_ticket_key", "")
    log.info("CB-006 DONE — Verification: %s", report_key)
    _save_state("cb006", cb006_result)

    # --- CB-007: Cost Estimator ---
    log.info("\n>>> STAGE 7/8: CB-007 Cost Estimator")
    from agents.consultant.cb007_cost_estimator import run as run_cb007
    cb007_result = run_cb007(project_key, adr_key)
    cost_key = cb007_result.get("cost_ticket_key", "")
    log.info("CB-007 DONE — Cost Estimate: %s", cost_key)
    _save_state("cb007", cb007_result)

    log.info("\n>>> STAGE 8/8: CB-008 Unstuck Agent — SKIPPED (no failures to diagnose)")

    # --- Summary ---
    log.info("\n" + "=" * 70)
    log.info("PIPELINE COMPLETE — Consultant Brain (Layer 1)")
    log.info("=" * 70)
    log.info("Jira Project:      %s", project_key)
    log.info("Blueprint:         %s", blueprint_key)
    log.info("Market Research:   %s", market_key)
    log.info("Tech Research:     %s", tech_key)
    log.info("ADR:               %s", adr_key)
    log.info("Plan Summary:      %s", plan_key)
    log.info("Stories Created:   %d", len(story_keys))
    log.info("Verification:      %s", report_key)
    log.info("Cost Estimate:     %s", cost_key)
    log.info("=" * 70)


def run_single_agent(agent_id: str, ticket_key: str = None, project_idea: str = None):
    """Run a single agent for testing."""
    log.info("Running single agent: %s", agent_id)

    if agent_id == "cb001":
        from agents.consultant.cb001_orchestrator import run as agent_run
        result = agent_run(project_idea or "Test project")
    elif agent_id == "cb002":
        from agents.consultant.cb002_market_research import run as agent_run
        result = agent_run(ticket_key)
    elif agent_id == "cb003":
        from agents.consultant.cb003_tech_research import run as agent_run
        result = agent_run(ticket_key)
    elif agent_id == "cb004":
        from agents.consultant.cb004_architecture import run as agent_run
        result = agent_run(ticket_key)
    elif agent_id == "cb005":
        from agents.consultant.cb005_project_planner import run as agent_run
        result = agent_run(ticket_key)
    elif agent_id == "cb006":
        from agents.consultant.cb006_tech_verification import run as agent_run
        result = agent_run(ticket_key)
    elif agent_id == "cb007":
        from agents.consultant.cb007_cost_estimator import run as agent_run
        result = agent_run(ticket_key)
    elif agent_id == "cb008":
        from agents.consultant.cb008_unstuck import run as agent_run
        result = agent_run(ticket_key)
    else:
        log.error("Unknown agent: %s", agent_id)
        return

    print(json.dumps(result, indent=2, default=str))


def _save_state(stage: str, result: dict):
    """Save pipeline state to file for debugging / resume."""
    import os
    state_dir = os.path.join(os.path.dirname(__file__), ".pipeline_state")
    os.makedirs(state_dir, exist_ok=True)
    path = os.path.join(state_dir, f"{stage}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    log.debug("State saved: %s", path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI Agent Company Pipeline")
    parser.add_argument("idea", nargs="?", default=None, help="Project idea (for full pipeline or cb001)")
    parser.add_argument("--step", type=str, help="Run single agent: cb001-cb008")
    parser.add_argument("--ticket", type=str, help="Jira ticket key (for single agent runs)")
    args = parser.parse_args()

    if args.step:
        run_single_agent(args.step, ticket_key=args.ticket, project_idea=args.idea)
    elif args.idea:
        run_full_pipeline(args.idea)
    else:
        print("Usage:")
        print('  python run_pipeline.py "Your project idea here"')
        print('  python run_pipeline.py --step cb001 "Your project idea"')
        print('  python run_pipeline.py --step cb002 --ticket PROJ-1')
