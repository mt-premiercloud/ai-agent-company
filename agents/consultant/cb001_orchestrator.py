"""CB-001 — Company Orchestrator (CEO Brain)

Receives project requests from the owner. Classifies project type.
Generates clarifying questions. Creates the Project Blueprint.
Creates Jira project with epics. Challenges the owner like a senior consultant.
"""

import json
from shared.config import get_logger
from shared.llm_client import call_llm
from shared import jira_client

log = get_logger("CB-001.Orchestrator")

SYSTEM_PROMPT = """You are the Company Orchestrator — the CEO brain of an AI development agency.

Your job is to receive a project idea from a client/owner and produce a structured Project Blueprint.

## Your Process:
1. ANALYZE the project idea
2. CLASSIFY the project type (web app, mobile app, API, platform, e-commerce, SaaS, etc.)
3. CHALLENGE the owner — identify blind spots, ask hard questions like:
   - "Who is the target user?"
   - "What problem does this solve?"
   - "What's the revenue model?"
   - "Who are the competitors?"
   - "What's the budget and timeline?"
4. PRODUCE a structured Project Blueprint

## Output Format (JSON):
{
    "project_name": "...",
    "project_type": "web_app|mobile_app|api|platform|saas|e_commerce|other",
    "one_liner": "One sentence describing the product",
    "target_users": "Who will use this",
    "problem_solved": "What problem it solves",
    "revenue_model": "How it makes money (if applicable)",
    "key_features": ["feature 1", "feature 2", ...],
    "technical_requirements": ["requirement 1", ...],
    "integrations_needed": ["integration 1", ...],
    "estimated_complexity": "simple|medium|complex|enterprise",
    "clarifying_questions": ["question 1", ...],
    "blind_spots": ["thing the owner might not have considered 1", ...],
    "recommended_phases": [
        {"phase": "Phase 1 — MVP", "description": "...", "features": [...]},
        {"phase": "Phase 2 — Growth", "description": "...", "features": [...]}
    ],
    "risks": ["risk 1", ...],
    "success_metrics": ["metric 1", ...]
}

ALWAYS push back on vague ideas. Be a senior consultant, not a yes-man.
ALWAYS output valid JSON only — no markdown, no extra text.
"""


def run(project_idea: str, owner_answers: str = None) -> dict:
    """Run the Company Orchestrator agent.

    Args:
        project_idea: The raw project idea from the owner.
        owner_answers: Optional answers to clarifying questions from a previous round.

    Returns:
        dict with: blueprint (parsed JSON), jira_project_key, epic_keys
    """
    log.info("=" * 60)
    log.info("CB-001 Company Orchestrator — START")
    log.info("=" * 60)
    log.debug("Project idea: %s", project_idea)

    # Step 1: Generate the Project Blueprint via LLM
    user_message = f"## Project Idea\n{project_idea}"
    if owner_answers:
        user_message += f"\n\n## Owner's Answers to Previous Questions\n{owner_answers}"

    log.info("Step 1: Calling LLM to generate Project Blueprint...")
    raw_response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        temperature=0.7,
        max_tokens=4096,
    )

    # Step 2: Parse the blueprint
    log.info("Step 2: Parsing blueprint JSON...")
    try:
        # Strip markdown code fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        blueprint = json.loads(cleaned)
        log.info("Blueprint parsed successfully: project_name=%s type=%s complexity=%s",
                 blueprint.get("project_name"), blueprint.get("project_type"),
                 blueprint.get("estimated_complexity"))
    except json.JSONDecodeError as e:
        log.error("Failed to parse blueprint JSON: %s", e)
        log.debug("Raw response: %s", raw_response)
        blueprint = {"raw_response": raw_response, "parse_error": str(e)}

    # Step 3: Create Jira project and epics
    log.info("Step 3: Creating Jira project and epics...")
    project_key = _create_project_with_retry(blueprint.get("project_name", "PROJECT"))
    if not project_key:
        log.error("Could not create Jira project. Returning blueprint only.")
        return {"blueprint": blueprint, "jira_project_key": None, "epic_keys": [], "blueprint_ticket_key": None}
    jira_result = _create_jira_structure(project_key, blueprint)

    log.info("=" * 60)
    log.info("CB-001 Company Orchestrator — COMPLETE")
    log.info("Jira project: %s | Epics created: %d", project_key, len(jira_result.get("epic_keys", [])))
    log.info("=" * 60)

    return {
        "blueprint": blueprint,
        "jira_project_key": project_key,
        "epic_keys": jira_result.get("epic_keys", []),
        "blueprint_ticket_key": jira_result.get("blueprint_ticket_key"),
    }


def _create_project_with_retry(name: str) -> str:
    """Create a Jira project, trying different keys if needed."""
    import re
    import random

    words = re.findall(r"[A-Za-z]+", name)
    if len(words) >= 2:
        base_key = "".join(w[0] for w in words[:4]).upper()
    else:
        base_key = re.sub(r"[^A-Z]", "", name.upper())[:4]
    if len(base_key) < 2:
        base_key = "PROJ"
    base_key = base_key[:4]

    # Try base key, then with number suffix
    keys_to_try = [base_key] + [f"{base_key}{i}" for i in range(2, 6)]
    # Also add a random suffix as last resort
    keys_to_try.append(f"{base_key[:3]}{random.randint(10,99)}")

    for i, key in enumerate(keys_to_try):
        try:
            # Vary the name too (Jira rejects duplicate names even with different keys)
            proj_name = name[:50] if i == 0 else f"{name[:45]} ({key})"
            log.info("Trying to create project: key=%s name=%s", key, proj_name)
            jira_client.create_project(key=key, name=proj_name)
            log.info("Project created successfully: %s", key)
            return key
        except Exception as e:
            log.warning("Key %s failed: %s", key, str(e)[:100])
            continue

    log.error("All project key attempts failed")
    return None


def _create_jira_structure(project_key: str, blueprint: dict) -> dict:
    """Create Jira project with standard epics."""
    result = {"epic_keys": []}

    # Project already created by _create_project_with_retry
    # Standard epics for every project
    epics = [
        ("Planning & Research", "Market research, technology research, architecture decisions"),
        ("Design", "UI/UX design, design system, wireframes"),
        ("Backend Development", "API endpoints, business logic, database"),
        ("Frontend Development", "UI components, pages, state management"),
        ("Integration", "Third-party services, external APIs"),
        ("Testing & QA", "Unit tests, integration tests, code review"),
        ("Deployment & Ops", "CI/CD, infrastructure, monitoring"),
    ]

    for epic_name, epic_desc in epics:
        try:
            epic = jira_client.create_epic(project_key, epic_name, epic_desc)
            epic_key = epic.get("key", "")
            result["epic_keys"].append(epic_key)
            log.info("Epic created: %s — %s", epic_key, epic_name)
        except Exception as e:
            log.error("Failed to create epic '%s': %s", epic_name, e)

    # Create the Project Blueprint ticket
    try:
        blueprint_desc = json.dumps(blueprint, indent=2)
        ticket = jira_client.create_issue(
            project_key=project_key,
            summary="Project Blueprint",
            description=blueprint_desc,
            issue_type="Task",
            labels=["blueprint", "planning"],
        )
        result["blueprint_ticket_key"] = ticket.get("key", "")
        log.info("Blueprint ticket created: %s", result["blueprint_ticket_key"])
    except Exception as e:
        log.error("Failed to create blueprint ticket: %s", e)

    return result
