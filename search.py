from duckduckgo_search import DDGS

queries = [
    "python-pptx copy complex shapes charts xml",
    "python-pptx copy slide apply new layout",
    "Vertex AI Gemini 1.5 Pro multimodal python example",
    "GCP Vertex AI global region limitations",
    "win32com.client powerpoint export shape as image",
    "python-pptx identify placeholder types",
    "python-pptx handle text overflow layout",
    "enterprise powerpoint automation python",
    "GCP Windows Server Compute Engine powerpoint automation",
    "python-pptx read smartart objects"
]

with DDGS() as ddgs:
    for q in queries:
        print(f"\n--- Query: {q} ---")
        results = ddgs.text(q, max_results=2)
        for r in results:
            print(f"- {r['title']}: {r['body']}")
