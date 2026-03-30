import sys
from duckduckgo_search import DDGS
import json
import time

queries = [
    "AI presentation maker market size report",
    "Templafy vs UpSlide PowerPoint brand consistency tool review",
    "Microsoft 365 Copilot PowerPoint limitations brand enforcement",
    "Beautiful.ai Gamma Tome enterprise branding templates",
    "Digital marketing agency time wasted formatting presentations",
    "Google Vertex AI Gemini 1.5 Pro multimodal image analysis presentation",
    "Automating PPTX brand transformation AI",
    "Enterprise document automation market growth B2B",
    "python-pptx enterprise layout manipulation limitations",
    "PowerPoint brand compliance checker tools"
]

results = {}
try:
    with DDGS() as ddgs:
        for q in queries:
            print(f"Searching: {q}")
            try:
                # Add slight delay to avoid rate limiting
                time.sleep(1)
                res = []
                for r in ddgs.text(q, max_results=3):
                    res.append(r)
                results[q] = res
            except Exception as e:
                print(f"Error on {q}: {e}")
                results[q] = str(e)
except Exception as e:
    print(f"Global error: {e}")

with open('search_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
print("Searches completed.")
