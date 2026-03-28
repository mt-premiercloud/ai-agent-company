import requests
from bs4 import BeautifulSoup

queries = [
    "Hello Bonsai pricing tiers 2026",
    "HoneyBook pricing tiers 2026",
    "ClickUp pricing tiers 2026"
]

headers = {'User-Agent': 'Mozilla/5.0'}

for q in queries:
    url = "https://lite.duckduckgo.com/lite/"
    data = {'q': q}
    try:
        res = requests.post(url, headers=headers, data=data)
        soup = BeautifulSoup(res.text, 'html.parser')
        print(f"\n--- {q} ---")
        for td in soup.find_all('td', class_='result-snippet', limit=3):
            print("-", td.text.strip())
    except Exception as e:
        print(f"Error: {e}")
