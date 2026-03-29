import json
from duckduckgo_search import DDGS

queries = [
    "python-pptx text auto fit overflow limitations bounds",
    "Vertex AI Gemini 1.5 Pro multimodal capabilities JSON schema PPTX",
    "convert PPTX to image Python LibreOffice GCP Cloud Run",
    "GCP Cloud Run Jobs limits processing large files",
    "GCP Cloud Storage triggers Eventarc Cloud Run pipeline",
    "Cloud SQL PostgreSQL JSONB AI logging state tracking",
    "extract overlapping shapes python-pptx coordinates",
    "insert image placeholder python-pptx maintain aspect ratio",
    "Human-in-the-loop React UI slide preview components",
    "GCP Firestore vs Cloud SQL JSON state tracking AI jobs"
]

def search(q):
    print(f"\n--- Searching: {q} ---")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(q, max_results=3))
            for i, r in enumerate(results):
                print(f"[{i+1}] {r['title']}\n    {r['body'][:200]}...")
    except Exception as e:
        print(f"Error: {e}")

for q in queries:
    search(q)
