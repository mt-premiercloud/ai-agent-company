import json
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import time

queries = [
    "top accounting firm client portals Canada Quebec",
    "portail client pour cabinet comptable Québec prix",
    "TaxDome vs Karbon vs Canopy pricing Canada accountant",
    "secure document portal accounting market gaps Quebec",
    "Quebec CPA firm client demographics user persona",
    "Quebec Law 25 accounting data residency client portal",
    "accounting client portal complaints pain points",
    "best software for accountants Quebec",
    "Canadian accounting software pricing portal",
    "GCP hosting for accounting portal Quebec"
]

results_data = {}

def get_snippets(query):
    results = []
    try:
        urls = list(search(query, num_results=3, lang='en'))
        for url in urls:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                res = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(res.text, 'html.parser')
                title = soup.title.string if soup.title else url
                paragraphs = soup.find_all('p')
                text = " ".join([p.text.strip() for p in paragraphs[:2]])
                results.append({"title": title, "url": url, "snippet": text[:300]})
            except Exception as e:
                pass
    except Exception as e:
        print(f"Error on query {query}: {e}")
    return results

for i, q in enumerate(queries):
    print(f"Searching {i+1}/10: {q}")
    results_data[q] = get_snippets(q)
    time.sleep(1)

with open('research_results3.json', 'w', encoding='utf-8') as f:
    json.dump(results_data, f, ensure_ascii=False, indent=2)

print("Done. Saved to research_results3.json")
