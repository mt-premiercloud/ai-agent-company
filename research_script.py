import sys
import subprocess
try:
    from duckduckgo_search import DDGS
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "duckduckgo-search"])
    from duckduckgo_search import DDGS

queries = [
    "python-pptx extract smartart constraints",
    "python-pptx extract copy charts keep original formatting",
    "convert pptx slide to image python headless",
    "Vertex AI Gemini 1.5 Pro multimodal image analysis limitations",
    "python-pptx preserve exact text formatting runs",
    "python-pptx handle text overflow dynamic sizing",
    "apply custom fonts python-pptx Proxima Nova",
    "match powerpoint layouts AI layout analysis",
    "python-pptx read template layouts placeholders shapes",
    "extract images from pptx python-pptx original resolution"
]

results_text = ""
with DDGS() as ddgs:
    for i, q in enumerate(queries):
        results_text += f"\n--- QUERY {i+1}: {q} ---\n"
        try:
            results = ddgs.text(q, max_results=3)
            for r in results:
                results_text += f"Title: {r.get('title')}\nSnippet: {r.get('body')}\n\n"
        except Exception as e:
            results_text += f"Error: {e}\n"

with open("research_results.txt", "w", encoding="utf-8") as f:
    f.write(results_text)
print("Research complete. Results saved to research_results.txt.")
