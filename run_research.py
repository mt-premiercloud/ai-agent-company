from shared.web_search import search_web, search_and_summarize
import time

queries = [
    "FastAPI generic exception handling security best practices GCP Cloud Run",
    "FastAPI secure error handling HTTP 401 prevent information leakage",
    "FastAPI limit parameter input validation DoS prevention",
    "Pydantic query parameter validation max value FastAPI",
    "Pydantic string length validation max_length FastAPI Cloud SQL",
    "FastAPI dependency injection Firebase Auth token validation",
    "Pydantic model for Firebase Auth decoded token FastAPI",
    "GCP Cloud Run FastAPI security best practices",
    "Cloud SQL SQLAlchemy connection pooling security FastAPI",
    "Firebase Admin SDK Python FastAPI secure token verification"
]

results = []
for q in queries:
    print(f"Searching: {q}")
    res = search_web(q, num_results=3)
    results.append({"query": q, "results": res})
    time.sleep(1)

import json
with open("research_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("Done")
