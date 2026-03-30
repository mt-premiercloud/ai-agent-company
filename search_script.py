import sys
import time
from duckduckgo_search import DDGS

queries = [
    "ornithologist jobs Quebec OR ornithologie emploi Québec",
    "environmental researcher jobs UQAM Laval McGill",
    "NSERC research grants environmental science job postings",
    "Quebec government wildlife agency jobs MFFP MELCC",
    "academic job portals Quebec universities",
    "Applicant tracking systems ATS used by Universite Laval UQAM McGill",
    "GCP Vertex AI Gemini 3.1 Pro document processing limits",
    "GCP AlloyDB Vector Search pgvector best practices",
    "parsing academic CVs publications python tools",
    "Google Custom Search API Programmable Search limits for job scraping"
]

def search():
    with DDGS() as ddgs:
        for q in queries:
            print(f"\n--- Query: {q} ---")
            try:
                results = ddgs.text(q, max_results=3)
                for r in results:
                    print(f"- {r['title']}: {r['body']}")
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    search()
