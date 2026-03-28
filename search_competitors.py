import sys
import subprocess

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])

try:
    from duckduckgo_search import DDGS
except ImportError:
    install('duckduckgo-search')
    from duckduckgo_search import DDGS

queries = [
    "best task management SaaS for freelancers",
    "top project management tools for independent contractors",
    "freelancer task management software Quebec",
    "Hello Bonsai pricing and weaknesses",
    "HoneyBook freelancer pricing cons",
    "ClickUp for freelancers reviews weaknesses",
    "Asana vs Todoist for solo freelancers",
    "freelance project management SaaS 2026",
    "task management tools with invoicing for freelancers",
    "best CRM and task tracker for Quebec freelancers"
]

try:
    ddgs = DDGS()
    for q in queries:
        print(f"\n--- Search: {q} ---")
        try:
            results = ddgs.text(q, max_results=3)
            for r in results:
                print(f"Title: {r['title']}")
                print(f"Snippet: {r['body']}")
        except Exception as e:
            print(f"Error for query {q}: {e}")
except Exception as main_e:
    print(f"Main Error: {main_e}")
