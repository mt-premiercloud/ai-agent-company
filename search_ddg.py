import requests
from bs4 import BeautifulSoup
import time

def search_ddg(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        for a in soup.find_all('a', class_='result__url', limit=3):
            results.append(a.get('href'))
        for div in soup.find_all('div', class_='result__snippet', limit=3):
            results.append(div.text.strip())
        print(f"\\n--- Query: {query} ---")
        for r in results:
            print(r)
    except Exception as e:
        print(f"Error for {query}: {e}")

queries = [
    "top 3 freelancer task management SaaS Quebec",
    "freelancer task management software pricing",
    "Hello Bonsai key weaknesses cons",
    "HoneyBook freelancer key weaknesses cons",
    "ClickUp task management freelancer cons",
    "Todoist freelancer SaaS weaknesses",
    "Asana vs Monday freelancer SaaS Quebec",
    "freelancer SaaS task tracking GCP",
    "best freelancer project management Quebec 2026",
    "task tracker SaaS independent contractors"
]

for q in queries:
    search_ddg(q)
    time.sleep(1)
