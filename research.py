from ddgs import DDGS
import json

queries = [
    "automated slide rebranding tool powerpoint agency",
    "powerpoint presentation brand enforcement AI software",
    "how to copy powerpoint charts python-pptx without corruption",
    "python-pptx map free floating shapes to placeholders",
    "GCP architecture processing parsing pptx files vertex AI",
    "Gemini Pro Vertex AI document classification target layout",
    "Slide presentation template management competitors",
    "extracting embedded excel from powerpoint chart python",
    "programmatically change powerpoint chart series colors python-pptx",
    "spatial analysis text boxes powerpoint heuristic algorithm"
]

results = {}
with DDGS() as ddgs:
    for q in queries:
        try:
            res = list(ddgs.text(q, max_results=3))
            results[q] = res
        except Exception as e:
            results[q] = str(e)

with open('research_results_ddg2.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
