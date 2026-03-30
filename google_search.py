from googlesearch import search
import time

queries = [
    "ornithologist jobs Quebec OR ornithologie emploi Québec",
    "environmental researcher jobs UQAM Laval McGill",
    "academic job portals Quebec universities ATS",
    "GCP Vertex AI Gemini Pro document parsing limits",
    "GCP AlloyDB Vector Search pgvector best practices",
    "parsing academic CVs publications python tools",
    "Google Custom Search API Programmable Search limits for job scraping",
    "NSERC research grants environmental science jobs",
    "Quebec government wildlife agency jobs",
    "Quebec environmental NGOs job boards"
]

for q in queries:
    print(f"\n--- Query: {q} ---")
    try:
        results = search(q, num_results=3, advanced=True)
        for r in results:
            print(f"- {r.title}: {r.description}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(3)
