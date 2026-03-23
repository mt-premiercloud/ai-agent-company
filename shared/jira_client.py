"""Jira API wrapper — all agents use this to read/write tickets."""

from atlassian import Jira
from shared.config import JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, get_logger

log = get_logger("shared.jira_client")


def _get_client() -> Jira:
    """Create a fresh Jira client."""
    log.debug("Connecting to Jira: %s as %s", JIRA_URL, JIRA_EMAIL)
    return Jira(url=JIRA_URL, username=JIRA_EMAIL, password=JIRA_API_TOKEN)


# --------------- Projects ---------------

def create_project(key: str, name: str, lead_account_id: str = None) -> dict:
    """Create a Jira project via REST API v3."""
    client = _get_client()
    log.info("Creating project: key=%s name=%s", key, name)

    # Get lead account ID if not provided
    if not lead_account_id:
        myself = client.myself()
        lead_account_id = myself.get("accountId", "")
        log.debug("Using lead account: %s", lead_account_id)

    data = {
        "key": key,
        "name": name,
        "projectTypeKey": "business",
        "leadAccountId": lead_account_id,
    }
    result = client.post("rest/api/3/project", data=data)
    log.debug("Project created: %s", result)
    return result


def get_project(key: str) -> dict:
    """Get project details."""
    client = _get_client()
    log.debug("Fetching project: %s", key)
    return client.project(key)


# --------------- Issues / Tickets ---------------

def create_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
    labels: list = None,
    parent_key: str = None,
) -> dict:
    """Create a Jira issue (epic, story, task, subtask)."""
    client = _get_client()
    fields = {
        "project": {"key": project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
    }
    if labels:
        fields["labels"] = labels
    if parent_key:
        fields["parent"] = {"key": parent_key}

    log.info("Creating %s in %s: %s", issue_type, project_key, summary)
    log.debug("Fields: %s", {k: v for k, v in fields.items() if k != "description"})
    result = client.issue_create(fields)
    log.debug("Issue created: %s", result)
    return result


def create_epic(project_key: str, summary: str, description: str) -> dict:
    """Create an epic-like task (Jira business projects don't have Epics)."""
    return create_issue(project_key, summary, description, issue_type="Task", labels=["epic"])


def get_issue(issue_key: str) -> dict:
    """Read a Jira issue with all fields."""
    client = _get_client()
    log.debug("Fetching issue: %s", issue_key)
    return client.issue(issue_key)


def update_issue(issue_key: str, fields: dict) -> dict:
    """Update issue fields."""
    client = _get_client()
    log.info("Updating issue %s: %s", issue_key, list(fields.keys()))
    log.debug("Update fields: %s", fields)
    return client.issue_update(issue_key, fields)


def add_comment(issue_key: str, comment: str) -> dict:
    """Add a comment to an issue — this is how agents log their work."""
    client = _get_client()
    log.info("Adding comment to %s (%d chars)", issue_key, len(comment))
    log.debug("Comment preview: %s...", comment[:200])
    return client.issue_add_comment(issue_key, comment)


def transition_issue(issue_key: str, status: str) -> None:
    """Move issue to a new status (e.g., 'In Progress', 'Done')."""
    client = _get_client()
    log.info("Transitioning %s to '%s'", issue_key, status)
    transitions = client.get_issue_transitions(issue_key)
    log.debug("Available transitions: %s", [(t["id"], t["name"]) for t in transitions])
    for t in transitions:
        if t["name"].lower() == status.lower():
            client.set_issue_status(issue_key, t["name"])
            log.info("Transition complete: %s -> %s", issue_key, status)
            return
    log.warning("Transition '%s' not found for %s. Available: %s", status, issue_key, [t["name"] for t in transitions])


def search_issues(jql: str, max_results: int = 50) -> list:
    """Search issues with JQL (uses v3 API)."""
    client = _get_client()
    log.debug("JQL search: %s (max %d)", jql, max_results)
    # Use the new v3 search endpoint (v2 was deprecated)
    data = {"jql": jql, "maxResults": max_results}
    try:
        results = client.post("rest/api/3/search/jql", data=data)
    except Exception:
        # Fallback to v3 search GET
        from urllib.parse import quote
        results = client.get(f"rest/api/3/search?jql={quote(jql)}&maxResults={max_results}")
    total = results.get("total", 0)
    log.debug("Found %d issues", total)
    return results.get("issues", [])


def get_issue_comments(issue_key: str) -> list:
    """Get all comments on an issue."""
    client = _get_client()
    log.debug("Fetching comments for %s", issue_key)
    return client.issue_get_comments(issue_key)


def link_issues(inward_key: str, outward_key: str, link_type: str = "Blocks") -> None:
    """Link two issues (e.g., 'blocks', 'is blocked by')."""
    client = _get_client()
    log.info("Linking: %s %s %s", inward_key, link_type, outward_key)
    client.create_issue_link(
        {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key},
        }
    )
