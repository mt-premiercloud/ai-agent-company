import json
from duckduckgo_search import DDGS

queries = [
    "enterprise powerpoint rebranding automation tools",
    "Templafy vs UpSlide powerpoint formatting",
    "python-pptx complex shapes smartart extraction",
    "GCP Vertex AI multimodal presentation analysis",
    "PowerPoint Open XML changing brand colors programmatically",
    "GCP Cloud Run processing large PPTX files",
    "AI powerpoint slide layout matching algorithms",
    "python library for preserving powerpoint charts XML",
    "GCP Document AI powerpoint pptx parsing limitations",
    "converting powerpoint to images headless linux python"
]

results = {}
try:
    with DDGS() as ddgs:
        for q in queries:
            try:
                res = list(ddgs.text(q, max_results=3))
                results[q] = res
            except Exception as e:
                results[q] = str(e)
except Exception as e:
    results["error"] = str(e)

with open("research_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("Research complete")
