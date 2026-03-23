"""CB-003 — Technology Research Agent

Senior technical consultant. Researches technologies relevant to the project.
Strict priority: 1) Official docs, 2) GitHub repos, 3) Stack Overflow, 4) Blog posts.
NEVER recommends tech based on a blog post alone.
"""

import json
from shared.config import get_logger
from shared.llm_client import call_llm
from shared import jira_client
from shared.web_search import search_web, fetch_page

log = get_logger("CB-003.TechResearch")

SYSTEM_PROMPT = """You are a senior technical consultant researching technologies for a software project.

You receive a Project Blueprint, Market Research, and web search results about relevant technologies.

## Rules:
- Follow strict priority: 1) Official documentation 2) GitHub repos with real code 3) Stack Overflow verified answers 4) Blog posts
- NEVER recommend a technology based on a blog post alone
- For EVERY recommendation include: official docs link, current stable version, at least one limitation, a GitHub example
- If you can't find all four, flag it as "unverified"

## Output Format (JSON):
{
    "recommended_stack": {
        "frontend": {"name": "...", "version": "...", "docs_url": "...", "github_example": "...", "limitations": ["..."], "rationale": "...", "verified": true},
        "backend": {"name": "...", "version": "...", "docs_url": "...", "github_example": "...", "limitations": ["..."], "rationale": "...", "verified": true},
        "database": {"name": "...", "version": "...", "docs_url": "...", "github_example": "...", "limitations": ["..."], "rationale": "...", "verified": true},
        "hosting": {"name": "...", "rationale": "..."},
        "auth": {"name": "...", "rationale": "..."},
        "other": [{"name": "...", "purpose": "...", "rationale": "..."}]
    },
    "rejected_alternatives": [
        {"name": "...", "reason": "..."}
    ],
    "integration_technologies": [
        {"name": "...", "purpose": "...", "docs_url": "...", "complexity": "low|medium|high"}
    ],
    "technical_risks": ["risk 1", "risk 2"],
    "prerequisites": ["what's needed before building"],
    "sources": ["url1", "url2"]
}

Output valid JSON only.
"""


def run(blueprint_ticket_key: str, market_research_ticket_key: str = None) -> dict:
    """Run technology research.

    Args:
        blueprint_ticket_key: Jira ticket with Project Blueprint.
        market_research_ticket_key: Optional Jira ticket with market research.

    Returns:
        dict with tech recommendations and created ticket key.
    """
    log.info("=" * 60)
    log.info("CB-003 Technology Research Agent — START")
    log.info("Blueprint: %s | Market Research: %s", blueprint_ticket_key, market_research_ticket_key)
    log.info("=" * 60)

    # Step 1: Read inputs from Jira
    log.info("Step 1: Reading inputs from Jira...")
    bp_issue = jira_client.get_issue(blueprint_ticket_key)
    blueprint_text = bp_issue["fields"].get("description", "") or ""
    project_key = bp_issue["fields"]["project"]["key"]

    market_text = ""
    if market_research_ticket_key:
        mr_issue = jira_client.get_issue(market_research_ticket_key)
        market_text = mr_issue["fields"].get("description", "") or ""

    try:
        blueprint = json.loads(blueprint_text)
    except (json.JSONDecodeError, TypeError):
        blueprint = {"raw": blueprint_text}

    # Step 2: Generate search queries based on project needs
    log.info("Step 2: Generating technology search queries...")
    features = blueprint.get("key_features", [])
    tech_reqs = blueprint.get("technical_requirements", [])
    integrations = blueprint.get("integrations_needed", [])
    project_type = blueprint.get("project_type", "web app")

    search_queries = [
        f"best {project_type} tech stack 2026",
        f"best framework for {project_type} official documentation",
        f"{project_type} production ready framework comparison",
    ]
    # Add feature-specific searches
    for feat in features[:3]:
        search_queries.append(f"{feat} library framework official docs")
    for req in tech_reqs[:3]:
        search_queries.append(f"{req} implementation github example")
    for integ in integrations[:2]:
        search_queries.append(f"{integ} API official documentation SDK")

    # Pad to at least 10 searches
    while len(search_queries) < 10:
        search_queries.append(f"{project_type} best practices architecture 2026")

    # Step 3: Execute searches
    log.info("Step 3: Conducting %d web searches...", len(search_queries))
    all_results = []
    for i, query in enumerate(search_queries[:12]):
        log.info("  Search %d/%d: '%s'", i + 1, len(search_queries), query)
        results = search_web(query, num_results=5)
        all_results.extend(results)

    # Step 4: Fetch official doc pages
    log.info("Step 4: Fetching top pages (prioritizing official docs)...")
    page_contents = []
    fetched = set()
    for r in all_results[:8]:
        url = r.get("url", "")
        if url and url not in fetched:
            fetched.add(url)
            log.info("  Fetching: %s", url)
            content = fetch_page(url, max_chars=4000)
            page_contents.append({"url": url, "content": content})

    # Step 5: LLM analysis
    log.info("Step 5: Analyzing with LLM...")
    context = (
        f"## Project Blueprint\n{json.dumps(blueprint, indent=2)}\n\n"
        f"## Market Research\n{market_text[:3000]}\n\n"
        f"## Search Results ({len(all_results)} results)\n"
    )
    for r in all_results:
        context += f"- {r.get('title', '')} | {r.get('url', '')}\n"
    context += f"\n## Fetched Pages ({len(page_contents)} pages)\n"
    for p in page_contents:
        context += f"\n### {p['url']}\n{p['content'][:2500]}\n"

    raw_response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=context,
        temperature=0.4,
        max_tokens=6000,
    )

    # Step 6: Parse and save to Jira
    log.info("Step 6: Saving to Jira...")
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        tech_research = json.loads(cleaned)
    except json.JSONDecodeError:
        tech_research = {"raw_response": raw_response}
        log.warning("Could not parse tech research as JSON")

    ticket = jira_client.create_issue(
        project_key=project_key,
        summary="Technology Research Report",
        description=json.dumps(tech_research, indent=2),
        issue_type="Task",
        labels=["research", "tech-research", "planning"],
    )
    ticket_key = ticket.get("key", "")

    jira_client.add_comment(blueprint_ticket_key,
                            f"*CB-003 Tech Research Complete* — See {ticket_key}")

    log.info("=" * 60)
    log.info("CB-003 Technology Research — COMPLETE: %s", ticket_key)
    log.info("=" * 60)

    return {"tech_research": tech_research, "tech_research_ticket_key": ticket_key}
