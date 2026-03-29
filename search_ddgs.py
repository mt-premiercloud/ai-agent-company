from ddgs import DDGS
import json

queries = [
    "GCP Firestore Native mode limits and pricing 2024",
    "Cloud Run Go cold start performance optimization",
    "Firebase Auth vs Google Cloud Identity Platform",
    "Cloud Run to Firestore connection best practices",
    "GCP API Gateway vs Cloud Run direct REST API",
    "Cloud Build CI/CD pipeline for Cloud Run Go REST API",
    "GCP Secret Manager integration with Cloud Run",
    "GCP IAM least privilege Cloud Run to Firestore",
    "Cloud Logging and Cloud Trace Cloud Run Go",
    "REST API market trends Todo List applications enterprise"
]

results = {}
for q in queries:
    try:
        res = list(DDGS().text(q, max_results=3))
        results[q] = res
    except Exception as e:
        results[q] = str(e)

with open('search_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("Searches completed.")
