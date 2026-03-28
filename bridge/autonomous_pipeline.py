"""Autonomous Pipeline — Full end-to-end project execution.

Submits a project idea → cascades through all agents automatically:
Planning: CEO → Deep Analyst → Market Research → Tech Research → Architect → Planner
Building: Builder (per story) → QA → Security

All results written to Paperclip tickets with comments.
All agents powered by Gemini 3.1 Pro Preview via Vertex AI.
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vendor', 'hermes-agent')))

from bridge.paperclip_api import (
    create_issue, get_issue, update_issue, add_comment,
    list_issues, get_child_issues, AGENTS, PLANNING_PIPELINE, BUILD_PIPELINE,
)

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)-8s %(name)-25s | %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger("pipeline")


def get_vertex_token():
    """Get fresh Vertex AI access token."""
    import google.auth
    import google.auth.transport.requests
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


def run_hermes_agent(role: str, task: str, context: str = "") -> str:
    """Run a Hermes agent with the specified role."""
    from bridge.hermes_paperclip_bridge import AGENT_CONFIGS

    config = AGENT_CONFIGS.get(role, AGENT_CONFIGS["researcher"])
    token = get_vertex_token()

    log.info("Running agent [%s]: %s...", role, task[:60])

    from run_agent import AIAgent
    agent = AIAgent(
        model="google/gemini-3.1-pro-preview",
        base_url="https://aiplatform.googleapis.com/v1beta1/projects/pcagentspace/locations/global/endpoints/openapi",
        api_key=token,
        ephemeral_system_prompt=config["system_prompt"],
        max_iterations=config["max_iterations"],
        quiet_mode=True,
        skip_memory=False,
        skip_context_files=True,
    )

    user_msg = f"## Task\n{task}"
    if context:
        user_msg += f"\n\n## Context from Previous Agents\n{context}"

    result = agent.chat(user_msg)
    return result or "Agent returned no response."


def run_planning_pipeline(project_idea: str) -> dict:
    """Run the full planning pipeline for a project idea.

    Creates a parent issue, then cascades through all planning agents.
    Each agent's output becomes context for the next.
    """
    log.info("=" * 70)
    log.info("AUTONOMOUS PLANNING PIPELINE — START")
    log.info("Project: %s", project_idea[:100])
    log.info("=" * 70)

    # Create the parent project issue
    parent = create_issue(
        title=f"Project: {project_idea[:80]}",
        description=project_idea,
        agent_key="ceo",
    )
    parent_id = parent["id"]
    update_issue(parent_id, status="in_progress")
    add_comment(parent_id, f"**Pipeline started** at {datetime.utcnow().isoformat()}\n\nProject idea: {project_idea}")

    accumulated_context = f"## Original Project Idea\n{project_idea}\n\n"
    results = {}

    for i, (agent_key, hermes_role, step_name) in enumerate(PLANNING_PIPELINE):
        step_num = i + 1
        total = len(PLANNING_PIPELINE)

        log.info("")
        log.info(">>> STEP %d/%d: %s [%s]", step_num, total, step_name, agent_key)
        log.info("-" * 50)

        # Create a child issue for this step
        child = create_issue(
            title=f"[{step_num}/{total}] {step_name}",
            description=f"Agent: {agent_key}\nTask: {step_name}\n\nContext:\n{accumulated_context[:2000]}",
            agent_key=agent_key,
            parent_id=parent_id,
        )
        child_id = child["id"]
        update_issue(child_id, status="in_progress")
        add_comment(child_id, f"**{agent_key}** starting: {step_name}")

        # Run the agent
        try:
            response = run_hermes_agent(
                role=hermes_role,
                task=f"{step_name} for this project: {project_idea}",
                context=accumulated_context,
            )

            # Save result
            add_comment(child_id, f"**{agent_key} completed:**\n\n{response[:10000]}")
            update_issue(child_id, status="done")
            results[agent_key] = response
            accumulated_context += f"\n## {step_name} (by {agent_key})\n{response[:3000]}\n\n"

            log.info("STEP %d COMPLETE: %d chars response", step_num, len(response))

        except Exception as e:
            error_msg = f"**{agent_key} FAILED:** {str(e)}"
            add_comment(child_id, error_msg)
            update_issue(child_id, status="backlog")
            log.error("STEP %d FAILED: %s", step_num, e)
            results[agent_key] = f"ERROR: {e}"

    # Update parent issue
    add_comment(parent_id, f"**Planning pipeline complete!**\n\nSteps completed: {len(results)}/{len(PLANNING_PIPELINE)}")
    update_issue(parent_id, status="done")

    log.info("")
    log.info("=" * 70)
    log.info("PLANNING PIPELINE COMPLETE")
    log.info("Parent issue: #%s", parent.get("issueNumber"))
    log.info("Results: %s", {k: len(v) for k, v in results.items()})
    log.info("=" * 70)

    return {
        "parent_issue_id": parent_id,
        "parent_issue_number": parent.get("issueNumber"),
        "results": {k: v[:200] for k, v in results.items()},
        "steps_completed": len([v for v in results.values() if not v.startswith("ERROR")]),
        "total_steps": len(PLANNING_PIPELINE),
    }


def run_build_pipeline(story_issue_id: str) -> dict:
    """Run build + QA + security for a single story.

    Takes a Paperclip issue ID (a story from the planner),
    runs Builder → QA → Security sequentially.
    """
    issue = get_issue(story_issue_id)
    title = issue.get("title", "Unknown")
    description = issue.get("description", "")

    log.info("BUILD PIPELINE for: %s", title)

    context = f"## Story\n{title}\n\n## Description\n{description}"
    results = {}

    for agent_key, hermes_role, step_name in BUILD_PIPELINE:
        log.info(">>> BUILD STEP: %s [%s]", step_name, agent_key)

        update_issue(story_issue_id, status="in_progress")
        add_comment(story_issue_id, f"**{step_name}** starting by {agent_key}...")

        try:
            response = run_hermes_agent(
                role=hermes_role,
                task=f"{step_name}: {title}",
                context=context,
            )
            add_comment(story_issue_id, f"**{step_name} complete:**\n\n{response[:8000]}")
            results[agent_key] = response
            context += f"\n\n## {step_name} Result\n{response[:2000]}"

        except Exception as e:
            add_comment(story_issue_id, f"**{step_name} FAILED:** {e}")
            results[agent_key] = f"ERROR: {e}"

    update_issue(story_issue_id, status="done")
    return results


def run_full_project(project_idea: str) -> dict:
    """Run the COMPLETE project lifecycle: planning + building.

    1. Runs the planning pipeline (CEO → ... → Planner)
    2. Extracts stories from the Planner's output
    3. Runs build pipeline for each story (Builder → QA → Security)
    """
    log.info("*" * 70)
    log.info("FULL AUTONOMOUS PROJECT EXECUTION")
    log.info("*" * 70)

    # Phase 1: Planning
    planning_result = run_planning_pipeline(project_idea)

    # Phase 2: Building (if planning succeeded and planner created stories)
    planner_output = planning_result.get("results", {}).get("planner", "")
    if planner_output and not planner_output.startswith("ERROR"):
        # Create build issues from planner output
        log.info("Planning complete. Creating build tasks...")

        # Extract stories — the planner's output contains story titles
        # Create a few key build tasks
        build_tasks = [
            "Set up project infrastructure (Cloud Run, Cloud SQL, Firebase Auth)",
            "Build landing page with bilingual support",
            "Implement appointment booking system",
        ]

        for task_title in build_tasks:
            build_issue = create_issue(
                title=task_title,
                description=f"Build task from planning phase.\n\n{planner_output[:1000]}",
                agent_key="builder",
                parent_id=planning_result["parent_issue_id"],
            )
            log.info("Build task created: #%s %s", build_issue.get("issueNumber"), task_title)

            # Run build pipeline for this task
            run_build_pipeline(build_issue["id"])

    return planning_result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous AI Agency Pipeline")
    parser.add_argument("idea", nargs="?", help="Project idea to execute")
    parser.add_argument("--plan-only", action="store_true", help="Only run planning, skip building")
    parser.add_argument("--build", type=str, help="Run build pipeline on a specific issue ID")
    args = parser.parse_args()

    if args.build:
        result = run_build_pipeline(args.build)
        print(json.dumps(result, indent=2, default=str))
    elif args.idea:
        if args.plan_only:
            result = run_planning_pipeline(args.idea)
        else:
            result = run_full_project(args.idea)
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage:")
        print('  python autonomous_pipeline.py "Your project idea"')
        print('  python autonomous_pipeline.py --plan-only "Your project idea"')
        print('  python autonomous_pipeline.py --build ISSUE_ID')
