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

    # Create a Paperclip project to group all issues
    from bridge.paperclip_api import create_project
    project_name = project_idea[:60].strip().rstrip('.')
    paperclip_project = create_project(project_name, project_idea[:500])
    project_id = paperclip_project["id"]
    log.info("Paperclip project created: %s", project_id[:8])

    # Create the parent project issue
    parent = create_issue(
        title=f"Project: {project_idea[:80]}",
        description=project_idea,
        agent_key="ceo",
        project_id=project_id,
    )
    parent_id = parent["id"]
    update_issue(parent_id, status="todo")
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
            project_id=project_id,
        )
        child_id = child["id"]
        update_issue(child_id, status="todo")
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


def run_build_pipeline(story_issue_id: str, project_name: str = None, accumulated_context: str = "") -> dict:
    """Run build + QA + security for a single story using REAL execution.

    1. Builder: generates actual code files, writes to disk, runs tests, commits
    2. QA: runs unit tests, scans for bugs, AI code review
    3. Security: OWASP pattern scan, dependency audit, STRIDE threat model

    All results written to Paperclip as comments.
    """
    from bridge.builder_agent import build_task
    from bridge.qa_agent import run_qa
    from bridge.security_agent import run_security_audit

    issue = get_issue(story_issue_id)
    title = issue.get("title", "Unknown")
    description = issue.get("description", "")

    log.info("=" * 60)
    log.info("BUILD PIPELINE: %s", title)
    log.info("=" * 60)

    if not project_name:
        project_name = title.lower().replace(" ", "-")[:30]

    results = {}

    # --- STEP 1: Builder Agent (actually writes code) ---
    log.info(">>> BUILD STEP 1/3: Builder Agent — Writing Code")
    update_issue(story_issue_id, status="todo")
    add_comment(story_issue_id, "**Builder Agent** starting — generating and writing actual code files...")

    try:
        build_result = build_task(
            task_title=title,
            task_description=description,
            project_name=project_name,
            context=accumulated_context,
        )
        project_dir = build_result["project_dir"]
        files_list = "\n".join(f"  - {f}" for f in build_result["files_created"])
        comment = (
            f"**Builder Agent complete:**\n\n"
            f"Files created ({len(build_result['files_created'])}):\n{files_list}\n\n"
            f"Tests: {'PASSED' if build_result['tests_passed'] else 'FAILED'}\n"
            f"Commit: {build_result['commit_hash']}\n\n"
            f"Summary: {build_result['summary']}"
        )
        add_comment(story_issue_id, comment)
        results["builder"] = build_result
        log.info("Builder done: %d files, tests=%s", len(build_result["files_created"]), build_result["tests_passed"])

    except Exception as e:
        add_comment(story_issue_id, f"**Builder FAILED:** {e}")
        results["builder"] = {"error": str(e)}
        log.error("Builder failed: %s", e)
        update_issue(story_issue_id, status="backlog")
        return results

    # --- STEP 2: QA Agent (actually runs tests and scans) ---
    log.info(">>> BUILD STEP 2/3: QA Agent — Testing")
    add_comment(story_issue_id, "**QA Agent** starting — running tests and scanning for bugs...")

    try:
        qa_result = run_qa(
            project_dir=project_dir,
            app_description=f"{title}: {description[:500]}",
        )
        bugs_list = "\n".join(
            f"  - [{b.get('severity','?')}] {b.get('type','?')}: {b.get('description','?')[:80]}"
            for b in qa_result.get("bugs", [])
        )
        comment = (
            f"**QA Agent complete:**\n\n"
            f"Unit tests: {'PASSED' if qa_result.get('unit_tests_passed') else 'FAILED'}\n"
            f"Bugs found: {qa_result.get('total_bugs', 0)}\n"
            f"{bugs_list if bugs_list else '  No bugs found!'}"
        )
        add_comment(story_issue_id, comment)
        results["qa"] = qa_result
        log.info("QA done: %d bugs", qa_result.get("total_bugs", 0))

    except Exception as e:
        add_comment(story_issue_id, f"**QA FAILED:** {e}")
        results["qa"] = {"error": str(e)}
        log.error("QA failed: %s", e)

    # --- STEP 3: Security Agent (actually scans code) ---
    log.info(">>> BUILD STEP 3/3: Security Agent — Auditing")
    add_comment(story_issue_id, "**Security Agent** starting — OWASP scan + STRIDE threat model...")

    try:
        sec_result = run_security_audit(
            project_dir=project_dir,
            app_description=f"{title}: {description[:500]}",
        )
        vuln_list = "\n".join(
            f"  - [{v.get('severity','?')}] {v.get('type','?')}: {v.get('file','?')}:{v.get('line','')} — {v.get('evidence','')[:60]}"
            for v in sec_result.get("vulnerabilities", [])[:10]
        )
        recs = "\n".join(f"  - {r}" for r in sec_result.get("recommendations", [])[:5])
        comment = (
            f"**Security Agent complete:**\n\n"
            f"Vulnerabilities: {sec_result.get('summary', {}).get('total_vulnerabilities', 0)} "
            f"(High: {sec_result.get('summary', {}).get('high', 0)}, "
            f"Medium: {sec_result.get('summary', {}).get('medium', 0)}, "
            f"Low: {sec_result.get('summary', {}).get('low', 0)})\n\n"
            f"Findings:\n{vuln_list if vuln_list else '  No vulnerabilities found!'}\n\n"
            f"Recommendations:\n{recs if recs else '  None'}\n\n"
            f"Score: {sec_result.get('score', 'N/A')}/100"
        )
        add_comment(story_issue_id, comment)
        results["security"] = sec_result
        log.info("Security done: %d vulns, score=%s",
                 sec_result.get("summary", {}).get("total_vulnerabilities", 0),
                 sec_result.get("score", "?"))

    except Exception as e:
        add_comment(story_issue_id, f"**Security FAILED:** {e}")
        results["security"] = {"error": str(e)}
        log.error("Security failed: %s", e)

    # Mark done
    update_issue(story_issue_id, status="done")

    log.info("=" * 60)
    log.info("BUILD PIPELINE COMPLETE for: %s", title)
    log.info("=" * 60)

    return results


def _extract_build_tasks(planner_output: str, project_idea: str) -> list:
    """Use Gemini to extract concrete build tasks from the planner's output."""
    from openai import OpenAI
    token = get_vertex_token()
    client = OpenAI(
        base_url="https://aiplatform.googleapis.com/v1beta1/projects/pcagentspace/locations/global/endpoints/openapi",
        api_key=token,
    )
    resp = client.chat.completions.create(
        model="google/gemini-3.1-pro-preview",
        messages=[
            {"role": "system", "content": "Extract the top 3-5 most important build tasks from this project plan. Output ONLY a JSON array of task title strings. No markdown, no explanation."},
            {"role": "user", "content": f"Project: {project_idea[:500]}\n\nPlanner output:\n{planner_output[:4000]}"},
        ],
        max_tokens=500,
        temperature=0.1,
    )
    try:
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        tasks = json.loads(text)
        if isinstance(tasks, list):
            return [t if isinstance(t, str) else t.get("title", str(t)) for t in tasks]
    except:
        pass
    # Fallback: use the project idea itself as the single build task
    return [f"Build the complete solution: {project_idea[:80]}"]


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

        # Extract actual build tasks from planner output using Gemini
        build_tasks = _extract_build_tasks(planner_output, project_idea)
        log.info("Extracted %d build tasks from planner", len(build_tasks))

        for task_title in build_tasks[:5]:  # Max 5 tasks per project
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
