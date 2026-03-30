import urllib.request
import json
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            html = response.read().decode('utf-8')
            # Strip HTML tags for cleaner output if duckduckgo
            if "duckduckgo" in url:
                text = re.sub('<[^<]+>', ' ', html)
                text = re.sub('\s+', ' ', text)
                return text[:500]
            return html[:500]
    except Exception as e:
        return str(e)

urls = [
    "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json", # 1. eBird taxonomy
    "https://en.wikipedia.org/api/rest_v1/page/summary/Blue_jay", # 2. Wikipedia summary
    "https://xeno-canto.org/api/2/recordings?query=cyanocitta+cristata", # 3. Xeno-canto API
    "https://api.gbif.org/v1/species/match?name=Cyanocitta%20cristata", # 4. GBIF API
    "https://api.inaturalist.org/v1/taxa?q=mallard", # 5. iNaturalist API
    "https://html.duckduckgo.com/html/?q=Merlin+Bird+ID+API+pricing+open", # 6. Merlin API
    "https://html.duckduckgo.com/html/?q=IUCN+Red+List+API+documentation", # 7. IUCN API Docs
    "https://html.duckduckgo.com/html/?q=open+source+bird+species+database+encyclopedia+diet+habitat", # 8. Open bird encyclopedias
    "https://html.duckduckgo.com/html/?q=Google+Cloud+Vertex+AI+Gemini+multimodal+json+schema+vision", # 9. Vertex AI multimodal
    "https://html.duckduckgo.com/html/?q=Wikipedia+API+parse+infobox+conservation+status+bird" # 10. Wikipedia infobox extraction
]

for i, url in enumerate(urls, 1):
    print(f"--- Search {i} ---")
    print(f"URL: {url}")
    res = fetch(url)
    print(f"Result: {res.strip()[:250]}...\n")
