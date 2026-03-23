"""CB-005 — Project Planner Agent

Senior PM that breaks down the project into Jira user stories.
Each story: small enough for one agent session, has Given/When/Then criteria,
dependency links, agent labels, complexity estimate.
"""

import json
from shared.config import get_logger
from shared.llm_client import call_llm
from shared import jira_client

log = get_logger("CB-005.ProjectPlanner")

SYSTEM_PROMPT = """You are a senior project manager decomposing a software project into user stories for AI builder agents.

You receive the Project Blueprint, Architecture Decision Record, and research. Break the ENTIRE project into Jira user stories.

## Rules:
- Each story must be completable by a single AI agent in one session (under 1 hour)
- If a story feels too big, SPLIT IT
- Every story MUST have acceptance criteria in Given/When/Then format
- Every story MUST have a label for agent assignment
- Link dependencies explicitly (story B depends on story A)

## Labels (one per story):
- design — UI/UX design tasks → BLD-001
- frontend — Frontend code → BLD-002
- backend-api — API endpoints → BLD-003
- backend-logic — Business logic → BLD-004
- database — Schema/migrations → BLD-005
- integration — Third-party APIs → BLD-006
- security — Auth/security → BLD-007
- infrastructure — CI/CD/deploy → BLD-008
- platform — Platform-specific → BLD-009
- documentation — Docs → BLD-010

## Output Format (JSON):
{
    "epics": [
        {
            "name": "Epic Name",
            "stories": [
                {
                    "title": "Short, actionable title",
                    "description": "What to build and why",
                    "acceptance_criteria": "Given X\\nWhen Y\\nThen Z",
                    "label": "backend-api",
                    "complexity": "S|M|L",
                    "depends_on": ["Story title it depends on"],
                    "technical_notes": "Implementation hints for the builder agent"
                }
            ]
        }
    ],
    "critical_path": ["Story 1 title", "Story 2 title", "..."],
    "total_stories": 0,
    "estimated_sessions": 0
}

Output valid JSON only.
"""


def run(blueprint_ticket_key: str, adr_ticket_key: str = None) -> dict:
    """Run project planning — decompose into stories.

    Args:
        blueprint_ticket_key: Jira ticket with Project Blueprint.
        adr_ticket_key: Jira ticket with Architecture Decision Record.

    Returns:
        dict with created story keys and plan summary.
    """
    log.info("=" * 60)
    log.info("CB-005 Project Planner Agent — START")
    log.info("=" * 60)

    # Step 1: Gather inputs
    log.info("Step 1: Reading blueprint and ADR from Jira...")
    bp_issue = jira_client.get_issue(blueprint_ticket_key)
    blueprint_text = bp_issue["fields"].get("description", "") or ""
    project_key = bp_issue["fields"]["project"]["key"]

    inputs = f"## Project Blueprint\n{blueprint_text}\n\n"
    if adr_ticket_key:
        adr_issue = jira_client.get_issue(adr_ticket_key)
        inputs += f"## Architecture Decision Record\n{adr_issue['fields'].get('description', '')}\n\n"

    # Step 2: Generate stories with LLM
    log.info("Step 2: Generating user stories with LLM...")
    raw_response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=inputs,
        temperature=0.5,
        max_tokens=8192,
    )

    # Step 3: Parse
    log.info("Step 3: Parsing story plan...")
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        plan = json.loads(cleaned)
    except json.JSONDecodeError:
        log.error("Failed to parse plan JSON")
        plan = {"raw_response": raw_response}
        return {"plan": plan, "story_keys": []}

    # Step 4: Create stories in Jira
    log.info("Step 4: Creating %d stories in Jira...", plan.get("total_stories", 0))
    story_keys = []
    story_title_to_key = {}

    for epic_data in plan.get("epics", []):
        epic_name = epic_data.get("name", "Unnamed Epic")
        log.info("  Processing epic: %s (%d stories)", epic_name, len(epic_data.get("stories", [])))

        # Create epic
        try:
            epic = jira_client.create_epic(project_key, epic_name, f"Epic: {epic_name}")
            epic_key = epic.get("key", "")
            log.info("  Epic created: %s", epic_key)
        except Exception as e:
            log.error("  Failed to create epic '%s': %s", epic_name, e)
            epic_key = None

        for story in epic_data.get("stories", []):
            title = story.get("title", "Untitled Story")
            desc = (
                f"{story.get('description', '')}\n\n"
                f"## Acceptance Criteria\n{story.get('acceptance_criteria', 'TBD')}\n\n"
                f"## Technical Notes\n{story.get('technical_notes', 'None')}\n\n"
                f"## Complexity: {story.get('complexity', 'M')}\n"
                f"## Dependencies: {', '.join(story.get('depends_on', []))}"
            )
            labels = [story.get("label", "backend-api"), f"complexity-{story.get('complexity', 'M').lower()}", f"epic-{epic_name.lower().replace(' ', '-')}"]

            try:
                ticket = jira_client.create_issue(
                    project_key=project_key,
                    summary=title,
                    description=desc,
                    issue_type="Task",
                    labels=labels,
                )
                key = ticket.get("key", "")
                story_keys.append(key)
                story_title_to_key[title] = key
                log.info("    Story created: %s — %s [%s]", key, title, story.get("label", ""))
            except Exception as e:
                log.error("    Failed to create story '%s': %s", title, e)

    # Step 5: Link dependencies
    log.info("Step 5: Linking dependencies...")
    for epic_data in plan.get("epics", []):
        for story in epic_data.get("stories", []):
            title = story.get("title", "")
            current_key = story_title_to_key.get(title, "")
            for dep_title in story.get("depends_on", []):
                dep_key = story_title_to_key.get(dep_title, "")
                if current_key and dep_key:
                    try:
                        jira_client.link_issues(dep_key, current_key, "Blocks")
                        log.debug("    Linked: %s blocks %s", dep_key, current_key)
                    except Exception as e:
                        log.warning("    Failed to link %s -> %s: %s", dep_key, current_key, e)

    # Step 6: Create plan summary ticket
    log.info("Step 6: Creating plan summary ticket...")
    summary_ticket = jira_client.create_issue(
        project_key=project_key,
        summary="Project Plan Summary",
        description=json.dumps(plan, indent=2),
        issue_type="Task",
        labels=["planning", "plan-summary"],
    )
    summary_key = summary_ticket.get("key", "")

    jira_client.add_comment(blueprint_ticket_key,
                            f"*CB-005 Project Planning Complete*\nStories created: {len(story_keys)}\nPlan summary: {summary_key}")

    log.info("=" * 60)
    log.info("CB-005 Project Planner — COMPLETE: %d stories created", len(story_keys))
    log.info("=" * 60)

    return {"plan": plan, "story_keys": story_keys, "plan_summary_key": summary_key}
