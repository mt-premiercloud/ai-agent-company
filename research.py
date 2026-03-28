import json
from googlesearch import search
import time
import requests
from bs4 import BeautifulSoup

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

results_data = {}

def get_snippets(query):
    results = []
    try:
        # get top 3 urls
        urls = list(search(query, num=3, stop=3, pause=2))
        for url in urls:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                res = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(res.text, 'html.parser')
                title = soup.title.string if soup.title else url
                # get some text content
                paragraphs = soup.find_all('p')
                text = " ".join([p.text.strip() for p in paragraphs[:3]])
                results.append({"title": title, "url": url, "snippet": text[:300]})
            except Exception as e:
                results.append({"title": url, "url": url, "snippet": str(e)})
    except Exception as e:
        print(f"Error on query {query}: {e}")
    return results

for i, q in enumerate(queries):
    print(f"Searching {i+1}/10: {q}")
    results_data[q] = get_snippets(q)
    time.sleep(1)

with open('research_results.json', 'w', encoding='utf-8') as f:
    json.dump(results_data, f, ensure_ascii=False, indent=2)

print("Done. Saved to research_results.json")
