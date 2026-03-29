"""Paperclip API client — read/write issues, comments, agents."""

import requests
import logging

log = logging.getLogger("paperclip_api")

BASE_URL = "http://127.0.0.1:3100/api"
COMPANY_ID = "a5eb8615-c637-42c2-ab85-64796dc24d7b"

# Agent IDs
AGENTS = {
    "ceo": "3d365d30-cec3-4daa-8a56-05655070807f",
    "deep_analyst": "d0834e93-7600-44d7-9386-ddfac5859a6f",
    "market_research": "e150ff97-066f-4381-a548-47f8dbde8f85",
    "tech_research": "9c31128a-40ab-4b98-aa34-82cf8cbc9e16",
    "architect": "16589337-90f1-485e-b026-ef001868de3a",
    "planner": "a7c6ba2d-e662-443b-aac0-f6db74afe846",
    "builder": "808c6e75-c0d3-4004-88f9-ddd8bb4f8b8b",
    "qa": "50c7b20f-7abb-48ed-ad50-1b37e168842f",
    "security": "9997b80f-a402-4cc3-9749-84c4d2120cb9",
}

# Pipeline order — each step creates a child issue for the next agent
PLANNING_PIPELINE = [
    ("ceo", "ceo", "Create Project Blueprint"),
    ("deep_analyst", "researcher", "Deep Problem Analysis"),
    ("market_research", "researcher", "Market Research"),
    ("tech_research", "researcher", "Technology Research"),
    ("architect", "cto", "Architecture Decision"),
    ("planner", "pm", "Project Planning & Story Decomposition"),
]

BUILD_PIPELINE = [
    ("builder", "engineer", "Build Feature"),
    ("qa", "qa", "QA Testing"),
    ("security", "devops", "Security Audit"),
]


def create_project(name: str, description: str = "") -> dict:
    """Create a Paperclip project to group issues."""
    data = {"name": name, "description": description}
    resp = requests.post(f"{BASE_URL}/companies/{COMPANY_ID}/projects", json=data)
    resp.raise_for_status()
    project = resp.json()
    log.info("Project created: %s — %s", project.get("id", "?")[:8], name[:50])
    return project


def create_issue(title: str, description: str, agent_key: str = None, parent_id: str = None, project_id: str = None) -> dict:
    """Create an issue in Paperclip."""
    data = {
        "title": title,
        "description": description,
        "status": "backlog",
    }
    # NOTE: Don't assign agents via assigneeAgentId — it triggers Paperclip's
    # auto-heartbeat which conflicts with our bridge orchestration.
    # Instead, track agent in labels/description for dashboard visibility.
    if agent_key:
        data["description"] = f"[Agent: {agent_key}]\n\n{description}"
    if parent_id:
        data["parentId"] = parent_id
    if project_id:
        data["projectId"] = project_id

    resp = requests.post(f"{BASE_URL}/companies/{COMPANY_ID}/issues", json=data)
    resp.raise_for_status()
    issue = resp.json()
    log.info("Issue created: #%s %s", issue.get("issueNumber"), title[:50])
    return issue


def get_issue(issue_id: str) -> dict:
    """Get issue details."""
    resp = requests.get(f"{BASE_URL}/issues/{issue_id}")
    resp.raise_for_status()
    return resp.json()


def update_issue(issue_id: str, **fields) -> dict:
    """Update issue fields (status, assigneeAgentId, etc.)."""
    resp = requests.patch(f"{BASE_URL}/issues/{issue_id}", json=fields)
    resp.raise_for_status()
    result = resp.json()
    log.debug("Issue %s updated: %s", issue_id[:8], list(fields.keys()))
    return result


def add_comment(issue_id: str, body: str) -> dict:
    """Add a comment to an issue (agent's work log)."""
    resp = requests.post(f"{BASE_URL}/issues/{issue_id}/comments", json={"body": body})
    resp.raise_for_status()
    log.debug("Comment added to %s (%d chars)", issue_id[:8], len(body))
    return resp.json()


def list_issues(status: str = None) -> list:
    """List all issues, optionally filtered by status."""
    resp = requests.get(f"{BASE_URL}/companies/{COMPANY_ID}/issues")
    resp.raise_for_status()
    issues = resp.json()
    if status:
        issues = [i for i in issues if i.get("status") == status]
    return issues


def get_child_issues(parent_id: str) -> list:
    """Get child issues of a parent."""
    all_issues = list_issues()
    return [i for i in all_issues if i.get("parentId") == parent_id]
