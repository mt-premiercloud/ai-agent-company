"""CB-006 — Technical Verification Agent

Reviews every user story BEFORE building starts.
Checks feasibility, acceptance criteria, contradictions, dependencies, gaps.
This is the quality gate between planning and building.
"""

import json
from shared.config import get_logger
from shared.llm_client import call_llm
from shared import jira_client

log = get_logger("CB-006.TechVerification")

SYSTEM_PROMPT = """You are a senior technical reviewer verifying user stories before they go to builder agents.

For each story, check:
1. Is this technically feasible with the chosen stack?
2. Do the acceptance criteria make sense and are they testable?
3. Are there contradictions between stories?
4. Are dependencies correct and complete?
5. Are there missing stories (gaps in the plan)?
6. Is the story small enough for one AI agent session?

## Output Format (JSON):
{
    "verified_stories": [
        {
            "story_key": "...",
            "title": "...",
            "status": "approved|needs_revision",
            "issues": ["issue 1", "issue 2"],
            "suggestions": ["suggestion 1"]
        }
    ],
    "missing_stories": [
        {"title": "Suggested story", "reason": "Why it's needed", "label": "backend-api"}
    ],
    "contradictions": [
        {"stories": ["KEY-1", "KEY-2"], "description": "What contradicts"}
    ],
    "overall_assessment": "ready_to_build|needs_revision",
    "critical_issues_count": 0,
    "summary": "Brief assessment"
}

Be thorough but practical. Don't block stories for minor issues.
Output valid JSON only.
"""


def run(project_key: str, adr_ticket_key: str = None) -> dict:
    """Verify all stories in a project.

    Args:
        project_key: Jira project key.
        adr_ticket_key: Optional ADR ticket for tech stack reference.

    Returns:
        dict with verification results and report ticket key.
    """
    log.info("=" * 60)
    log.info("CB-006 Technical Verification Agent — START")
    log.info("Project: %s", project_key)
    log.info("=" * 60)

    # Step 1: Fetch all stories
    log.info("Step 1: Fetching all stories from project %s...", project_key)
    stories = jira_client.search_issues(
        f'project = "{project_key}" AND issuetype = Task ORDER BY created ASC',
        max_results=100,
    )
    log.info("Found %d stories to verify", len(stories))

    # Step 2: Fetch ADR
    adr_text = ""
    if adr_ticket_key:
        adr_issue = jira_client.get_issue(adr_ticket_key)
        adr_text = adr_issue["fields"].get("description", "") or ""

    # Step 3: Build context for LLM
    log.info("Step 2: Building verification context...")
    stories_context = "## Stories to Verify\n\n"
    for s in stories:
        key = s.get("key", "")
        fields = s.get("fields", {})
        stories_context += (
            f"### {key}: {fields.get('summary', '')}\n"
            f"Labels: {fields.get('labels', [])}\n"
            f"Description:\n{fields.get('description', 'No description')}\n\n"
        )

    context = f"## Architecture Decision Record\n{adr_text[:4000]}\n\n{stories_context}"

    # Step 4: LLM verification
    log.info("Step 3: Running LLM verification...")
    raw_response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=context,
        temperature=0.3,
        max_tokens=6000,
    )

    # Step 5: Parse and save
    log.info("Step 4: Parsing verification results...")
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        verification = json.loads(cleaned)
    except json.JSONDecodeError:
        verification = {"raw_response": raw_response}

    # Step 6: Add comments to stories
    log.info("Step 5: Adding verification comments to stories...")
    for v_story in verification.get("verified_stories", []):
        story_key = v_story.get("story_key", "")
        if story_key:
            status = v_story.get("status", "unknown")
            issues = v_story.get("issues", [])
            comment = f"*CB-006 Verification: {status.upper()}*\n"
            if issues:
                comment += "Issues:\n" + "\n".join(f"- {i}" for i in issues)
            else:
                comment += "No issues found."
            try:
                jira_client.add_comment(story_key, comment)
                log.debug("Comment added to %s: %s", story_key, status)
            except Exception as e:
                log.warning("Failed to comment on %s: %s", story_key, e)

    # Create verification report ticket
    report = jira_client.create_issue(
        project_key=project_key,
        summary="Technical Verification Report",
        description=json.dumps(verification, indent=2),
        issue_type="Task",
        labels=["verification", "quality-gate", "planning"],
    )
    report_key = report.get("key", "")

    log.info("=" * 60)
    log.info("CB-006 Verification — COMPLETE: %s | Assessment: %s",
             report_key, verification.get("overall_assessment", "unknown"))
    log.info("=" * 60)

    return {"verification": verification, "report_ticket_key": report_key}
