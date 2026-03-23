"""CB-008 — Unstuck Agent

The firefighter. Called when a builder agent fails 3+ times on the same task.
Reads error history, goes to official docs, finds working examples,
produces a COMPLETELY FRESH approach. Never patches broken code.
"""

import json
from shared.config import get_logger
from shared.llm_client import call_llm
from shared import jira_client
from shared.web_search import search_web, fetch_page

log = get_logger("CB-008.Unstuck")

SYSTEM_PROMPT = """You are the Unstuck Agent — a senior debugging expert called when builder agents fail repeatedly.

You receive a Jira ticket with error history from failed attempts. Your job is to diagnose the root cause and provide a COMPLETELY FRESH approach.

## Rules:
- NEVER try to patch the existing broken code
- Go back to FUNDAMENTALS: what does the official documentation say?
- Find a WORKING open-source example on GitHub
- Provide step-by-step instructions for a fresh approach
- Include actual code snippets from working examples

## Your Process:
1. Read ALL error comments to understand the failure pattern
2. Identify the ROOT CAUSE (not just the symptom)
3. Search official documentation for the correct approach
4. Find a working GitHub example
5. Write a fresh, tested approach

## Output Format (JSON):
{
    "root_cause_analysis": {
        "symptom": "What the error looks like",
        "root_cause": "Why it's actually failing",
        "why_previous_attempts_failed": "Pattern in the failures"
    },
    "fresh_approach": {
        "strategy": "High-level description of the new approach",
        "steps": [
            {"step": 1, "action": "...", "code_snippet": "...", "explanation": "..."}
        ],
        "official_doc_reference": "URL to official docs",
        "working_example": "URL to GitHub repo/example"
    },
    "prevention": "How to avoid this in future",
    "confidence": "high|medium|low"
}

Output valid JSON only.
"""


def run(failed_ticket_key: str) -> dict:
    """Unstuck a failed ticket.

    Args:
        failed_ticket_key: Jira ticket with error history in comments.

    Returns:
        dict with fresh approach and updated ticket.
    """
    log.info("=" * 60)
    log.info("CB-008 Unstuck Agent — START")
    log.info("Failed ticket: %s", failed_ticket_key)
    log.info("=" * 60)

    # Step 1: Read the failed ticket and all error comments
    log.info("Step 1: Reading failed ticket and error history...")
    issue = jira_client.get_issue(failed_ticket_key)
    fields = issue.get("fields", {})
    title = fields.get("summary", "")
    description = fields.get("description", "") or ""
    labels = fields.get("labels", [])
    project_key = fields["project"]["key"]

    comments = jira_client.get_issue_comments(failed_ticket_key)
    error_history = ""
    for c in comments:
        body = c.get("body", "") if isinstance(c, dict) else str(c)
        error_history += f"\n---\n{body}\n"

    log.info("Ticket: %s | Comments: %d | Labels: %s", title, len(comments), labels)
    log.debug("Error history: %d chars", len(error_history))

    # Step 2: Search for solutions
    log.info("Step 2: Searching for solutions...")
    # Extract key terms from the error
    search_queries = [
        f"{title} official documentation",
        f"{title} working example github",
        f"{title} solution stack overflow",
    ]
    # Add label-specific searches
    for label in labels[:2]:
        search_queries.append(f"{label} {title} tutorial")

    all_results = []
    for i, q in enumerate(search_queries):
        log.info("  Search %d/%d: '%s'", i + 1, len(search_queries), q)
        results = search_web(q, num_results=5)
        all_results.extend(results)

    # Step 3: Fetch top pages
    log.info("Step 3: Fetching reference pages...")
    page_contents = []
    fetched = set()
    for r in all_results[:4]:
        url = r.get("url", "")
        if url and url not in fetched:
            fetched.add(url)
            content = fetch_page(url, max_chars=4000)
            page_contents.append({"url": url, "content": content})

    # Step 4: LLM analysis
    log.info("Step 4: Generating fresh approach with LLM...")
    context = (
        f"## Failed Ticket\nTitle: {title}\nDescription: {description}\nLabels: {labels}\n\n"
        f"## Error History (from comments)\n{error_history}\n\n"
        f"## Search Results\n"
    )
    for r in all_results:
        context += f"- {r.get('title', '')} | {r.get('url', '')}\n"
    context += "\n## Reference Pages\n"
    for p in page_contents:
        context += f"\n### {p['url']}\n{p['content'][:2500]}\n"

    raw_response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=context,
        temperature=0.4,
        max_tokens=6000,
    )

    # Step 5: Parse and save
    log.info("Step 5: Saving fresh approach to Jira...")
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        approach = json.loads(cleaned)
    except json.JSONDecodeError:
        approach = {"raw_response": raw_response}

    # Add the fresh approach as a comment on the failed ticket
    comment = (
        f"*CB-008 UNSTUCK AGENT — FRESH APPROACH*\n\n"
        f"*Root Cause:* {approach.get('root_cause_analysis', {}).get('root_cause', 'Unknown')}\n\n"
        f"*Strategy:* {approach.get('fresh_approach', {}).get('strategy', 'See details')}\n\n"
        f"*Full Analysis:*\n```json\n{json.dumps(approach, indent=2)}\n```"
    )
    jira_client.add_comment(failed_ticket_key, comment)

    log.info("=" * 60)
    log.info("CB-008 Unstuck Agent — COMPLETE")
    log.info("Confidence: %s", approach.get("confidence", "unknown"))
    log.info("=" * 60)

    return {"approach": approach, "ticket_key": failed_ticket_key}
