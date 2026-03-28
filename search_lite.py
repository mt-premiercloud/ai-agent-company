import requests
from bs4 import BeautifulSoup
import time

queries = [
    "best freelancer task management SaaS",
    "freelance project management software Quebec",
    "Bonsai software pricing and weaknesses",
    "HoneyBook freelancer pricing cons",
    "ClickUp task management freelancer cons",
    "Todoist freelancer SaaS weaknesses",
    "Asana vs Monday freelancer SaaS Quebec",
    "freelancer SaaS task tracking GCP",
    "top 3 freelancer project management 2026",
    "task tracker SaaS independent contractors"
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for i, q in enumerate(queries):
    url = "https://lite.duckduckgo.com/lite/"
    data = {'q': q}
    try:
        res = requests.post(url, headers=headers, data=data)
        soup = BeautifulSoup(res.text, 'html.parser')
        print(f"\n[{i+1}/10] Query: {q}")
        results = soup.find_all('tr')
        count = 0
        for tr in results:
            td = tr.find('td', class_='result-snippet')
            if td:
                print("-", td.text.strip())
                count += 1
                if count >= 3:
                    break
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(1)
