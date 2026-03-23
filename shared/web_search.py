"""Web search tool — used by research agents (CB-002, CB-003, CB-008).

Uses Google Custom Search API via the google-genai grounding feature,
or falls back to a simple httpx-based search.
"""

import httpx
from shared.config import get_logger

log = get_logger("shared.web_search")


def search_web(query: str, num_results: int = 10) -> list[dict]:
    """Search the web and return results.

    Returns list of dicts with: title, url, snippet.
    Uses Google search via httpx scraping as a simple approach.
    """
    log.info("Web search: '%s' (max %d results)", query, num_results)

    try:
        # Use Google's public search endpoint
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        params = {"q": query, "num": num_results}
        resp = httpx.get(
            "https://www.google.com/search",
            params=params,
            headers=headers,
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()

        # Basic extraction from search results HTML
        results = _parse_search_results(resp.text, num_results)
        log.info("Search returned %d results", len(results))
        for i, r in enumerate(results):
            log.debug("Result %d: %s — %s", i + 1, r.get("title", ""), r.get("url", ""))
        return results

    except Exception as e:
        log.error("Web search failed: %s", e)
        return []


def fetch_page(url: str, max_chars: int = 15000) -> str:
    """Fetch a web page and return its text content (truncated)."""
    log.info("Fetching page: %s (max %d chars)", url, max_chars)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
        resp.raise_for_status()

        # Strip HTML tags for a rough text extraction
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
    # Remove script/style blocks
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_search_results(html: str, max_results: int) -> list[dict]:
    """Extract search results from Google HTML (basic parsing)."""
    import re
    results = []

    # Find result blocks — Google wraps results in <div class="g"> or similar
    # This is a rough heuristic, not a production scraper
    # Look for links that look like search results
    pattern = r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>'
    matches = re.findall(pattern, html, re.DOTALL)

    seen_urls = set()
    for url, title_html in matches:
        # Skip Google's own links
        if "google.com" in url or "googleapis.com" in url:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = re.sub(r"<[^>]+>", "", title_html).strip()
        if title and len(title) > 5:
            results.append({"title": title, "url": url, "snippet": ""})
            if len(results) >= max_results:
                break

    return results
