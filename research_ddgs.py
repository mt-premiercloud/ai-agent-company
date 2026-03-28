from duckduckgo_search import DDGS
import json

queries = [
    "top accounting client portals Quebec",
    "portail client comptable Québec prix",
    "TaxDome pricing Canada",
    "Karbon accounting pricing",
    "Canopy tax pricing",
    "market gaps accounting firm portals",
    "accounting firm client demographics user persona Quebec",
    "Quebec Law 25 accounting data residency",
    "accounting client portal features pain points",
    "CPA firm secure document exchange Quebec"
]

results = {}

with DDGS() as ddgs:
    for q in queries:
        print(f"Searching: {q}")
        try:
            results[q] = list(ddgs.text(q, max_results=3))
        except Exception as e:
            print(f"Error for {q}: {e}")

with open('research_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Done.")