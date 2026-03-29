import urllib.request
from bs4 import BeautifulSoup
import urllib.parse
import json

queries = [
    "python-pptx text auto fit overflow limitations",
    "Vertex AI Gemini 1.5 Pro multimodal capabilities JSON schema",
    "convert PPTX to image Python LibreOffice GCP",
    "GCP Cloud Run Jobs limits processing large files",
    "GCP Cloud Storage triggers Eventarc Cloud Run",
    "Cloud SQL PostgreSQL JSONB AI logging state tracking",
    "extract overlapping shapes python-pptx coordinates",
    "insert image placeholder python-pptx maintain aspect ratio",
    "Human-in-the-loop React UI slide preview components",
    "GCP Firestore vs Cloud SQL JSON state tracking AI jobs"
]

def search(q):
    print(f"\n--- Searching: {q} ---")
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req).read()
        soup = BeautifulSoup(html, 'html.parser')
        results = soup.find_all('a', class_='result__snippet')
        for r in results[:2]:
            print("-", r.text.strip())
    except Exception as e:
        print(f"Error: {e}")

for q in queries:
    search(q)
