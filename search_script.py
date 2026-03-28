import json
from ddgs import DDGS

queries = [
    "freelancers self-employed statistics Montreal Quebec 2023 2024",
    "Quebec Law 25 SaaS data privacy compliance requirements",
    "Revenu Quebec GST QST API integration developers",
    "Stripe Tax automation Canada Quebec GST QST",
    "GCP Montreal region northamerica-northeast1 services availability",
    "Momenteo vs Freshbooks pricing features Canada",
    "Best GCP serverless architecture Next.js Cloud Run Cloud SQL",
    "React Next.js i18n bilingual localization best practices",
    "Firebase Auth vs Google Cloud Identity Platform multi-tenant SaaS",
    "GCP Cloud SQL PostgreSQL IAM serverless connection pooling"
]

results = {}
try:
    with DDGS() as ddgs:
        for q in queries:
            try:
                # `ddgs.text()` returns a generator
                res = list(ddgs.text(q, max_results=3))
                results[q] = [r.get("body", "") for r in res]
            except Exception as e:
                results[q] = []
except Exception as e:
    pass

with open("search_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
