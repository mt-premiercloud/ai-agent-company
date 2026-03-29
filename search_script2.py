from ddgs import DDGS
import json

queries = [
    "Automated slide rebranding tools market",
    "AI presentation generators enterprise features",
    "Wpromote digital marketing agency presentation needs",
    "PowerPoint python-pptx competitors enterprise",
    "Slide processing API GCP alternatives",
    "AI PowerPoint formatting software",
    "Enterprise slide template management software",
    "Market size presentation software AI",
    "Automated PPTX translation and reformatting",
    "Human in the loop AI presentation design"
]

results = {}
with DDGS() as ddgs:
    for q in queries:
        try:
            res = list(ddgs.text(q, max_results=3))
            results[q] = res
        except Exception as e:
            results[q] = str(e)

with open("search_results.json", "w") as f:
    json.dump(results, f, indent=2)
