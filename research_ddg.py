import json
import requests
from bs4 import BeautifulSoup
import time

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

def ddg_search(query):
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for a in soup.find_all('a', class_='result__url', limit=4):
            href = a.get('href')
            if href.startswith('//duckduckgo.com/l/?'):
                # Extract actual URL, but for simplicity we can just keep the snippet text
                pass
                
        for result in soup.find_all('div', class_='result__body', limit=4):
            title_elem = result.find('a', class_='result__snippet')
            if title_elem:
                snippet = title_elem.text
                results.append(snippet)
    except Exception as e:
        print(f"Error on query {query}: {e}")
    return results

for i, q in enumerate(queries):
    print(f"Searching {i+1}/10: {q}")
    results_data[q] = ddg_search(q)
    time.sleep(1.5)

with open('research_results.json', 'w', encoding='utf-8') as f:
    json.dump(results_data, f, ensure_ascii=False, indent=2)

print("Done.")