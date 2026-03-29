import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

def search(query):
    print(f"\n--- Search: {query} ---")
    data = urllib.parse.urlencode({'q': query}).encode('utf-8')
    req = urllib.request.Request("https://lite.duckduckgo.com/lite/", data=data, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    html = urllib.request.urlopen(req).read()
    soup = BeautifulSoup(html, 'html.parser')
    for tr in soup.find_all('tr'):
        td = tr.find('td', class_='result-snippet')
        if td:
            print("-", td.text.strip())

queries = [
    "python-pptx limitations text overflow auto-fit",
    "GCP Vertex AI Gemini 1.5 Pro slide analysis PPTX",
    "Cloud Run memory limits maximum processing GKE",
    "python-pptx extract free shapes tables images",
    "Automated slide rebranding AI market tools",
    "GCP Cloud Run Jobs vs GKE for data processing",
    "PostgreSQL JSONB AI metadata tracking schema",
    "Mapping PowerPoint layouts semantic archetypes",
    "Converting PPTX to images Python multimodal",
    "Human in the loop QA UI architecture Google Cloud"
]

for q in queries:
    search(q)
