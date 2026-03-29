from ddgs import DDGS
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
        try:
            print(f"\n--- Query: {q} ---")
            for r in ddgs.text(q, max_results=2):
                print(f"- {r['title']}")
        except Exception as e:
            print(f"Error: {e}")
