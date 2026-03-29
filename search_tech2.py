from googlesearch import search
import urllib.request
from bs4 import BeautifulSoup
import time

queries = [
    "site:stackoverflow.com python-pptx auto_size MSO_AUTO_SIZE text overflow",
    "Vertex AI Gemini multimodal schema extraction presentation",
    "site:cloud.google.com Cloud Run Jobs limits LibreOffice",
    "GCP Eventarc to Cloud Run pipeline architecture storage trigger",
    "Cloud SQL PostgreSQL JSONB AI job state tracking",
    "python-pptx get shape coordinates overlapping",
    "python-pptx insert image into placeholder crop aspect ratio",
    "React human in the loop UI presentation review",
    "GCP Cloud Run memory limit processing large PPTX files",
    "LibreOffice headless convert PPTX to PDF python GCP"
]

def search_q(q):
    print(f"\n--- Searching: {q} ---")
    try:
        results = list(search(q, num_results=2, advanced=True))
        for r in results:
            print(f"- {r.title} | {r.url}")
            print(f"  {r.description}")
        time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")

for q in queries:
    search_q(q)
