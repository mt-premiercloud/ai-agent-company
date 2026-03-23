"""CB-002 — Market Research Agent

Deep market researcher. Investigates target market, sizes opportunity,
identifies competitors, finds gaps. Minimum 10 distinct searches.
Cross-references findings from multiple sources.
"""

import json
from shared.config import get_logger
from shared.llm_client import call_llm
from shared import jira_client
from shared.web_search import search_web, fetch_page

log = get_logger("CB-002.MarketResearch")

SYSTEM_PROMPT = """You are a senior market research analyst at a top consulting firm.

You receive a Project Blueprint and web search results. Your job is to produce a comprehensive market research report.

## Your Research Process:
1. ANALYZE the target market and industry
2. SIZE the market opportunity (TAM/SAM/SOM if possible)
3. IDENTIFY top 3-5 competitors with strengths and weaknesses
4. FIND market gaps and opportunities
5. DEFINE target user persona
6. HIGHLIGHT key findings that should influence the product

## Rules:
- NEVER produce a report from a single source
- Cross-reference findings from multiple search results
- Clearly flag when data is ESTIMATED vs CONFIRMED
- Prioritize: industry reports > government data > competitor sites > review sites > forums > articles
- Be specific with numbers when available

## Output Format (JSON):
{
    "market_overview": "Brief market description",
    "market_size": {
        "tam": "Total Addressable Market estimate",
        "sam": "Serviceable Addressable Market",
        "som": "Serviceable Obtainable Market",
        "data_quality": "estimated|confirmed|mixed"
    },
    "competitors": [
        {
            "name": "...",
            "url": "...",
            "strengths": ["..."],
            "weaknesses": ["..."],
            "pricing": "...",
            "market_position": "leader|challenger|niche"
        }
    ],
    "market_gaps": ["gap 1", "gap 2"],
    "target_user_persona": {
        "role": "...",
        "pain_points": ["..."],
        "current_solutions": ["..."],
        "willingness_to_pay": "..."
    },
    "key_findings": ["finding 1", "finding 2"],
    "recommendations": ["rec 1", "rec 2"],
    "sources": ["url1", "url2"]
}

Output valid JSON only.
"""


def run(ticket_key: str) -> dict:
    """Run market research for a project.

    Args:
        ticket_key: Jira ticket key containing the Project Blueprint.

    Returns:
        dict with research results and created ticket key.
    """
    log.info("=" * 60)
    log.info("CB-002 Market Research Agent — START")
    log.info("Ticket: %s", ticket_key)
    log.info("=" * 60)

    # Step 1: Read the blueprint from Jira
    log.info("Step 1: Reading Project Blueprint from Jira...")
    issue = jira_client.get_issue(ticket_key)
    blueprint_text = issue["fields"].get("description", "") or ""
    project_key = issue["fields"]["project"]["key"]
    log.debug("Blueprint loaded: %d chars from project %s", len(blueprint_text), project_key)

    # Step 2: Parse blueprint to understand what to research
    log.info("Step 2: Parsing blueprint for research targets...")
    try:
        blueprint = json.loads(blueprint_text)
    except (json.JSONDecodeError, TypeError):
        blueprint = {"raw": blueprint_text}

    project_name = blueprint.get("project_name", "the project")
    target_users = blueprint.get("target_users", "")
    problem = blueprint.get("problem_solved", "")
    project_type = blueprint.get("project_type", "")

    # Step 3: Conduct web searches (minimum 10 as per spec)
    log.info("Step 3: Conducting web searches (10+ queries)...")
    search_queries = [
        f"{project_name} market size {project_type}",
        f"{project_name} competitors",
        f"{target_users} software solutions market",
        f"{problem} industry report",
        f"{project_name} {project_type} market trends 2026",
        f"top {project_type} companies {target_users}",
        f"{target_users} pain points software",
        f"{project_type} market growth forecast",
        f"{project_name} alternative solutions",
        f"{target_users} willingness to pay {project_type}",
    ]

    all_search_results = []
    for i, query in enumerate(search_queries):
        log.info("  Search %d/10: '%s'", i + 1, query)
        results = search_web(query, num_results=5)
        all_search_results.extend(results)
        log.debug("  Got %d results", len(results))

    # Step 4: Fetch top pages for deeper context
    log.info("Step 4: Fetching top pages for deeper analysis...")
    page_contents = []
    fetched_urls = set()
    for result in all_search_results[:5]:  # Fetch top 5 unique pages
        url = result.get("url", "")
        if url and url not in fetched_urls:
            fetched_urls.add(url)
            log.info("  Fetching: %s", url)
            content = fetch_page(url, max_chars=5000)
            page_contents.append({"url": url, "content": content})

    # Step 5: Call LLM with all research data
    log.info("Step 5: Analyzing research data with LLM...")
    research_data = (
        f"## Project Blueprint\n{json.dumps(blueprint, indent=2)}\n\n"
        f"## Search Results ({len(all_search_results)} results from {len(search_queries)} searches)\n"
    )
    for r in all_search_results:
        research_data += f"- {r.get('title', '')} | {r.get('url', '')} | {r.get('snippet', '')}\n"

    research_data += f"\n## Fetched Page Contents ({len(page_contents)} pages)\n"
    for p in page_contents:
        research_data += f"\n### {p['url']}\n{p['content'][:3000]}\n"

    raw_response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=research_data,
        temperature=0.5,
        max_tokens=6000,
    )

    # Step 6: Parse and save to Jira
    log.info("Step 6: Saving research to Jira...")
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        research = json.loads(cleaned)
    except json.JSONDecodeError:
        research = {"raw_response": raw_response}
        log.warning("Could not parse research as JSON, saving raw")

    research_ticket = jira_client.create_issue(
        project_key=project_key,
        summary="Market Research Report",
        description=json.dumps(research, indent=2),
        issue_type="Task",
        labels=["research", "market-research", "planning"],
    )
    research_key = research_ticket.get("key", "")
    log.info("Research ticket created: %s", research_key)

    # Add a summary comment to the blueprint ticket
    summary_comment = (
        f"*CB-002 Market Research Complete*\n\n"
        f"Research ticket: {research_key}\n"
        f"Searches conducted: {len(search_queries)}\n"
        f"Competitors found: {len(research.get('competitors', []))}\n"
        f"Key findings: {len(research.get('key_findings', []))}\n"
    )
    jira_client.add_comment(ticket_key, summary_comment)

    log.info("=" * 60)
    log.info("CB-002 Market Research Agent — COMPLETE")
    log.info("=" * 60)

    return {"research": research, "research_ticket_key": research_key}
