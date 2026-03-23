"""Web search tool — used by research agents (CB-002, CB-003, CB-008).

Uses Gemini's built-in Google Search grounding via Vertex AI.
No extra API key needed — search is native to the google-genai SDK.
"""

from google import genai
from google.genai import types
from shared.config import GCP_PROJECT_ID, GCP_LOCATION, get_logger

log = get_logger("shared.web_search")

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    return _client


def search_web(query: str, num_results: int = 10) -> list[dict]:
    """Search the web using Gemini's Google Search grounding.

    Returns list of dicts with: title, url, snippet.
    Uses gemini-2.5-flash (fast/cheap) with Google Search tool.
    """
    log.info("Web search (grounded): '%s'", query)

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Search the web for: {query}\n\nReturn the top {num_results} most relevant results with title, URL, and a brief description for each.",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )

        # Extract grounding sources from metadata
        results = []
        seen_urls = set()

        if response.candidates and response.candidates[0].grounding_metadata:
            gm = response.candidates[0].grounding_metadata
            if gm.grounding_chunks:
                for chunk in gm.grounding_chunks:
                    if chunk.web and chunk.web.uri:
                        url = chunk.web.uri
                        if url not in seen_urls:
                            seen_urls.add(url)
                            results.append({
                                "title": chunk.web.title or "",
                                "url": url,
                                "snippet": "",
                            })

        # Also extract the LLM's synthesized text as context
        response_text = response.text or ""
        log.info("Search returned %d grounding sources, %d chars of analysis",
                 len(results), len(response_text))

        for i, r in enumerate(results[:num_results]):
            log.debug("Source %d: %s — %s", i + 1, r["title"], r["url"][:80])

        # Attach the LLM summary to the first result for agents to use
        if results:
            results[0]["snippet"] = response_text[:2000]
        elif response_text:
            # No grounding chunks but LLM gave a response — return as single result
            results.append({
                "title": f"Search summary: {query[:50]}",
                "url": "",
                "snippet": response_text[:2000],
            })

        return results[:num_results]

    except Exception as e:
        log.error("Grounded search failed: %s", e)
        return []


def search_and_summarize(query: str) -> str:
    """Search the web and return a grounded summary (text only).

    This is a simpler API for agents that just need research text,
    not structured results. The response is grounded in real web data.
    """
    log.info("Search & summarize: '%s'", query)

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
                max_output_tokens=4096,
            ),
        )
        result = response.text or ""
        log.info("Summary: %d chars", len(result))
        log.debug("Preview: %s...", result[:200])
        return result

    except Exception as e:
        log.error("Search & summarize failed: %s", e)
        return f"ERROR: Search failed for '{query}': {e}"


def fetch_page(url: str, max_chars: int = 15000) -> str:
    """Fetch a web page and return its text content (truncated)."""
    import httpx
    log.info("Fetching page: %s (max %d chars)", url, max_chars)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
        resp.raise_for_status()
        text = _strip_html(resp.text)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [truncated]"
        log.debug("Page fetched: %d chars", len(text))
        return text
    except Exception as e:
        log.error("Page fetch failed for %s: %s", url, e)
        return f"ERROR: Could not fetch {url}: {e}"


def _strip_html(html: str) -> str:
    """Rough HTML to text conversion."""
    import re
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
