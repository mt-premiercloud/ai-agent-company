from duckduckgo_search import DDGS
import json
import time

queries = [
    "top accounting firm client portals Canada Quebec",
    "portail client pour cabinet comptable Québec prix",
    "TaxDome vs Karbon vs Canopy pricing Canada accountant",
    "TaxDome pricing Canada",
    "Karbon accounting pricing",
    "Canopy tax pricing",
    "secure document portal accounting market gaps",
    "Quebec CPA firm client demographics user persona",
    "Quebec Law 25 accounting data residency client portal",
    "accounting client portal complaints pain points"
]

results = {}

with DDGS() as ddgs:
    for q in queries:
        print(f"Searching: {q}")
        try:
            # use region 'ca-en' or 'ca-fr'
            results[q] = list(ddgs.text(q, region='ca-en', max_results=4))
        except Exception as e:
            print(f"Error for {q}: {e}")
        time.sleep(1)

with open('research_results2.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Done.")